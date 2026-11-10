import SwiftUI

// MARK: - Le dialogue, gardé hors de la fenêtre

/// Une demande faite à Claude, et ce qu'elle est devenue.
struct DemandeCorrection: Identifiable, Equatable {
    enum Etat: Equatable {
        /// Claude lit la demande.
        case lecture
        /// Claude a compris : la proposition attend l'accord du praticien.
        case proposee(LectureAssistant)
        /// Une relecture : des améliorations à cocher.
        case relecture([PropositionRelecture])
        /// L'accord est donné, Oris applique (depuis quand : pour la barre de progression).
        case application(Date)
        case traitee(String)
        case annulee
        case incomprise(String)
        case echec(String)
    }

    let id: Int
    let texte: String
    var etat: Etat

    /// Ce qu'on lit sous la demande : où elle en est, d'un mot.
    var marque: (texte: String, icone: String, ton: Pastille.Ton)? {
        switch etat {
        case .lecture: ("Lecture…", "ellipsis", .neutre)
        case .proposee, .relecture: ("À confirmer", "hand.tap", .attention)
        case .application: ("En cours", "arrow.triangle.2.circlepath", .attention)
        case .traitee: ("Traitée", "checkmark", .valide)
        case .annulee: ("Annulée", "xmark", .neutre)
        case .incomprise: ("À préciser", "questionmark", .neutre)
        case .echec: ("Non aboutie", "exclamationmark.triangle", .alerte)
        }
    }
}

/// Le dialogue de correction d'une consultation.
///
/// Il vit **en dehors de la fenêtre** : la fermer n'arrête pas le travail en cours et
/// n'efface pas l'historique (Franck, 11/11/2026 : « si je sors et que je reviens, garder
/// l'historique, ne pas en remettre une vierge »). Il dure le temps que l'app reste
/// ouverte ; rien n'en est écrit sur le téléphone.
@MainActor
@Observable
final class DialogueCorrection {
    private(set) var demandes: [DemandeCorrection] = []
    var coches: [Int: Set<String>] = [:]
    /// Appelé quand une correction a changé un document : l'écran derrière se recharge.
    var aChange: (String) -> Void = { _ in }
    private var compteur = 0

    var occupe: Bool {
        demandes.contains { demande in
            switch demande.etat {
            case .lecture, .application: true
            default: false
            }
        }
    }

    /// Une correction est en train de s'appliquer : le bouton de l'écran le montre.
    var enApplication: Bool {
        demandes.contains { demande in
            if case .application = demande.etat { return true }
            return false
        }
    }

    private func ajouter(_ texte: String, _ etat: DemandeCorrection.Etat) -> Int {
        compteur += 1
        demandes.append(DemandeCorrection(id: compteur, texte: texte, etat: etat))
        return compteur
    }

    func poser(_ id: Int, _ etat: DemandeCorrection.Etat) {
        if let rang = demandes.firstIndex(where: { $0.id == id }) { demandes[rang].etat = etat }
    }

    func demander(_ texte: String, client: APIClient, encounterId: String) async {
        let demande = texte.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !demande.isEmpty, !occupe else { return }
        let id = ajouter(demande, .lecture)
        do {
            let lecture = try await client.comprendre(encounterId: encounterId, demande: demande)
            poser(id, lecture.nature == "incompris" ? .incomprise(lecture.resume) : .proposee(lecture))
        } catch {
            poser(id, .echec(Labels.erreur(error)))
        }
    }

    func relire(client: APIClient, documentId: String) async {
        guard !occupe else { return }
        let id = ajouter("Relis ce document et propose des améliorations.", .lecture)
        do {
            let propositions = try await client.relire(documentId: documentId)
            if propositions.isEmpty {
                poser(id, .traitee("Rien à proposer : le document se lit bien tel qu’il est."))
            } else {
                coches[id] = Set(propositions.map(\.consigne))
                poser(id, .relecture(propositions))
            }
        } catch {
            poser(id, .echec(Labels.erreur(error)))
        }
    }

    func appliquer(_ id: Int, lecture: LectureAssistant, retenir: Bool,
                   client: APIClient, encounterId: String, documentId: String) async {
        await appliquer(id) {
            try await client.appliquer(encounterId: encounterId, documentId: documentId,
                                       lecture: lecture, retenir: retenir)
        }
    }

    func appliquer(_ id: Int, consignes: [String], retenir: Bool,
                   client: APIClient, encounterId: String, documentId: String) async {
        await appliquer(id) {
            try await client.appliquer(encounterId: encounterId, documentId: documentId,
                                       consignes: consignes, retenir: retenir)
        }
    }

