import Foundation
import Observation

enum CapturePhase: String, Sendable, Equatable {
    case ready
    case starting
    case recording
    case paused
    /// Appel, Siri… : suspendu par le système ; reprise explicite uniquement.
    case interrupted
    case microphoneLost
    case finishing
    case finished
    case error
}

enum FinishOutcome: Sendable, Equatable {
    case finished
    case chunksMissing([String])
}

protocol CaptureAPI: Sendable {
    func start(patientInformed: Bool) async throws
    func finish(finalSequence: Int, recordedMs: Int, acceptGaps: Bool) async throws -> FinishOutcome
}

struct CaptureLimits: Sendable {
    var maxSessionMs: Int = 90 * 60_000
    var warnSessionMs: Int = 80 * 60_000
    /// Au-delà, un changement d'entrée audio est signalé comme trou.
    var routeChangeToleranceMs: Int = 1_000
}

/// Pilotage d'une écoute iPhone : entrée audio → segments chiffrés → file d'envoi.
///
/// L'état est toujours explicite (spec §11, §65) ; aucune interruption n'est masquée :
/// appel, micro perdu, changement d'écouteurs trop long ou app fermée deviennent un
/// trou signalé, donc une alerte critique dans le dossier.
@MainActor
@Observable
final class CaptureController {
    private(set) var phase: CapturePhase = .ready
    private(set) var errorCode: String?
    private(set) var recordedMs = 0
    private(set) var level: Double = 0
    private(set) var reconnecting = false
    private(set) var pendingUploads = 0
    private(set) var lostUploads = 0
    private(set) var warnDurationReached = false
    private(set) var maxDurationReached = false
    /// Le micro ne capte rien depuis plusieurs secondes : on le dit tout de suite, au lieu
    /// de le découvrir à la fin (« transcription impossible »).
    private(set) var microMuet = false
    private var dernierSon: Date?
    private var debutEcoute: Date?

    let uploader: Uploader
    private let api: any CaptureAPI
    private let makeInput: @MainActor () -> any AudioInput
    private let limits: CaptureLimits
    private let now: @MainActor () -> Date

    private var chunker: Chunker
    private var resampler: Resampler?
    private var input: (any AudioInput)?
    private var eventTask: Task<Void, Never>?
    private var interruptedAt: Date?
    private var microphoneLostAt: Date?
    private var routeChangedAt: Date?
    private var acceptGaps = false
    private var finishing: Task<FinishOutcome, Error>?

    init(
        api: any CaptureAPI,
        uploaderFactory: (@escaping @Sendable (UploadStatus) -> Void) -> Uploader,
        makeInput: @escaping @MainActor () -> any AudioInput,
        limits: CaptureLimits = CaptureLimits(),
        resumeFrom: (nextSequence: Int, nextTimestampMs: Int)? = nil,
        now: @escaping @MainActor () -> Date = { Date() }
    ) {
        self.api = api
        self.makeInput = makeInput
        self.limits = limits
        self.now = now
        self.chunker = Chunker(
            startSequence: resumeFrom?.nextSequence ?? 0,
            startTimestampMs: resumeFrom?.nextTimestampMs ?? 0
        )
        let relay = StatusRelay()
        self.uploader = uploaderFactory { status in
            Task { @MainActor in relay.controller?.apply(status) }
        }
        relay.controller = self
        recordedMs = chunker.recordedMs
    }

    // MARK: Actions du praticien

    /// Micro d'abord (autorisation), puis démarrage côté serveur.
    func start(patientInformed: Bool) async {
        guard phase == .ready || phase == .error else { return }
        phase = .starting
        errorCode = nil
        guard await openInput() else { return }
        do {
            try await api.start(patientInformed: patientInformed)
        } catch {
            closeInput()
            fail(code: (error as? APIError)?.code ?? "START_FAILED")
            return
        }
        phase = .recording
    }

    /// Réouverture après fermeture de l'app : segments du tampon renvoyés, trou signalé.
    func resumeAfterRelaunch(interruptionMs: Int?, wasPaused: Bool) async {
        _ = await uploader.restorePending()
        if !wasPaused {
            await uploader.enqueue(.gap(reason: .appTerminated, durationMs: interruptionMs))
        }
        phase = .starting
        guard await openInput() else { return }
        if wasPaused { await uploader.enqueue(.resume) }
        phase = .recording
    }

    func pause() async {
        guard phase == .recording else { return }
        await flushChunk()
        closeInput()
        await uploader.enqueue(.pause)
        phase = .paused
        level = 0
        // La pause n'est pas un silence : la surveillance repart à la reprise.
        debutEcoute = nil
        dernierSon = nil
        microMuet = false
    }

    func resume() async {
        let previous = phase
        guard [.paused, .interrupted, .microphoneLost].contains(previous), !maxDurationReached else { return }
        guard await openInput() else { return }
        switch previous {
        case .paused:
            await uploader.enqueue(.resume)
        case .interrupted:
            await reportGap(.audioInterruption)
        default:
            await reportGap(.microphoneLost)
        }
        phase = .recording
        errorCode = nil
    }

    /// Termine : vide la file puis clôt côté serveur. `acceptGaps` abandonne ce qui n'est pas parti.
    func finish(acceptGaps: Bool = false) async throws -> FinishOutcome {
        if acceptGaps {
            self.acceptGaps = true
            await uploader.abandon()
        }
        if let finishing { return try await finishing.value }
        let task = Task { try await self.completeFinish() }
        finishing = task
        defer { finishing = nil }
        return try await task.value
    }

    // MARK: Interne

