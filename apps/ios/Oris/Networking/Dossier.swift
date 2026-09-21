import Foundation

// Le dossier du patient et le traitement des documents : les mêmes appels que le site.

struct PatientFiche: Codable, Equatable, Sendable {
    let id: String
    let firstName: String
    let lastName: String
    let birthDate: String?
    let externalId: String?
    let email: String
    let note: String

    enum CodingKeys: String, CodingKey {
        case id, email, note
        case firstName = "first_name"
        case lastName = "last_name"
        case birthDate = "birth_date"
        case externalId = "external_id"
    }

    var resume: PatientSummary { PatientSummary(id: id, firstName: firstName, lastName: lastName) }
}

struct PieceJointe: Codable, Equatable, Sendable, Identifiable {
    let id: String
    let filename: String
    let mediaType: String
    let kind: String
    let label: String
    let encounterId: String?
    let createdAt: String

    var estImage: Bool { mediaType.hasPrefix("image/") }

    enum CodingKeys: String, CodingKey {
        case id, filename, kind, label
        case mediaType = "media_type"
        case encounterId = "encounter_id"
        case createdAt = "created_at"
    }
}

struct Figure: Codable, Equatable, Sendable, Identifiable {
    let attachmentId: String
    var caption: String
    let position: Int
    var format: String
    let filename: String
    let mediaType: String

    var id: String { attachmentId }

    enum CodingKeys: String, CodingKey {
        case caption, position, format, filename
        case attachmentId = "attachment_id"
        case mediaType = "media_type"
    }
}

struct CandidatEnvoi: Codable, Equatable, Sendable, Identifiable {
    let cle: String
    let genre: String
    let libelle: String
    let detail: String
    let email: String
    let coche: Bool

    var id: String { cle }
}

struct EnvoiPrepare: Codable, Equatable, Sendable {
    let expediteur: String
    let configure: Bool
    let raison: String?
    let candidats: [CandidatEnvoi]
    let objet: String
    let message: String
    let brouillon: Bool
    let nomFichier: String

    enum CodingKeys: String, CodingKey {
        case expediteur, configure, raison, candidats, objet, message, brouillon
        case nomFichier = "nom_fichier"
    }
}

struct ResultatEnvoi: Codable, Equatable, Sendable {
    let destinataire: String
    let envoye: Bool
    let code: String?
}

/// Un fichier rendu par le serveur (le PDF d'un document, une photo).
struct Fichier: Sendable {
    let donnees: Data
    let nom: String
}

extension APIClient {
    func patient(id: String) async throws -> PatientFiche {
        try await get("patients/\(id)")
    }

    func encounters(patientId: String) async throws -> [EncounterSummary] {
        try await get("encounters", query: [URLQueryItem(name: "patient_id", value: patientId)])
    }

    func piecesJointes(patientId: String) async throws -> [PieceJointe] {
        try await get("patients/\(patientId)/attachments")
    }

    func valider(documentId: String, alertesLues: [String]) async throws -> DocumentDetail {
        try await send("documents/\(documentId)/validate", method: "POST",
                       body: ["acknowledged_warning_codes": alertesLues])
    }

    func modifierTexte(documentId: String, texte: String) async throws -> DocumentDetail {
        try await send("documents/\(documentId)/text", method: "POST", body: ["content": texte])
    }

    func rediger(encounterId: String, courrier: Bool) async throws -> [DocumentDetail] {
        try await send("encounters/\(encounterId)/documents/\(courrier ? "referral-letter" : "operative-note")",
                       method: "POST", body: [:])
    }

    func preparerEnvoi(documentId: String) async throws -> EnvoiPrepare {
        try await get("documents/\(documentId)/envoi")
    }

    func envoyer(documentId: String, destinataires: [String], adresses: [String],
                 objet: String, message: String) async throws -> [ResultatEnvoi] {
        try await send("documents/\(documentId)/envoi", method: "POST", body: [
            "destinataires": destinataires, "adresses": adresses, "objet": objet, "message": message,
        ])
    }

    func figures(documentId: String) async throws -> [Figure] {
        try await get("documents/\(documentId)/figures")
    }

    func enregistrerFigures(documentId: String, _ figures: [Figure]) async throws -> [Figure] {
        try await send("documents/\(documentId)/figures", method: "PUT", body: [
            "figures": figures.map { ["attachment_id": $0.attachmentId, "caption": $0.caption, "format": $0.format] },
        ])
    }

    /// Le PDF du document, avec le nom de fichier choisi par le serveur.
    func pdf(documentId: String) async throws -> Fichier {
        try await fichier(baseURL.appending(path: "documents/\(documentId)/export")
            .appending(queryItems: [URLQueryItem(name: "format", value: "pdf")]))
    }

    /// L'aperçu d'une pièce jointe (les photos HEIC arrivent en JPEG).
    func apercu(pieceJointeId: String) async throws -> Fichier {
        try await fichier(baseURL.appending(path: "patients/attachments/\(pieceJointeId)/apercu"))
    }

    /// Dépose une photo dans le dossier du patient, rattachée à la consultation.
    func deposerPhoto(patientId: String, encounterId: String?, jpeg: Data, nom: String) async throws -> [PieceJointe] {
        let frontiere = "oris-\(UUID().uuidString)"
        var corps = Data()
        func ligne(_ texte: String) { corps.append(Data(texte.utf8)) }
        if let encounterId {
            ligne("--\(frontiere)\r\nContent-Disposition: form-data; name=\"encounter_id\"\r\n\r\n\(encounterId)\r\n")
        }
        ligne("--\(frontiere)\r\nContent-Disposition: form-data; name=\"files\"; filename=\"\(nom)\"\r\n")
        ligne("Content-Type: image/jpeg\r\n\r\n")
        corps.append(jpeg)
        ligne("\r\n--\(frontiere)--\r\n")

        var request = URLRequest(url: baseURL.appending(path: "patients/\(patientId)/attachments"))
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(frontiere)", forHTTPHeaderField: "Content-Type")
        request.httpBody = corps
        request.timeoutInterval = 60
        return try await perform(request)
    }

    private func fichier(_ url: URL) async throws -> Fichier {
        var request = URLRequest(url: url)
        request.timeoutInterval = 60
        let (data, response) = try await transport.send(request)
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            if let error = try? JSONDecoder().decode(APIErrorBody.self, from: data) {
                throw APIError.server(status: http.statusCode, code: error.code, details: error.details ?? [])
            }
            throw APIError.httpStatus(http.statusCode)
        }
        let disposition = http.value(forHTTPHeaderField: "Content-Disposition") ?? ""
        let nom = disposition.components(separatedBy: "filename=\"").dropFirst().first?
            .components(separatedBy: "\"").first ?? url.lastPathComponent
        return Fichier(donnees: data, nom: nom)
    }
}
