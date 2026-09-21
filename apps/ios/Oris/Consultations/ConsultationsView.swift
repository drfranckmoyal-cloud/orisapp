import SwiftUI

/// Historique des consultations, sur le modèle du site : filtres, bandeau par jour,
/// puis une ligne par consultation — heure, praticien, patient, documents, statut.
struct ConsultationsView: View {
    enum Filtre: String, CaseIterable, Identifiable {
        case toutes = "Toutes"
        case aRelire = "À relire"
        case aEnvoyer = "À envoyer"
        case terminees = "Terminées"
        case aReprendre = "À reprendre"

        var id: String { rawValue }

        func garde(_ e: EncounterSummary) -> Bool {
            switch self {
            case .toutes: true
            case .aRelire: e.status == .review
            // Un document validé qui n'est jamais parti — la page « Envois » du site.
            case .aEnvoyer: e.documents.contains { [.validated, .exported].contains($0.status) && ($0.sentTo ?? []).isEmpty }
            case .terminees: [.validated, .exported, .archived].contains(e.status)
            case .aReprendre: [.draft, .recording, .paused, .audioError, .uploadInterrupted,
                               .transcriptionFailed, .generationFailed].contains(e.status)
            }
        }
    }

    @State var model: ConsultationsViewModel
    let client: APIClient
    @State private var filtre: Filtre = .toutes
    @State private var recherche = ""
    @State private var aSupprimer: EncounterSummary?
    @State private var erreur: String?
    @State private var toast: String?

    var body: some View {
        NavigationStack {
            // Une liste iOS : le geste « glisser pour supprimer » y est natif et fiable.
            List {
                VStack(alignment: .leading, spacing: OrisSpacing.s16) {
                    EnTetePage(surtitre: "Historique", titre: "Consultations")
                    ChoixFiltre(filtre: $filtre)
                    ChampRecherche(texte: $recherche)
                    if let erreur {
                        Text(erreur).font(Police.note).foregroundStyle(Teinte.alerte)
                    }
                }
                .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 4, trailing: 16))
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)

