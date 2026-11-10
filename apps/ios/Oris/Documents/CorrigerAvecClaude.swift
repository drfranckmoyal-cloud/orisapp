import SwiftUI

/// Corriger avec Claude : on dit ce qui ne va pas, Oris dit ce qu'il a compris, on confirme.
///
/// Le même dialogue que sur le site (Franck, 10/11/2026). Sur l'iPhone, la dictée est
/// celle du clavier : le micro à droite de la barre d'espace.
struct CorrigerAvecClaude: View {
    let client: APIClient
    let encounterId: String
    let document: DocumentDetail
    let change: (String) -> Void

    private enum Echange: Identifiable {
        case moi(Int, String)
        case attente(Int, String)
        case fait(Int, String)
        case erreur(Int, String)
        case lecture(Int, LectureAssistant)
        case relecture(Int, [PropositionRelecture])

        var id: Int {
            switch self {
            case .moi(let id, _), .attente(let id, _), .fait(let id, _), .erreur(let id, _),
                 .lecture(let id, _), .relecture(let id, _):
                return id
            }
        }
    }

    @Environment(\.dismiss) private var fermer
    @State private var fil: [Echange] = []
    @State private var saisie = ""
    @State private var occupe = false
    @State private var compteur = 0
    @State private var coches: [Int: Set<String>] = [:]
    @FocusState private var clavier: Bool

    private var relisible: Bool {
        document.documentType == .consultationNote || document.documentType == .referralLetter
    }

