import SwiftUI

@main
struct OrisApp: App {
    @State private var client: APIClient
    /// Change à chaque reconnexion : toute l'interface repart avec le nouveau client.
    @State private var generation = 0
    @State private var ouverture = true
    @State private var verrou = Verrou()
    @Environment(\.scenePhase) private var scenePhase

    init() {
        Connexion.reglerDepuisLeMac()
        ApparenceOris.appliquer()
        if !["localhost", "127.0.0.1", "::1"].contains(Connexion.serveur.host() ?? "") {
            ReseauLocal.demanderLAutorisation()
        }
        _client = State(initialValue: Connexion.client())
    }

    var body: some Scene {
        WindowGroup {
            ZStack {
                RootView(client: client) {
                    client = Connexion.client()
                    generation += 1
                }
                .id(generation)

                if verrou.verrouille && !ouverture {
                    EcranVerrou(verrou: verrou)
                        .transition(.opacity)
                }
                if ouverture {
                    EcranOuverture()
                        .transition(.opacity)
                }
            }
            .animation(.easeInOut(duration: 0.35), value: ouverture)
            .animation(.easeInOut(duration: 0.25), value: verrou.verrouille)
            // Le site n'a qu'une apparence : l'app ne bascule pas en sombre avec l'iPhone.
            .preferredColorScheme(.light)
            .task {
                // Le logo en grand, 2,3 secondes, puis l'accueil (ou Face ID).
                try? await Task.sleep(for: .seconds(2.3))
                ouverture = false
                await verrou.deverrouiller()
            }
            .onChange(of: scenePhase) { _, phase in
                verrou.changement(phase)
                if phase == .active, verrou.verrouille, !ouverture {
                    Task { await verrou.deverrouiller() }
                }
            }
        }
    }
}
