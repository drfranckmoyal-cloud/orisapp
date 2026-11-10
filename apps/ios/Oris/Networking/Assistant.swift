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

    enum CodingKeys: String, CodingKey {
        case nature, demande, resume, consigne, civilite, operations, question
        case objectVersion = "object_version"
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

private struct Relecture: Decodable {
    let propositions: [PropositionRelecture]
}

extension APIClient {
    /// Dit ce que la demande change, sans rien changer.
    func comprendre(encounterId: String, demande: String) async throws -> LectureAssistant {
        try await send("encounters/\(encounterId)/assistant", method: "POST",
                       body: ["demande": demande], delai: 90)
    }

    /// Applique une lecture que le praticien vient de confirmer.
    func appliquer(encounterId: String, documentId: String, lecture: LectureAssistant,
                   retenir: Bool = false) async throws -> ResultatAssistant {
        var corps: [String: Any] = ["nature": lecture.nature, "document_id": documentId]
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
                   retenir: Bool) async throws -> ResultatAssistant {
        try await send("encounters/\(encounterId)/assistant/appliquer", method: "POST",
                       body: ["nature": "redaction", "document_id": documentId,
                              "consignes": consignes, "retenir": retenir],
                       delai: 240)
    }

    /// Claude relit le document et propose des améliorations de forme.
    func relire(documentId: String) async throws -> [PropositionRelecture] {
        let relecture: Relecture = try await send("documents/\(documentId)/relecture",
                                                  method: "POST", body: [:], delai: 120)
        return relecture.propositions
    }
}
