import SwiftUI

/// Ce qu'on fait d'un document, comme sur le site : le valider, lire le PDF (imprimer,
/// partager), l'envoyer par courriel, reprendre le texte, et y joindre des photos.
struct TraitementDocument: View {
    let client: APIClient
    let content: ConsultationDetailViewModel.Content
    let document: DocumentDetail
    let recharger: () async -> Void
    @Binding var toast: String?
    var supprime: () -> Void = {}

    @State private var alerteLue = false
    @State private var enCours = false
    @State private var erreur: String?
    @State private var pdf: PDFOuvert?
    @State private var envoiOuvert = false
    @State private var editionOuverte = false
    @State private var confirmerSuppression = false
    @State private var redaction = false

    private var valide: Bool { [.validated, .exported].contains(document.status) }
    private var critiques: [EncounterWarning] { content.criticalWarnings }
    private var partis: [String] {
        content.encounter.documents.first { $0.id == document.id }?.sentTo ?? []
    }

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
            if valide {
                Label {
                    Text(partis.isEmpty
                         ? "\(Labels.documentType(document.documentType)) validé"
                         : "Validé · " + Labels.envoyeA(partis))
                } icon: {
                    Image(systemName: "checkmark.seal.fill")
                }
                .font(Police.interface(14.5, .bold))
                .foregroundStyle(Teinte.accent)
            } else {
                if !critiques.isEmpty {
                    Toggle(isOn: $alerteLue) {
                        Text("J’ai pris connaissance de l’alerte critique : ce document n’est pas exhaustif.")
                            .font(Police.interface(13.5, .semibold))
                            .foregroundStyle(Teinte.alerte)
                    }
                    .tint(Teinte.alerte)
                }
                Button {
                    Task { await valider() }
                } label: {
                    Label(enCours ? "Validation…" : "Valider ce document", systemImage: "checkmark")
                }
                .buttonStyle(BoutonPrincipal())
                .disabled(enCours || (!critiques.isEmpty && !alerteLue))
            }