    private func appliquer(_ id: Int, _ travail: () async throws -> ResultatAssistant) async {
        guard !occupe else { return }
        poser(id, .application(Date()))
        do {
            let resultat = try await travail()
            poser(id, .traitee(resultat.message))
            aChange(resultat.message)
        } catch {
            poser(id, .echec(Labels.erreur(error)))
        }
    }
}

/// Un dialogue par consultation, retrouvé quand on rouvre la fenêtre.
@MainActor
enum DialoguesCorrection {
    private static var ouverts: [String: DialogueCorrection] = [:]

    static func pour(_ encounterId: String) -> DialogueCorrection {
        if let dialogue = ouverts[encounterId] { return dialogue }
        let dialogue = DialogueCorrection()
        ouverts[encounterId] = dialogue
        return dialogue
    }
}

// MARK: - La fenêtre

/// Corriger avec Claude : on dit ce qui ne va pas, Oris dit ce qu'il a compris, on confirme.
///
/// Le même dialogue que sur le site (Franck, 10/11/2026). Sur l'iPhone, la dictée est
/// celle du clavier : le micro à droite de la barre d'espace.
struct CorrigerAvecClaude: View {
    let client: APIClient
    let encounterId: String
    let document: DocumentDetail
    let dialogue: DialogueCorrection

