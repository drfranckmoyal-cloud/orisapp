import CryptoKit
import Foundation
import Security

/// Tampon local chiffré des segments audio pas encore confirmés par le serveur (spec §13.2).
///
/// - un fichier par segment, chiffré AES-GCM ; le son n'est jamais écrit en clair ;
/// - protection de données iOS en plus (fichiers illisibles avant le premier déverrouillage) ;
/// - exclu des sauvegardes iCloud / ordinateur ;
/// - supprimé dès l'accusé de réception du serveur (audio éphémère, D010).
struct ChunkStore: Sendable {
    let root: URL
    private let key: SymmetricKey

    init(root: URL, key: SymmetricKey) {
        self.root = root
        self.key = key
    }

    static func production() throws -> ChunkStore {
        let base = try FileManager.default.url(
            for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true
        )
        var root = base.appending(path: "OrisAudioBuffer", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try root.setResourceValues(values)
        return ChunkStore(root: root, key: try KeychainKey.loadOrCreate())
    }

    private func directory(_ encounterId: String) -> URL {
        root.appending(path: encounterId, directoryHint: .isDirectory)
    }

    private func file(_ encounterId: String, _ sequence: Int) -> URL {
        directory(encounterId).appending(path: String(format: "%08d.chunk", sequence))
    }

    func save(_ chunk: PcmChunk, encounterId: String) throws {
        try FileManager.default.createDirectory(at: directory(encounterId), withIntermediateDirectories: true)
        var plaintext = Data()
        withUnsafeBytes(of: Int64(chunk.timestampMs).littleEndian) { plaintext.append(contentsOf: $0) }
        withUnsafeBytes(of: Int32(chunk.durationMs).littleEndian) { plaintext.append(contentsOf: $0) }
        plaintext.append(chunk.data)
        let sealed = try AES.GCM.seal(plaintext, using: key)
        guard let combined = sealed.combined else { throw CocoaError(.fileWriteUnknown) }
        try combined.write(
            to: file(encounterId, chunk.sequence),
            options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication]
        )
    }

    func load(encounterId: String, sequence: Int) throws -> PcmChunk? {
        let url = file(encounterId, sequence)
        guard FileManager.default.fileExists(atPath: url.path()) else { return nil }
        let box = try AES.GCM.SealedBox(combined: Data(contentsOf: url))
        let plaintext = try AES.GCM.open(box, using: key)
        guard plaintext.count >= 12 else { throw CocoaError(.fileReadCorruptFile) }
        let timestamp = plaintext.prefix(8).withUnsafeBytes { Int64(littleEndian: $0.loadUnaligned(as: Int64.self)) }
        let duration = plaintext.dropFirst(8).prefix(4).withUnsafeBytes { Int32(littleEndian: $0.loadUnaligned(as: Int32.self)) }
        return PcmChunk(
            sequence: sequence,
            timestampMs: Int(timestamp),
            durationMs: Int(duration),
            samples: PCM.samples(from: Data(plaintext.dropFirst(12)))
        )
    }

    func pendingSequences(encounterId: String) -> [Int] {
        let names = (try? FileManager.default.contentsOfDirectory(atPath: directory(encounterId).path())) ?? []
        return names.compactMap { name in
            name.hasSuffix(".chunk") ? Int(name.dropLast(6)) : nil
        }.sorted()
    }

    func delete(encounterId: String, sequence: Int) {
        try? FileManager.default.removeItem(at: file(encounterId, sequence))
    }

    func deleteAll(encounterId: String) {
        try? FileManager.default.removeItem(at: directory(encounterId))
    }

    func encountersWithPendingAudio() -> [String] {
        let names = (try? FileManager.default.contentsOfDirectory(atPath: root.path())) ?? []
        return names.filter { !pendingSequences(encounterId: $0).isEmpty }.sorted()
    }
}

/// Clé AES du tampon audio, dans le trousseau de l'appareil (jamais synchronisée).
enum KeychainKey {
    private static let service = "fr.oris.app.audio-buffer"

    static func loadOrCreate() throws -> SymmetricKey {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecReturnData as String: true,
        ]
        var item: CFTypeRef?
        if SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess, let data = item as? Data {
            return SymmetricKey(data: data)
        }
        let key = SymmetricKey(size: .bits256)
        let data = key.withUnsafeBytes { Data($0) }
        let attributes: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecValueData as String: data,
            // Écriture possible écran verrouillé (écoute en arrière-plan), jamais hors de cet appareil.
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]
        let status = SecItemAdd(attributes as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw NSError(domain: NSOSStatusErrorDomain, code: Int(status))
        }
        return key
    }
}
