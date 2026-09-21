import SwiftUI

/// S01 — Accueil iPhone, sur le modèle de l'accueil du site : la date, le grand bandeau
/// vert pour commencer, puis ce qui attend une relecture.
struct HomeView: View {
    @State var model: HomeViewModel
    let client: APIClient
    @State private var showNewConsultation = false

    var body: some View {
        NavigationStack {
            GeometryReader { ecran in
                ScrollView {
                    VStack(spacing: OrisSpacing.s24) {
                        // Premier écran : la marque en haut, le bouton au centre. « À relire »
                        // commence plus bas, on le trouve en faisant défiler.
                        VStack(spacing: 0) {
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
                            .padding(.top, OrisSpacing.s8)
                            Spacer(minLength: OrisSpacing.s24)
                            BoutonEcoute { showNewConsultation = true }
                            Spacer(minLength: OrisSpacing.s24)
                            ServerStatusCard(state: model.serverState, diagnostic: model.diagnostic, compact: true)
                            Image(systemName: "chevron.compact.down")
                                .font(.system(size: 22, weight: .semibold))
                                .foregroundStyle(Teinte.traitFort)
                                .padding(.top, 6)
                                .accessibilityHidden(true)
                        }
                        .frame(minHeight: ecran.size.height - 12)

                        CarteARelire(consultations: model.aRelire)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.horizontal, OrisSpacing.s16)
                    .padding(.bottom, OrisSpacing.s32)
                }
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
    @Environment(\.accessibilityReduceMotion) private var sansMouvement

    var body: some View {
        Button(action: action) {
            VStack(spacing: 18) {
                TimelineView(.animation(paused: sansMouvement)) { contexte in
                    let t = contexte.date.timeIntervalSinceReferenceDate
                    // Une respiration : 4,5 s pour inspirer et expirer, le halo en léger décalage.
                    let souffle = sansMouvement ? 0 : sin(t * 2 * .pi / 4.5)
                    let halo = sansMouvement ? 0 : sin(t * 2 * .pi / 4.5 - 0.6)
                    ZStack {
                        Circle()
                            .fill(Teinte.accentDouce.opacity(0.55))
                            .frame(width: 250, height: 250)
                            .scaleEffect(1 + 0.07 * halo)
                        Circle()
                            .fill(Teinte.accentDouce)
                            .frame(width: 214, height: 214)
                            .scaleEffect(1 + 0.05 * halo)
                        Circle()
                            .fill(LinearGradient(colors: [Teinte.accentVif, Teinte.accent, Teinte.accentFonce],
                                                 startPoint: .topLeading, endPoint: .bottomTrailing))
                            .frame(width: 180, height: 180)
                            .overlay(Circle().strokeBorder(.white.opacity(0.16), lineWidth: 1))
                            .shadow(color: Teinte.accentFonce.opacity(0.28), radius: 3, y: 2)
                            .shadow(color: Teinte.accentFonce.opacity(0.4 + 0.1 * souffle), radius: 24 + 6 * souffle, y: 16)
                            .scaleEffect(1 + 0.045 * souffle)
                        SymboleOris(couleur: .white, anime: true)
                            .frame(width: 96, height: 96)
                    }
                    .frame(width: 270, height: 270)
                }
                .scaleEffect(appuye ? 0.95 : 1)
                VStack(spacing: 4) {
                    Text("Commencer une consultation")
                        .font(Police.marque(24))
                        .foregroundStyle(Teinte.accentFonce)
                    Text("Oris écoute. Le dossier sera prêt avant la fin du rendez-vous.")
                        .font(Police.interface(14, .medium))
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
            // Un vrai titre de carte : plus grand, une icône, un filet dessous.
            HStack(spacing: 10) {
                Image(systemName: "doc.text.magnifyingglass")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(Teinte.attention)
                    .frame(width: 34, height: 34)
                    .background(Teinte.attentionDouce, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                VStack(alignment: .leading, spacing: 0) {
                    Text("À relire")
                        .font(Police.interface(20, .heavy, relativeTo: .title3))
                        .foregroundStyle(Teinte.encre)
                    Text(consultations.isEmpty ? "rien en attente"
                         : "\(consultations.count) compte\(consultations.count > 1 ? "s" : "") rendu\(consultations.count > 1 ? "s" : "") à valider")
                        .font(Police.interface(12.5, .semibold))
                        .foregroundStyle(Teinte.encreTresDouce)
                }
                Spacer()
            }
            .padding(.bottom, 6)
            Divider().overlay(Teinte.trait)
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