    @Environment(\.dismiss) private var fermer
    @State private var saisie = ""
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
                            ForEach(dialogue.demandes) { demande in
                                echange(demande).id(demande.id)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(OrisSpacing.s16)
                    }
                    .onChange(of: dialogue.demandes) {
                        if let derniere = dialogue.demandes.last {
                            withAnimation { defile.scrollTo(derniere.id, anchor: .bottom) }
                        }
                    }
                    .onAppear {
                        if let derniere = dialogue.demandes.last { defile.scrollTo(derniere.id, anchor: .bottom) }
                    }
                }

                VStack(spacing: 8) {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 6) {
                            ForEach(suggestions, id: \.self) { suggestion in
                                puce(suggestion) {
                                    Task { await dialogue.demander(suggestion, client: client, encounterId: encounterId) }
                                }
                            }
                            if relisible {
                                puce("✦ Relire tout le document") {
                                    Task { await dialogue.relire(client: client, documentId: document.id) }
                                }
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
                            let texte = saisie
                            saisie = ""
                            clavier = false
                            Task { await dialogue.demander(texte, client: client, encounterId: encounterId) }
                        } label: {
                            Image(systemName: "arrow.up")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundStyle(.white)
                                .frame(width: 40, height: 40)
                                .background(Teinte.accent, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                        }
                        .disabled(envoiImpossible)
                        .opacity(envoiImpossible ? 0.45 : 1)
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

    private var envoiImpossible: Bool {
        dialogue.occupe || saisie.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    // MARK: Un échange : la demande, sa marque, puis la réponse d'Oris

    @ViewBuilder
    private func echange(_ demande: DemandeCorrection) -> some View {
        VStack(alignment: .trailing, spacing: 4) {
            Text(demande.texte)
                .font(Police.interface(14.5, .medium))
                .foregroundStyle(.white)
                .padding(.horizontal, 13).padding(.vertical, 9)
                .background(Teinte.accent, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
            if let marque = demande.marque {
                Label(marque.texte, systemImage: marque.icone)
                    .font(Police.interface(11.5, .bold))
                    .foregroundStyle(couleur(marque.ton))
            }
        }
        .frame(maxWidth: .infinity, alignment: .trailing)

        switch demande.etat {
        case .lecture:
            cadre { Text("Je lis votre demande…").italic().foregroundStyle(Teinte.encreDouce) }
        case .application(let debut):
            cadre { Progression(debut: debut) }
        case .traitee(let message):
            cadre(fond: Teinte.accentDouce) {
                Label(message, systemImage: "checkmark").foregroundStyle(Teinte.accent)
            }
        case .annulee:
            cadre { Text("Annulé : rien n’a changé.").foregroundStyle(Teinte.encreDouce) }
        case .incomprise(let question):
            cadre { Text(question) }
        case .echec(let message):
            cadre(fond: Teinte.alerteDouce) { Text(message).foregroundStyle(Teinte.alerte) }
        case .proposee(let lecture):
            cadre {
                VStack(alignment: .leading, spacing: 8) {
                    Text((nature(lecture.nature) + " · à confirmer").uppercased())
                        .font(Police.interface(11, .heavy))
                        .foregroundStyle(lecture.nature == "dossier" ? Teinte.attention : Teinte.accent)
                    Text(lecture.resume)
                    if lecture.nature == "redaction" {
                        Text("Consigne : \(lecture.consigne)")
                            .font(Police.note).foregroundStyle(Teinte.encreDouce)
                    }
                    Button(principal(lecture.nature)) {
                        Task {
                            await dialogue.appliquer(demande.id, lecture: lecture, retenir: false, client: client,
                                                     encounterId: encounterId, documentId: document.id)
                        }
                    }
                    .buttonStyle(BoutonPrincipal())
                    if lecture.nature == "redaction" {
                        Button("Appliquer et retenir pour toujours") {
                            Task {
                                await dialogue.appliquer(demande.id, lecture: lecture, retenir: true, client: client,
                                                         encounterId: encounterId, documentId: document.id)
                            }
                        }
                        .buttonStyle(BoutonSecondaire())
                    }
                    Button("Annuler") { dialogue.poser(demande.id, .annulee) }
                        .font(Police.interface(14, .semibold))
                        .foregroundStyle(Teinte.encreDouce)
                }
                .disabled(dialogue.occupe)
            }
        case .relecture(let propositions):
            let choisies = dialogue.coches[demande.id] ?? []
            cadre {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Relecture — \(propositions.count) amélioration\(propositions.count > 1 ? "s" : "") possible\(propositions.count > 1 ? "s" : ""), aucune ne touche aux faits :")
                    ForEach(propositions) { proposition in
                        Button {
                            var suite = choisies
                            if suite.contains(proposition.consigne) { suite.remove(proposition.consigne) }
                            else { suite.insert(proposition.consigne) }
                            dialogue.coches[demande.id] = suite
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
                        Task {
                            await dialogue.appliquer(demande.id, consignes: Array(choisies), retenir: false,
                                                     client: client, encounterId: encounterId, documentId: document.id)
                        }
                    }
                    .buttonStyle(BoutonPrincipal())
                    .disabled(choisies.isEmpty)
                    Button("Appliquer et retenir pour toujours") {
                        Task {
                            await dialogue.appliquer(demande.id, consignes: Array(choisies), retenir: true,
                                                     client: client, encounterId: encounterId, documentId: document.id)
                        }
                    }
                    .buttonStyle(BoutonSecondaire())
                    .disabled(choisies.isEmpty)
                    Button("Écarter") { dialogue.poser(demande.id, .annulee) }
                        .font(Police.interface(14, .semibold))
                        .foregroundStyle(Teinte.encreDouce)
                }
                .disabled(dialogue.occupe)
            }
        }
    }

    private func couleur(_ ton: Pastille.Ton) -> Color {
        switch ton {
        case .valide: Teinte.accent
        case .attention: Teinte.attention
        case .alerte: Teinte.alerte
        default: Teinte.encreTresDouce
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
        .disabled(dialogue.occupe)
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
}

// MARK: - La barre de progression

/// Où en est une correction qui s'applique.
///
/// Oris ne sait pas à l'avance combien de temps Claude mettra : la barre avance donc sur
/// le temps écoulé, vite au début puis plus lentement, sans jamais prétendre être arrivée.
/// Une réécriture prend d'ordinaire entre trente secondes et deux minutes.
struct Progression: View {
    let debut: Date

    /// La part parcourue après `secondes` : la moitié vers 30 s, 90 % vers 100 s, jamais 100 %.
    static func part(_ secondes: TimeInterval) -> Double {
        min(0.95, 1 - exp(-max(0, secondes) / 43))
    }

    static func duree(_ secondes: TimeInterval) -> String {
        let entier = Int(max(0, secondes))
        return String(format: "%d:%02d", entier / 60, entier % 60)
    }

    var body: some View {
        TimelineView(.periodic(from: debut, by: 0.5)) { instant in
            let ecoule = instant.date.timeIntervalSince(debut)
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(ecoule < 8 ? "J’applique votre correction…" : "Claude rédige à nouveau le document…")
                    Spacer()
                    Text(Self.duree(ecoule))
                        .font(Police.interface(13, .semibold).monospacedDigit())
                        .foregroundStyle(Teinte.encreDouce)
                }
                ProgressView(value: Self.part(ecoule))
                    .tint(Teinte.accent)
                Label("Vous pouvez fermer cette fenêtre : la correction continue, et le document se mettra à jour tout seul.",
                      systemImage: "arrow.down.right.and.arrow.up.left")
                    .font(Police.note)
                    .foregroundStyle(Teinte.encreDouce)
            }
        }
    }
}
