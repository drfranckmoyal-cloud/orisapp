import SwiftUI

/// Historique des consultations, sur le modèle du site : filtres, bandeau par jour,
/// puis une ligne par consultation — heure, praticien, patient, documents, statut.
struct ConsultationsView: View {
    enum Filtre: String, CaseIterable, Identifiable {
        case toutes = "Toutes"
        case aRelire = "À relire"
        case terminees = "Terminées"
        case aReprendre = "À reprendre"

        var id: String { rawValue }

        func garde(_ e: EncounterSummary) -> Bool {
            switch self {
            case .toutes: true
            case .aRelire: e.status == .review
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

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: OrisSpacing.s16) {
                    EnTetePage(surtitre: "Historique", titre: "Consultations")

                    ChoixFiltre(filtre: $filtre)
                    ChampRecherche(texte: $recherche)

                    contenu
                }
                .padding(.horizontal, OrisSpacing.s16)
                .padding(.bottom, OrisSpacing.s32)
            }
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
            .refreshable { await model.refresh() }
            .task { await model.refresh() }
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
        case .failed:
            MessageVide(icone: "exclamationmark.triangle", titre: "Serveur Oris injoignable",
                        texte: "Tirez vers le bas pour réessayer.")
        case .loaded(let encounters):
            let jours = Self.parJour(encounters.filter { filtre.garde($0) && correspond($0) })
            if jours.isEmpty {
                MessageVide(icone: "waveform", titre: "Aucune consultation",
                            texte: "Commencez une consultation depuis l’accueil.")
            }
            ForEach(jours, id: \.jour) { groupe in
                BandeauJour(jour: groupe.jour, nombre: groupe.consultations.count)
                VStack(spacing: 0) {
                    ForEach(groupe.consultations) { encounter in
                        NavigationLink(value: encounter.id) {
                            EncounterRow(encounter: encounter)
                        }
                        .buttonStyle(.plain)
                        if encounter.id != groupe.consultations.last?.id {
                            Divider().overlay(Teinte.trait).padding(.leading, 14)
                        }
                    }
                }
                .carte(rembourrage: 0)
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
            VStack(alignment: .leading, spacing: 6) {
                NomPatient(patient: encounter.patient, taille: 15.5)
                Flux(espace: 4) {
                    Pastille(texte: Labels.encounterStatus(encounter.status), ton: encounter.status.ton)
                    ForEach(encounter.documents) { document in
                        PastilleDocument(
                            type: document.documentType,
                            valide: [.validated, .exported].contains(document.status)
                        )
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
        .padding(.vertical, 12)
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
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
