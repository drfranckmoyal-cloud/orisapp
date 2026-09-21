import Foundation
import Network
import Observation

/// Assemble une écoute réelle : tampon chiffré, envoi HTTP, entrée audio choisie.
@MainActor
enum CaptureEnvironment {
    static func makeController(
        client: APIClient,
        encounterId: String,
        useTestTone: Bool,
        config: ClientConfig?,
        visitKind: VisitKind = .consultation,
        resumeFrom: (nextSequence: Int, nextTimestampMs: Int)? = nil
    ) throws -> CaptureController {
        let store = try ChunkStore.production()
        let transport = HTTPAudioTransport(baseURL: client.baseURL, encounterId: encounterId, transport: client.transport)
        var limits = CaptureLimits()
        if let config {
            limits.maxSessionMs = config.maxSessionMinutes * 60_000
            limits.warnSessionMs = config.warnSessionMinutes * 60_000
        }
        return CaptureController(
            api: APICaptureBridge(client: client, encounterId: encounterId, visitKind: visitKind),
            uploaderFactory: { onStatus in
                Uploader(encounterId: encounterId, store: store, transport: transport, onStatus: onStatus)
            },
            makeInput: { useTestTone ? TestToneInput() as any AudioInput : MicrophoneInput() },
            limits: limits,
            resumeFrom: resumeFrom
        )
    }

    /// Point de reprise : après le dernier segment reçu par le serveur ou resté dans le tampon.
    static func resumePoint(audio: AudioSessionState?, encounterId: String) -> (nextSequence: Int, nextTimestampMs: Int) {
        var next = (nextSequence: audio?.nextSequence ?? 0, nextTimestampMs: audio?.nextTimestampMs ?? 0)
        guard let store = try? ChunkStore.production() else { return next }
        for sequence in store.pendingSequences(encounterId: encounterId) where sequence >= next.nextSequence {
            if let chunk = try? store.load(encounterId: encounterId, sequence: sequence) {
                next = (sequence + 1, chunk.timestampMs + chunk.durationMs)
            }
        }
        return next
    }
}

/// État du réseau, affiché en permanence et utilisé pour relancer les envois sans attendre.
@MainActor
@Observable
final class NetworkMonitor {
    private(set) var isOnline = true
    private let monitor = NWPathMonitor()
    var onReconnect: (@MainActor () -> Void)?

    init() {
        monitor.pathUpdateHandler = { [weak self] path in
            let online = path.status == .satisfied
            Task { @MainActor in
                guard let self else { return }
                let wasOffline = !self.isOnline
                self.isOnline = online
                if online && wasOffline { self.onReconnect?() }
            }
        }
        monitor.start(queue: DispatchQueue(label: "fr.oris.network"))
    }

    deinit {
        monitor.cancel()
    }
}
