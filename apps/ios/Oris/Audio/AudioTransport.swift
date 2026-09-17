import CryptoKit
import Foundation

enum GapReason: String, Sendable, Codable {
    case microphoneLost = "microphone_lost"
    case audioInterruption = "audio_interruption"
    case routeChange = "route_change"
    case appTerminated = "app_terminated"
    case captureError = "capture_error"
}

/// Élément de la file d'envoi. Le son d'un segment vit dans le tampon chiffré, pas ici.
enum UploadItem: Sendable, Equatable {
    case chunk(sequence: Int)
    case pause
    case resume
    case gap(reason: GapReason, durationMs: Int?)
}

enum SendResult: Sendable, Equatable {
    case ok
    case failed(code: String, retry: Bool)
}

protocol AudioTransporting: Sendable {
    func send(_ item: UploadItem, chunk: PcmChunk?) async -> SendResult
}

struct HTTPAudioTransport: AudioTransporting {
    let baseURL: URL
    let encounterId: String
    let transport: any HTTPTransport

    /// Erreurs qu'un nouvel essai ne corrigera pas.
    static let permanentCodes: Set<String> = [
        "CHUNK_CONFLICT", "ENCOUNTER_NOT_RECORDING", "CHUNK_TOO_LARGE",
        "UNSUPPORTED_AUDIO_FORMAT", "INVALID_CHUNK", "ENCOUNTER_NOT_FOUND",
    ]

    static func interpret(status: Int, body: Data) -> SendResult {
        if (200..<300).contains(status) { return .ok }
        let code = (try? JSONDecoder().decode(APIErrorBody.self, from: body))?.code ?? "HTTP_\(status)"
        // Pause ou reprise déjà appliquée (réponse perdue puis renvoi) : l'état est atteint.
        if code == "INVALID_TRANSITION" { return .ok }
        let retry = status >= 500 || status == 408 || status == 429 || !permanentCodes.contains(code)
        return .failed(code: code, retry: retry)
    }

    func request(for item: UploadItem, chunk: PcmChunk?) throws -> URLRequest {
        let root = baseURL.appending(path: "encounters/\(encounterId)")
        var request: URLRequest
        switch item {
        case .chunk(let sequence):
            guard let chunk, chunk.sequence == sequence else { throw URLError(.fileDoesNotExist) }
            let data = chunk.data
            request = URLRequest(url: root.appending(path: "audio/chunks/\(sequence)"))
            request.httpMethod = "PUT"
            request.setValue(AudioFormat.contentType, forHTTPHeaderField: "Content-Type")
            request.setValue(String(chunk.timestampMs), forHTTPHeaderField: "X-Chunk-Timestamp-Ms")
            request.setValue(
                SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined(),
                forHTTPHeaderField: "X-Chunk-Checksum"
            )
            request.httpBody = data
        case .pause, .resume:
            request = URLRequest(url: root.appending(path: item == .pause ? "pause" : "resume"))
            request.httpMethod = "POST"
        case .gap(let reason, let durationMs):
            request = URLRequest(url: root.appending(path: "audio/gaps"))
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            var body: [String: Any] = ["reason": reason.rawValue]
            body["duration_ms"] = durationMs ?? NSNull()
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        request.timeoutInterval = 15
        return request
    }

    func send(_ item: UploadItem, chunk: PcmChunk?) async -> SendResult {
        do {
            let (data, response) = try await transport.send(try request(for: item, chunk: chunk))
            guard let http = response as? HTTPURLResponse else {
                return .failed(code: "INVALID_RESPONSE", retry: true)
            }
            return Self.interpret(status: http.statusCode, body: data)
        } catch {
            return .failed(code: "NETWORK_UNREACHABLE", retry: true)
        }
    }
}

struct APIErrorBody: Decodable, Sendable {
    let code: String
    let details: [String]?
}
