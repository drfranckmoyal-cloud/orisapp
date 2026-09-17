import CryptoKit
import Foundation
import XCTest

@testable import Oris

func temporaryStore(key: SymmetricKey = SymmetricKey(size: .bits256)) -> ChunkStore {
    let root = FileManager.default.temporaryDirectory.appending(path: "oris-tests-\(UUID().uuidString)")
    return ChunkStore(root: root, key: key)
}

final class PCMTests: XCTestCase {
    func testResamplerKeepsSampleCountAcrossBlocks() {
        var resampler = Resampler(inputRate: 48_000)
        var total = 0
        for _ in 0..<10 {
            total += resampler.process([Float](repeating: 0.5, count: 128)).count
        }
        XCTAssertEqual(total, 1280 / 3)
    }

    func testInt16ConversionIsClampedAndLittleEndian() {
        XCTAssertEqual(PCM.toInt16([1, -1, 2, 0]), [32767, -32768, 32767, 0])
        XCTAssertEqual([UInt8](PCM.bytes([1, -2])), [1, 0, 254, 255])
        XCTAssertEqual(PCM.samples(from: PCM.bytes([1, -2, 300])), [1, -2, 300])
    }

    func testChunkerTimestampsMatchTheServerContract() {
        var chunker = Chunker()
        let chunks = chunker.push([Int16](repeating: 0, count: 32_000 * 2 + 8_000))
        XCTAssertEqual(chunks.map { [$0.sequence, $0.timestampMs, $0.durationMs] }, [[0, 0, 2000], [1, 2000, 2000]])
        XCTAssertEqual(chunker.recordedMs, 4500)
        let partial = chunker.flush()
        XCTAssertEqual(partial.map { [$0.sequence, $0.timestampMs, $0.durationMs] }, [2, 4000, 500])
        XCTAssertNil(chunker.flush())
    }

    func testChunkerResumesNumbering() {
        var chunker = Chunker(startSequence: 7, startTimestampMs: 14_000)
        XCTAssertEqual(chunker.push([Int16](repeating: 0, count: 32_000)).first?.timestampMs, 14_000)
        XCTAssertEqual(chunker.lastSequence, 7)
    }
}

final class ChunkStoreTests: XCTestCase {
    private let chunk = PcmChunk(sequence: 3, timestampMs: 6000, durationMs: 2000, samples: (0..<32_000).map { Int16($0 % 1000) })

    func testChunkRoundTripsThroughEncryption() throws {
        let store = temporaryStore()
        try store.save(chunk, encounterId: "enc")
        XCTAssertEqual(try store.load(encounterId: "enc", sequence: 3), chunk)
        XCTAssertEqual(store.pendingSequences(encounterId: "enc"), [3])
        XCTAssertEqual(store.encountersWithPendingAudio(), ["enc"])
    }

    func testAudioIsNeverWrittenInClear() throws {
        let store = temporaryStore()
        try store.save(chunk, encounterId: "enc")
        let file = store.root.appending(path: "enc/00000003.chunk")
        let raw = try Data(contentsOf: file)
        XCTAssertNil(raw.range(of: chunk.data.prefix(64)), "le PCM ne doit pas apparaître en clair")
    }

    func testAnotherKeyCannotReadTheBuffer() throws {
        let store = temporaryStore()
        try store.save(chunk, encounterId: "enc")
        let intruder = ChunkStore(root: store.root, key: SymmetricKey(size: .bits256))
        XCTAssertThrowsError(try intruder.load(encounterId: "enc", sequence: 3))
    }

    func testDeletion() throws {
        let store = temporaryStore()
        try store.save(chunk, encounterId: "enc")
        store.delete(encounterId: "enc", sequence: 3)
        XCTAssertEqual(store.pendingSequences(encounterId: "enc"), [])
        try store.save(chunk, encounterId: "enc")
        store.deleteAll(encounterId: "enc")
        XCTAssertEqual(store.encountersWithPendingAudio(), [])
    }
}

/// Transport de test : enregistre ce qui part, simule panne réseau et refus.
actor FakeTransport: AudioTransporting {
    private(set) var sent: [UploadItem] = []
    var online = true
    var rejectSequences: Set<Int> = []

    func setOnline(_ value: Bool) { online = value }
    func reject(_ sequence: Int) { rejectSequences.insert(sequence) }

    func send(_ item: UploadItem, chunk: PcmChunk?) async -> SendResult {
        guard online else { return .failed(code: "NETWORK_UNREACHABLE", retry: true) }
        if case .chunk(let sequence) = item, rejectSequences.contains(sequence) {
            return .failed(code: "CHUNK_CONFLICT", retry: false)
        }
        if case .chunk = item, chunk == nil { return .failed(code: "MISSING_PAYLOAD", retry: false) }
        sent.append(item)
        return .ok
    }
}

func pcmChunk(_ sequence: Int) -> PcmChunk {
    PcmChunk(sequence: sequence, timestampMs: sequence * 2000, durationMs: 2000, samples: [Int16](repeating: 7, count: 32_000))
}

final class UploaderTests: XCTestCase {
    private let fast: [Duration] = [.milliseconds(5)]

