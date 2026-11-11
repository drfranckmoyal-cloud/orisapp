import XCTest
@testable import Oris

private final class Reponses: HTTPTransport, @unchecked Sendable {
    private var file: [String]
    private(set) var chemins: [String] = []
    init(_ file: [String]) { self.file = file }

    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        chemins.append("\(request.httpMethod ?? "GET") \(request.url!.path())")
        let corps = file.isEmpty ? "[]" : file.removeFirst()
        return (Data(corps.utf8), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

/// Franck, le 11/11/2026 : « si je sors et que je reviens dans Corriger avec Claude, garder
/// l'historique, ne pas en remettre une vierge, et marquer les demandes traitées » — et pas
/// seulement tant que l'app reste ouverte. La conversation vit donc sur le serveur.
@MainActor
final class DialogueCorrectionTests: XCTestCase {
    private let lecture = """
    {"nature":"redaction","demande":"plus court","resume":"Je vais raccourcir.","consigne":"Faire plus court",
     "civilite":"","operations":[],"question":"","source":"claude","object_version":3,"demande_id":"d-1"}
    """
    private func historique(_ etat: String, message: String = "", code: String = "") -> String {
        """
        [{"id":"d-1","document_id":"doc","texte":"plus court","etat":"\(etat)",
          "lecture":\(lecture),"propositions":[],"message":"\(message)","code":"\(code)",
          "created_at":"2026-11-11T08:00:00.000000+00:00","depuis":"2026-11-11T08:00:05.123456+00:00"}]
        """
    }

    func testTheConversationIsReadBackFromTheServer() async {
        let client = APIClient(baseURL: URL(string: "http://api.test")!,
                               transport: Reponses([historique("traitee", message: "Document rédigé.")]))
        let dialogue = DialogueCorrection()
        await dialogue.charger(client: client, encounterId: "e1")
        XCTAssertEqual(dialogue.demandes.map(\.texte), ["plus court"])
        XCTAssertEqual(dialogue.demandes.first?.marque?.texte, "Traitée")
    }

    func testARequestIsKeptByTheServerThenConfirmedThenTreated() async throws {
        let transport = Reponses([
            lecture,
            historique("proposee"),
            #"{"applique":true,"message":"Document rédigé à nouveau avec votre consigne.","object_version":3}"#,
            historique("traitee", message: "Document rédigé à nouveau avec votre consigne."),
        ])
        let client = APIClient(baseURL: URL(string: "http://api.test")!, transport: transport)
        let dialogue = DialogueCorrection()
        var recharge = ""
        dialogue.aChange = { recharge = $0 }

        await dialogue.demander("plus court", client: client, encounterId: "e1", documentId: "doc")
        XCTAssertEqual(dialogue.demandes.map(\.id), ["d-1"])
        XCTAssertEqual(dialogue.demandes.first?.marque?.texte, "À confirmer")

        guard case .proposee(let proposee) = try XCTUnwrap(dialogue.demandes.first).etat else {
            return XCTFail("la demande devait attendre l'accord")
        }
        await dialogue.appliquer("d-1", lecture: proposee, retenir: false, client: client,
                                 encounterId: "e1", documentId: "doc")
        XCTAssertEqual(dialogue.demandes.first?.marque?.texte, "Traitée")
        XCTAssertEqual(recharge, "Document rédigé à nouveau avec votre consigne.")
        XCTAssertFalse(dialogue.occupe)
        XCTAssertEqual(transport.chemins, [
            "POST /encounters/e1/assistant",
            "GET /encounters/e1/assistant",
            "POST /encounters/e1/assistant/appliquer",
            "GET /encounters/e1/assistant",
        ])
    }

    func testAFailureKeptByTheServerSaysWhy() async {
        let client = APIClient(baseURL: URL(string: "http://api.test")!,
                               transport: Reponses([historique("echec", code: "ANTHROPIC_AUTH")]))
        let dialogue = DialogueCorrection()
        await dialogue.charger(client: client, encounterId: "e1")
        guard case .echec(let raison) = dialogue.demandes.first?.etat else {
            return XCTFail("la demande devait être non aboutie")
        }
        XCTAssertTrue(raison.contains("clé"))
    }

    func testTheProgressNeverClaimsToBeDone() {
        XCTAssertEqual(Progression.part(0), 0, accuracy: 0.001)
        XCTAssertEqual(Progression.part(30), 0.5, accuracy: 0.05)
        XCTAssertLessThanOrEqual(Progression.part(600), 0.95)
        XCTAssertEqual(Progression.duree(83), "1:23")
    }
}
