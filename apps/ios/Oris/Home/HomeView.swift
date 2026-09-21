import SwiftUI

/// S01 — Accueil iPhone, sur le modèle de l'accueil du site : la date, le grand bandeau
/// vert pour commencer, puis ce qui attend une relecture.
struct HomeView: View {
    @State var model: HomeViewModel
    let client: APIClient
    @State private var showNewConsultation = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: OrisSpacing.s24) {
                    MarqueOris()
                        .padding(.top, OrisSpacing.s4)

                    EnTetePage(surtitre: DateOris.jour(Date()), titre: "Accueil")

                    BandeauCommencer { showNewConsultation = true }

                    CarteARelire(consultations: model.aRelire)

                    ServerStatusCard(state: model.serverState, diagnostic: model.diagnostic)
                }
                .padding(.horizontal, OrisSpacing.s16)
                .padding(.bottom, OrisSpacing.s32)
            }
            .pageOris()
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(for: String.self) { id in
                ConsultationDetailView(model: ConsultationDetailViewModel(encounterId: id, client: client))
            }
            .refreshable { await model.refresh() }
            .task { await model.refresh() }
            .fullScreenCover(isPresented: $showNewConsultation) {
                NewConsultationView(client: client) { showNewConsultation = false }
            }
        }
    }
}

/// « Commencer une consultation » : le cœur de l'app, à la taille du cœur de l'app.
struct BandeauCommencer: View {
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: OrisSpacing.s16) {
                Image("Symbole-creme")
                    .resizable()
                    .interpolation(.high)
                    .frame(width: 34, height: 34)
                    .frame(width: 68, height: 68)
                    .background(.white.opacity(0.13), in: Circle())
                    .overlay(Circle().strokeBorder(.white.opacity(0.22), lineWidth: 1))
                VStack(alignment: .leading, spacing: 5) {
                    Text("Commencer une consultation")
                        .font(Police.marque(23))
                        .tracking(-0.4)
                        .foregroundStyle(.white)
                        .multilineTextAlignment(.leading)
                        .fixedSize(horizontal: false, vertical: true)
                    Text("Oris écoute. Le dossier sera prêt avant la fin du rendez-vous.")
                        .font(Police.interface(14, .semibold, relativeTo: .subheadline))
                        .foregroundStyle(Teinte.accentClair)
                        .multilineTextAlignment(.leading)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 22)
            .background(
                LinearGradient(colors: [Teinte.accentVif, Teinte.accent, Teinte.accentFonce],
                               startPoint: .topLeading, endPoint: .bottomTrailing),
                in: RoundedRectangle(cornerRadius: 22, style: .continuous)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .strokeBorder(Teinte.accentFonce, lineWidth: 1)
            )
            .shadow(color: Teinte.accentFonce.opacity(0.25), radius: 2, y: 2)
            .shadow(color: Teinte.accentFonce.opacity(0.45), radius: 22, y: 16)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Commencer une consultation")
    }
}

/// Les comptes rendus qui attendent la relecture, comme la carte « À relire » du site.
struct CarteARelire: View {
    let consultations: [EncounterSummary]

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
            HStack {
                Text("À relire")
                    .font(Police.titreCarte)
                    .foregroundStyle(Teinte.encre)
                Spacer()
                Text("\(consultations.count)")
                    .font(Police.interface(13, .heavy))
                    .foregroundStyle(Teinte.attention)
                    .frame(minWidth: 26, minHeight: 26)
                    .background(Teinte.attentionDouce, in: Circle())
            }
            if consultations.isEmpty {
                Text("Rien n’attend votre relecture.")
                    .font(Police.note)
                    .foregroundStyle(Teinte.encreTresDouce)
            }
            ForEach(consultations.prefix(6)) { consultation in
                NavigationLink(value: consultation.id) {
                    HStack(spacing: OrisSpacing.s12) {
                        VStack(alignment: .leading, spacing: 3) {
                            NomPatient(patient: consultation.patient, taille: 15.5)
                            Text(detail(consultation))
                                .font(Police.interface(12.5, .medium, relativeTo: .caption))
                                .foregroundStyle(Teinte.encreTresDouce)
                        }
                        Spacer(minLength: OrisSpacing.s8)
                        Pastille(texte: "à relire", ton: .attention)
                        Image(systemName: "chevron.right")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(Teinte.traitFort)
                    }
                    .padding(.vertical, 6)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                if consultation.id != consultations.prefix(6).last?.id {
                    Divider().overlay(Teinte.trait)
                }
            }
        }
        .carte()
    }

    private func detail(_ consultation: EncounterSummary) -> String {
        let quand = consultation.date.map { "\(DateOris.court($0)) \(DateOris.heure($0))" } ?? ""
        let n = consultation.documents.count
        return n == 0 ? quand : "\(quand) · \(n) document\(n > 1 ? "s" : "")"
    }
}

struct ServerStatusCard: View {
    let state: HomeViewModel.ServerState
    var diagnostic: String? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
            Text("État du service")
                .font(Police.titreCarte)
                .foregroundStyle(Teinte.encre)

            // L'état est écrit en toutes lettres, jamais porté par la seule couleur.
            switch state {
            case .checking:
                Label("Vérification du serveur…", systemImage: "hourglass")
                    .foregroundStyle(Teinte.encreDouce)
            case .unreachable:
                Label("Serveur Oris injoignable", systemImage: "exclamationmark.triangle")
                    .foregroundStyle(Teinte.alerte)
                if let diagnostic {
                    Text(diagnostic)
                        .font(Police.note)
                        .foregroundStyle(Teinte.encreDouce)
                        .fixedSize(horizontal: false, vertical: true)
                }
            case .reachable(let health):
                Label("Serveur Oris connecté · version \(health.version)", systemImage: "checkmark.circle")
                    .foregroundStyle(Teinte.accent)
                if health.providers.allMock {
                    Text("Mode démonstration : aucun moteur d’IA réel n’est branché.")
                        .font(Police.note)
                        .foregroundStyle(Teinte.encreDouce)
                }
            }
        }
        .font(Police.interface(15, .semibold))
        .carte()
        .accessibilityElement(children: .combine)
    }
}
