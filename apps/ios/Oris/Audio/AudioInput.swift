import AVFAudio
import Foundation

enum AudioInputEvent: Sendable {
    case samples([Float], sampleRate: Double)
    /// Appel, Siri, alarme… : le système a coupé l'audio.
    case interruptionBegan
    case interruptionEnded
    /// Entrée audio ajoutée ou retirée (AirPods, micro filaire).
    case routeChanged
    /// La capture s'est arrêtée d'elle-même (services média réinitialisés, entrée disparue).
    case stopped
}

enum CaptureFailure: String, Error, Sendable {
    case permissionDenied = "permission_denied"
    case noMicrophone = "no_microphone"
    case captureFailed = "capture_failed"
}

enum MicrophonePermission: Sendable {
    case granted, denied, undetermined
}

@MainActor
protocol AudioInput: AnyObject {
    /// Démarre et renvoie le flux d'événements ; lève `CaptureFailure`.
    func start() async throws -> AsyncStream<AudioInputEvent>
    func stop()
}

/// Micro réel : AVAudioSession + AVAudioEngine.
@MainActor
final class MicrophoneInput: AudioInput {
    private let engine = AVAudioEngine()
    private var continuation: AsyncStream<AudioInputEvent>.Continuation?
    private var observers: [NSObjectProtocol] = []

    static var permission: MicrophonePermission {
        switch AVAudioApplication.shared.recordPermission {
        case .granted: .granted
        case .denied: .denied
        default: .undetermined
        }
    }

    func start() async throws -> AsyncStream<AudioInputEvent> {
        if Self.permission != .granted {
            guard await AVAudioApplication.requestRecordPermission() else {
                throw CaptureFailure.permissionDenied
            }
        }
        let session = AVAudioSession.sharedInstance()
        do {
            // Micro des AirPods autorisé ; capture poursuivie écran verrouillé (mode audio).
            // Mode « enregistrement » standard : `.spokenAudio` est fait pour *lire* de la
            // parole (livres audio), pas pour la capter.
            try session.setCategory(.playAndRecord, mode: .default, options: [.allowBluetoothHFP, .defaultToSpeaker])
            try session.setActive(true)
        } catch {
            throw CaptureFailure.captureFailed
        }
        guard session.isInputAvailable else { throw CaptureFailure.noMicrophone }

        let (stream, continuation) = AsyncStream.makeStream(of: AudioInputEvent.self)
        self.continuation = continuation
        observe(session: session, continuation: continuation)
        do {
            try installTapAndStart(continuation: continuation)
        } catch {
            stop()
            throw CaptureFailure.captureFailed
        }
        return stream
    }

    func stop() {
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        observers.forEach { NotificationCenter.default.removeObserver($0) }
        observers.removeAll()
        continuation?.finish()
        continuation = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    private func installTapAndStart(continuation: AsyncStream<AudioInputEvent>.Continuation) throws {
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        guard format.sampleRate > 0, format.channelCount > 0 else { throw CaptureFailure.noMicrophone }
        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 4096, format: format, block: Self.tapBlock(continuation))
        engine.prepare()
        try engine.start()
    }

    /// Bloc exécuté sur le fil audio temps réel : aucune isolation acteur, copie puis transmission.
    private nonisolated static func tapBlock(
        _ continuation: AsyncStream<AudioInputEvent>.Continuation
    ) -> AVAudioNodeTapBlock {
        { buffer, _ in
            guard let channel = buffer.floatChannelData?[0] else { return }
            let samples = Array(UnsafeBufferPointer(start: channel, count: Int(buffer.frameLength)))
            continuation.yield(.samples(samples, sampleRate: buffer.format.sampleRate))
        }
    }

    private func observe(session: AVAudioSession, continuation: AsyncStream<AudioInputEvent>.Continuation) {
        let center = NotificationCenter.default
        observers.append(center.addObserver(forName: AVAudioSession.interruptionNotification, object: session, queue: nil) { notification in
            let raw = notification.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt
            switch raw.flatMap(AVAudioSession.InterruptionType.init(rawValue:)) {
            case .began: continuation.yield(.interruptionBegan)
            case .ended: continuation.yield(.interruptionEnded)
            default: break
            }
        })
        observers.append(center.addObserver(forName: AVAudioSession.routeChangeNotification, object: session, queue: nil) { notification in
            let raw = notification.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt
            switch raw.flatMap(AVAudioSession.RouteChangeReason.init(rawValue:)) {
            case .oldDeviceUnavailable, .newDeviceAvailable: continuation.yield(.routeChanged)
            default: break
            }
        })
        observers.append(center.addObserver(forName: AVAudioSession.mediaServicesWereResetNotification, object: session, queue: nil) { _ in
            continuation.yield(.stopped)
        })
    }
}

/// Son de test sans micro (simulateur, développement) : 220 Hz faible, par blocs de 100 ms.
@MainActor
final class TestToneInput: AudioInput {
    private var task: Task<Void, Never>?

    func start() async throws -> AsyncStream<AudioInputEvent> {
        let (stream, continuation) = AsyncStream.makeStream(of: AudioInputEvent.self)
        task = Task.detached {
            var phase: Float = 0
            let step = 2 * Float.pi * 220 / 16_000
            while !Task.isCancelled {
                var block = [Float](repeating: 0, count: 1_600)
                for index in block.indices {
                    block[index] = 0.05 * sin(phase)
                    phase += step
                }
                continuation.yield(.samples(block, sampleRate: 16_000))
                try? await Task.sleep(for: .milliseconds(100))
            }
            continuation.finish()
        }
        return stream
    }

    func stop() {
        task?.cancel()
        task = nil
    }
}
