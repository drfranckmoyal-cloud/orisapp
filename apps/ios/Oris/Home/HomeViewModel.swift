import Foundation
import Observation

@MainActor
@Observable
final class HomeViewModel {
    enum ServerState: Equatable {
        case checking
        case reachable(HealthResponse)
        case unreachable
    }

    private(set) var serverState: ServerState = .checking
    /// En clair : l'adresse essayée et pourquoi elle n'a pas répondu.
    private(set) var diagnostic: String?
    private let client: APIClient

    init(client: APIClient) {
        self.client = client
    }

    func refresh() async {
        serverState = .checking
        diagnostic = nil
        do {
            serverState = .reachable(try await client.health())
        } catch {
            serverState = .unreachable
            diagnostic = Connexion.pourquoi(error, adresse: client.baseURL)
        }
    }
}
