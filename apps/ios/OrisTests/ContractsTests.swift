import Foundation
import XCTest

@testable import Oris

/// Les modèles Swift générés décodent et réencodent fidèlement les contrats.
final class ContractsTests: XCTestCase {
    private static let repoRoot = URL(filePath: #filePath)
        .deletingLastPathComponent()  // OrisTests
        .deletingLastPathComponent()  // ios
        .deletingLastPathComponent()  // apps
        .deletingLastPathComponent()  // racine

    private func corpusCases() throws -> [[String: Any]] {
        let url = Self.repoRoot.appending(path: "corpus/synthetic_consultations_100.jsonl")
        let lines = try String(contentsOf: url, encoding: .utf8).split(separator: "\n")
        return try lines.map { line in
            try XCTUnwrap(JSONSerialization.jsonObject(with: Data(line.utf8)) as? [String: Any])
        }
    }

    private func json(_ object: Any) throws -> Data {
        try JSONSerialization.data(withJSONObject: object)
    }

    func testEveryCorpusFactDecodesAndRoundTrips() throws {
        let cases = try corpusCases()
        XCTAssertEqual(cases.count, 100)
        for corpusCase in cases {
            let expected = try XCTUnwrap(corpusCase["expected"] as? [String: Any])
            let factsJSON = try XCTUnwrap(expected["facts"] as? [Any])
            let facts = try JSONDecoder().decode([ClinicalFact].self, from: json(factsJSON))
            let reencoded = try JSONSerialization.jsonObject(with: JSONEncoder().encode(facts))
            XCTAssertEqual(reencoded as? NSArray, factsJSON as NSArray, "\(corpusCase["case_id"] ?? "")")

            let segmentsJSON = try XCTUnwrap(corpusCase["transcript_segments"] as? [Any])
            _ = try JSONDecoder().decode([TranscriptSegment].self, from: json(segmentsJSON))

            if let plan = expected["treatment_plan"], !(plan is NSNull) {
                _ = try JSONDecoder().decode(TreatmentPlan.self, from: json(plan))
            }
        }
    }

    func testToothCorrectionCaseKeepsFinalTooth() throws {
        let toothCase = try XCTUnwrap(try corpusCases().first { $0["case_id"] as? String == "ORIS-SYN-091" })
        let expected = try XCTUnwrap(toothCase["expected"] as? [String: Any])
        let facts = try JSONDecoder().decode([ClinicalFact].self, from: json(expected["facts"] as Any))
        XCTAssertEqual(facts.first?.teeth, ["27"])
    }

    func testRequiredNullableFieldIsEncodedAsNull() throws {
        let encounter = ClinicalEncounter(
            encounterId: "enc", patientId: "pat", practitionerId: "usr",
            startedAt: "2026-09-16T09:00:00Z", endedAt: nil, status: .review, objectVersion: 1,
            facts: [], treatmentPlan: nil, procedures: [], warnings: []
        )
        let object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: JSONEncoder().encode(encounter)) as? [String: Any]
        )
        XCTAssertTrue(object["ended_at"] is NSNull)
        XCTAssertTrue(object["treatment_plan"] is NSNull)
    }

    func testMissingRequiredKeyIsRejected() throws {
        let incomplete = #"{"encounter_id":"enc","patient_id":"pat","practitioner_id":"usr","started_at":"x","status":"review","object_version":1,"facts":[],"treatment_plan":null,"procedures":[],"warnings":[]}"#
        XCTAssertThrowsError(try JSONDecoder().decode(ClinicalEncounter.self, from: Data(incomplete.utf8)))
    }

    func testUnknownEnumValueIsRejected() throws {
        let invalid = #"{"code":"x","severity":"catastrophic","message":"m"}"#
        XCTAssertThrowsError(try JSONDecoder().decode(EncounterWarning.self, from: Data(invalid.utf8)))
    }
}