            if document.versionSimplifiee {
                VStack(alignment: .leading, spacing: 8) {
                    Label("Version simplifiée : la rédaction par Claude n’a pas abouti pour ce document. Oris a posé sa version de secours, fidèle mais télégraphique.",
                          systemImage: "text.badge.xmark")
                        .font(Police.interface(13.5, .semibold))
                        .foregroundStyle(Teinte.attention)
                    Button {
                        Task { await redigerANouveau() }
                    } label: {
                        Label(redaction ? "Rédaction en cours…" : "Rédiger à nouveau", systemImage: "arrow.clockwise")
                    }
                    .buttonStyle(BoutonSecondaire())
                    .disabled(redaction)
                }
                .padding(12)
                .background(Teinte.attentionDouce, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
            }

            HStack(spacing: 8) {
                action("PDF", "doc.richtext") { Task { await ouvrirPDF() } }
                action("Envoyer", "paperplane") { envoiOuvert = true }
                action("Modifier", "pencil") { editionOuverte = true }
                action("Supprimer", "trash", couleur: Teinte.alerte) { confirmerSuppression = true }
            }

            if let erreur {
                Text(erreur)
                    .font(Police.note)
                    .foregroundStyle(Teinte.alerte)
            }
        }
        .carte(fond: valide ? Teinte.accentDouce : Teinte.surface)
        .sheet(item: $pdf, onDismiss: { pdf?.effacer() }) { ouvert in
            ApercuPDF(fichier: ouvert.url).ignoresSafeArea()
        }
        .confirmationDialog("Supprimer ce \(Labels.documentType(document.documentType).lowercased()) ?",
                            isPresented: $confirmerSuppression, titleVisibility: .visible) {
            Button("Supprimer", role: .destructive) { Task { await supprimer() } }
        } message: {
            Text("Ses versions, ses photos placées et ses envois notés partent avec lui. Le dossier clinique de la consultation reste.")
        }
        .sheet(isPresented: $envoiOuvert) {
            EnvoiView(client: client, document: document) { resultat in
                toast = resultat
                Task { await recharger() }
            }
        }
        .sheet(isPresented: $editionOuverte) {
            EditionTexteView(client: client, document: document) {
                toast = "Texte enregistré. Le dossier clinique est inchangé."
                Task { await recharger() }
            }
        }
    }

    private func action(_ titre: String, _ icone: String, couleur: Color = Teinte.accent,
                        _ faire: @escaping () -> Void) -> some View {
        Button(action: faire) {
            VStack(spacing: 4) {
                Image(systemName: icone).font(.system(size: 17, weight: .semibold))
                Text(titre).font(Police.interface(12.5, .bold)).lineLimit(1).minimumScaleFactor(0.8)
            }
            .foregroundStyle(couleur)
            .frame(maxWidth: .infinity, minHeight: 58)
            .background(Teinte.surface, in: RoundedRectangle(cornerRadius: OrisRadius.button, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: OrisRadius.button, style: .continuous)
                .strokeBorder(Teinte.traitFort, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }

    private func valider() async {
        enCours = true
        erreur = nil
        defer { enCours = false }
        do {
            _ = try await client.valider(documentId: document.id,
                                         alertesLues: alerteLue ? critiques.map(\.code) : [])
            toast = "\(Labels.documentType(document.documentType)) validé."
            await recharger()
        } catch {
            erreur = Labels.erreur(error)
        }
    }

    private func redigerANouveau() async {
        redaction = true
        erreur = nil
        defer { redaction = false }
        do {
            _ = try await client.redigerANouveau(documentId: document.id)
            toast = "Document rédigé à nouveau."
            await recharger()
        } catch {
            erreur = Labels.erreur(error)
        }
    }

    private func supprimer() async {
        erreur = nil
        do {
            try await client.supprimerDocument(id: document.id)
            toast = "\(Labels.documentType(document.documentType)) supprimé."
            supprime()
            await recharger()
        } catch {
            erreur = Labels.erreur(error)
        }
    }

    private func ouvrirPDF() async {
        erreur = nil
        do {
            pdf = try PDFOuvert.poser(try await client.pdf(documentId: document.id))
        } catch {
            erreur = Labels.erreur(error)
        }
    }
}

// MARK: - Envoi par courriel

/// Envoi du PDF, comme sur le site : les correspondants à cocher (le principal l'est
/// déjà), d'autres adresses, l'objet et le message.
struct EnvoiView: View {
    let client: APIClient
    let document: DocumentDetail
    let envoye: (String) -> Void

    @Environment(\.dismiss) private var fermer
    @State private var prepare: EnvoiPrepare?
    @State private var coches: Set<String> = []
    @State private var adresses: [String] = [""]
    @State private var objet = ""
    @State private var message = ""
    @State private var enCours = false
    @State private var erreur: String?

    private var adressesValides: [String] {
        adresses.map { $0.trimmingCharacters(in: .whitespaces) }.filter { $0.contains("@") }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: OrisSpacing.s16) {
                    if let prepare {
                        formulaire(prepare)
                    } else if erreur == nil {
                        ProgressView().tint(Teinte.accent).frame(maxWidth: .infinity).padding(.top, 40)
                    }
                    if let erreur {
                        Label(erreur, systemImage: "exclamationmark.triangle")
                            .font(Police.note)
                            .foregroundStyle(Teinte.alerte)
                            .carte(rembourrage: OrisSpacing.s12, fond: Teinte.alerteDouce)
                    }
                }
                .padding(OrisSpacing.s16)
            }
            .pageOris()
            .navigationTitle("Envoyer")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Annuler") { fermer() } }
            }
            .task { await charger() }
        }
        .tint(Teinte.accent)
    }

    @ViewBuilder
    private func formulaire(_ p: EnvoiPrepare) -> some View {
        if !p.configure {
            Label(p.raison ?? "La boîte d’envoi n’est pas configurée : réglez-la sur l’ordinateur, dans Paramètres.",
                  systemImage: "envelope.badge.shield.half.filled")
                .font(Police.note)
                .foregroundStyle(Teinte.attention)
                .carte(rembourrage: OrisSpacing.s12, fond: Teinte.attentionDouce)
        }
        if p.brouillon {
            Label("Ce document n’est pas encore validé : il partira tel quel.", systemImage: "exclamationmark.triangle")
                .font(Police.note)
                .foregroundStyle(Teinte.attention)
                .carte(rembourrage: OrisSpacing.s12, fond: Teinte.attentionDouce)
        }

        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
            Text("Destinataires").font(Police.titreCarte).foregroundStyle(Teinte.encre)
            ForEach(p.candidats) { c in
                Button {
                    if coches.contains(c.cle) { coches.remove(c.cle) } else { coches.insert(c.cle) }
                } label: {
                    HStack(alignment: .top, spacing: OrisSpacing.s12) {
                        Image(systemName: coches.contains(c.cle) ? "checkmark.square.fill" : "square")
                            .font(.system(size: 22))
                            .foregroundStyle(coches.contains(c.cle) ? Teinte.accent : Teinte.traitFort)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(c.libelle).font(Police.interface(15, .bold)).foregroundStyle(Teinte.encre)
                            Text([c.detail, c.email].filter { !$0.isEmpty }.joined(separator: " · "))
                                .font(Police.interface(12.5, .medium))
                                .foregroundStyle(Teinte.encreTresDouce)
                        }
                        Spacer(minLength: 0)
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .disabled(c.email.isEmpty)
                .opacity(c.email.isEmpty ? 0.5 : 1)
            }
            ForEach(adresses.indices, id: \.self) { i in
                TextField("Autre adresse", text: $adresses[i])
                    .keyboardType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .font(Police.texte)
                    .padding(.horizontal, 12)
                    .frame(minHeight: 44)
                    .background(Teinte.surface2, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).strokeBorder(Teinte.trait))
            }
            if adresses.count < 10 {
                Button { adresses.append("") } label: {
                    Label("Ajouter une adresse", systemImage: "plus")
                        .font(Police.interface(14, .bold))
                        .foregroundStyle(Teinte.accent)
                }
            }
        }
        .carte()

        VStack(alignment: .leading, spacing: OrisSpacing.s8) {
            Text("Objet").font(Police.petit).foregroundStyle(Teinte.encreTresDouce)
            TextField("Objet", text: $objet)
                .font(Police.texteFort)
            Divider().overlay(Teinte.trait)
            Text("Message").font(Police.petit).foregroundStyle(Teinte.encreTresDouce)
            TextEditor(text: $message)
                .font(Police.texte)
                .frame(minHeight: 180)
                .scrollContentBackground(.hidden)
            Label(p.nomFichier, systemImage: "paperclip")
                .font(Police.interface(12.5, .semibold))
                .foregroundStyle(Teinte.encreDouce)
        }
        .foregroundStyle(Teinte.encre)
        .carte()

        Text("Envoyé depuis \(p.expediteur)")
            .font(Police.interface(12.5, .medium))
            .foregroundStyle(Teinte.encreTresDouce)

        Button {
            Task { await envoyer() }
        } label: {
            Label(enCours ? "Envoi…" : "Envoyer", systemImage: "paperplane.fill")
        }
        .buttonStyle(BoutonPrincipal())
        .disabled(enCours || !p.configure || objet.trimmingCharacters(in: .whitespaces).isEmpty
                  || (coches.isEmpty && adressesValides.isEmpty))
    }

    private func charger() async {
        do {
            let p = try await client.preparerEnvoi(documentId: document.id)
            prepare = p
            coches = Set(p.candidats.filter(\.coche).map(\.cle))
            objet = p.objet
            message = p.message
        } catch {
            erreur = Labels.erreur(error)
        }
    }

    private func envoyer() async {
        enCours = true
        erreur = nil
        defer { enCours = false }
        do {
            let resultats = try await client.envoyer(
                documentId: document.id, destinataires: Array(coches), adresses: adressesValides,
                objet: objet, message: message
            )
            let rates = resultats.filter { !$0.envoye }
            if rates.isEmpty {
                envoye(resultats.count > 1 ? "Envoyé à \(resultats.count) destinataires." : "Envoyé à \(resultats.first?.destinataire ?? "")." )
                fermer()
            } else {
                erreur = "Non parti vers : " + rates.map(\.destinataire).joined(separator: ", ")
            }
        } catch {
            erreur = Labels.erreur(error)
        }
    }
}