    private let suggestions = ["Plus court", "Moins de répétitions", "Phrases plus simples"]

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollViewReader { defile in
                    ScrollView {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Dites ce qui ne va pas, comme à un assistant. Rien ne change sans votre accord.")
                                .font(Police.note)
                                .foregroundStyle(Teinte.encreDouce)
                            ForEach(fil) { echange in
                                bulle(echange).id(echange.id)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(OrisSpacing.s16)
                    }
                    .onChange(of: fil.count) {
                        if let dernier = fil.last { withAnimation { defile.scrollTo(dernier.id, anchor: .bottom) } }
                    }
                }

                VStack(spacing: 8) {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 6) {
                            ForEach(suggestions, id: \.self) { suggestion in
                                puce(suggestion) { Task { await demander(suggestion) } }
                            }
                            if relisible {
                                puce("✦ Relire tout le document") { Task { await relire() } }
                            }
                        }
                        .padding(.horizontal, OrisSpacing.s16)
                    }
                    HStack(spacing: 8) {
                        TextField("« c’est trop long », « la 26 c’est la 27 »…", text: $saisie, axis: .vertical)
                            .lineLimit(1...4)
                            .focused($clavier)
                            .font(Police.interface(15.5, .regular))
                            .padding(.horizontal, 12).padding(.vertical, 10)
                            .background(Teinte.surface, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                            .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).strokeBorder(Teinte.traitFort))
                        Button {
                            Task { await demander(saisie) }
                        } label: {
                            Image(systemName: "arrow.up")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundStyle(.white)
                                .frame(width: 40, height: 40)
                                .background(Teinte.accent, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                        }
                        .disabled(occupe || saisie.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                        .opacity(occupe || saisie.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? 0.45 : 1)
                        .accessibilityLabel("Envoyer la demande")
                    }
                    .padding(.horizontal, OrisSpacing.s16)
                }
                .padding(.vertical, 10)
                .background(Teinte.fond)
            }
            .background(Teinte.fond.ignoresSafeArea())
            .navigationTitle("Corriger avec Claude")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("Fermer") { fermer() } }
            }
        }
        .tint(Teinte.accent)
    }

    // MARK: Bulles

    @ViewBuilder
    private func bulle(_ echange: Echange) -> some View {
        switch echange {
        case .moi(_, let texte):
            Text(texte)
                .font(Police.interface(14.5, .medium))
                .foregroundStyle(.white)
                .padding(.horizontal, 13).padding(.vertical, 9)
                .background(Teinte.accent, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                .frame(maxWidth: .infinity, alignment: .trailing)
        case .attente(_, let texte):
            cadre { Text(texte).italic().foregroundStyle(Teinte.encreDouce) }
        case .fait(_, let texte):
            cadre(fond: Teinte.accentDouce) {
                Label(texte, systemImage: "checkmark").foregroundStyle(Teinte.accent)
            }
        case .erreur(_, let texte):
            cadre(fond: Teinte.alerteDouce) { Text(texte).foregroundStyle(Teinte.alerte) }
        case .lecture(let id, let lecture):
            cadre {
                VStack(alignment: .leading, spacing: 8) {
                    Text(nature(lecture.nature).uppercased())
                        .font(Police.interface(11, .heavy))
                        .foregroundStyle(lecture.nature == "dossier" ? Teinte.attention : Teinte.accent)
                    Text(lecture.resume)
                    if lecture.nature == "redaction" {
                        Text("Consigne : \(lecture.consigne)")
                            .font(Police.note).foregroundStyle(Teinte.encreDouce)
                    }
                    if lecture.nature != "incompris" {
                        Button(principal(lecture.nature)) { Task { await appliquer(id, lecture) } }
                            .buttonStyle(BoutonPrincipal())
                        if lecture.nature == "redaction" {
                            Button("Appliquer et retenir pour toujours") {
                                Task { await appliquer(id, lecture, retenir: true) }
                            }
                            .buttonStyle(BoutonSecondaire())
                        }
                        Button("Annuler") { remplacer(id, .fait(id, "Annulé : rien n’a changé.")) }
                            .font(Police.interface(14, .semibold))
                            .foregroundStyle(Teinte.encreDouce)
                    }
                }
                .disabled(occupe)
            }
        case .relecture(let id, let propositions):
            let choisies = coches[id] ?? []
            cadre {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Relecture — \(propositions.count) amélioration\(propositions.count > 1 ? "s" : "") possible\(propositions.count > 1 ? "s" : ""), aucune ne touche aux faits :")
                    ForEach(propositions) { proposition in
                        Button {
                            var suite = choisies
                            if suite.contains(proposition.consigne) { suite.remove(proposition.consigne) }
                            else { suite.insert(proposition.consigne) }
                            coches[id] = suite
                        } label: {
                            HStack(alignment: .top, spacing: 9) {
                                Image(systemName: choisies.contains(proposition.consigne) ? "checkmark.square.fill" : "square")
                                    .foregroundStyle(Teinte.accent)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(proposition.titre).font(Police.interface(14, .bold)).foregroundStyle(Teinte.encre)
                                    Text(proposition.detail).font(Police.note).foregroundStyle(Teinte.encreDouce)
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        .buttonStyle(.plain)
                    }
                    Button("Appliquer (\(choisies.count))") {
                        Task { await appliquerConsignes(id, Array(choisies), retenir: false) }
                    }
                    .buttonStyle(BoutonPrincipal())
                    .disabled(choisies.isEmpty)
                    Button("Appliquer et retenir pour toujours") {
                        Task { await appliquerConsignes(id, Array(choisies), retenir: true) }
                    }
                    .buttonStyle(BoutonSecondaire())
                    .disabled(choisies.isEmpty)
                }
                .disabled(occupe)
            }
        }
    }

    private func cadre<Contenu: View>(fond: Color = Teinte.surface,
                                      @ViewBuilder _ contenu: () -> Contenu) -> some View {
        contenu()
            .font(Police.interface(14.5, .medium))
            .foregroundStyle(Teinte.encre)
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(fond, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).strokeBorder(Teinte.trait))
    }

    private func puce(_ titre: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(titre)
                .font(Police.interface(13, .semibold))
                .foregroundStyle(Teinte.encreDouce)
                .padding(.horizontal, 12).padding(.vertical, 7)
                .background(Teinte.surface, in: Capsule())
                .overlay(Capsule().strokeBorder(Teinte.trait))
        }
        .buttonStyle(.plain)
        .disabled(occupe)
    }

    private func nature(_ nature: String) -> String {
        switch nature {
        case "dossier": "Dossier clinique"
        case "redaction": "Rédaction"
        case "civilite": "Fiche patient"
        default: "À préciser"
        }
    }

    private func principal(_ nature: String) -> String {
        switch nature {
        case "dossier": "Corriger le dossier"
        case "civilite": "Enregistrer dans la fiche"
        default: "Appliquer ici"
        }
    }

    // MARK: Actions

    private func suivant() -> Int {
        compteur += 1
        return compteur
    }

    private func remplacer(_ id: Int, _ echange: Echange) {
        if let rang = fil.firstIndex(where: { $0.id == id }) { fil[rang] = echange }
    }

    private func demander(_ texte: String) async {
        let demande = texte.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !demande.isEmpty, !occupe else { return }
        saisie = ""
        clavier = false
        fil.append(.moi(suivant(), demande))
        let attente = suivant()
        fil.append(.attente(attente, "Je lis votre demande…"))
        occupe = true
        defer { occupe = false }
        do {
            let lecture = try await client.comprendre(encounterId: encounterId, demande: demande)
            remplacer(attente, .lecture(attente, lecture))
        } catch {
            remplacer(attente, .erreur(attente, Labels.erreur(error)))
        }
    }

    private func appliquer(_ id: Int, _ lecture: LectureAssistant, retenir: Bool = false) async {
        occupe = true
        defer { occupe = false }
        remplacer(id, .attente(id, "J’applique… (une réécriture prend jusqu’à deux minutes)"))
        do {
            let resultat = try await client.appliquer(encounterId: encounterId, documentId: document.id,
                                                      lecture: lecture, retenir: retenir)
            remplacer(id, .fait(id, resultat.message))
            change(resultat.message)
        } catch {
            remplacer(id, .erreur(id, Labels.erreur(error)))
        }
    }

    private func appliquerConsignes(_ id: Int, _ consignes: [String], retenir: Bool) async {
        occupe = true
        defer { occupe = false }
        remplacer(id, .attente(id, "J’applique… (une réécriture prend jusqu’à deux minutes)"))
        do {
            let resultat = try await client.appliquer(encounterId: encounterId, documentId: document.id,
                                                      consignes: consignes, retenir: retenir)
            remplacer(id, .fait(id, resultat.message))
            change(resultat.message)
        } catch {
            remplacer(id, .erreur(id, Labels.erreur(error)))
        }
    }

    private func relire() async {
        guard !occupe else { return }
        fil.append(.moi(suivant(), "Relis ce document et propose des améliorations."))
        let attente = suivant()
        fil.append(.attente(attente, "Je relis le document…"))
        occupe = true
        defer { occupe = false }
        do {
            let propositions = try await client.relire(documentId: document.id)
            if propositions.isEmpty {
                remplacer(attente, .fait(attente, "Rien à proposer : le document se lit bien tel qu’il est."))
            } else {
                coches[attente] = Set(propositions.map(\.consigne))
                remplacer(attente, .relecture(attente, propositions))
            }
        } catch {
            remplacer(attente, .erreur(attente, Labels.erreur(error)))
        }
    }
}
