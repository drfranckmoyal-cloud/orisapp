import Foundation
import Security

/// Ajoute le jeton d'accès à chaque requête : API comme envoi de l'audio.
///
/// Sur le simulateur, le serveur de ce Mac répond sans jeton. Sur l'iPhone, qui passe par
/// le Wi-Fi du cabinet, le serveur exige un jeton : sans lui, il refuse tout.
struct AuthorizingTransport: HTTPTransport {
    let base: any HTTPTransport
    let token: String

    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        var authorized = request
        authorized.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        return try await base.send(authorized)
    }
}

/// Où est le serveur Oris, et avec quel jeton lui parler.
///
/// L'adresse est un réglage ordinaire ; le jeton est un secret, rangé dans le trousseau
/// de l'iPhone (jamais synchronisé, jamais affiché une fois enregistré).
enum Connexion {
    private static let serveurKey = "oris.serveur"
    private static let service = "fr.oris.app.jeton"

    static let serveurParDefaut = URL(string: "http://localhost:8000")!

    /// Variable d'environnement (schéma Xcode) > réglage de l'app > localhost.
    static var serveur: URL {
        if let override = ProcessInfo.processInfo.environment["ORIS_API_URL"],
           let url = URL(string: override) {
            return url
        }
        if let saisi = UserDefaults.standard.string(forKey: serveurKey), let url = adresse(saisi) {
            return url
        }
        return serveurParDefaut
    }

    /// « 192.168.1.20:8000 » ou « http://mac.local:8000 » ; nil si ce n'est pas une adresse.
    static func adresse(_ texte: String) -> URL? {
        let brut = texte.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !brut.isEmpty else { return nil }
        let complet = brut.contains("://") ? brut : "http://\(brut)"
        guard let url = URL(string: complet), url.host() != nil,
              ["http", "https"].contains(url.scheme ?? "") else { return nil }
        return url
    }

    static func enregistrer(serveur: String) {
        let brut = serveur.trimmingCharacters(in: .whitespacesAndNewlines)
        if brut.isEmpty {
            UserDefaults.standard.removeObject(forKey: serveurKey)
        } else {
            UserDefaults.standard.set(brut, forKey: serveurKey)
        }
    }

    static var serveurSaisi: String {
        UserDefaults.standard.string(forKey: serveurKey) ?? ""
    }

    // MARK: Jeton

    static var jeton: String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecReturnData as String: true,
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data, let texte = String(data: data, encoding: .utf8),
              !texte.isEmpty else { return nil }
        return texte
    }

    @discardableResult
    static func enregistrer(jeton: String) -> Bool {
        oublierJeton()
        let attributes: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecValueData as String: Data(jeton.utf8),
            // Utilisable écran verrouillé (envoi de l'audio en arrière-plan), jamais ailleurs.
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]
        return SecItemAdd(attributes as CFDictionary, nil) == errSecSuccess
    }

    static func oublierJeton() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
        ]
        SecItemDelete(query as CFDictionary)
    }

    /// Le client de toute l'app, avec le jeton s'il y en a un.
    static func client() -> APIClient {
        let base = URLSessionTransport(session: .shared)
        guard let jeton else { return APIClient(baseURL: serveur, transport: base) }
        return APIClient(baseURL: serveur, transport: AuthorizingTransport(base: base, token: jeton))
    }
}