// MARK: - Reprendre le texte

/// Reprendre le texte du document à la main. Le dossier clinique n'est pas touché.
struct EditionTexteView: View {
    let client: APIClient
    let document: DocumentDetail
    let enregistre: () -> Void

    @Environment(\.dismiss) private var fermer
    @State private var texte = ""
    @State private var enCours = false
    @State private var erreur: String?

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: OrisSpacing.s12) {
                Text("Seul le texte change : les faits cliniques de la consultation restent tels quels.")
                    .font(Police.note)
                    .foregroundStyle(Teinte.encreDouce)
                TextEditor(text: $texte)
                    .font(Police.interface(15.5, .regular))
                    .foregroundStyle(Teinte.encre)
                    .scrollContentBackground(.hidden)
                    .padding(10)
                    .background(Teinte.surface, in: RoundedRectangle(cornerRadius: OrisRadius.card, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: OrisRadius.card, style: .continuous).strokeBorder(Teinte.trait))
                if let erreur {
                    Text(erreur).font(Police.note).foregroundStyle(Teinte.alerte)
                }
            }
            .padding(OrisSpacing.s16)
            .background(Teinte.fond.ignoresSafeArea())
            .navigationTitle(Labels.documentTitle(document.documentType))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Annuler") { fermer() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button(enCours ? "…" : "Enregistrer") { Task { await enregistrer() } }
                        .disabled(enCours || texte.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
            .onAppear { texte = document.content }
        }
        .tint(Teinte.accent)
    }

    private func enregistrer() async {
        enCours = true
        defer { enCours = false }
        do {
            _ = try await client.modifierTexte(documentId: document.id, texte: texte)
            enregistre()
            fermer()
        } catch {
            erreur = Labels.erreur(error)
        }
    }
}

