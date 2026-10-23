import Foundation
import Observation

@MainActor
@Observable
final class HomeViewModel {
    enum ServerState: Equatable {
        case checking
        case reachable(HealthResponse)
        /// Le serveur répond, mais il **refuse cet iPhone** : jeton absent ou faux.
        /// L'accueil annonçait « connecté » — le contrôle ne portait que sur la santé du
        /// serveur, qui ne demande pas de jeton — et la liste des consultations restait
        /// vide sans rien dire. Deux semaines perdues à chercher côté réseau (24/10/2026).
        case refuse(String)
        case unreachable
    }

    private(set) var serverState: ServerState = .checking
    /// En clair : l'adresse essayée et pourquoi elle n'a pas répondu.
    private(set) var diagnostic: String?
    /// Comptes rendus qui attendent la relecture du praticien.
    private(set) var aRelire: [EncounterSummary] = []
    private let client: APIClient

    init(client: APIClient) {
        self.client = client
    }

    func refresh() async {
        serverState = .checking
        diagnostic = nil
        do {
            let sante = try await client.health()
            do {
                // Une vraie lecture, celle-là, qui exige le jeton : sans elle, « connecté »
                // ne veut rien dire.
                aRelire = try await client.encounters(status: .review)
                serverState = .reachable(sante)
            } catch {
                aRelire = []
                serverState = .refuse(Labels.erreur(error))
            }
        } catch {
            serverState = .unreachable
            diagnostic = Connexion.pourquoi(error, adresse: client.baseURL)
        }
    }
}
