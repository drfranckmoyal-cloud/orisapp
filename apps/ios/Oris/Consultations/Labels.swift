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

    /// Le nom complet, pour la liste des documents du dossier.
    /// Les messages d'erreur du site, pour les mêmes codes du serveur.
    static let messages: [String: String] = [
        "SMTP_NOT_CONFIGURED": "La boîte d’envoi n’est pas branchée (mot de passe d’application manquant).",
        "SENDING_EMAIL_MISSING": "Renseignez votre adresse d’envoi dans Paramètres.",
        "SMTP_AUTH_FAILED": "La messagerie a refusé l’identification : vérifiez le mot de passe d’application.",
        "SMTP_RECIPIENT_REFUSED": "Adresse refusée par la messagerie.",
        "SMTP_UNAVAILABLE": "Messagerie injoignable : réessayez dans un instant.",
        "NO_RECIPIENT": "Cochez au moins un destinataire.",
        "EMAIL_INVALID": "Une adresse saisie n’est pas valide.",
        "RECIPIENT_UNKNOWN": "Destinataire inconnu : tirez vers le bas pour actualiser.",
        "FIGURE_NOT_PRINTABLE": "Ce format ne s’imprime pas encore (HEIC, radio, empreinte) : choisissez une photo JPEG ou PNG.",
        "TOO_MANY_FIGURES": "Douze photos au plus par document.",
        "DELIVERY_RECIPIENT_MISSING": "Indiquez à qui le document a été envoyé.",
        "DELIVERY_NOT_FOUND": "Cet envoi a déjà été retiré.",
        "NETWORK_UNREACHABLE": "Serveur Oris injoignable.",
        "MICROPHONE_UNAVAILABLE": "Micro indisponible : autorisez-le dans le iPhone.",
        "OBJECT_VERSION_REQUIRED": "Actualisez avant d’appliquer cette correction.",
        "STT_UNAVAILABLE": "La transcription est indisponible : réessayez dans un instant.",
        "NO_PROCEDURE_TO_DOCUMENT": "Aucun acte n’a été dit : il n’y a pas de compte rendu de soins à rédiger.",
        "DOCUMENT_EMPTY": "Ce document n’a pas encore de contenu.",
        "DOCUMENT_NOT_FOUND": "Ce document est introuvable.",
        "COPY_FAILED": "La copie a échoué : votre iPhone l’a refusée.",
        "DOCUMENT_OUTDATED": "Ce document est périmé : régénérez-le avant de le valider.",
        "DOCUMENT_HAS_CRITICAL_ISSUES": "Le document contient une phrase non justifiée : validation impossible.",
        "WARNING_NOT_ACKNOWLEDGED": "Confirmez d’abord avoir pris connaissance de l’alerte critique.",
        "DOCUMENT_ALREADY_VALIDATED": "Ce document est déjà validé.",
        "DOCUMENTS_NOT_VALIDATED": "Tous les documents doivent être validés avant la consultation.",
        "OBJECT_VERSION_CONFLICT": "La consultation a été modifiée entre-temps : tirez vers le bas pour actualiser.",
        "CORRECTION_REJECTED": "Correction refusée : elle rendrait le dossier incohérent.",
        "TOOTH_NOT_FOUND": "Aucun élément ne porte cette dent.",
        "SAME_TOOTH": "Les deux numéros de dent sont identiques.",
        "NO_CHANGE": "Aucune modification à enregistrer.",
        "FACT_REFERENCED": "Ce fait appuie le plan de traitement : modifiez d’abord le plan.",
        "INVALID_TRANSITION": "Cette action n’est pas possible dans l’état actuel de la consultation.",
        "PATIENT_INFORMATION_REQUIRED": "Confirmez d’abord que le patient a été informé de l’enregistrement.",
        "AUDIO_CHUNKS_MISSING": "Des segments audio ne sont pas arrivés au serveur.",
        "SMILECLOUD_NON_RELIE": "Reliez d’abord ce patient à son dossier SmileCloud.",
        "SMILECLOUD_INVALIDE": "Identifiant de dossier SmileCloud non reconnu.",
        "INVALID_TOKEN": "Jeton refusé : il a pu être désactivé. Créez-en un nouveau sur le Mac.",
    ]

    static func erreur(_ error: Error) -> String {
        if case .server(_, let code, _)? = error as? APIError {
            return messages[code] ?? "Action impossible (\(code))."
        }
        if case .httpStatus(let status)? = error as? APIError {
            return "Le serveur a refusé (\(status))."
        }
        return "Serveur Oris injoignable : vérifiez le Wi-Fi."
    }

    /// « envoyé au patient et au Dr Aubert » : à + le = au, à + les = aux.
    static func envoyeA(_ destinataires: [String]) -> String {
        let noms = destinataires.map { nom -> String in
            if nom.hasPrefix("le ") { return "au " + nom.dropFirst(3) }
            if nom.hasPrefix("les ") { return "aux " + nom.dropFirst(4) }
            return "à " + nom
        }
        guard let dernier = noms.last else { return "" }
        return "envoyé " + (noms.count == 1 ? dernier : noms.dropLast().joined(separator: ", ") + " et " + dernier)
    }

    static func documentTitle(_ type: DocumentDocumentType) -> String {
        switch type {
        case .consultationNote: "Compte rendu de consultation"
        case .treatmentPlanText: "Plan de traitement"
        case .operativeNote: "Compte rendu de soins"
        case .patientSummary: "Résumé patient"
        case .referralLetter: "Courrier d’adressage"
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