// MARK: - Documentation clinique

/// Les photos jointes au document : prises à l'iPhone, légendées, pleine largeur ou
/// demi-largeur dans le PDF.
struct DocumentationClinique: View {
    let client: APIClient
    let patientId: String
    let encounterId: String
    let document: DocumentDetail
    @Binding var toast: String?

    @State private var figures: [Figure] = []
    @State private var charge = false
    @State private var erreur: String?
    @State private var enregistrement: Task<Void, Never>?
    @State private var aRetoucher: Figure?

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
            HStack {
                Text("Documentation clinique").font(Police.titreCarte).foregroundStyle(Teinte.encre)
                Spacer()
                if !figures.isEmpty {
                    Text("\(figures.count)")
                        .font(Police.interface(13, .heavy))
                        .foregroundStyle(Teinte.accent)
                        .frame(minWidth: 26, minHeight: 26)
                        .background(Teinte.accentDouce, in: Circle())
                }
            }
            Text("Les photos s’impriment dans le PDF, sous le texte.")
                .font(Police.note)
                .foregroundStyle(Teinte.encreTresDouce)

            ForEach($figures) { $figure in
                VStack(alignment: .leading, spacing: 8) {
                    HStack(alignment: .top, spacing: 8) {
                        Button { aRetoucher = figure } label: {
                            PhotoDistante(client: client, pieceJointeId: figure.attachmentId)
                                .frame(height: figure.format == "demi" ? 140 : 210)
                                .frame(maxWidth: figure.format == "demi" ? 200 : .infinity)
                                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                                .overlay(alignment: .bottomTrailing) {
                                    Label("Retoucher", systemImage: "crop")
                                        .font(Police.interface(12, .bold))
                                        .foregroundStyle(.white)
                                        .padding(.horizontal, 10).padding(.vertical, 6)
                                        .background(.black.opacity(0.55), in: Capsule())
                                        .padding(8)
                                }
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Retoucher la photo \(numero(figure) + 1)")
                        Spacer(minLength: 0)
                        // L'ordre des photos dans le PDF : on monte, on descend.
                        VStack(spacing: 6) {
                            Text("\(numero(figure) + 1)")
                                .font(Police.interface(13, .heavy))
                                .foregroundStyle(Teinte.accent)
                                .frame(width: 36, height: 28)
                                .background(Teinte.accentDouce, in: Capsule())
                            fleche("chevron.up", "Monter la photo", actif: numero(figure) > 0) { deplacer(figure, de: -1) }
                            fleche("chevron.down", "Descendre la photo", actif: numero(figure) < figures.count - 1) { deplacer(figure, de: 1) }
                        }
                    }
                    TextField("Légende", text: $figure.caption)
                        .font(Police.interface(14, .medium))
                        .foregroundStyle(Teinte.encre)
                        .padding(.horizontal, 10)
                        .frame(minHeight: 40)
                        .background(Teinte.surface2, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                        .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).strokeBorder(Teinte.trait))
                        .onChange(of: figure.caption) { _, _ in enregistrerPlusTard() }
                    HStack {
                        Onglets(selection: $figure.format, choix: [("large", "Pleine largeur"), ("demi", "Demi-largeur")])
                            .onChange(of: figure.format) { _, _ in enregistrerPlusTard(delai: 0) }
                        Button(role: .destructive) {
                            figures.removeAll { $0.id == figure.id }
                            enregistrerPlusTard(delai: 0)
                        } label: {
                            Image(systemName: "trash")
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundStyle(Teinte.alerte)
                                .frame(width: 44, height: 44)
                        }
                        .accessibilityLabel("Retirer la photo du document")
                    }
                }
                .padding(.vertical, 4)
                if figure.id != figures.last?.id { Divider().overlay(Teinte.trait) }
            }

