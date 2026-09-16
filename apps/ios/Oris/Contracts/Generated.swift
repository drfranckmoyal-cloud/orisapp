// Généré par scripts/generate_contracts.py depuis schemas/ — ne pas modifier à la main.

import Foundation

/// Valeur JSON arbitraire (propriétés sans type fixe dans les schémas).
public enum JSONValue: Codable, Equatable, Sendable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else {
            self = .object(try container.decode([String: JSONValue].self))
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value): try container.encode(value)
        case .number(let value): try container.encode(value)
        case .bool(let value): try container.encode(value)
        case .object(let value): try container.encode(value)
        case .array(let value): try container.encode(value)
        case .null: try container.encodeNil()
        }
    }
}

public enum TranscriptSegmentSpeakerRole: String, Codable, CaseIterable, Sendable {
    case practitioner = "practitioner"
    case patient = "patient"
    case assistant = "assistant"
    case companion = "companion"
    case unknown = "unknown"
}

public enum ClinicalFactCategory: String, Codable, CaseIterable, Sendable {
    case chiefComplaint = "chief_complaint"
    case history = "history"
    case symptom = "symptom"
    case clinicalFinding = "clinical_finding"
    case radiographicFinding = "radiographic_finding"
    case assessment = "assessment"
    case diagnosis = "diagnosis"
    case treatmentOption = "treatment_option"
    case treatmentDecision = "treatment_decision"
    case procedure = "procedure"
    case material = "material"
    case medication = "medication"
    case patientInformation = "patient_information"
    case followUp = "follow_up"
    case other = "other"
}

public enum ClinicalFactSurfaces: String, Codable, CaseIterable, Sendable {
    case m = "M"
    case d = "D"
    case o = "O"
    case v = "V"
    case b = "B"
    case l = "L"
    case p = "P"
    case i = "I"
    case c = "C"
}

public enum ClinicalFactAssertion: String, Codable, CaseIterable, Sendable {
    case present = "present"
    case absent = "absent"
    case uncertain = "uncertain"
}

public enum ClinicalFactTemporality: String, Codable, CaseIterable, Sendable {
    case past = "past"
    case current = "current"
    case future = "future"
}

public enum ClinicalFactClinicalStatus: String, Codable, CaseIterable, Sendable {
    case patientReported = "patient_reported"
    case observed = "observed"
    case clinicianAssessment = "clinician_assessment"
    case differential = "differential"
    case discussed = "discussed"
    case proposed = "proposed"
    case accepted = "accepted"
    case refused = "refused"
    case deferred = "deferred"
    case planned = "planned"
    case performed = "performed"
}

public enum ClinicalFactSpeakerRole: String, Codable, CaseIterable, Sendable {
    case practitioner = "practitioner"
    case patient = "patient"
    case assistant = "assistant"
    case companion = "companion"
    case unknown = "unknown"
    case manual = "manual"
}

public enum ClinicalFactCertainty: String, Codable, CaseIterable, Sendable {
    case certain = "certain"
    case probable = "probable"
    case possible = "possible"
    case unknown = "unknown"
}

public enum ClinicalFactSourceType: String, Codable, CaseIterable, Sendable {
    case audio = "audio"
    case manual = "manual"
    case priorRecord = "prior_record"
    case systemTest = "system_test"
}

public enum TreatmentPlanStatus: String, Codable, CaseIterable, Sendable {
    case draft = "draft"
    case review = "review"
    case validated = "validated"
    case superseded = "superseded"
}

public enum TreatmentPlanItemStatus: String, Codable, CaseIterable, Sendable {
    case discussed = "discussed"
    case proposed = "proposed"
    case accepted = "accepted"
    case refused = "refused"
    case deferred = "deferred"
    case planned = "planned"
    case completed = "completed"
}

public enum TreatmentPlanItemPriority: String, Codable, CaseIterable, Sendable {
    case urgent = "urgent"
    case high = "high"
    case routine = "routine"
    case low = "low"
    case unspecified = "unspecified"
}

public enum ProcedureProcedureType: String, Codable, CaseIterable, Sendable {
    case composite = "composite"
    case directAesthetic = "direct_aesthetic"
    case veneerPreparation = "veneer_preparation"
    case veneerBonding = "veneer_bonding"
    case wearAdditive = "wear_additive"
    case extraction = "extraction"
    case minorSurgeryGeneric = "minor_surgery_generic"
}

