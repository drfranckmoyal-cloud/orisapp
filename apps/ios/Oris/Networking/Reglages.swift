import Foundation

// Les réglages du praticien et du cabinet : les mêmes appels que la page Paramètres du site.

struct Cabinet: Codable, Equatable, Sendable {
    var name: String
    var address: String
    var phone: String
    var email: String
    var legal: String
    var city: String
    var practitionerTitle: String
    var qualifications: String
    let practitionerName: String
    var sendingEmail: String

    enum CodingKeys: String, CodingKey {
        case name, address, phone, email, legal, city, qualifications
        case practitionerTitle = "practitioner_title"
        case practitionerName = "practitioner_name"
        case sendingEmail = "sending_email"
    }

    var praticien: String { "\(practitionerTitle) \(practitionerName)".trimmingCharacters(in: .whitespaces) }

    var initiales: String {
        practitionerName.split(separator: " ").compactMap(\.first).prefix(2).map(String.init).joined().uppercased()
    }

    var corps: [String: Any] {
        ["name": name, "address": address, "phone": phone, "email": email, "legal": legal, "city": city,
         "practitioner_title": practitionerTitle, "qualifications": qualifications, "sending_email": sendingEmail]
    }
}

struct PreferencesRedaction: Codable, Equatable, Sendable {
    var documentLength: String
    var terminology: [String: String]

    enum CodingKeys: String, CodingKey {
        case documentLength = "document_length"
        case terminology
    }
}

struct BoiteEnvoi: Codable, Equatable, Sendable {
    let adresse: String
    let configure: Bool
    let raison: String?
    let serveur: String
}

struct Appareil: Codable, Equatable, Sendable, Identifiable {
    let id: String
    let nom: String
    let creeLe: String
    let dernierUsage: String?
    let actif: Bool

    enum CodingKeys: String, CodingKey {
        case id, nom, actif
        case creeLe = "cree_le"
        case dernierUsage = "dernier_usage"
    }
}

struct Voyant: Codable, Equatable, Sendable {
    let etat: String
    let ton: String
    let detail: String
    let ouvrir: String?
}

struct EtatConnecteurs: Codable, Equatable, Sendable {
    let doctolib: Voyant
    let smilecloud: Voyant
    let peutOuvrir: Bool

    enum CodingKeys: String, CodingKey {
        case doctolib, smilecloud
        case peutOuvrir = "peut_ouvrir"
    }
}

extension APIClient {
    func cabinet() async throws -> Cabinet { try await get("me/cabinet") }

    func enregistrer(_ cabinet: Cabinet) async throws -> Cabinet {
        try await send("me/cabinet", method: "PATCH", body: cabinet.corps)
    }

    func preferences() async throws -> PreferencesRedaction { try await get("me/preferences") }

    func longueurDocuments(_ valeur: String) async throws -> PreferencesRedaction {
        try await send("me/preferences", method: "PATCH", body: ["document_length": valeur])
    }

    func boiteEnvoi() async throws -> BoiteEnvoi { try await get("me/boite-envoi") }

    func appareils() async throws -> [Appareil] { try await get("me/appareils") }

    func deconnecter(appareilId: String) async throws {
        try await sansReponse("me/appareils/\(appareilId)", method: "DELETE")
    }

    func connecteurs() async throws -> EtatConnecteurs { try await get("connecteurs") }
}


struct MotDuDictionnaire: Codable, Equatable, Sendable, Identifiable {
    let id: String
    let canonical: String
    let aliases: [String]
    let frequency: Int
}

struct SuggestionOris: Codable, Equatable, Sendable, Identifiable {
    let key: String
    let message: String
    var id: String { key }
}

struct CorrectionFrequente: Codable, Equatable, Sendable {
    let eventType: String
    let detail: String
    let occurrences: Int

    enum CodingKeys: String, CodingKey {
        case detail, occurrences
        case eventType = "event_type"
    }
}

extension APIClient {
    func dictionnaire() async throws -> [MotDuDictionnaire] { try await get("glossary") }
    func suggestionsOris() async throws -> [SuggestionOris] { try await get("me/learning/suggestions") }
    func correctionsFrequentes() async throws -> [CorrectionFrequente] { try await get("me/learning/corrections") }
}
