import Foundation

// Réponses de l'API Oris (packages/openapi/openapi.json). Les objets cliniques
// eux-mêmes viennent des contrats générés (Contracts/Generated.swift).
// Contrat vérifié par OrisTests/APIContractTests à partir de vraies réponses.

struct PatientSummary: Codable, Equatable, Sendable, Identifiable {
    let id: String
    let firstName: String
    let lastName: String

    var displayName: String { "\(firstName) \(lastName)" }

    enum CodingKeys: String, CodingKey {
        case id
        case firstName = "first_name"
        case lastName = "last_name"
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

struct EncounterSummary: Codable, Equatable, Sendable, Identifiable {
    let id: String
    let patient: PatientSummary
    let status: ClinicalEncounterStatus
    let objectVersion: Int
    let startedAt: String?
    let createdAt: String
    let syntheticCaseId: String?
    let processingErrors: [ProcessingError]
    let criticalWarningCount: Int
    let documents: [DocumentSummary]

    enum CodingKeys: String, CodingKey {
        case id, patient, status, documents
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
