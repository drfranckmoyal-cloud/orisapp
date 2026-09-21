import Foundation
import XCTest

@testable import Oris

@MainActor
final class FakeInput: AudioInput {
    var failure: CaptureFailure?
    private(set) var continuation: AsyncStream<AudioInputEvent>.Continuation?
    private(set) var stopped = false

    init(failure: CaptureFailure? = nil) {
        self.failure = failure
    }

    func start() async throws -> AsyncStream<AudioInputEvent> {
        if let failure { throw failure }
        let (stream, continuation) = AsyncStream.makeStream(of: AudioInputEvent.self)
        self.continuation = continuation
        return stream
    }

    func stop() {
        stopped = true
        continuation?.finish()
    }

    func emit(seconds: Double) {
        continuation?.yield(.samples([Float](repeating: 0.1, count: Int(16_000 * seconds)), sampleRate: 16_000))
    }

    func emitSilence(seconds: Double) {
        continuation?.yield(.samples([Float](repeating: 0, count: Int(16_000 * seconds)), sampleRate: 16_000))
    }

    func emit(_ event: AudioInputEvent) {
        continuation?.yield(event)
    }
}

final class FakeCaptureAPI: CaptureAPI, @unchecked Sendable {
    private let lock = NSLock()
    private var _started: [Bool] = []
    private var _finishes: [[Int]] = []
    private var _acceptGaps: [Bool] = []

    var started: [Bool] { lock.withLock { _started } }
    var finishes: [[Int]] { lock.withLock { _finishes } }
    var acceptGaps: [Bool] { lock.withLock { _acceptGaps } }

    func start(patientInformed: Bool) async throws {
        lock.withLock { _started.append(patientInformed) }
    }

    func finish(finalSequence: Int, recordedMs: Int, acceptGaps: Bool) async throws -> FinishOutcome {
        lock.withLock {
            _finishes.append([finalSequence, recordedMs])
            _acceptGaps.append(acceptGaps)
        }
        return .finished
    }
}

@MainActor
final class CaptureControllerTests: XCTestCase {
    private var inputs: [FakeInput] = []
    private var clock = Date(timeIntervalSince1970: 1_000_000)
    private var transport = FakeTransport()
    private var api = FakeCaptureAPI()
    private var nextFailure: CaptureFailure?

    private func makeController(limits: CaptureLimits = CaptureLimits(), resumeFrom: (Int, Int)? = nil) -> CaptureController {
        let store = temporaryStore()
        let transport = transport
        return CaptureController(
            api: api,
            uploaderFactory: { onStatus in
                Uploader(encounterId: "enc", store: store, transport: transport, backoff: [.milliseconds(5)], onStatus: onStatus)
            },
            makeInput: { [unowned self] in
                let input = FakeInput(failure: self.nextFailure)
                self.inputs.append(input)
                return input
            },
            limits: limits,
            resumeFrom: resumeFrom.map { (nextSequence: $0.0, nextTimestampMs: $0.1) },
            now: { [unowned self] in self.clock }
        )
    }

    /// Attend qu'une condition soit vraie (travail asynchrone du contrôleur), 5 s maximum.
    private func waitUntil(_ condition: () -> Bool) async {
        for _ in 0..<500 where !condition() {
            try? await Task.sleep(for: .milliseconds(10))
        }
    }

    /// Laisse le contrôleur consommer les événements émis.
    private func settle() async {
        for _ in 0..<20 { await Task.yield() }
        try? await Task.sleep(for: .milliseconds(60))
    }

    private func sent() async -> [String] {
        await transport.sent.map { item in
            switch item {
            case .chunk(let sequence): "chunk\(sequence)"
            case .pause: "pause"
            case .resume: "resume"
            case .gap(let reason, let duration): "gap:\(reason.rawValue):\(duration.map(String.init) ?? "nil")"
            }
        }
    }

    func testRecordPauseResumeFinish() async throws {
        let controller = makeController()
        await controller.start(patientInformed: true)
        XCTAssertEqual(api.started, [true])
        XCTAssertEqual(controller.phase, .recording)

        inputs[0].emit(seconds: 3)
        await settle()
        XCTAssertEqual(controller.recordedMs, 3000)
        await controller.pause()
        XCTAssertEqual(controller.phase, .paused)
        XCTAssertTrue(inputs[0].stopped, "micro libéré pendant la pause")

        await controller.resume()
        inputs[1].emit(seconds: 2)
        await settle()
        let outcome = try await controller.finish()

        XCTAssertEqual(outcome, .finished)
        XCTAssertEqual(controller.phase, .finished)
        let items = await sent()
        XCTAssertEqual(items, ["chunk0", "chunk1", "pause", "resume", "chunk2"])
        XCTAssertEqual(api.finishes, [[2, 5000]])
        XCTAssertEqual(api.acceptGaps, [false])
    }

    /// Panne iPhone du 21/09 : un micro muet se voit pendant l'écoute, pas à la fin.
    func testAMuteMicrophoneIsFlaggedWhileListening() async {
        let controller = makeController()
        await controller.start(patientInformed: true)
        inputs[0].emitSilence(seconds: 1)
        await settle()
        XCTAssertFalse(controller.microMuet, "trop tôt pour conclure")
        clock += 7
        inputs[0].emitSilence(seconds: 1)
        await settle()
        XCTAssertTrue(controller.microMuet)
        inputs[0].emit(seconds: 1)
        await settle()
        XCTAssertFalse(controller.microMuet, "le bandeau disparaît dès que le micro entend")
    }

