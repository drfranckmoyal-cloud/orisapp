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
    case server(status: Int, code: String, details: [String])

    var code: String {
        switch self {
        case .invalidResponse: "INVALID_RESPONSE"
        case .httpStatus(let status): "HTTP_\(status)"
        case .server(_, let code, _): code
        }
    }
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

    func patients() async throws -> [PatientSummary] {
        try await get("patients")
    }

    func createPatient(firstName: String, lastName: String) async throws -> PatientSummary {
        try await send("patients", method: "POST", body: ["first_name": firstName, "last_name": lastName])
    }

    func createEncounter(patientId: String) async throws -> EncounterSummary {
        try await send("encounters", method: "POST", body: ["patient_id": patientId])
    }

    func startEncounter(
        id: String, patientInformed: Bool, visitKind: VisitKind = .consultation
    ) async throws -> EncounterSummary {
        try await send(
            "encounters/\(id)/start",
            method: "POST",
            body: ["patient_informed": patientInformed, "visit_kind": visitKind.rawValue]
        )
    }

    func finishEncounter(id: String, finalSequence: Int?, recordedMs: Int?, acceptGaps: Bool) async throws -> EncounterSummary {
        var body: [String: Any] = ["accept_gaps": acceptGaps]
        body["final_sequence"] = finalSequence ?? NSNull()
        body["client_recorded_ms"] = recordedMs ?? NSNull()
        return try await send("encounters/\(id)/finish", method: "POST", body: body)
    }

    func reportGap(encounterId: String, reason: GapReason, durationMs: Int?) async throws -> AudioSessionState {
        var body: [String: Any] = ["reason": reason.rawValue]
        body["duration_ms"] = durationMs ?? NSNull()
        return try await send("encounters/\(encounterId)/audio/gaps", method: "POST", body: body)
    }

    func audioState(encounterId: String) async throws -> AudioSessionState {
        try await get("encounters/\(encounterId)/audio")
    }

    func clientConfig() async throws -> ClientConfig {
        try await get("config/client")
    }

    func get<Response: Decodable>(_ path: String, query: [URLQueryItem] = []) async throws -> Response {
        var url = baseURL.appending(path: path)
        if !query.isEmpty {
            url.append(queryItems: query)
        }
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = 10
        return try await perform(request)
    }

    func send<Response: Decodable>(_ path: String, method: String, body: [String: Any]) async throws -> Response {
        var request = URLRequest(url: baseURL.appending(path: path))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        request.timeoutInterval = 30
        return try await perform(request)
    }

    func perform<Response: Decodable>(_ request: URLRequest) async throws -> Response {
        let (data, response) = try await transport.send(request)
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            if let error = try? JSONDecoder().decode(APIErrorBody.self, from: data) {
                throw APIError.server(status: http.statusCode, code: error.code, details: error.details ?? [])
            }
            throw APIError.httpStatus(http.statusCode)
        }
        return try JSONDecoder().decode(Response.self, from: data)
    }
}
