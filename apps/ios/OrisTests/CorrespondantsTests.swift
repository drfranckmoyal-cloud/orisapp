import XCTest
@testable import Oris

private final class Guichet: HTTPTransport, @unchecked Sendable {
    var derniere: URLRequest?
    let corps: Data

    init(corps: String) { self.corps = Data(corps.utf8) }

    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        derniere = request
        return (corps, HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

final class CorrespondantsTests: XCTestCase {
    private let base = URL(string: "http://api.test")!
    private let fiche = """
    {"id":"c1","kind":"practitioner","title":"Dr","last_name":"Aubert","first_name":"Léa ","specialty":"Pédodontie",
     "practice":"","email":"l.aubert@example.fr","phone":"","secondary_email":"","secondary_phone":"","address":"",
     "note":"","favorite":true,"created_at":"2026-09-21T10:00:00+02:00"}
    """

    func testALinkReadsItsRoleAndTheCorrespondentsName() async throws {
        let guichet = Guichet(corps: "[{\"role\":\"referred_by\",\"correspondent\":\(fiche)}]")
        let liens = try await APIClient(baseURL: base, transport: guichet)
            .rattacher(patientId: "p1", correspondantId: "c1", role: .referredBy)
        XCTAssertEqual(liens.first?.role, .referredBy)
        XCTAssertEqual(liens.first?.correspondent.nomCourt, "Dr Léa AUBERT")
        XCTAssertEqual(liens.first?.role.libelle, "nous l’a adressé")
        let corps = try JSONSerialization.jsonObject(with: try XCTUnwrap(guichet.derniere?.httpBody)) as? [String: String]
        XCTAssertEqual(corps, ["correspondent_id": "c1", "role": "referred_by"])
    }

    func testAnEmptyBirthDateAndFileNumberAreErased() async throws {
        let guichet = Guichet(corps: """
        {"id":"p1","first_name":"Anne","last_name":"TEST","birth_date":null,"external_id":null,"email":"","note":""}
        """)
        _ = try await APIClient(baseURL: base, transport: guichet).modifierPatient(
            id: "p1", prenom: " Anne ", nom: "TEST", naissance: nil, email: "", dossier: "  ", note: ""
        )
        let requete = try XCTUnwrap(guichet.derniere)
        XCTAssertEqual(requete.httpMethod, "PATCH")
        let corps = try XCTUnwrap(JSONSerialization.jsonObject(with: try XCTUnwrap(requete.httpBody)) as? [String: Any])
        XCTAssertTrue(corps["birth_date"] is NSNull)
        XCTAssertTrue(corps["external_id"] is NSNull)
        XCTAssertEqual(corps["first_name"] as? String, "Anne")
    }

    func testABirthDateIsSentAsADay() {
        let date = Calendar(identifier: .gregorian).date(from: DateComponents(year: 1958, month: 8, day: 30))!
        XCTAssertEqual(DateOris.jourISO(date), "1958-08-30")
        XCTAssertEqual("Stéphanie".sansAccents, "stephanie")
    }
}

final class SmileCloudTests: XCTestCase {
    func testTheServersSmileCloudStateIsRead() throws {
        let json = """
        {"case_id":"0f3c2a1b-1111-4222-8333-944455556666","nom":"Anne Essai","etat":"relie","candidats":[],
         "galeries":[{"id":"g1","nom":"Photos initiales","date":"2026-09-01","fichiers":[
           {"res_id":"a1","nom":"face.jpg","nature":"photo","rapatriable":true},
           {"res_id":"a2","nom":"sourire.mp4","nature":"video","rapatriable":false}]}],
         "galeries_lues_le":"2026-09-22T09:00:00+00:00","lecture_en_cours":false,
         "recuperation":{"demande":"d1","total":2,"recus":1,"ecartes":[{"res_id":"a2","raison":"video"}],
                         "termine":true,"demande_le":"2026-09-22T09:01:00+00:00"}}
        """
        let etat = try JSONDecoder().decode(EtatSmileCloud.self, from: Data(json.utf8))
        XCTAssertEqual(etat.etat, "relie")
        XCTAssertEqual(etat.galeries?.first?.fichiers.filter(\.rapatriable).count, 1)
        XCTAssertEqual(etat.recuperation?.recus, 1)
    }
}
