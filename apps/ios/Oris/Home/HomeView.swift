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
                    // La marque, bien visible, et la date du jour.
                    VStack(spacing: 4) {
                        HStack(spacing: 10) {
                            SymboleOris(couleur: Teinte.accent)
                                .frame(width: 40, height: 40)
                            Text("Oris")
                                .font(Police.marque(40))
                                .foregroundStyle(Teinte.accentFonce)
                        }
                        Text(DateOris.jour(Date()).capitalizedPremiere)
                            .font(Police.interface(14, .semibold))
                            .foregroundStyle(Teinte.encreTresDouce)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.top, OrisSpacing.s8)

                    BoutonEcoute { showNewConsultation = true }
                        .frame(maxWidth: .infinity)

                    CarteARelire(consultations: model.aRelire)

                    ServerStatusCard(state: model.serverState, diagnostic: model.diagnostic, compact: true)
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

/// Le cœur de l'app : le symbole Oris dans un grand rond vert qui respire. Un toucher
/// lance une consultation.
struct BoutonEcoute: View {
    let action: () -> Void
    @State private var appuye = false

    var body: some View {
        Button(action: action) {
            VStack(spacing: 14) {
                ZStack {
                    Circle()
                        .fill(Teinte.accentDouce)
                        .frame(width: 214, height: 214)
                    Circle()
                        .fill(LinearGradient(colors: [Teinte.accentVif, Teinte.accent, Teinte.accentFonce],
                                             startPoint: .topLeading, endPoint: .bottomTrailing))
                        .frame(width: 176, height: 176)
                        .overlay(Circle().strokeBorder(.white.opacity(0.16), lineWidth: 1))
                        .shadow(color: Teinte.accentFonce.opacity(0.28), radius: 3, y: 2)
                        .shadow(color: Teinte.accentFonce.opacity(0.45), radius: 24, y: 16)
                    SymboleOris(couleur: .white, anime: true)
                        .frame(width: 92, height: 92)
                }
                .scaleEffect(appuye ? 0.96 : 1)
                VStack(spacing: 3) {
                    Text("Commencer une consultation")
                        .font(Police.marque(22))
                        .foregroundStyle(Teinte.accentFonce)
                    Text("Oris écoute. Le dossier sera prêt avant la fin du rendez-vous.")
                        .font(Police.interface(13.5, .medium))
                        .foregroundStyle(Teinte.encreDouce)
                        .multilineTextAlignment(.center)
                }
            }
        }
        .buttonStyle(.plain)
        .simultaneousGesture(DragGesture(minimumDistance: 0)
            .onChanged { _ in withAnimation(.easeOut(duration: 0.12)) { appuye = true } }
            .onEnded { _ in withAnimation(.spring(duration: 0.3)) { appuye = false } })
        .accessibilityLabel("Commencer une consultation")
    }
}

/// Les comptes rendus qui attendent la relecture, comme la carte « À relire » du site.
struct CarteARelire: View {
    let consultations: [EncounterSummary]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
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
            VStack(spacing: 0) {
                ForEach(consultations.prefix(6)) { consultation in
                    NavigationLink(value: consultation.id) {
                        HStack(spacing: OrisSpacing.s8) {
                            NomPatient(patient: consultation.patient, taille: 14.5)
                            Spacer(minLength: 4)
                            Text(detail(consultation))
                                .font(Police.interface(12, .medium))
                                .foregroundStyle(Teinte.encreTresDouce)
                                .lineLimit(1)
                            Image(systemName: "chevron.right")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundStyle(Teinte.traitFort)
                        }
                        .padding(.vertical, 8)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    if consultation.id != consultations.prefix(6).last?.id {
                        Divider().overlay(Teinte.trait.opacity(0.7))
                    }
                }
            }
        }
        .carte()
    }

    private func detail(_ consultation: EncounterSummary) -> String {
        guard let date = consultation.date else { return "" }
        return DateOris.repere(date).map { "\($0.lowercased()) \(DateOris.heure(date))" } ?? DateOris.court(date)
    }
}

struct ServerStatusCard: View {
    let state: HomeViewModel.ServerState
    var diagnostic: String? = nil
    /// Accueil : une seule ligne discrète tant que tout va bien.
    var compact = false

    var body: some View {
        if compact, case .reachable = state {
            Label("Connecté au serveur Oris", systemImage: "checkmark.circle.fill")
                .font(Police.interface(12.5, .semibold))
                .foregroundStyle(Teinte.encreTresDouce)
                .frame(maxWidth: .infinity)
        } else {
            complet
        }
    }

    private var complet: some View {
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
