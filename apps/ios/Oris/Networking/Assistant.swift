import Foundation

/// Ce qu'Oris a compris d'une demande de correction — avant d'y toucher.
struct LectureAssistant: Decodable, Equatable, Sendable {
    /// « dossier », « redaction », « civilite » ou « incompris ».
    let nature: String
    let demande: String
    let resume: String
    let consigne: String
    let civilite: String
    /// Les corrections du dossier, telles que le serveur les a écrites : l'app les lui
    /// rend sans les relire — c'est lui qui les valide et les applique.
    let operations: [JSONValue]
    let question: String
    let objectVersion: Int
    /// La demande telle qu'elle est gardée dans l'historique de la consultation.
    let demandeId: String?

    enum CodingKeys: String, CodingKey {
        case nature, demande, resume, consigne, civilite, operations, question
        case objectVersion = "object_version"
        case demandeId = "demande_id"
    }
}

struct ResultatAssistant: Decodable, Equatable, Sendable {
    let applique: Bool
    let message: String
}

struct PropositionRelecture: Decodable, Equatable, Sendable, Identifiable {
    let titre: String
    let detail: String
    let consigne: String
    var id: String { consigne }
}

/// Une demande de l'historique, telle que le serveur la garde.
///
/// La conversation vit en base (Franck, 11/11/2026) : elle survit à l'app fermée et se
/// retrouve sur le site.
struct DemandeServeur: Decodable, Equatable, Sendable {
    let id: String
    let documentId: String?
    let texte: String
    /// lecture, proposee, relecture, application, traitee, annulee, incomprise, echec
    let etat: String
    let lecture: LectureAssistant?
    let propositions: [PropositionRelecture]
    let message: String
    let code: String
    let depuis: String

    enum CodingKeys: String, CodingKey {
        case id, texte, etat, lecture, propositions, message, code, depuis
        case documentId = "document_id"
    }

    /// Depuis quand la demande est dans son état : la barre de progression part de là.
    var depuisLe: Date {
        let lecteur = ISO8601DateFormatter()
        lecteur.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = lecteur.date(from: depuis) { return date }
        lecteur.formatOptions = [.withInternetDateTime]
        return lecteur.date(from: depuis) ?? Date()
    }
}

private struct Relecture: Decodable {
    let propositions: [PropositionRelecture]
}

extension APIClient {
    /// La conversation de la consultation, de la première demande à la dernière.
    func historique(encounterId: String) async throws -> [DemandeServeur] {
        try await get("encounters/\(encounterId)/assistant")
    }

    /// Dit ce que la demande change, sans rien changer — et la garde dans l'historique.
    func comprendre(encounterId: String, demande: String, documentId: String? = nil) async throws
        -> LectureAssistant
    {
        var corps: [String: Any] = ["demande": demande]
        if let documentId { corps["document_id"] = documentId }
        return try await send("encounters/\(encounterId)/assistant", method: "POST",
                              body: corps, delai: 90)
    }

    /// Applique une lecture que le praticien vient de confirmer.
    func appliquer(encounterId: String, documentId: String, lecture: LectureAssistant,
                   retenir: Bool = false, demandeId: String? = nil) async throws -> ResultatAssistant {
        var corps: [String: Any] = ["nature": lecture.nature, "document_id": documentId]
        if let demandeId { corps["demande_id"] = demandeId }
        switch lecture.nature {
        case "dossier":
            let donnees = try JSONEncoder().encode(lecture.operations)
            corps["operations"] = try JSONSerialization.jsonObject(with: donnees)
            corps["expected_object_version"] = lecture.objectVersion
        case "civilite":
            corps["civilite"] = lecture.civilite
        default:
            corps["consignes"] = [lecture.consigne]
            corps["retenir"] = retenir
        }
        // Réécrire un compte rendu prend jusqu'à deux minutes : le délai habituel
        // couperait la réponse d'un travail qui aboutit.
        return try await send("encounters/\(encounterId)/assistant/appliquer", method: "POST",
                              body: corps, delai: 240)
    }

    /// Applique les consignes cochées après une relecture.
    func appliquer(encounterId: String, documentId: String, consignes: [String],
                   retenir: Bool, demandeId: String? = nil) async throws -> ResultatAssistant {
        var corps: [String: Any] = ["nature": "redaction", "document_id": documentId,
                                    "consignes": consignes, "retenir": retenir]
        if let demandeId { corps["demande_id"] = demandeId }
        return try await send("encounters/\(encounterId)/assistant/appliquer", method: "POST",
                              body: corps, delai: 240)
    }

    /// Le praticien écarte une proposition : rien ne change, et c'est noté.
    func annuler(encounterId: String, demandeId: String) async throws {
        let _: DemandeServeur = try await send(
            "encounters/\(encounterId)/assistant/\(demandeId)/annuler", method: "POST", body: [:]
        )
    }

    /// Claude relit le document et propose des améliorations de forme.
    func relire(documentId: String) async throws -> [PropositionRelecture] {
        let relecture: Relecture = try await send("documents/\(documentId)/relecture",
                                                  method: "POST", body: [:], delai: 120)
        return relecture.propositions
    }
}