public enum ProcedureStatus: String, Codable, CaseIterable, Sendable {
    case planned = "planned"
    case performed = "performed"
    case cancelled = "cancelled"
}

public enum ClinicalEncounterStatus: String, Codable, CaseIterable, Sendable {
    case draft = "draft"
    case recording = "recording"
    case paused = "paused"
    case finalizing = "finalizing"
    case processing = "processing"
    case review = "review"
    case validated = "validated"
    case exported = "exported"
    case archived = "archived"
    case audioError = "audio_error"
    case uploadInterrupted = "upload_interrupted"
    case transcriptionFailed = "transcription_failed"
    case generationFailed = "generation_failed"
}

public enum EncounterWarningSeverity: String, Codable, CaseIterable, Sendable {
    case info = "info"
    case review = "review"
    case critical = "critical"
}

public enum DocumentDocumentType: String, Codable, CaseIterable, Sendable {
    case consultationNote = "consultation_note"
    case treatmentPlanText = "treatment_plan_text"
    case operativeNote = "operative_note"
    case patientSummary = "patient_summary"
    case referralLetter = "referral_letter"
}

public enum DocumentStatus: String, Codable, CaseIterable, Sendable {
    case draftAi = "draft_ai"
    case needsReview = "needs_review"
    case validated = "validated"
    case exported = "exported"
    case superseded = "superseded"
    case outdated = "outdated"
}

public enum LearningEventEventType: String, Codable, CaseIterable, Sendable {
    case transcriptWordCorrection = "transcript_word_correction"
    case toothNumberCorrection = "tooth_number_correction"
    case speakerRoleCorrection = "speaker_role_correction"
    case clinicalFactAdded = "clinical_fact_added"
    case clinicalFactRemoved = "clinical_fact_removed"
    case clinicalFactCorrected = "clinical_fact_corrected"
    case negationCorrection = "negation_correction"
    case temporalityCorrection = "temporality_correction"
    case certaintyCorrection = "certainty_correction"
    case treatmentStatusCorrection = "treatment_status_correction"
    case treatmentSequenceCorrection = "treatment_sequence_correction"
    case procedureTypeCorrection = "procedure_type_correction"
    case materialNameCorrection = "material_name_correction"
    case documentTextEdit = "document_text_edit"
    case documentSectionDeleted = "document_section_deleted"
    case documentSectionAdded = "document_section_added"
    case warningConfirmed = "warning_confirmed"
    case warningDismissed = "warning_dismissed"
    case glossaryTermAdded = "glossary_term_added"
    case stylePreferenceDetected = "style_preference_detected"
    case documentValidatedUnchanged = "document_validated_unchanged"
    case documentValidatedAfterMinorEdit = "document_validated_after_minor_edit"
    case documentValidatedAfterMajorEdit = "document_validated_after_major_edit"
    case generationRejected = "generation_rejected"
}

public enum LearningEventScope: String, Codable, CaseIterable, Sendable {
    case user = "user"
    case organization = "organization"
    case globalCandidate = "global_candidate"
}

public enum LearningEventLearningStatus: String, Codable, CaseIterable, Sendable {
    case captured = "captured"
    case reviewed = "reviewed"
    case promoted = "promoted"
    case rejected = "rejected"
    case purged = "purged"
}

public enum PractitionerLearningProfilePreferredDocumentLength: String, Codable, CaseIterable, Sendable {
    case short = "short"
    case standard = "standard"
    case detailed = "detailed"
}

public enum PractitionerLearningProfilePreferredStyle: String, Codable, CaseIterable, Sendable {
    case sentences = "sentences"
    case semiTelegraphic = "semi_telegraphic"
}

public struct TranscriptSegment: Codable, Equatable, Sendable {
    public var segmentId: String
    public var startMs: Int
    public var endMs: Int
    public var speakerRole: TranscriptSegmentSpeakerRole
    public var text: String
    public var confidence: Double
    public var isFinal: Bool

    public init(segmentId: String, startMs: Int, endMs: Int, speakerRole: TranscriptSegmentSpeakerRole, text: String, confidence: Double, isFinal: Bool) {
        self.segmentId = segmentId
        self.startMs = startMs
        self.endMs = endMs
        self.speakerRole = speakerRole
        self.text = text
        self.confidence = confidence
        self.isFinal = isFinal
    }