    func testSendsInOrderAndDeletesOnlyAfterAcknowledgement() async throws {
        let store = temporaryStore()
        let transport = FakeTransport()
        await transport.setOnline(false)
        let uploader = Uploader(encounterId: "enc", store: store, transport: transport, backoff: fast)
        try await uploader.enqueue(chunk: pcmChunk(0))
        await uploader.enqueue(.pause)
        try await uploader.enqueue(chunk: pcmChunk(1))
        try await Task.sleep(for: .milliseconds(30))
        XCTAssertEqual(store.pendingSequences(encounterId: "enc"), [0, 1], "conservés chiffrés pendant la coupure")
        let offline = await uploader.status
        XCTAssertTrue(offline.retrying)
        XCTAssertEqual(offline.pending, 3)

        await transport.setOnline(true)
        await uploader.wake()
        await uploader.waitUntilDrained()
        let sent = await transport.sent
        XCTAssertEqual(sent, [.chunk(sequence: 0), .pause, .chunk(sequence: 1)])
        XCTAssertEqual(store.pendingSequences(encounterId: "enc"), [])
        let online = await uploader.status
        XCTAssertFalse(online.retrying)
    }

    func testPermanentRejectionIsCountedAsLost() async throws {
        let store = temporaryStore()
        let transport = FakeTransport()
        await transport.reject(1)
        let uploader = Uploader(encounterId: "enc", store: store, transport: transport, backoff: fast)
        for sequence in 0..<3 { try await uploader.enqueue(chunk: pcmChunk(sequence)) }
        await uploader.waitUntilDrained()
        let status = await uploader.status
        XCTAssertEqual(status.lost, 1)
        let sent = await transport.sent
        XCTAssertEqual(sent, [.chunk(sequence: 0), .chunk(sequence: 2)])
    }

    func testPendingChunksSurviveAnAppRelaunch() async throws {
        let store = temporaryStore()
        let offline = FakeTransport()
        await offline.setOnline(false)
        let first = Uploader(encounterId: "enc", store: store, transport: offline, backoff: [.seconds(60)])
        try await first.enqueue(chunk: pcmChunk(0))
        try await first.enqueue(chunk: pcmChunk(1))
        await first.abandonWithoutDeletingForTest()

        // « Nouvelle session » de l'app : même tampon, nouvelle file.
        let transport = FakeTransport()
        let relaunched = Uploader(encounterId: "enc", store: store, transport: transport, backoff: fast)
        let restored = await relaunched.restorePending()
        XCTAssertEqual(restored, [0, 1])
        await relaunched.waitUntilDrained()
        let sent = await transport.sent
        XCTAssertEqual(sent, [.chunk(sequence: 0), .chunk(sequence: 1)])
        XCTAssertEqual(store.pendingSequences(encounterId: "enc"), [])
    }

    func testAbandonErasesUnsentAudio() async throws {
        let store = temporaryStore()
        let transport = FakeTransport()
        await transport.setOnline(false)
        let uploader = Uploader(encounterId: "enc", store: store, transport: transport, backoff: [.seconds(60)])
        try await uploader.enqueue(chunk: pcmChunk(0))
        await uploader.abandon()
        await uploader.waitUntilDrained()
        XCTAssertEqual(store.pendingSequences(encounterId: "enc"), [])
    }
}

final class AudioTransportTests: XCTestCase {
    private func body(_ code: String) -> Data { Data(#"{"code":"\#(code)"}"#.utf8) }

    func testResponsesAreInterpretedLikeTheWebClient() {
        XCTAssertEqual(HTTPAudioTransport.interpret(status: 201, body: Data()), .ok)
        XCTAssertEqual(HTTPAudioTransport.interpret(status: 200, body: Data()), .ok)
        XCTAssertEqual(HTTPAudioTransport.interpret(status: 409, body: body("INVALID_TRANSITION")), .ok)
        XCTAssertEqual(HTTPAudioTransport.interpret(status: 503, body: Data()), .failed(code: "HTTP_503", retry: true))
        XCTAssertEqual(HTTPAudioTransport.interpret(status: 422, body: body("CHECKSUM_MISMATCH")), .failed(code: "CHECKSUM_MISMATCH", retry: true))
        XCTAssertEqual(HTTPAudioTransport.interpret(status: 409, body: body("CHUNK_CONFLICT")), .failed(code: "CHUNK_CONFLICT", retry: false))
    }

    func testChunkRequestCarriesFormatTimestampAndChecksum() throws {
        let transport = HTTPAudioTransport(baseURL: URL(string: "http://api.test")!, encounterId: "enc", transport: URLSessionTransport(session: .shared))
        let chunk = pcmChunk(4)
        let request = try transport.request(for: .chunk(sequence: 4), chunk: chunk)
        XCTAssertEqual(request.url?.absoluteString, "http://api.test/encounters/enc/audio/chunks/4")
        XCTAssertEqual(request.httpMethod, "PUT")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), AudioFormat.contentType)
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-Chunk-Timestamp-Ms"), "8000")
        XCTAssertEqual(
            request.value(forHTTPHeaderField: "X-Chunk-Checksum"),
            SHA256.hash(data: chunk.data).map { String(format: "%02x", $0) }.joined()
        )
        XCTAssertEqual(request.httpBody?.count, 64_000)
    }

    func testGapRequestBody() throws {
        let transport = HTTPAudioTransport(baseURL: URL(string: "http://api.test")!, encounterId: "enc", transport: URLSessionTransport(session: .shared))
        let request = try transport.request(for: .gap(reason: .audioInterruption, durationMs: 1500), chunk: nil)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: XCTUnwrap(request.httpBody)) as? [String: Any])
        XCTAssertEqual(json["reason"] as? String, "audio_interruption")
        XCTAssertEqual(json["duration_ms"] as? Int, 1500)
    }
}
