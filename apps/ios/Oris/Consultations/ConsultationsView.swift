import SwiftUI

struct ConsultationsView: View {
    @State var model: ConsultationsViewModel
    let client: APIClient

    var body: some View {
        NavigationStack {
            Group {
                switch model.state {
                case .loading:
                    ProgressView("Chargement…")
                case .failed:
                    ContentUnavailableView(
                        "Serveur Oris injoignable",
                        systemImage: "exclamationmark.triangle",
                        description: Text("Tirez vers le bas pour réessayer.")
                    )
                case .loaded(let encounters) where encounters.isEmpty:
                    ContentUnavailableView(
                        "Aucune consultation",
                        systemImage: "waveform",
                        description: Text("Lancez une consultation fictive depuis le site web.")
                    )
                case .loaded(let encounters):
                    List(encounters) { encounter in
                        NavigationLink(value: encounter.id) {
                            EncounterRow(encounter: encounter)
                        }
                    }
                }
            }
            .navigationTitle("Consultations")
            .navigationDestination(for: String.self) { id in
                if case .loaded(let encounters) = model.state,
                   let encounter = encounters.first(where: { $0.id == id }),
                   [.draft, .recording, .paused].contains(encounter.status) {
                    ListeningView(client: client, encounter: encounter) {}
                } else {
                    ConsultationDetailView(model: ConsultationDetailViewModel(encounterId: id, client: client))
                }
            }
            .refreshable { await model.refresh() }
            .task { await model.refresh() }
        }
    }
}

struct EncounterRow: View {
    let encounter: EncounterSummary

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s4) {
            Text(encounter.patient.displayName)
                .font(.headline)
                .foregroundStyle(OrisColor.deepGreen)
            HStack(spacing: OrisSpacing.s8) {
                Text(Labels.encounterStatus(encounter.status))
                if encounter.criticalWarningCount > 0 {
                    Label("Alerte critique", systemImage: "exclamationmark.triangle.fill")
                        .foregroundStyle(OrisColor.danger)
                }
            }
            .font(.subheadline)
        }
        .padding(.vertical, OrisSpacing.s4)
        .accessibilityElement(children: .combine)
    }
}