    enum CodingKeys: String, CodingKey {
        case segmentId = "segment_id"
        case startMs = "start_ms"
        case endMs = "end_ms"
        case speakerRole = "speaker_role"
        case text = "text"
        case confidence = "confidence"
        case isFinal = "is_final"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        segmentId = try c.decode(String.self, forKey: .segmentId)
        startMs = try c.decode(Int.self, forKey: .startMs)
        endMs = try c.decode(Int.self, forKey: .endMs)
        speakerRole = try c.decode(TranscriptSegmentSpeakerRole.self, forKey: .speakerRole)
        text = try c.decode(String.self, forKey: .text)
        confidence = try c.decode(Double.self, forKey: .confidence)
        isFinal = try c.decode(Bool.self, forKey: .isFinal)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(segmentId, forKey: .segmentId)
        try c.encode(startMs, forKey: .startMs)
        try c.encode(endMs, forKey: .endMs)
        try c.encode(speakerRole, forKey: .speakerRole)
        try c.encode(text, forKey: .text)
        try c.encode(confidence, forKey: .confidence)
        try c.encode(isFinal, forKey: .isFinal)
    }
}

public struct ClinicalFact: Codable, Equatable, Sendable {
    public var factId: String
    public var category: ClinicalFactCategory
    public var concept: String
    public var value: JSONValue
    public var teeth: [String]
    public var surfaces: [ClinicalFactSurfaces]
    public var assertion: ClinicalFactAssertion
    public var temporality: ClinicalFactTemporality
    public var clinicalStatus: ClinicalFactClinicalStatus
    public var speakerRole: ClinicalFactSpeakerRole
    public var certainty: ClinicalFactCertainty
    public var sourceType: ClinicalFactSourceType
    public var evidenceSegmentIds: [String]
    public var confidence: Double
    public var manuallyValidated: Bool

    public init(factId: String, category: ClinicalFactCategory, concept: String, value: JSONValue, teeth: [String], surfaces: [ClinicalFactSurfaces], assertion: ClinicalFactAssertion, temporality: ClinicalFactTemporality, clinicalStatus: ClinicalFactClinicalStatus, speakerRole: ClinicalFactSpeakerRole, certainty: ClinicalFactCertainty, sourceType: ClinicalFactSourceType, evidenceSegmentIds: [String], confidence: Double, manuallyValidated: Bool) {
        self.factId = factId
        self.category = category
        self.concept = concept
        self.value = value
        self.teeth = teeth
        self.surfaces = surfaces
        self.assertion = assertion
        self.temporality = temporality
        self.clinicalStatus = clinicalStatus
        self.speakerRole = speakerRole
        self.certainty = certainty
        self.sourceType = sourceType
        self.evidenceSegmentIds = evidenceSegmentIds
        self.confidence = confidence
        self.manuallyValidated = manuallyValidated
    }

    enum CodingKeys: String, CodingKey {
        case factId = "fact_id"
        case category = "category"
        case concept = "concept"
        case value = "value"
        case teeth = "teeth"
        case surfaces = "surfaces"
        case assertion = "assertion"
        case temporality = "temporality"
        case clinicalStatus = "clinical_status"
        case speakerRole = "speaker_role"
        case certainty = "certainty"
        case sourceType = "source_type"
        case evidenceSegmentIds = "evidence_segment_ids"
        case confidence = "confidence"
        case manuallyValidated = "manually_validated"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        factId = try c.decode(String.self, forKey: .factId)
        category = try c.decode(ClinicalFactCategory.self, forKey: .category)
        concept = try c.decode(String.self, forKey: .concept)
        value = try c.decode(JSONValue.self, forKey: .value)
        teeth = try c.decode([String].self, forKey: .teeth)
        surfaces = try c.decode([ClinicalFactSurfaces].self, forKey: .surfaces)
        assertion = try c.decode(ClinicalFactAssertion.self, forKey: .assertion)
        temporality = try c.decode(ClinicalFactTemporality.self, forKey: .temporality)
        clinicalStatus = try c.decode(ClinicalFactClinicalStatus.self, forKey: .clinicalStatus)
        speakerRole = try c.decode(ClinicalFactSpeakerRole.self, forKey: .speakerRole)
        certainty = try c.decode(ClinicalFactCertainty.self, forKey: .certainty)
        sourceType = try c.decode(ClinicalFactSourceType.self, forKey: .sourceType)
        evidenceSegmentIds = try c.decode([String].self, forKey: .evidenceSegmentIds)
        confidence = try c.decode(Double.self, forKey: .confidence)
        manuallyValidated = try c.decode(Bool.self, forKey: .manuallyValidated)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(factId, forKey: .factId)
        try c.encode(category, forKey: .category)
        try c.encode(concept, forKey: .concept)
        try c.encode(value, forKey: .value)
        try c.encode(teeth, forKey: .teeth)
        try c.encode(surfaces, forKey: .surfaces)
        try c.encode(assertion, forKey: .assertion)
        try c.encode(temporality, forKey: .temporality)
        try c.encode(clinicalStatus, forKey: .clinicalStatus)
        try c.encode(speakerRole, forKey: .speakerRole)
        try c.encode(certainty, forKey: .certainty)
        try c.encode(sourceType, forKey: .sourceType)
        try c.encode(evidenceSegmentIds, forKey: .evidenceSegmentIds)
        try c.encode(confidence, forKey: .confidence)
        try c.encode(manuallyValidated, forKey: .manuallyValidated)
    }
}

