import SwiftUI

/// S01 — Accueil iPhone : action principale en un geste, état du service visible.
struct HomeView: View {
    @State var model: HomeViewModel
    let client: APIClient
    @State private var showNewConsultation = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: OrisSpacing.s24) {
                    VStack(alignment: .leading, spacing: OrisSpacing.s8) {
                        Text("Oris")
                            .font(.headline)
                            .foregroundStyle(OrisColor.deepGreen)
                        Text("Bonjour")
                            .font(.largeTitle.bold())
                            .foregroundStyle(OrisColor.deepGreen)
                    }

                    VStack(alignment: .leading, spacing: OrisSpacing.s8) {
                        Button {
                            showNewConsultation = true
                        } label: {
                            Text("Nouvelle consultation")
                                .font(.title3.bold())
                                .frame(maxWidth: .infinity, minHeight: 56)
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(OrisColor.orisGreen)
                        .clipShape(RoundedRectangle(cornerRadius: OrisRadius.button))

                        Text("Oris écoute ; le compte rendu vous attend ensuite dans « Consultations », ici ou sur l’ordinateur.")
                            .font(.footnote)
                            .foregroundStyle(OrisColor.ink)
                    }

                    ServerStatusCard(state: model.serverState)
                }
                .padding(OrisSpacing.s16)
            }
            .background(OrisColor.sand)
            .refreshable { await model.refresh() }
            .task { await model.refresh() }
            .fullScreenCover(isPresented: $showNewConsultation) {
                NewConsultationView(client: client) { showNewConsultation = false }
            }
        }
    }
}

struct ServerStatusCard: View {
    let state: HomeViewModel.ServerState

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
            Text("État du service")
                .font(.headline)
                .foregroundStyle(OrisColor.deepGreen)

            // L'état est écrit en toutes lettres, jamais porté par la seule couleur.
            switch state {
            case .checking:
                Label("Vérification du serveur…", systemImage: "hourglass")
            case .unreachable:
                Label("Serveur Oris injoignable", systemImage: "exclamationmark.triangle")
                    .foregroundStyle(OrisColor.danger)
            case .reachable(let health):
                Label("Serveur Oris connecté · version \(health.version)", systemImage: "checkmark.circle")
                    .foregroundStyle(OrisColor.success)
                if health.providers.allMock {
                    Text("Mode démonstration : aucun moteur d’IA réel n’est branché.")
                        .font(.footnote)
                        .foregroundStyle(OrisColor.ink)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(OrisSpacing.s16)
        .background(OrisColor.white, in: RoundedRectangle(cornerRadius: OrisRadius.card))
        .accessibilityElement(children: .combine)
    }
}
