import SwiftUI

/// S01 — Accueil iPhone, sur le modèle de l'accueil du site : la date, le grand bandeau
/// vert pour commencer, puis ce qui attend une relecture.
struct HomeView: View {
    @State var model: HomeViewModel
    let client: APIClient
    @State private var showNewConsultation = false
    @State private var chemin: [String] = []
    @State private var tiroirOuvert = false

    var body: some View {
        NavigationStack(path: $chemin) {
            // Tout tient sur un écran : la marque en haut, le bouton au centre, et « À relire »
            // en tiroir au bas de l'écran — visible sans rien faire défiler.
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

                Spacer(minLength: OrisSpacing.s16)
                BoutonEcoute { showNewConsultation = true }
                Spacer(minLength: OrisSpacing.s16)

                ServerStatusCard(state: model.serverState, diagnostic: model.diagnostic, compact: true)
                    .padding(.bottom, 10)
                TiroirARelire(consultations: model.aRelire) { tiroirOuvert = true }
            }
            .padding(.horizontal, OrisSpacing.s16)
            .padding(.bottom, OrisSpacing.s8)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Teinte.fond.ignoresSafeArea())
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(for: String.self) { id in
                ConsultationDetailView(model: ConsultationDetailViewModel(encounterId: id, client: client))
            }
            .sheet(isPresented: $tiroirOuvert) {
                PanneauARelire(consultations: model.aRelire) { id in
                    tiroirOuvert = false
                    chemin.append(id)
                }
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
                .presentationBackground(Teinte.fond)
                .presentationCornerRadius(28)
            }
            .task { await model.refresh() }
            .onAppear { Task { await model.refresh() } }
            .fullScreenCover(isPresented: $showNewConsultation) {
                NewConsultationView(client: client) { showNewConsultation = false }
            }
        }
    }
}

/// « À relire », replié en bas de l'accueil : le nombre et les premiers noms se voient
/// d'un coup d'œil ; un toucher ou un geste vers le haut ouvre la liste.
struct TiroirARelire: View {
    let consultations: [EncounterSummary]
    let ouvrir: () -> Void

    private var noms: String {
        let premiers = consultations.prefix(2).map { $0.patient.lastName.uppercased() }
        let reste = consultations.count - premiers.count
        let liste = premiers.joined(separator: ", ")
        return reste > 0 ? "\(liste) et \(reste) autre\(reste > 1 ? "s" : "")" : liste
    }

    var body: some View {
        Button(action: ouvrir) {
            VStack(spacing: 8) {
                Capsule()
                    .fill(Teinte.traitFort)
                    .frame(width: 38, height: 5)
                HStack(spacing: 12) {
                    Image(systemName: "doc.text.magnifyingglass")
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundStyle(consultations.isEmpty ? Teinte.accent : Teinte.attention)
                        .frame(width: 38, height: 38)
                        .background(consultations.isEmpty ? Teinte.accentDouce : Teinte.attentionDouce,
                                    in: RoundedRectangle(cornerRadius: 11, style: .continuous))
                    VStack(alignment: .leading, spacing: 1) {
                        HStack(spacing: 8) {
                            Text("À relire")
                                .font(Police.interface(18, .heavy, relativeTo: .headline))
                                .foregroundStyle(Teinte.encre)
                            if !consultations.isEmpty {
                                Text("\(consultations.count)")
                                    .font(Police.interface(13, .heavy))
                                    .foregroundStyle(.white)
                                    .frame(minWidth: 22, minHeight: 22)
                                    .padding(.horizontal, 4)
                                    .background(Teinte.attention, in: Capsule())
                            }
                        }
                        Text(consultations.isEmpty ? "Rien n’attend votre relecture" : noms)
                            .font(Police.interface(13, .semibold))
                            .foregroundStyle(Teinte.encreTresDouce)
                            .lineLimit(1)
                    }
                    Spacer(minLength: 4)
                    Image(systemName: "chevron.up")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(Teinte.encreTresDouce)
                }
            }
            .padding(.top, 8)
            .padding(.horizontal, 16)
            .padding(.bottom, 14)
            .background(Teinte.surface, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 24, style: .continuous).strokeBorder(Teinte.trait))
            .shadow(color: Teinte.encre.opacity(0.08), radius: 16, y: -2)
        }
        .buttonStyle(.plain)
        .disabled(consultations.isEmpty)
        .simultaneousGesture(DragGesture(minimumDistance: 12).onEnded { geste in
            if geste.translation.height < -20, !consultations.isEmpty { ouvrir() }
        })
        .accessibilityLabel(consultations.isEmpty ? "Rien à relire"
                            : "\(consultations.count) comptes rendus à relire : \(noms). Ouvrir la liste.")
    }
}

/// Le tiroir déplié : toute la liste « À relire ».
struct PanneauARelire: View {
    let consultations: [EncounterSummary]
    let choisir: (String) -> Void

    var body: some View {
        ScrollView {
            CarteARelire(consultations: consultations, choisir: choisir)
                .padding(OrisSpacing.s16)
                .padding(.top, OrisSpacing.s8)
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
    let choisir: (String) -> Void

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
                ForEach(consultations) { consultation in
                    Button { choisir(consultation.id) } label: {
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
                    if consultation.id != consultations.last?.id {
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