public struct TreatmentPlanItem: Codable, Equatable, Sendable {
    public var itemId: String
    public var teeth: [String]
    public var problem: String?
    public var action: String
    public var status: TreatmentPlanItemStatus
    public var priority: TreatmentPlanItemPriority
    public var sequence: Int?
    public var alternatives: [String]
    public var prerequisites: [String]
    public var uncertainties: [String]
    public var evidenceFactIds: [String]

    public init(itemId: String, teeth: [String], problem: String? = nil, action: String, status: TreatmentPlanItemStatus, priority: TreatmentPlanItemPriority, sequence: Int? = nil, alternatives: [String], prerequisites: [String], uncertainties: [String], evidenceFactIds: [String]) {
        self.itemId = itemId
        self.teeth = teeth
        self.problem = problem
        self.action = action
        self.status = status
        self.priority = priority
        self.sequence = sequence
        self.alternatives = alternatives
        self.prerequisites = prerequisites
        self.uncertainties = uncertainties
        self.evidenceFactIds = evidenceFactIds
    }

    enum CodingKeys: String, CodingKey {
        case itemId = "item_id"
        case teeth = "teeth"
        case problem = "problem"
        case action = "action"
        case status = "status"
        case priority = "priority"
        case sequence = "sequence"
        case alternatives = "alternatives"
        case prerequisites = "prerequisites"
        case uncertainties = "uncertainties"
        case evidenceFactIds = "evidence_fact_ids"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        itemId = try c.decode(String.self, forKey: .itemId)
        teeth = try c.decode([String].self, forKey: .teeth)
        problem = try c.decode(String?.self, forKey: .problem)
        action = try c.decode(String.self, forKey: .action)
        status = try c.decode(TreatmentPlanItemStatus.self, forKey: .status)
        priority = try c.decode(TreatmentPlanItemPriority.self, forKey: .priority)
        sequence = try c.decode(Int?.self, forKey: .sequence)
        alternatives = try c.decode([String].self, forKey: .alternatives)
        prerequisites = try c.decode([String].self, forKey: .prerequisites)
        uncertainties = try c.decode([String].self, forKey: .uncertainties)
        evidenceFactIds = try c.decode([String].self, forKey: .evidenceFactIds)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(itemId, forKey: .itemId)
        try c.encode(teeth, forKey: .teeth)
        try c.encode(problem, forKey: .problem)
        try c.encode(action, forKey: .action)
        try c.encode(status, forKey: .status)
        try c.encode(priority, forKey: .priority)
        try c.encode(sequence, forKey: .sequence)
        try c.encode(alternatives, forKey: .alternatives)
        try c.encode(prerequisites, forKey: .prerequisites)
        try c.encode(uncertainties, forKey: .uncertainties)
        try c.encode(evidenceFactIds, forKey: .evidenceFactIds)
    }
}

public struct TreatmentPlan: Codable, Equatable, Sendable {
    public var planId: String
    public var status: TreatmentPlanStatus
    public var goals: [String]
    public var notes: [String]
    public var items: [TreatmentPlanItem]

    public init(planId: String, status: TreatmentPlanStatus, goals: [String], notes: [String], items: [TreatmentPlanItem]) {
        self.planId = planId
        self.status = status
        self.goals = goals
        self.notes = notes
        self.items = items
    }

