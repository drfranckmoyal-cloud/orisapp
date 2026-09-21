import SwiftUI

@main
struct OrisApp: App {
    @State private var client: APIClient

    init() {
        Connexion.reglerDepuisLeMac()
        ApparenceOris.appliquer()
        if !["localhost", "127.0.0.1", "::1"].contains(Connexion.serveur.host() ?? "") {
            ReseauLocal.demanderLAutorisation()
        }
        _client = State(initialValue: Connexion.client())
    }
    /// Change à chaque reconnexion : toute l'interface repart avec le nouveau client.
    @State private var generation = 0

    var body: some Scene {
        WindowGroup {
            RootView(client: client) {
                client = Connexion.client()
                generation += 1
            }
            .id(generation)
            // Le site n'a qu'une apparence : l'app ne bascule pas en sombre avec l'iPhone.
            .preferredColorScheme(.light)
        }
    }
}
