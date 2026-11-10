import XCTest
@testable import Oris

private final class Comptoir: HTTPTransport, @unchecked Sendable {
    var derniere: URLRequest?
    let corps: Data

    init(corps: String) { self.corps = Data(corps.utf8) }

    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        derniere = request
        return (corps, HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

/// Le dialogue de correction : l'iPhone rend au serveur ce que le serveur a compris, sans
/// le réécrire — c'est le serveur qui valide et applique.
final class AssistantTests: XCTestCase {
    private let base = URL(string: "http://api.test")!
    private let fait = #"{"applique":true,"message":"Dossier corrigé ; les documents sont mis à jour.","object_version":4}"#

    private func corps(_ comptoir: Comptoir) throws -> [String: Any] {
        let requete = try XCTUnwrap(comptoir.derniere)
        return try XCTUnwrap(JSONSerialization.jsonObject(with: try XCTUnwrap(requete.httpBody)) as? [String: Any])
    }

    func testACorrectionOfTheRecordGoesBackUntouchedWithItsVersion() async throws {
        let lecture = try JSONDecoder().decode(LectureAssistant.self, from: Data("""
        {"nature":"dossier","demande":"la 26 c'est la 27","resume":"Je remplace la 26 par la 27.","consigne":"",
         "civilite":"","operations":[{"operation":"replace_tooth","from_tooth":"26","to_tooth":"27"}],
         "question":"","source":"regles","object_version":3}
        """.utf8))
        let comptoir = Comptoir(corps: fait)
        let resultat = try await APIClient(baseURL: base, transport: comptoir)
            .appliquer(encounterId: "e1", documentId: "d1", lecture: lecture)

        XCTAssertTrue(resultat.applique)
        XCTAssertEqual(comptoir.derniere?.url?.path(), "/encounters/e1/assistant/appliquer")
        let envoye = try corps(comptoir)
        XCTAssertEqual(envoye["nature"] as? String, "dossier")
        XCTAssertEqual(envoye["expected_object_version"] as? Int, 3)
        let operations = try XCTUnwrap(envoye["operations"] as? [[String: String]])
        XCTAssertEqual(operations, [["operation": "replace_tooth", "from_tooth": "26", "to_tooth": "27"]])
    }

    func testAStyleRequestCarriesAnInstructionAndNeverAnOperation() async throws {
        let lecture = try JSONDecoder().decode(LectureAssistant.self, from: Data("""
        {"nature":"redaction","demande":"plus court","resume":"Je raccourcis.","consigne":"Faire plus court",
         "civilite":"","operations":[],"question":"","source":"claude","object_version":3}
        """.utf8))
        let comptoir = Comptoir(corps: fait)
        _ = try await APIClient(baseURL: base, transport: comptoir)
            .appliquer(encounterId: "e1", documentId: "d1", lecture: lecture, retenir: true)

        let envoye = try corps(comptoir)
        XCTAssertEqual(envoye["consignes"] as? [String], ["Faire plus court"])
        XCTAssertEqual(envoye["retenir"] as? Bool, true)
        XCTAssertEqual(envoye["document_id"] as? String, "d1")
        XCTAssertNil(envoye["operations"])
    }

    func testAReviewComesBackAsProposals() async throws {
        let comptoir = Comptoir(corps: #"{"propositions":[{"titre":"Alléger","detail":"Dans le motif.","consigne":"Faire court"}]}"#)
        let propositions = try await APIClient(baseURL: base, transport: comptoir).relire(documentId: "d1")
        XCTAssertEqual(propositions.map(\.consigne), ["Faire court"])
        XCTAssertEqual(comptoir.derniere?.url?.path(), "/documents/d1/relecture")
    }
}
