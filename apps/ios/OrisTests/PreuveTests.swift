import XCTest
@testable import Oris

/// Répond comme le serveur et garde la requête, pour vérifier la route appelée.
private final class GuichetPreuve: HTTPTransport, @unchecked Sendable {
    var derniere: URLRequest?
    let corps: Data

    init(corps: String) { self.corps = Data(corps.utf8) }

    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        derniere = request
        let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
        return (corps, response)
    }
}

/// « D'où vient cette phrase ? » sur l'iPhone : la même route et la même réponse que
/// sur le Mac (docs/PARITE.md, 26/09/2026).
final class PreuveTests: XCTestCase {
    private let base = URL(string: "http://api.test")!

    private static let reponse = """
    {"document_id":"d1","version":2,"object_version":1,"transcription_disponible":true,
     "phrases":[
       {"index":0,"section":"Motif","text":"Sensibilité au froid sur la 26.",
        "faits":[{"fact_id":"f1","concept":"cold_sensitivity","libelle":"sensibilité au froid",
                  "valeur":"","teeth":["26"],"assertion":"present",
                  "clinical_status":"patient_reported","certainty":"certain",
                  "temporality":"past","speaker_role":"patient","source_type":"audio",
                  "manually_validated":false}],
        "passages":[{"segment_id":"s1","start_ms":72000,"speaker_role":"patient",
                     "text":"ça me fait mal quand je bois froid"}],
        "alertes":[],"sans_preuve":false,"saisi_a_la_main":false},
       {"index":1,"section":"Motif","text":"Phrase sans appui.","faits":[],"passages":[],
        "alertes":[],"sans_preuve":true,"saisi_a_la_main":false}]}
    """

    func testThePhoneAsksTheSameRouteAsTheMacAndReadsTheWordsSpoken() async throws {
        let guichet = GuichetPreuve(corps: Self.reponse)
        let client = APIClient(baseURL: base, transport: guichet)

        let preuve = try await client.preuve(documentId: "d1")

        XCTAssertEqual(guichet.derniere?.url?.path, "/documents/d1/preuve")
        XCTAssertEqual(preuve.transcriptionDisponible, true)
        let phrase = try XCTUnwrap(preuve.phrase(0))
        XCTAssertEqual(phrase.faits.first?.libelle, "sensibilité au froid")
        XCTAssertEqual(phrase.faits.first?.teeth, ["26"])
        XCTAssertEqual(phrase.passages.first?.text, "ça me fait mal quand je bois froid")
        XCTAssertEqual(phrase.passages.first?.speakerRole, "patient")
    }

    func testASentenceWithoutSupportIsMarkedInsteadOfBeingHidden() async throws {
        let client = APIClient(baseURL: base, transport: GuichetPreuve(corps: Self.reponse))
        let preuve = try await client.preuve(documentId: "d1")

        let phrase = try XCTUnwrap(preuve.phrase(1))
        XCTAssertTrue(phrase.sansPreuve)
        XCTAssertTrue(phrase.passages.isEmpty)
    }

    func testTheMomentIsShownAsMinutesAndSeconds() {
        XCTAssertEqual(PreuvePassage.horloge(0), "0:00")
        XCTAssertEqual(PreuvePassage.horloge(72_000), "1:12")
        XCTAssertEqual(PreuvePassage.horloge(3_605_000), "60:05")
    }

    func testEachSpeakerIsNamedInFrench() {
        XCTAssertEqual(Labels.locuteur("practitioner"), "Praticien")
        XCTAssertEqual(Labels.locuteur("patient"), "Patient")
        XCTAssertEqual(Labels.locuteur("assistant"), "Assistante")
        XCTAssertEqual(Labels.locuteur("n’importe quoi"), "Locuteur inconnu")
    }
}
