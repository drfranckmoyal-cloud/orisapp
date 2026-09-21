import Foundation

// Réponses de l'API Oris (packages/openapi/openapi.json). Les objets cliniques
// eux-mêmes viennent des contrats générés (Contracts/Generated.swift).
// Contrat vérifié par OrisTests/APIContractTests à partir de vraies réponses.

struct PatientSummary: Codable, Equatable, Sendable, Identifiable {
    let id: String
    let firstName: String
    let lastName: String
    /// Présents dans la liste des patients seulement.
    var consultations: Int? = nil
    var derniereConsultation: String? = nil
    var aRelire: Int? = nil

    var displayName: String { "\(firstName) \(lastName)" }

    enum CodingKeys: String, CodingKey {
        case id, consultations
        case firstName = "first_name"
        case lastName = "last_name"
        case derniereConsultation = "derniere_consultation"
        case aRelire = "a_relire"
    }
}

struct DocumentSummary: Codable, Equatable, Sendable, Identifiable {
    let id: String
    let documentType: DocumentDocumentType
    let status: DocumentStatus

    enum CodingKeys: String, CodingKey {
        case id
        case documentType = "document_type"
        case status
    }
}

struct ProcessingError: Codable, Equatable, Sendable {
    let rule: String
    let subjectId: String

    enum CodingKeys: String, CodingKey {
        case rule
        case subjectId = "subject_id"
    }
}

struct Praticien: Codable, Equatable, Sendable {
    let name: String

    var initiales: String {
        name.split(separator: " ").compactMap(\.first).prefix(2).map(String.init).joined().uppercased()
    }
}

struct EncounterSummary: Codable, Equatable, Sendable, Identifiable {
    let id: String
    let patient: PatientSummary
    var practitioner: Praticien? = nil
    let status: ClinicalEncounterStatus
    let objectVersion: Int
    let startedAt: String?
    let createdAt: String
    let syntheticCaseId: String?
    let processingErrors: [ProcessingError]
    let criticalWarningCount: Int
    let documents: [DocumentSummary]

    enum CodingKeys: String, CodingKey {
        case id, patient, practitioner, status, documents
        case objectVersion = "object_version"
        case startedAt = "started_at"
        case createdAt = "created_at"
        case syntheticCaseId = "synthetic_case_id"
        case processingErrors = "processing_errors"
        case criticalWarningCount = "critical_warning_count"
    }
}

struct DocumentClaim: Codable, Equatable, Sendable {
    let section: String
    let text: String
    let factIds: [String]
    let warningCodes: [String]

    enum CodingKeys: String, CodingKey {
        case section, text
        case factIds = "fact_ids"
        case warningCodes = "warning_codes"
    }
}

struct DocumentValidationIssue: Codable, Equatable, Sendable {
    let code: String
    let severity: String
    let factId: String?
    let claimIndex: Int?

    enum CodingKeys: String, CodingKey {
        case code, severity
        case factId = "fact_id"
        case claimIndex = "claim_index"
    }
}

struct DocumentDetail: Codable, Equatable, Sendable, Identifiable {
    let id: String
    let documentType: DocumentDocumentType
    let status: DocumentStatus
    let version: Int
    let generatedFromObjectVersion: Int
    let isCurrent: Bool
    let content: String
    let claims: [DocumentClaim]
    let validationIssues: [DocumentValidationIssue]

    enum CodingKeys: String, CodingKey {
        case id, status, version, content, claims
        case documentType = "document_type"
        case generatedFromObjectVersion = "generated_from_object_version"
        case isCurrent = "is_current"
        case validationIssues = "validation_issues"
    }
}

struct ClinicalObjectResponse: Codable, Equatable, Sendable {
    let clinicalObject: ClinicalEncounter

    enum CodingKeys: String, CodingKey {
        case clinicalObject = "clinical_object"
    }
}

struct TranscriptResponse: Codable, Equatable, Sendable {
    let segments: [TranscriptSegment]
}

struct AudioSessionState: Codable, Equatable, Sendable {
    let status: String
    let receivedCount: Int
    let lastSequence: Int?
    let nextSequence: Int
    let nextTimestampMs: Int
    let missingSequences: [Int]
    let receivedDurationMs: Int
    let gaps: [Gap]
    let purgeStatus: String
    let lastReceivedAt: String?

    struct Gap: Codable, Equatable, Sendable {
        let durationMs: Int?

        enum CodingKeys: String, CodingKey {
            case durationMs = "duration_ms"
        }
    }

    enum CodingKeys: String, CodingKey {
        case status, gaps
        case receivedCount = "received_count"
        case lastSequence = "last_sequence"
        case nextSequence = "next_sequence"
        case nextTimestampMs = "next_timestamp_ms"
        case missingSequences = "missing_sequences"
        case receivedDurationMs = "received_duration_ms"
        case purgeStatus = "purge_status"
        case lastReceivedAt = "last_received_at"
    }
}

struct ClientConfig: Codable, Equatable, Sendable {
    let environment: String
    let maxSessionMinutes: Int
    let warnSessionMinutes: Int
    let patientInformationMode: String
    let testAudioSourceEnabled: Bool

    enum CodingKeys: String, CodingKey {
        case environment
        case maxSessionMinutes = "max_session_minutes"
        case warnSessionMinutes = "warn_session_minutes"
        case patientInformationMode = "patient_information_mode"
        case testAudioSourceEnabled = "test_audio_source_enabled"
    }
}

/// Démarrage et fin d'écoute via l'API (implémentation réelle de `CaptureAPI`).
struct APICaptureBridge: CaptureAPI {
    let client: APIClient
    let encounterId: String
    var visitKind: VisitKind = .consultation

    func start(patientInformed: Bool) async throws {
        _ = try await client.startEncounter(
            id: encounterId, patientInformed: patientInformed, visitKind: visitKind
        )
    }

    func finish(finalSequence: Int, recordedMs: Int, acceptGaps: Bool) async throws -> FinishOutcome {
        do {
            _ = try await client.finishEncounter(
                id: encounterId, finalSequence: finalSequence, recordedMs: recordedMs, acceptGaps: acceptGaps
            )
            return .finished
        } catch APIError.server(_, "AUDIO_CHUNKS_MISSING", let details) {
            return .chunksMissing(details)
        }
    }
}