    func testDeniedMicrophoneDoesNotStartTheConsultation() async {
        nextFailure = .permissionDenied
        let controller = makeController()
        await controller.start(patientInformed: true)
        XCTAssertEqual(controller.phase, .error)
        XCTAssertEqual(controller.errorCode, "permission_denied")
        XCTAssertEqual(api.started, [])
    }

    func testPhoneCallIsNeverResumedSilentlyAndBecomesAGap() async throws {
        let controller = makeController()
        await controller.start(patientInformed: true)
        inputs[0].emit(seconds: 2)
        inputs[0].emit(.interruptionBegan)
        await settle()
        XCTAssertEqual(controller.phase, .interrupted)

        clock.addTimeInterval(45)
        inputs[0].emit(.interruptionEnded)
        await settle()
        XCTAssertEqual(controller.phase, .interrupted, "pas de reprise automatique")

        await controller.resume()
        XCTAssertEqual(controller.phase, .recording)
        _ = try await controller.finish()
        let items = await sent()
        XCTAssertEqual(items, ["chunk0", "gap:audio_interruption:45000"])
    }

    func testShortRouteChangeRestartsCaptureWithoutGap() async throws {
        let controller = makeController()
        await controller.start(patientInformed: true)
        inputs[0].emit(seconds: 2)
        inputs[0].emit(.routeChanged)
        await settle()
        XCTAssertEqual(inputs.count, 2, "capture relancée sur la nouvelle entrée")
        clock.addTimeInterval(0.3)
        inputs[1].emit(seconds: 2)
        await settle()
        _ = try await controller.finish()
        let items = await sent()
        XCTAssertEqual(items, ["chunk0", "chunk1"])
    }

    func testLongRouteChangeIsReportedAsGap() async throws {
        let controller = makeController()
        await controller.start(patientInformed: true)
        inputs[0].emit(seconds: 2)
        inputs[0].emit(.routeChanged)
        await settle()
        clock.addTimeInterval(4)
        inputs[1].emit(seconds: 2)
        await settle()
        _ = try await controller.finish()
        let items = await sent()
        XCTAssertEqual(items, ["chunk0", "gap:route_change:4000", "chunk1"])
    }

    func testLostMicrophoneReportedWhenFinishing() async throws {
        let controller = makeController()
        await controller.start(patientInformed: true)
        inputs[0].emit(seconds: 2)
        inputs[0].emit(.stopped)
        await settle()
        XCTAssertEqual(controller.phase, .microphoneLost)
        clock.addTimeInterval(10)
        _ = try await controller.finish()
        let items = await sent()
        XCTAssertEqual(items, ["chunk0", "gap:microphone_lost:10000"])
    }

    func testCaptureContinuesOfflineAndEverythingIsSentOnReturn() async throws {
        await transport.setOnline(false)
        let controller = makeController()
        await controller.start(patientInformed: true)
        inputs[0].emit(seconds: 6)
        await waitUntil { controller.pendingUploads == 3 && controller.reconnecting }
        XCTAssertEqual(controller.phase, .recording)
        XCTAssertTrue(controller.reconnecting)
        XCTAssertEqual(controller.pendingUploads, 3)

        await transport.setOnline(true)
        await controller.uploader.wake()
        _ = try await controller.finish()
        let items = await sent()
        XCTAssertEqual(items, ["chunk0", "chunk1", "chunk2"])
    }

    func testFinishAnywayDeclaresUnsentAudio() async throws {
        await transport.setOnline(false)
        let controller = makeController()
        await controller.start(patientInformed: true)
        inputs[0].emit(seconds: 4)
        await settle()
        let pending = Task { try await controller.finish() }
        await settle()
        XCTAssertEqual(controller.phase, .finishing)
        _ = try await controller.finish(acceptGaps: true)
        _ = try? await pending.value
        XCTAssertEqual(api.acceptGaps.last, true)
        XCTAssertEqual(api.finishes.last, [1, 4000])
    }

    func testMaximumDurationPausesAutomatically() async {
        let controller = makeController(limits: CaptureLimits(maxSessionMs: 60_000, warnSessionMs: 50_000))
        await controller.start(patientInformed: true)
        inputs[0].emit(seconds: 52)
        await waitUntil { controller.recordedMs >= 52_000 }
        XCTAssertTrue(controller.warnDurationReached)
        XCTAssertEqual(controller.phase, .recording)
        inputs[0].emit(seconds: 10)
        await waitUntil { controller.phase == .paused }
        XCTAssertEqual(controller.phase, .paused)
        XCTAssertTrue(controller.maxDurationReached)
        await controller.resume()
        XCTAssertEqual(controller.phase, .paused)
    }

    func testRelaunchReportsTheInterruptionAndContinuesNumbering() async throws {
        let controller = makeController(resumeFrom: (5, 10_000))
        await controller.resumeAfterRelaunch(interruptionMs: 30_000, wasPaused: false)
        XCTAssertEqual(controller.phase, .recording)
        XCTAssertEqual(controller.recordedMs, 10_000)
        inputs[0].emit(seconds: 2)
        await settle()
        _ = try await controller.finish()
        let items = await sent()
        XCTAssertEqual(items, ["gap:app_terminated:30000", "chunk5"])
        XCTAssertEqual(api.finishes, [[5, 12_000]])
    }
}