    enum CodingKeys: String, CodingKey {
        case planId = "plan_id"
        case status = "status"
        case goals = "goals"
        case notes = "notes"
        case items = "items"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        planId = try c.decode(String.self, forKey: .planId)
        status = try c.decode(TreatmentPlanStatus.self, forKey: .status)
        goals = try c.decode([String].self, forKey: .goals)
        notes = try c.decode([String].self, forKey: .notes)
        items = try c.decode([TreatmentPlanItem].self, forKey: .items)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(planId, forKey: .planId)
        try c.encode(status, forKey: .status)
        try c.encode(goals, forKey: .goals)
        try c.encode(notes, forKey: .notes)
        try c.encode(items, forKey: .items)
    }
}

public struct Procedure: Codable, Equatable, Sendable {
    public var procedureId: String
    public var procedureType: ProcedureProcedureType
    public var status: ProcedureStatus
    public var teeth: [String]
    public var structuredData: [String: JSONValue]
    public var evidenceFactIds: [String]

    public init(procedureId: String, procedureType: ProcedureProcedureType, status: ProcedureStatus, teeth: [String], structuredData: [String: JSONValue], evidenceFactIds: [String]) {
        self.procedureId = procedureId
        self.procedureType = procedureType
        self.status = status
        self.teeth = teeth
        self.structuredData = structuredData
        self.evidenceFactIds = evidenceFactIds
    }

    enum CodingKeys: String, CodingKey {
        case procedureId = "procedure_id"
        case procedureType = "procedure_type"
        case status = "status"
        case teeth = "teeth"
        case structuredData = "structured_data"
        case evidenceFactIds = "evidence_fact_ids"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        procedureId = try c.decode(String.self, forKey: .procedureId)
        procedureType = try c.decode(ProcedureProcedureType.self, forKey: .procedureType)
        status = try c.decode(ProcedureStatus.self, forKey: .status)
        teeth = try c.decode([String].self, forKey: .teeth)
        structuredData = try c.decode([String: JSONValue].self, forKey: .structuredData)
        evidenceFactIds = try c.decode([String].self, forKey: .evidenceFactIds)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(procedureId, forKey: .procedureId)
        try c.encode(procedureType, forKey: .procedureType)
        try c.encode(status, forKey: .status)
        try c.encode(teeth, forKey: .teeth)
        try c.encode(structuredData, forKey: .structuredData)
        try c.encode(evidenceFactIds, forKey: .evidenceFactIds)
    }
}

public struct EncounterWarning: Codable, Equatable, Sendable {
    public var code: String
    public var severity: EncounterWarningSeverity
    public var message: String

    public init(code: String, severity: EncounterWarningSeverity, message: String) {
        self.code = code
        self.severity = severity
        self.message = message
    }

    enum CodingKeys: String, CodingKey {
        case code = "code"
        case severity = "severity"
        case message = "message"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        code = try c.decode(String.self, forKey: .code)
        severity = try c.decode(EncounterWarningSeverity.self, forKey: .severity)
        message = try c.decode(String.self, forKey: .message)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(code, forKey: .code)
        try c.encode(severity, forKey: .severity)
        try c.encode(message, forKey: .message)
    }
}

public struct ClinicalEncounter: Codable, Equatable, Sendable {
    public var encounterId: String
    public var patientId: String
    public var practitionerId: String
    public var startedAt: String
    public var endedAt: String?
    public var status: ClinicalEncounterStatus
    public var objectVersion: Int
    public var facts: [ClinicalFact]
    public var treatmentPlan: TreatmentPlan?
    public var procedures: [Procedure]
    public var warnings: [EncounterWarning]

    public init(encounterId: String, patientId: String, practitionerId: String, startedAt: String, endedAt: String? = nil, status: ClinicalEncounterStatus, objectVersion: Int, facts: [ClinicalFact], treatmentPlan: TreatmentPlan? = nil, procedures: [Procedure], warnings: [EncounterWarning]) {
        self.encounterId = encounterId
        self.patientId = patientId
        self.practitionerId = practitionerId
        self.startedAt = startedAt
        self.endedAt = endedAt
        self.status = status
        self.objectVersion = objectVersion
        self.facts = facts
        self.treatmentPlan = treatmentPlan
        self.procedures = procedures
        self.warnings = warnings
    }