                contenu
            }
            .listStyle(.plain)
            .environment(\.defaultMinListRowHeight, 0)
            .pageOris()
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(for: String.self) { id in
                if case .loaded(let encounters) = model.state,
                   let encounter = encounters.first(where: { $0.id == id }),
                   [.draft, .recording, .paused].contains(encounter.status) {
                    ListeningView(client: client, encounter: encounter) {}
                } else {
                    ConsultationDetailView(model: ConsultationDetailViewModel(encounterId: id, client: client))
                }
            }
            .confirmationDialog(titreSuppression, isPresented: Binding(
                get: { aSupprimer != nil }, set: { if !$0 { aSupprimer = nil } }
            ), titleVisibility: .visible) {
                Button("Supprimer", role: .destructive) {
                    if let e = aSupprimer { Task { await supprimer(e) } }
                }
            } message: {
                Text("La transcription, le dossier clinique et les documents seront effacés, sans retour possible. Le patient et ses photos restent.")
            }
            .toast($toast)
            .refreshable { await model.refresh() }
            .task { await model.refresh() }
        }
    }

    private var titreSuppression: String {
        guard let e = aSupprimer else { return "" }
        let n = e.documents.count
        return "Supprimer la consultation de \(e.patient.displayName)" + (n > 0 ? " et ses \(n) document\(n > 1 ? "s" : "") ?" : " ?")
    }

    private func supprimer(_ e: EncounterSummary) async {
        erreur = nil
        do {
            try await model.supprimer(e.id)
            toast = "Consultation supprimée."
        } catch {
            erreur = Labels.erreur(error)
        }
    }

    @ViewBuilder
    private var contenu: some View {
        switch model.state {
        case .loading:
            ProgressView("Chargement…")
                .tint(Teinte.accent)
                .frame(maxWidth: .infinity)
                .padding(.top, OrisSpacing.s32)
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)
        case .failed:
            MessageVide(icone: "exclamationmark.triangle", titre: "Serveur Oris injoignable",
                        texte: "Tirez vers le bas pour réessayer.")
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)
        case .loaded(let encounters):
            let jours = Self.parJour(encounters.filter { filtre.garde($0) && correspond($0) })
            if jours.isEmpty {
                MessageVide(icone: "waveform", titre: "Aucune consultation",
                            texte: "Commencez une consultation depuis l’accueil.")
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
            }
            ForEach(jours, id: \.jour) { groupe in
                Section {
                    ForEach(groupe.consultations) { encounter in
                        ZStack {
                            // Le lien invisible sous la ligne : pas de chevron système en double.
                            NavigationLink(value: encounter.id) { EmptyView() }.opacity(0)
                            EncounterRow(encounter: encounter)
                        }
                        .listRowInsets(EdgeInsets(top: 0, leading: 16, bottom: 0, trailing: 16))
                        .listRowBackground(
                            FondLigne(premiere: encounter.id == groupe.consultations.first?.id,
                                      derniere: encounter.id == groupe.consultations.last?.id)
                        )
                        .listRowSeparatorTint(Teinte.trait)
                        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                            if encounter.supprimable {
                                Button(role: .destructive) { aSupprimer = encounter } label: {
                                    Label("Supprimer", systemImage: "trash")
                                }
                                .tint(Teinte.alerte)
                            }
                        }
                        .contextMenu {
                            if encounter.supprimable {
                                Button(role: .destructive) { aSupprimer = encounter } label: {
                                    Label("Supprimer la consultation", systemImage: "trash")
                                }
                            }
                        }
                    }
                } header: {
                    BandeauJour(jour: groupe.jour, nombre: groupe.consultations.count)
                        .padding(.horizontal, 16)
                        .padding(.bottom, 4)
                        .background(Teinte.fond)
                        .listRowInsets(EdgeInsets())
                }
                .listSectionSeparator(.hidden)
            }
        }
    }

    private func correspond(_ e: EncounterSummary) -> Bool {
        recherche.isEmpty || e.patient.displayName.localizedCaseInsensitiveContains(recherche)
    }

    static func parJour(_ encounters: [EncounterSummary]) -> [(jour: Date, consultations: [EncounterSummary])] {
        let calendrier = Calendar.current
        let tries = encounters.sorted { ($0.date ?? .distantPast) > ($1.date ?? .distantPast) }
        var groupes: [(jour: Date, consultations: [EncounterSummary])] = []
        for e in tries {
            let jour = calendrier.startOfDay(for: e.date ?? .distantPast)
            if let dernier = groupes.last, dernier.jour == jour {
                groupes[groupes.count - 1].consultations.append(e)
            } else {
                groupes.append((jour, [e]))
            }
        }
        return groupes
    }
}

/// Les onglets de filtre du site : une pilule blanche sur le fond sable.
struct ChoixFiltre: View {
    @Binding var filtre: ConsultationsView.Filtre

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 4) {
                ForEach(ConsultationsView.Filtre.allCases) { f in
                    Button {
                        filtre = f
                    } label: {
                        Text(f.rawValue)
                            .font(Police.interface(14, f == filtre ? .bold : .semibold))
                            .foregroundStyle(f == filtre ? Teinte.accent : Teinte.encreDouce)
                            .padding(.horizontal, 14)
                            .frame(minHeight: 36)
                            .background {
                                if f == filtre {
                                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                                        .fill(Teinte.surface)
                                        .shadow(color: Teinte.encre.opacity(0.1), radius: 3, y: 1)
                                }
                            }
                    }
                    .buttonStyle(.plain)
                    .accessibilityAddTraits(f == filtre ? .isSelected : [])
                }
            }
            .padding(4)
            .background(Teinte.surfaceDouce, in: RoundedRectangle(cornerRadius: 13, style: .continuous))
        }
    }
}

/// « AUJOURD’HUI  lundi 21 septembre ———— 6 consultations »
struct BandeauJour: View {
    let jour: Date
    let nombre: Int

    var body: some View {
        HStack(spacing: OrisSpacing.s8) {
            if let repere = DateOris.repere(jour) {
                Text(repere.uppercased())
                    .font(Police.interface(11.5, .heavy, relativeTo: .caption))
                    .tracking(0.9)
                    .foregroundStyle(Teinte.accent)
                    .fixedSize()
            }
            Text(DateOris.jour(jour))
                .font(Police.interface(13, .semibold, relativeTo: .caption))
                .foregroundStyle(Teinte.encreDouce)
                .lineLimit(1)
                .fixedSize()
            Rectangle().fill(Teinte.traitFort).frame(height: 1)
            Text("\(nombre)")
                .font(Police.interface(12, .heavy, relativeTo: .caption))
                .foregroundStyle(Teinte.encreTresDouce)
                .fixedSize()
                .accessibilityLabel("\(nombre) consultation\(nombre > 1 ? "s" : "")")
        }
        .padding(.top, OrisSpacing.s8)
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isHeader)
    }
}

