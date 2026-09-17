import Foundation

/// Libellés français de l'interface iPhone (mêmes termes que le web).
enum Labels {
    static func encounterStatus(_ status: ClinicalEncounterStatus) -> String {
        switch status {
        case .draft: "Brouillon"
        case .recording: "En écoute"
        case .paused: "En pause"
        case .finalizing: "Finalisation"
        case .processing: "Traitement en cours"
        case .review: "À valider"
        case .validated: "Validée"
        case .exported: "Exportée"
        case .archived: "Archivée"
        case .audioError: "Erreur audio"
        case .uploadInterrupted: "Envoi interrompu"
        case .transcriptionFailed: "Transcription impossible"
        case .generationFailed: "Extraction refusée"
        }
    }

    static func documentStatus(_ status: DocumentStatus) -> String {
        switch status {
        case .draftAi: "Brouillon Oris"
        case .needsReview: "À vérifier"
        case .validated: "Validé"
        case .exported: "Exporté"
        case .superseded: "Remplacé"
        case .outdated: "Périmé"
        }
    }

    static func documentType(_ type: DocumentDocumentType) -> String {
        switch type {
        case .consultationNote: "Compte rendu"
        case .treatmentPlanText: "Plan"
        case .operativeNote: "Opératoire"
        case .patientSummary: "Résumé"
        case .referralLetter: "Courrier"
        }
    }

    static func assertion(_ value: ClinicalFactAssertion) -> String {
        switch value {
        case .present: "présent"
        case .absent: "absent"
        case .uncertain: "incertain"
        }
    }

    static func clinicalStatus(_ value: ClinicalFactClinicalStatus) -> String {
        switch value {
        case .patientReported: "rapporté par le patient"
        case .observed: "constaté"
        case .clinicianAssessment: "évaluation du praticien"
        case .differential: "hypothèse"
        case .discussed: "discuté"
        case .proposed: "proposé"
        case .accepted: "accepté"
        case .refused: "refusé"
        case .deferred: "reporté"
        case .planned: "prévu"
        case .performed: "réalisé"
        }
    }

    static func certainty(_ value: ClinicalFactCertainty) -> String {
        switch value {
        case .certain: "certain"
        case .probable: "probable"
        case .possible: "possible"
        case .unknown: "indéterminé"
        }
    }

    static func issue(_ code: String) -> String {
        switch code {
        case "unsupported_claim": "Phrase sans fait d’appui"
        case "unknown_fact_id": "Phrase citant un fait inconnu"
        case "tooth_not_supported": "Dent citée absente des faits"
        case "performed_not_supported": "« Réalisé » sans acte réalisé"
        case "fact_not_rendered": "Fait non repris dans le document"
        case "unrendered_concept": "Élément non reconnu à rédiger"
        default: code
        }
    }
}
