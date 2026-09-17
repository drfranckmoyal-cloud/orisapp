import SwiftUI

/// Navigation principale iPhone (docs/UI_SCREEN_SPEC.md) : seul l'accueil existe en M0.
struct RootView: View {
    let client: APIClient

    var body: some View {
        TabView {
            Tab("Accueil", systemImage: "house") {
                HomeView(model: HomeViewModel(client: client))
            }
            Tab("Patients", systemImage: "person.2") {
                PlaceholderView(title: "Patients")
            }
            Tab("Consultations", systemImage: "waveform") {
                ConsultationsView(model: ConsultationsViewModel(client: client), client: client)
            }
            Tab("Paramètres", systemImage: "gearshape") {
                PlaceholderView(title: "Paramètres")
            }
        }
        .tint(OrisColor.orisBlue)
    }
}

private struct PlaceholderView: View {
    let title: String

    var body: some View {
        NavigationStack {
            ContentUnavailableView(
                title,
                systemImage: "hammer",
                description: Text("Disponible à une prochaine étape du développement.")
            )
            .navigationTitle(title)
        }
    }
}
