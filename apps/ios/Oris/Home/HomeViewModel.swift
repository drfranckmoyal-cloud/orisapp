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
    private let client: APIClient

    init(client: APIClient) {
        self.client = client
    }

    func refresh() async {
        serverState = .checking
        do {
            serverState = .reachable(try await client.health())
        } catch {
            serverState = .unreachable
        }
    }
}
