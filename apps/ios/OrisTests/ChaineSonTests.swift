import AVFAudio
import CryptoKit
import XCTest
@testable import Oris

/// La chaîne du micro jusqu'aux octets envoyés, sur une vraie phrase : rééchantillonnage
/// 48 kHz → 16 kHz, conversion 16 bits, découpe en segments, chiffrement local et relecture.
final class ChaineSonTests: XCTestCase {
    func testASpokenSentenceSurvivesTheWholeChain() throws {
        let source = ProcessInfo.processInfo.environment["ORIS_PHRASE_48K"] ?? ""
        try XCTSkipIf(source.isEmpty, "phrase d'essai non fournie")
        let fichier = try AVAudioFile(forReading: URL(fileURLWithPath: source))
        let format = fichier.processingFormat
        let tampon = try XCTUnwrap(AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(fichier.length)))
        try fichier.read(into: tampon)
        let tout = Array(UnsafeBufferPointer(start: tampon.floatChannelData![0], count: Int(tampon.frameLength)))

        var resampler = Resampler(inputRate: format.sampleRate)
        var chunker = Chunker()
        var segments: [PcmChunk] = []
        for debut in stride(from: 0, to: tout.count, by: 4096) {
            let bloc = Array(tout[debut..<min(debut + 4096, tout.count)])
            segments += chunker.push(PCM.toInt16(resampler.process(bloc)))
        }
        if let dernier = chunker.flush() { segments.append(dernier) }

        let dossier = FileManager.default.temporaryDirectory.appending(path: "essai-chaine \(UUID().uuidString)")
        let magasin = ChunkStore(root: dossier, key: SymmetricKey(size: .bits256))
        var sortie = Data()
        for segment in segments {
            try magasin.save(segment, encounterId: "e")
            sortie.append(try XCTUnwrap(magasin.load(encounterId: "e", sequence: segment.sequence)).data)
        }
        let attendu = Double(tout.count) / format.sampleRate * 16_000 * 2
        XCTAssertEqual(Double(sortie.count), attendu, accuracy: 64)
        let echantillons = PCM.samples(from: sortie)
        let crete = echantillons.map { abs(Int($0)) }.max() ?? 0
        XCTAssertGreaterThan(crete, 3_000, "le son sort presque muet")
        if let cible = ProcessInfo.processInfo.environment["ORIS_SORTIE_PCM"] {
            try sortie.write(to: URL(fileURLWithPath: cible))
        }
    }
}
