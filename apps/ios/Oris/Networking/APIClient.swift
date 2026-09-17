import Foundation

/// Réponse de `GET /health` (technique, hors contrats cliniques).
struct HealthResponse: Codable, Equatable, Sendable {
    struct Providers: Codable, Equatable, Sendable {
        let speechToText: String
        let clinicalExtraction: String
        let documentGeneration: String
        let clinicalValidation: String

        enum CodingKeys: String, CodingKey {
            case speechToText = "speech_to_text"
            case clinicalExtraction = "clinical_extraction"
            case documentGeneration = "document_generation"
            case clinicalValidation = "clinical_validation"
        }

        var allMock: Bool {
            [speechToText, clinicalExtraction, documentGeneration, clinicalValidation]
                .allSatisfy { $0 == "mock" }
        }
    }

    let status: String
    let service: String
    let version: String
    let environment: String
    let providers: Providers
}

enum APIError: Error, Equatable {
    case invalidResponse
    case httpStatus(Int)
}

/// Transport HTTP injectable, pour tester le client sans réseau.
protocol HTTPTransport: Sendable {
    func send(_ request: URLRequest) async throws -> (Data, URLResponse)
}

struct URLSessionTransport: HTTPTransport {
    let session: URLSession

    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        try await session.data(for: request)
    }
}

/// Client typé de l'API Oris, commun à tous les écrans.
struct APIClient: Sendable {
    let baseURL: URL
    let transport: any HTTPTransport

    init(baseURL: URL, transport: any HTTPTransport = URLSessionTransport(session: .shared)) {
        self.baseURL = baseURL
        self.transport = transport
    }

    func health() async throws -> HealthResponse {
        try await get("health")
    }

    func encounters(status: ClinicalEncounterStatus? = nil) async throws -> [EncounterSummary] {
        try await get("encounters", query: status.map { [URLQueryItem(name: "status", value: $0.rawValue)] } ?? [])
    }

    func encounter(id: String) async throws -> EncounterSummary {
        try await get("encounters/\(id)")
    }

    func documents(encounterId: String) async throws -> [DocumentDetail] {
        try await get("encounters/\(encounterId)/documents")
    }

    func clinicalObject(encounterId: String) async throws -> ClinicalEncounter {
        let response: ClinicalObjectResponse = try await get("encounters/\(encounterId)/clinical-object")
        return response.clinicalObject
    }

    private func get<Response: Decodable>(_ path: String, query: [URLQueryItem] = []) async throws -> Response {
        var url = baseURL.appending(path: path)
        if !query.isEmpty {
            url.append(queryItems: query)
        }
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = 10
        let (data, response) = try await transport.send(request)
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else { throw APIError.httpStatus(http.statusCode) }
        return try JSONDecoder().decode(Response.self, from: data)
    }
}
