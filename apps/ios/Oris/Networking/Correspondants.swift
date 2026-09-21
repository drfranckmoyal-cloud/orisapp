import Foundation

// Le carnet de correspondants et la fiche patient modifiable : les mêmes appels que le site.

struct Correspondant: Codable, Equatable, Sendable, Identifiable, Hashable {
    let id: String
    var kind: String
    var title: String
    var lastName: String
    var firstName: String
    var specialty: String
    var practice: String
    var email: String
    var phone: String
    var secondaryEmail: String
    var secondaryPhone: String
    var address: String
    var note: String
    var favorite: Bool

    enum CodingKeys: String, CodingKey {
        case id, kind, title, specialty, practice, email, phone, address, note, favorite
        case lastName = "last_name"
        case firstName = "first_name"
        case secondaryEmail = "secondary_email"
        case secondaryPhone = "secondary_phone"
    }

    var estStructure: Bool { kind == "organisation" }

    /// « Dr Flora ADJEL », ou le nom de la structure.
    var nomCourt: String {
        if estStructure { return lastName }
        return [title, firstName.trimmingCharacters(in: .whitespaces), lastName.uppercased()]
            .filter { !$0.isEmpty }.joined(separator: " ")
    }

    var initiales: String {
        if estStructure { return String(lastName.prefix(2)).uppercased() }
        return "\(firstName.trimmingCharacters(in: .whitespaces).prefix(1))\(lastName.prefix(1))".uppercased()
    }

    /// Couleur de la vignette : celle de la spécialité ; une structure reste neutre.
    func teinte(_ specialites: [String]) -> TeinteVignette {
        estStructure ? .neutre : .specialite(specialty, connues: specialites)
    }

    /// Une fiche vide, pour la création.
    static func nouveau() -> Correspondant {
        Correspondant(id: "", kind: "practitioner", title: "Dr", lastName: "", firstName: "", specialty: "",
                      practice: "", email: "", phone: "", secondaryEmail: "", secondaryPhone: "",
                      address: "", note: "", favorite: false)
    }

    var corps: [String: Any] {
        ["kind": kind, "title": title, "last_name": lastName.trimmingCharacters(in: .whitespaces),
         "first_name": firstName.trimmingCharacters(in: .whitespaces), "specialty": specialty,
         "practice": practice, "email": email.trimmingCharacters(in: .whitespaces), "phone": phone,
         "secondary_email": secondaryEmail.trimmingCharacters(in: .whitespaces),
         "secondary_phone": secondaryPhone, "address": address, "note": note, "favorite": favorite]
    }
}

/// Ce que le lien veut dire : qui a adressé ce patient, à qui on l'adresse.
enum RoleCorrespondant: String, Codable, CaseIterable, Identifiable, Sendable {
    case referredBy = "referred_by"
    case referredTo = "referred_to"
    case alsoFollows = "also_follows"

    var id: String { rawValue }

    var libelle: String {
        switch self {
        case .referredBy: "nous l’a adressé"
        case .referredTo: "nous lui adressons"
        case .alsoFollows: "suit aussi ce patient"
        }
    }

    var court: String {
        switch self {
        case .referredBy: "Adresseur"
        case .referredTo: "Destinataire"
        case .alsoFollows: "Suit aussi"
        }
    }
}

struct Rattachement: Codable, Equatable, Sendable, Identifiable {
    let role: RoleCorrespondant
    let correspondent: Correspondant

    var id: String { correspondent.id }
}

extension APIClient {
    func correspondants(recherche: String? = nil) async throws -> [Correspondant] {
        try await get("correspondents", query: recherche.map { [URLQueryItem(name: "q", value: $0)] } ?? [])
    }

    func specialites() async throws -> [String] {
        try await get("correspondents/specialties")
    }

    func creer(_ correspondant: Correspondant) async throws -> Correspondant {
        try await send("correspondents", method: "POST", body: correspondant.corps)
    }

    func modifier(_ correspondant: Correspondant) async throws -> Correspondant {
        try await send("correspondents/\(correspondant.id)", method: "PATCH", body: correspondant.corps)
    }

    func supprimer(correspondantId: String) async throws {
        try await sansReponse("correspondents/\(correspondantId)", method: "DELETE")
    }

    func rattachements(patientId: String) async throws -> [Rattachement] {
        try await get("patients/\(patientId)/correspondents")
    }

    func rattacher(patientId: String, correspondantId: String, role: RoleCorrespondant) async throws -> [Rattachement] {
        try await send("patients/\(patientId)/correspondents", method: "POST",
                       body: ["correspondent_id": correspondantId, "role": role.rawValue])
    }

    func detacher(patientId: String, correspondantId: String) async throws {
        try await sansReponse("patients/\(patientId)/correspondents/\(correspondantId)", method: "DELETE")
    }

    /// Les champs de la fiche patient ; une date de naissance vide l'efface.
    func modifierPatient(id: String, prenom: String, nom: String, naissance: Date?, email: String,
                         dossier: String, note: String) async throws -> PatientFiche {
        var corps: [String: Any] = [
            "first_name": prenom.trimmingCharacters(in: .whitespaces),
            "last_name": nom.trimmingCharacters(in: .whitespaces),
            "email": email.trimmingCharacters(in: .whitespaces),
            "note": note,
        ]
        let numero = dossier.trimmingCharacters(in: .whitespaces)
        corps["external_id"] = numero.isEmpty ? NSNull() : numero
        corps["birth_date"] = naissance.map(DateOris.jourISO) ?? NSNull()
        return try await send("patients/\(id)", method: "PATCH", body: corps)
    }

    /// Une requête dont la réponse n'a pas de corps (suppression).
    func sansReponse(_ chemin: String, method: String) async throws {
        var request = URLRequest(url: baseURL.appending(path: chemin))
        request.httpMethod = method
        request.timeoutInterval = 30
        let (data, response) = try await transport.send(request)
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            if let error = try? JSONDecoder().decode(APIErrorBody.self, from: data) {
                throw APIError.server(status: http.statusCode, code: error.code, details: error.details ?? [])
            }
            throw APIError.httpStatus(http.statusCode)
        }
    }
}

extension APIClient {
    /// Supprime une consultation : son, transcription, dossier clinique et documents.
    func supprimerConsultation(id: String) async throws {
        try await sansReponse("encounters/\(id)", method: "DELETE")
    }

    /// Rédige à nouveau ce seul document ; les autres ne bougent pas.
    func redigerANouveau(documentId: String) async throws -> [DocumentDetail] {
        try await send("documents/\(documentId)/rediger", method: "POST", body: [:])
    }

    /// Supprime un document ; le dossier clinique de la consultation reste.
    func supprimerDocument(id: String) async throws {
        try await sansReponse("documents/\(id)", method: "DELETE")
    }
}