    private func completeFinish() async throws -> FinishOutcome {
        if phase != .finishing {
            await flushChunk()
            closeInput()
            await reportGap(.audioInterruption)
            await reportGap(.microphoneLost)
            phase = .finishing
            level = 0
            errorCode = nil
        }
        await uploader.waitUntilDrained()
        let lost = await uploader.status.lost
        do {
            let outcome = try await api.finish(
                finalSequence: chunker.lastSequence,
                recordedMs: chunker.recordedMs,
                acceptGaps: acceptGaps || lost > 0
            )
            if outcome == .finished { phase = .finished }
            return outcome
        } catch {
            errorCode = (error as? APIError)?.code ?? "FINISH_FAILED"
            throw error
        }
    }

    private func openInput() async -> Bool {
        let input = makeInput()
        do {
            let stream = try await input.start()
            self.input = input
            resampler = nil
            eventTask?.cancel()
            eventTask = Task { [weak self] in
                for await event in stream {
                    await self?.handle(event)
                }
            }
            return true
        } catch {
            let code = (error as? CaptureFailure)?.rawValue ?? CaptureFailure.captureFailed.rawValue
            if phase == .starting {
                fail(code: code)
            } else {
                errorCode = code
            }
            return false
        }
    }

    private func closeInput() {
        eventTask?.cancel()
        eventTask = nil
        input?.stop()
        input = nil
    }

    func handle(_ event: AudioInputEvent) async {
        switch event {
        case .samples(let samples, let sampleRate):
            await receive(samples, sampleRate: sampleRate)
        case .interruptionBegan:
            guard phase == .recording else { return }
            await flushChunk()
            closeInput()
            interruptedAt = now()
            phase = .interrupted
            level = 0
        case .interruptionEnded:
            // Pas de reprise automatique : le praticien décide (écoute jamais relancée à son insu).
            break
        case .routeChanged:
            guard phase == .recording else { return }
            await flushChunk()
            closeInput()
            routeChangedAt = now()
            if !(await openInput()) {
                microphoneLostAt = routeChangedAt
                routeChangedAt = nil
                phase = .microphoneLost
            }
        case .stopped:
            guard phase == .recording else { return }
            await flushChunk()
            closeInput()
            microphoneLostAt = now()
            phase = .microphoneLost
            errorCode = "microphone_lost"
            level = 0
        }
    }

    private func receive(_ samples: [Float], sampleRate: Double) async {
        guard phase == .recording else { return }
        if let changed = routeChangedAt {
            let elapsed = Int(now().timeIntervalSince(changed) * 1000)
            routeChangedAt = nil
            if elapsed > limits.routeChangeToleranceMs {
                await uploader.enqueue(.gap(reason: .routeChange, durationMs: elapsed))
            }
        }
        if resampler?.inputRate != sampleRate {
            resampler = Resampler(inputRate: sampleRate)
        }
        let pcm = PCM.toInt16(resampler!.process(samples))
        for chunk in chunker.push(pcm) {
            await store(chunk)
        }
        recordedMs = chunker.recordedMs
        level = PCM.level(samples)
        surveillerLeSon(samples)
        if recordedMs >= limits.warnSessionMs { warnDurationReached = true }
        if recordedMs >= limits.maxSessionMs {
            // Durée maximale : pause automatique, rien n'est perdu (spec §12).
            maxDurationReached = true
            await pause()
        }
    }

    /// Au-dessous de ce niveau de crête (≈ -50 dBFS), le micro n'entend rien : même le
    /// souffle d'une pièce calme passe au-dessus.
    static let seuilSilence: Float = 0.003
    static let delaiMicroMuetMs = 6_000

    private func surveillerLeSon(_ samples: [Float]) {
        let instant = now()
        if debutEcoute == nil { debutEcoute = instant }
        let crete = samples.reduce(Float(0)) { max($0, abs($1)) }
        if crete >= Self.seuilSilence { dernierSon = instant }
        let depuis = dernierSon ?? debutEcoute ?? instant
        microMuet = instant.timeIntervalSince(depuis) * 1000 >= Double(Self.delaiMicroMuetMs)
        #if DEBUG
        // Diagnostic de la prise de son : un nombre, jamais le son.
        if Int(instant.timeIntervalSince1970 * 10) % 20 == 0 {
            print("oris.niveau crete=\(crete) taux=\(Int(resampler?.inputRate ?? 0))")
        }
        #endif
    }

    private func store(_ chunk: PcmChunk) async {
        do {
            try await uploader.enqueue(chunk: chunk)
        } catch {
            // Écriture locale impossible : segment perdu, jamais masqué.
            errorCode = "LOCAL_STORAGE_FAILED"
            await uploader.enqueue(.gap(reason: .captureError, durationMs: chunk.durationMs))
        }
    }

    private func flushChunk() async {
        if let chunk = chunker.flush() {
            await store(chunk)
        }
    }

    /// Signale la durée d'une interruption en cours (appel ou micro perdu) et la clôt.
    private func reportGap(_ reason: GapReason) async {
        let began: Date?
        switch reason {
        case .audioInterruption:
            began = interruptedAt
            interruptedAt = nil
        case .microphoneLost:
            began = microphoneLostAt
            microphoneLostAt = nil
        default:
            return
        }
        guard let began else { return }
        let duration = max(0, Int(now().timeIntervalSince(began) * 1000))
        await uploader.enqueue(.gap(reason: reason, durationMs: duration))
    }

    private func apply(_ status: UploadStatus) {
        reconnecting = status.retrying
        pendingUploads = status.pending
        lostUploads = status.lost
    }

    private func fail(code: String) {
        phase = .error
        errorCode = code
    }
}

/// Transmet l'état de la file d'envoi au contrôleur sans le retenir.
@MainActor
private final class StatusRelay {
    weak var controller: CaptureController?
}
