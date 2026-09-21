import XCTest
@testable import Oris

/// Répond comme le serveur, et garde la dernière requête pour l'inspecter.
private final class Guichet: HTTPTransport, @unchecked Sendable {
    var derniere: URLRequest?
    let corps: Data
    let entetes: [String: String]

    init(corps: String, entetes: [String: String] = [:]) {
        self.corps = Data(corps.utf8)
        self.entetes = entetes
    }

    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        derniere = request
        let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: entetes)!
        return (corps, response)
    }
}

final class DossierTests: XCTestCase {
    private let base = URL(string: "http://api.test")!

    func testAPhotoIsSentAsMultipartWithItsConsultation() async throws {
        let guichet = Guichet(corps: """
        [{"id":"a1","filename":"photo.jpg","media_type":"image/jpeg","kind":"photo","byte_size":3,
          "label":"","encounter_id":"e1","created_at":"2026-09-21T10:00:00+02:00"}]
        """)
        let client = APIClient(baseURL: base, transport: guichet)
        let pieces = try await client.deposerPhoto(patientId: "p1", encounterId: "e1", jpeg: Data([1, 2, 3]), nom: "photo.jpg")

        XCTAssertEqual(pieces.first?.id, "a1")
        let requete = try XCTUnwrap(guichet.derniere)
        XCTAssertEqual(requete.url?.path, "/patients/p1/attachments")
        XCTAssertEqual(requete.httpMethod, "POST")
        let type = try XCTUnwrap(requete.value(forHTTPHeaderField: "Content-Type"))
        XCTAssertTrue(type.hasPrefix("multipart/form-data; boundary="))
        let corps = String(decoding: try XCTUnwrap(requete.httpBody), as: UTF8.self)
        XCTAssertTrue(corps.contains("name=\"encounter_id\"\r\n\r\ne1\r\n"))
        XCTAssertTrue(corps.contains("name=\"files\"; filename=\"photo.jpg\""))
        XCTAssertTrue(corps.contains("Content-Type: image/jpeg"))
    }

    func testThePDFKeepsTheServersFileName() async throws {
        let guichet = Guichet(corps: "%PDF", entetes: [
            "Content-Disposition": "attachment; filename=\"Compte-rendu-consultation_TEST-Anne_2026-09-21.pdf\"",
        ])
        let fichier = try await APIClient(baseURL: base, transport: guichet).pdf(documentId: "d1")
        XCTAssertEqual(fichier.nom, "Compte-rendu-consultation_TEST-Anne_2026-09-21.pdf")
        XCTAssertEqual(guichet.derniere?.url?.query, "format=pdf")
    }

    func testSentToReadsAsFrench() {
        XCTAssertEqual(Labels.envoyeA(["le patient"]), "envoyé au patient")
        XCTAssertEqual(Labels.envoyeA(["le patient", "Dr Aubert"]), "envoyé au patient et à Dr Aubert")
        XCTAssertEqual(Labels.envoyeA([]), "")
    }

    func testServerErrorsSpeakFrench() {
        XCTAssertEqual(Labels.erreur(APIError.server(status: 409, code: "WARNING_NOT_ACKNOWLEDGED", details: [])),
                       "Confirmez d’abord avoir pris connaissance de l’alerte critique.")
        XCTAssertEqual(Labels.erreur(APIError.server(status: 409, code: "INCONNU", details: [])),
                       "Action impossible (INCONNU).")
    }
}
