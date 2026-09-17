import Foundation
import XCTest

@testable import Oris

/// Contrat API ↔ iOS : décode de vraies réponses de l'API
/// (générées par services/api/tests/test_client_fixtures.py).
final class APIContractTests: XCTestCase {
    private func fixture<T: Decodable>(_ name: String, as type: T.Type) throws -> T {
        let url = URL(filePath: #filePath)
            .deletingLastPathComponent()
            .appending(path: "Fixtures/\(name)")
        return try JSONDecoder().decode(T.self, from: Data(contentsOf: url))
    }

    func testEncounterListAndDetailDecode() throws {
        let encounters = try fixture("encounters.json", as: [EncounterSummary].self)
        XCTAssertEqual(encounters.count, 1)
        let encounter = try fixture("encounter.json", as: EncounterSummary.self)
        XCTAssertEqual(encounter.status, .review)
        XCTAssertEqual(encounter.criticalWarningCount, 1)
        XCTAssertEqual(encounter.syntheticCaseId, "ORIS-SYN-099")
    }

    func testDocumentsDecodeWithClaimsAndStatus() throws {
        let documents = try fixture("documents_with_plan.json", as: [DocumentDetail].self)
        XCTAssertEqual(Set(documents.map(\.documentType)), [.consultationNote, .treatmentPlanText])
        XCTAssertTrue(documents.allSatisfy { $0.isCurrent && !$0.claims.isEmpty })
        let note = try XCTUnwrap(documents.first { $0.documentType == .consultationNote })
        XCTAssertTrue(note.claims.contains { $0.text == "Suspicion de fissure (16), non confirmée." })
    }

    func testClinicalObjectDecodesIntoGeneratedContract() throws {
        let response = try fixture("clinical_object.json", as: ClinicalObjectResponse.self)
        XCTAssertEqual(response.clinicalObject.warnings.first?.severity, .critical)
        let withPlan = try fixture("clinical_object_with_plan.json", as: ClinicalObjectResponse.self)
        let crack = try XCTUnwrap(withPlan.clinicalObject.facts.first { $0.concept == "crack" })
        XCTAssertEqual(crack.assertion, .uncertain)
        XCTAssertEqual(crack.certainty, .possible)
        XCTAssertFalse(crack.manuallyValidated)
        XCTAssertEqual(withPlan.clinicalObject.treatmentPlan?.items.first?.sequence, 1)
    }

    func testTranscriptDecodes() throws {
        let transcript = try fixture("transcript.json", as: TranscriptResponse.self)
        XCTAssertEqual(transcript.segments.count, 3)
    }

    @MainActor
    func testDetailModelCountsItemsToReview() async throws {
        let transport = FixtureTransport()
        let model = ConsultationDetailViewModel(
            encounterId: "00000000-0000-4000-8000-000000000002",
            client: APIClient(baseURL: URL(string: "http://api.test")!, transport: transport)
        )
        await model.refresh()
        guard case .loaded(let content) = model.state else {
            return XCTFail("consultation chargée attendue")
        }
        XCTAssertEqual(content.criticalWarnings.map(\.code), ["AUDIO_GAP"])
        XCTAssertEqual(content.reviewItemCount, 1)
    }
}

/// Sert les fixtures selon le chemin demandé.
private struct FixtureTransport: HTTPTransport {
    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        let path = request.url!.path()
        let name: String
        if path.hasSuffix("/documents") {
            name = "documents.json"
        } else if path.hasSuffix("/clinical-object") {
            name = "clinical_object.json"
        } else {
            name = "encounter.json"
        }
        let url = URL(filePath: #filePath).deletingLastPathComponent().appending(path: "Fixtures/\(name)")
        let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
        return (try Data(contentsOf: url), response)
    }
}