struct EncounterRow: View {
    let encounter: EncounterSummary

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Text(encounter.date.map(DateOris.heure) ?? "—")
                .font(Police.interface(13, .bold).monospacedDigit())
                .foregroundStyle(Teinte.encreDouce)
                .frame(width: 42, alignment: .leading)
                .padding(.top, 1)
            Vignette(initiales: encounter.practitioner?.initiales ?? "FM", taille: 24)
            VStack(alignment: .leading, spacing: 4) {
                NomPatient(patient: encounter.patient, taille: 15.5)
                Flux(espace: 10) {
                    StatutLeger(texte: Labels.encounterStatus(encounter.status), ton: encounter.status.ton)
                    if !encounter.documents.isEmpty {
                        DocumentsLegers(documents: encounter.documents)
                    }
                }
                if encounter.criticalWarningCount > 0 {
                    Label("Alerte critique", systemImage: "exclamationmark.triangle.fill")
                        .font(Police.interface(12, .bold))
                        .foregroundStyle(Teinte.alerte)
                }
            }
            Spacer(minLength: 4)
            Image(systemName: "chevron.right")
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(Teinte.traitFort)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
    }
}

extension View {
    /// Un appui long propose de supprimer, seulement si la ligne peut l'être.
    @ViewBuilder
    func supprimable(_ possible: Bool, _ action: @escaping () -> Void) -> some View {
        if possible {
            contextMenu {
                Button(role: .destructive, action: action) { Label("Supprimer la consultation", systemImage: "trash") }
            }
        } else {
            self
        }
    }
}

/// Le fond blanc d'une ligne, arrondi en haut de la première et en bas de la dernière :
/// les lignes d'un même jour forment une carte, comme sur le site.
struct FondLigne: View {
    let premiere: Bool
    let derniere: Bool

    var body: some View {
        UnevenRoundedRectangle(
            topLeadingRadius: premiere ? OrisRadius.card : 0,
            bottomLeadingRadius: derniere ? OrisRadius.card : 0,
            bottomTrailingRadius: derniere ? OrisRadius.card : 0,
            topTrailingRadius: premiere ? OrisRadius.card : 0,
            style: .continuous
        )
        .fill(Teinte.surface)
        .padding(.horizontal, 16)
    }
}

/// Un écran vide qui dit pourquoi, dans une carte.
struct MessageVide: View {
    let icone: String
    let titre: String
    let texte: String

    var body: some View {
        VStack(spacing: OrisSpacing.s8) {
            Image(systemName: icone)
                .font(.system(size: 26, weight: .semibold))
                .foregroundStyle(Teinte.accent)
            Text(titre).font(Police.titreCarte).foregroundStyle(Teinte.encre)
            Text(texte).font(Police.note).foregroundStyle(Teinte.encreDouce)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .carte(rembourrage: OrisSpacing.s24)
    }
}

/// Des pastilles côte à côte, qui passent à la ligne au lieu d'être coupées.
struct Flux: Layout {
    var espace: CGFloat = 4

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let largeur = proposal.width ?? .infinity
        var x: CGFloat = 0, y: CGFloat = 0, ligne: CGFloat = 0, plusLarge: CGFloat = 0
        for vue in subviews {
            let taille = vue.sizeThatFits(.unspecified)
            if x > 0, x + taille.width > largeur {
                y += ligne + espace; x = 0; ligne = 0
            }
            x += taille.width + espace
            ligne = max(ligne, taille.height)
            plusLarge = max(plusLarge, x - espace)
        }
        return CGSize(width: min(plusLarge, largeur), height: y + ligne)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, ligne: CGFloat = 0
        for vue in subviews {
            let taille = vue.sizeThatFits(.unspecified)
            if x > bounds.minX, x + taille.width > bounds.maxX {
                y += ligne + espace; x = bounds.minX; ligne = 0
            }
            vue.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(taille))
            x += taille.width + espace
            ligne = max(ligne, taille.height)
        }
    }
}
