import XCTest
@testable import Oris

private final class Reponses: HTTPTransport, @unchecked Sendable {
    private var file: [String]
    init(_ file: [String]) { self.file = file }

    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        let corps = file.isEmpty ? "{}" : file.removeFirst()
        return (Data(corps.utf8), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

/// Franck, le 11/11/2026 : « si je sors et que je reviens dans Corriger avec Claude, garder
/// l'historique, ne pas en remettre une vierge, et marquer les demandes traitées ».
@MainActor
final class DialogueCorrectionTests: XCTestCase {
    private let lecture = """
    {"nature":"redaction","demande":"plus court","resume":"Je vais raccourcir.","consigne":"Faire plus court",
     "civilite":"","operations":[],"question":"","source":"claude","object_version":3}
    """
    private let fait = #"{"applique":true,"message":"Document rédigé à nouveau avec votre consigne.","object_version":3}"#

    func testTheDialogueOfAConsultationIsFoundAgainWhenTheWindowReopens() async {
        let client = APIClient(baseURL: URL(string: "http://api.test")!, transport: Reponses([lecture]))
        let premier = DialoguesCorrection.pour("consultation-a")
        await premier.demander("plus court", client: client, encounterId: "consultation-a")

        let rouvert = DialoguesCorrection.pour("consultation-a")
        XCTAssertTrue(rouvert === premier)
        XCTAssertEqual(rouvert.demandes.map(\.texte), ["plus court"])
        XCTAssertTrue(DialoguesCorrection.pour("consultation-b").demandes.isEmpty)
    }

    func testARequestIsMarkedToConfirmThenTreated() async throws {
        let client = APIClient(baseURL: URL(string: "http://api.test")!, transport: Reponses([lecture, fait]))
        let dialogue = DialogueCorrection()
        var recharge = ""
        dialogue.aChange = { recharge = $0 }

        await dialogue.demander("plus court", client: client, encounterId: "e1")
        XCTAssertEqual(dialogue.demandes.first?.marque?.texte, "À confirmer")

        guard case .proposee(let proposee) = try XCTUnwrap(dialogue.demandes.first).etat else {
            return XCTFail("la demande devait attendre l'accord")
        }
        await dialogue.appliquer(1, lecture: proposee, retenir: false, client: client,
                                 encounterId: "e1", documentId: "d1")
        XCTAssertEqual(dialogue.demandes.first?.marque?.texte, "Traitée")
        XCTAssertEqual(recharge, "Document rédigé à nouveau avec votre consigne.")
        XCTAssertFalse(dialogue.occupe)
    }

    func testTheProgressNeverClaimsToBeDone() {
        XCTAssertEqual(Progression.part(0), 0, accuracy: 0.001)
        XCTAssertEqual(Progression.part(30), 0.5, accuracy: 0.05)
        XCTAssertLessThanOrEqual(Progression.part(600), 0.95)
        XCTAssertEqual(Progression.duree(83), "1:23")
    }
}
