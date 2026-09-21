import SwiftUI

/// Navigation principale iPhone (docs/UI_SCREEN_SPEC.md).
struct RootView: View {
    let client: APIClient
    /// Après un changement de serveur ou de jeton dans Paramètres.
    var reconnect: () -> Void = {}

    var body: some View {
        TabView {
            Tab("Accueil", systemImage: "house") {
                HomeView(model: HomeViewModel(client: client), client: client)
            }
            Tab("Patients", systemImage: "person.2") {
                NewConsultationView(client: client, onClose: {}, embedded: true)
            }
            Tab("Consultations", systemImage: "waveform") {
                ConsultationsView(model: ConsultationsViewModel(client: client), client: client)
            }
            Tab("Correspondants", systemImage: "person.crop.rectangle.stack") {
                CarnetView(client: client)
            }
            Tab("Paramètres", systemImage: "gearshape") {
                SettingsView(model: HomeViewModel(client: client), client: client, reconnect: reconnect)
            }
        }
        .tint(Teinte.accent)
    }
}
