import SwiftUI

@main
struct OrisApp: App {
    @State private var client = Connexion.client()
    /// Change à chaque reconnexion : toute l'interface repart avec le nouveau client.
    @State private var generation = 0

    var body: some Scene {
        WindowGroup {
            RootView(client: client) {
                client = Connexion.client()
                generation += 1
            }
            .id(generation)
        }
    }
}