    enum CodingKeys: String, CodingKey {
        case encounterId = "encounter_id"
        case patientId = "patient_id"
        case practitionerId = "practitioner_id"
        case startedAt = "started_at"
        case endedAt = "ended_at"
        case status = "status"
        case objectVersion = "object_version"
        case facts = "facts"
        case treatmentPlan = "treatment_plan"
        case procedures = "procedures"
        case warnings = "warnings"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        encounterId = try c.decode(String.self, forKey: .encounterId)
        patientId = try c.decode(String.self, forKey: .patientId)
        practitionerId = try c.decode(String.self, forKey: .practitionerId)
        startedAt = try c.decode(String.self, forKey: .startedAt)
        endedAt = try c.decode(String?.self, forKey: .endedAt)
        status = try c.decode(ClinicalEncounterStatus.self, forKey: .status)
        objectVersion = try c.decode(Int.self, forKey: .objectVersion)
        facts = try c.decode([ClinicalFact].self, forKey: .facts)
        treatmentPlan = try c.decode(TreatmentPlan?.self, forKey: .treatmentPlan)
        procedures = try c.decode([Procedure].self, forKey: .procedures)
        warnings = try c.decode([EncounterWarning].self, forKey: .warnings)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(encounterId, forKey: .encounterId)
        try c.encode(patientId, forKey: .patientId)
        try c.encode(practitionerId, forKey: .practitionerId)
        try c.encode(startedAt, forKey: .startedAt)
        try c.encode(endedAt, forKey: .endedAt)
        try c.encode(status, forKey: .status)
        try c.encode(objectVersion, forKey: .objectVersion)
        try c.encode(facts, forKey: .facts)
        try c.encode(treatmentPlan, forKey: .treatmentPlan)
        try c.encode(procedures, forKey: .procedures)
        try c.encode(warnings, forKey: .warnings)
    }
}

public struct Document: Codable, Equatable, Sendable {
    public var documentId: String
    public var documentType: DocumentDocumentType
    public var status: DocumentStatus
    public var encounterObjectVersion: Int
    public var content: String
    public var supportedFactIds: [String]

    public init(documentId: String, documentType: DocumentDocumentType, status: DocumentStatus, encounterObjectVersion: Int, content: String, supportedFactIds: [String]) {
        self.documentId = documentId
        self.documentType = documentType
        self.status = status
        self.encounterObjectVersion = encounterObjectVersion
        self.content = content
        self.supportedFactIds = supportedFactIds
    }

    enum CodingKeys: String, CodingKey {
        case documentId = "document_id"
        case documentType = "document_type"
        case status = "status"
        case encounterObjectVersion = "encounter_object_version"
        case content = "content"
        case supportedFactIds = "supported_fact_ids"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        documentId = try c.decode(String.self, forKey: .documentId)
        documentType = try c.decode(DocumentDocumentType.self, forKey: .documentType)
        status = try c.decode(DocumentStatus.self, forKey: .status)
        encounterObjectVersion = try c.decode(Int.self, forKey: .encounterObjectVersion)
        content = try c.decode(String.self, forKey: .content)
        supportedFactIds = try c.decode([String].self, forKey: .supportedFactIds)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(documentId, forKey: .documentId)
        try c.encode(documentType, forKey: .documentType)
        try c.encode(status, forKey: .status)
        try c.encode(encounterObjectVersion, forKey: .encounterObjectVersion)
        try c.encode(content, forKey: .content)
        try c.encode(supportedFactIds, forKey: .supportedFactIds)
    }
}

public struct LearningEvent: Codable, Equatable, Sendable {
    public var learningEventId: String
    public var organizationId: String
    public var userId: String
    public var encounterId: String
    public var eventType: LearningEventEventType
    public var scope: LearningEventScope
    public var sourceVersion: String
    public var before: JSONValue
    public var after: JSONValue
    public var reason: String?
    public var confidenceBefore: Double?
    public var validatedByPractitioner: Bool
    public var createdAt: String
    public var eligibleForGlobalLearning: Bool
    public var learningStatus: LearningEventLearningStatus

    public init(learningEventId: String, organizationId: String, userId: String, encounterId: String, eventType: LearningEventEventType, scope: LearningEventScope, sourceVersion: String, before: JSONValue, after: JSONValue, reason: String? = nil, confidenceBefore: Double? = nil, validatedByPractitioner: Bool, createdAt: String, eligibleForGlobalLearning: Bool, learningStatus: LearningEventLearningStatus) {
        self.learningEventId = learningEventId
        self.organizationId = organizationId
        self.userId = userId
        self.encounterId = encounterId
        self.eventType = eventType
        self.scope = scope
        self.sourceVersion = sourceVersion
        self.before = before
        self.after = after
        self.reason = reason
        self.confidenceBefore = confidenceBefore
        self.validatedByPractitioner = validatedByPractitioner
        self.createdAt = createdAt
        self.eligibleForGlobalLearning = eligibleForGlobalLearning
        self.learningStatus = learningStatus
    }