            if figures.count > 1 {
                Text("Les photos s’impriment dans cet ordre. Flèches pour le changer ; toucher une photo pour la retoucher.")
                    .font(Police.interface(12, .medium)).foregroundStyle(Teinte.encreTresDouce)
            }
            if figures.count < 12 {
                BoutonAjoutPhoto { jpegs in await ajouter(jpegs) }
            }
            if let erreur {
                Text(erreur).font(Police.note).foregroundStyle(Teinte.alerte)
            }
        }
        .carte()
        .fullScreenCover(item: $aRetoucher) { figure in
            RetoucheImageView(client: client, pieceJointeId: figure.attachmentId) { jpeg in
                await remplacer(figure, par: jpeg)
            }
        }
        .task(id: document.id) {
            figures = (try? await client.figures(documentId: document.id)) ?? []
            charge = true
        }
    }

    private func ajouter(_ jpegs: [Data]) async {
        erreur = nil
        var nouvelles: [Figure] = []
        for (i, jpeg) in jpegs.enumerated() {
            let nom = "photo-\(Int(Date().timeIntervalSince1970))-\(i + 1).jpg"
            if let pieces = try? await client.deposerPhoto(patientId: patientId, encounterId: encounterId, jpeg: jpeg, nom: nom),
               let piece = pieces.first {
                nouvelles.append(Figure(attachmentId: piece.id, caption: "", position: figures.count + i,
                                        format: figures.isEmpty && i == 0 ? "large" : "demi",
                                        filename: piece.filename, mediaType: piece.mediaType))
            }
        }
        if nouvelles.count < jpegs.count { erreur = "\(jpegs.count - nouvelles.count) photo(s) n’ont pas pu être envoyées." }
        guard !nouvelles.isEmpty else { return }
        figures.append(contentsOf: nouvelles)
        await enregistrer()
        toast = nouvelles.count > 1 ? "\(nouvelles.count) photos ajoutées." : "Photo ajoutée."
    }

    private func numero(_ figure: Figure) -> Int {
        figures.firstIndex { $0.id == figure.id } ?? 0
    }

    private func fleche(_ icone: String, _ nom: String, actif: Bool, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: icone)
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(actif ? Teinte.accent : Teinte.traitFort)
                .frame(width: 36, height: 36)
                .background(Teinte.surface, in: Circle())
                .overlay(Circle().strokeBorder(Teinte.trait))
        }
        .buttonStyle(.plain)
        .disabled(!actif)
        .accessibilityLabel(nom)
    }

    private func deplacer(_ figure: Figure, de pas: Int) {
        guard let i = figures.firstIndex(where: { $0.id == figure.id }) else { return }
        let j = i + pas
        guard figures.indices.contains(j) else { return }
        withAnimation(.spring(duration: 0.3)) { figures.swapAt(i, j) }
        enregistrerPlusTard(delai: 0)
    }

    /// La photo corrigée entre dans le dossier du patient et prend la place de l'ancienne
    /// dans le document, avec sa légende et sa largeur. L'originale reste au dossier.
    private func remplacer(_ figure: Figure, par jpeg: Data?) async {
        guard let jpeg else { return }
        erreur = nil
        let nom = figure.filename.replacingOccurrences(of: #"\.[^.]+$"#, with: "", options: .regularExpression) + "-corrigee.jpg"
        do {
            let pieces = try await client.deposerPhoto(patientId: patientId, encounterId: encounterId, jpeg: jpeg, nom: nom)
            guard let piece = pieces.first, let i = figures.firstIndex(where: { $0.id == figure.id }) else { return }
            figures[i] = Figure(attachmentId: piece.id, caption: figure.caption, position: figure.position,
                                format: figure.format, filename: piece.filename, mediaType: piece.mediaType)
            await enregistrer()
            toast = "Photo retouchée."
        } catch {
            erreur = Labels.erreur(error)
        }
    }

    /// La légende s'enregistre seule, une seconde après la dernière frappe.
    private func enregistrerPlusTard(delai: Double = 1) {
        guard charge else { return }
        enregistrement?.cancel()
        enregistrement = Task {
            try? await Task.sleep(for: .seconds(delai))
            guard !Task.isCancelled else { return }
            await enregistrer()
        }
    }

    private func enregistrer() async {
        do {
            figures = try await client.enregistrerFigures(documentId: document.id, figures)
        } catch {
            erreur = Labels.erreur(error)
        }
    }
}