    enum CodingKeys: String, CodingKey {
        case learningEventId = "learning_event_id"
        case organizationId = "organization_id"
        case userId = "user_id"
        case encounterId = "encounter_id"
        case eventType = "event_type"
        case scope = "scope"
        case sourceVersion = "source_version"
        case before = "before"
        case after = "after"
        case reason = "reason"
        case confidenceBefore = "confidence_before"
        case validatedByPractitioner = "validated_by_practitioner"
        case createdAt = "created_at"
        case eligibleForGlobalLearning = "eligible_for_global_learning"
        case learningStatus = "learning_status"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        learningEventId = try c.decode(String.self, forKey: .learningEventId)
        organizationId = try c.decode(String.self, forKey: .organizationId)
        userId = try c.decode(String.self, forKey: .userId)
        encounterId = try c.decode(String.self, forKey: .encounterId)
        eventType = try c.decode(LearningEventEventType.self, forKey: .eventType)
        scope = try c.decode(LearningEventScope.self, forKey: .scope)
        sourceVersion = try c.decode(String.self, forKey: .sourceVersion)
        before = try c.decode(JSONValue.self, forKey: .before)
        after = try c.decode(JSONValue.self, forKey: .after)
        reason = try c.decodeIfPresent(String.self, forKey: .reason)
        confidenceBefore = try c.decodeIfPresent(Double.self, forKey: .confidenceBefore)
        validatedByPractitioner = try c.decode(Bool.self, forKey: .validatedByPractitioner)
        createdAt = try c.decode(String.self, forKey: .createdAt)
        eligibleForGlobalLearning = try c.decode(Bool.self, forKey: .eligibleForGlobalLearning)
        learningStatus = try c.decode(LearningEventLearningStatus.self, forKey: .learningStatus)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(learningEventId, forKey: .learningEventId)
        try c.encode(organizationId, forKey: .organizationId)
        try c.encode(userId, forKey: .userId)
        try c.encode(encounterId, forKey: .encounterId)
        try c.encode(eventType, forKey: .eventType)
        try c.encode(scope, forKey: .scope)
        try c.encode(sourceVersion, forKey: .sourceVersion)
        try c.encode(before, forKey: .before)
        try c.encode(after, forKey: .after)
        try c.encodeIfPresent(reason, forKey: .reason)
        try c.encodeIfPresent(confidenceBefore, forKey: .confidenceBefore)
        try c.encode(validatedByPractitioner, forKey: .validatedByPractitioner)
        try c.encode(createdAt, forKey: .createdAt)
        try c.encode(eligibleForGlobalLearning, forKey: .eligibleForGlobalLearning)
        try c.encode(learningStatus, forKey: .learningStatus)
    }
}

public struct SpeechAlias: Codable, Equatable, Sendable {
    public var heard: String
    public var canonical: String

    public init(heard: String, canonical: String) {
        self.heard = heard
        self.canonical = canonical
    }

    enum CodingKeys: String, CodingKey {
        case heard = "heard"
        case canonical = "canonical"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        heard = try c.decode(String.self, forKey: .heard)
        canonical = try c.decode(String.self, forKey: .canonical)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(heard, forKey: .heard)
        try c.encode(canonical, forKey: .canonical)
    }
}

public struct PractitionerLearningProfile: Codable, Equatable, Sendable {
    public var userId: String
    public var preferredDocumentLength: PractitionerLearningProfilePreferredDocumentLength
    public var preferredStyle: PractitionerLearningProfilePreferredStyle
    public var preferredTerms: [String: String]
    public var frequentMaterials: [String]
    public var speechAliases: [SpeechAlias]
    public var documentPreferences: [String: JSONValue]
    public var lastUpdatedAt: String

    public init(userId: String, preferredDocumentLength: PractitionerLearningProfilePreferredDocumentLength, preferredStyle: PractitionerLearningProfilePreferredStyle, preferredTerms: [String: String], frequentMaterials: [String], speechAliases: [SpeechAlias], documentPreferences: [String: JSONValue], lastUpdatedAt: String) {
        self.userId = userId
        self.preferredDocumentLength = preferredDocumentLength
        self.preferredStyle = preferredStyle
        self.preferredTerms = preferredTerms
        self.frequentMaterials = frequentMaterials
        self.speechAliases = speechAliases
        self.documentPreferences = documentPreferences
        self.lastUpdatedAt = lastUpdatedAt
    }

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case preferredDocumentLength = "preferred_document_length"
        case preferredStyle = "preferred_style"
        case preferredTerms = "preferred_terms"
        case frequentMaterials = "frequent_materials"
        case speechAliases = "speech_aliases"
        case documentPreferences = "document_preferences"
        case lastUpdatedAt = "last_updated_at"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        userId = try c.decode(String.self, forKey: .userId)
        preferredDocumentLength = try c.decode(PractitionerLearningProfilePreferredDocumentLength.self, forKey: .preferredDocumentLength)
        preferredStyle = try c.decode(PractitionerLearningProfilePreferredStyle.self, forKey: .preferredStyle)
        preferredTerms = try c.decode([String: String].self, forKey: .preferredTerms)
        frequentMaterials = try c.decode([String].self, forKey: .frequentMaterials)
        speechAliases = try c.decode([SpeechAlias].self, forKey: .speechAliases)
        documentPreferences = try c.decode([String: JSONValue].self, forKey: .documentPreferences)
        lastUpdatedAt = try c.decode(String.self, forKey: .lastUpdatedAt)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(userId, forKey: .userId)
        try c.encode(preferredDocumentLength, forKey: .preferredDocumentLength)
        try c.encode(preferredStyle, forKey: .preferredStyle)
        try c.encode(preferredTerms, forKey: .preferredTerms)
        try c.encode(frequentMaterials, forKey: .frequentMaterials)
        try c.encode(speechAliases, forKey: .speechAliases)
        try c.encode(documentPreferences, forKey: .documentPreferences)
        try c.encode(lastUpdatedAt, forKey: .lastUpdatedAt)
    }
}

public struct EvaluationRun: Codable, Equatable, Sendable {
    public var evaluationRunId: String
    public var component: String
    public var candidateVersion: String
    public var datasetVersion: String
    public var metrics: [String: Double]
    public var criticalRegressions: [String]
    public var createdAt: String
    public var releaseGatePassed: Bool

    public init(evaluationRunId: String, component: String, candidateVersion: String, datasetVersion: String, metrics: [String: Double], criticalRegressions: [String], createdAt: String, releaseGatePassed: Bool) {
        self.evaluationRunId = evaluationRunId
        self.component = component
        self.candidateVersion = candidateVersion
        self.datasetVersion = datasetVersion
        self.metrics = metrics
        self.criticalRegressions = criticalRegressions
        self.createdAt = createdAt
        self.releaseGatePassed = releaseGatePassed
    }

    enum CodingKeys: String, CodingKey {
        case evaluationRunId = "evaluation_run_id"
        case component = "component"
        case candidateVersion = "candidate_version"
        case datasetVersion = "dataset_version"
        case metrics = "metrics"
        case criticalRegressions = "critical_regressions"
        case createdAt = "created_at"
        case releaseGatePassed = "release_gate_passed"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        evaluationRunId = try c.decode(String.self, forKey: .evaluationRunId)
        component = try c.decode(String.self, forKey: .component)
        candidateVersion = try c.decode(String.self, forKey: .candidateVersion)
        datasetVersion = try c.decode(String.self, forKey: .datasetVersion)
        metrics = try c.decode([String: Double].self, forKey: .metrics)
        criticalRegressions = try c.decode([String].self, forKey: .criticalRegressions)
        createdAt = try c.decode(String.self, forKey: .createdAt)
        releaseGatePassed = try c.decode(Bool.self, forKey: .releaseGatePassed)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(evaluationRunId, forKey: .evaluationRunId)
        try c.encode(component, forKey: .component)
        try c.encode(candidateVersion, forKey: .candidateVersion)
        try c.encode(datasetVersion, forKey: .datasetVersion)
        try c.encode(metrics, forKey: .metrics)
        try c.encode(criticalRegressions, forKey: .criticalRegressions)
        try c.encode(createdAt, forKey: .createdAt)
        try c.encode(releaseGatePassed, forKey: .releaseGatePassed)
    }
}
