import SwiftUI

/// Le dossier d'un patient, comme sa fiche sur le site : ses consultations, ses documents
/// validés (PDF à lire, imprimer, partager) et ses photos.
struct PatientDossierView: View {
    enum Volet: Hashable { case consultations, documents, photos }

    let client: APIClient
    let patient: PatientSummary

    @State private var fiche: PatientFiche?
    @State private var consultations: [EncounterSummary] = []
    @State private var photos: [PieceJointe] = []
    @State private var volet: Volet = .consultations
    @State private var chargement = true
    @State private var erreur: String?
    @State private var nouvelle: EncounterSummary?
    @State private var pdf: PDFOuvert?
    @State private var pdfEnCours: String?
    @State private var photoOuverte: PieceJointe?
    @State private var toast: String?
    @State private var edition = false
    @State private var aSupprimer: EncounterSummary?

    private var documentsValides: [(document: DocumentSummary, consultation: EncounterSummary)] {
        consultations
            .flatMap { e in e.documents.filter { [.validated, .exported].contains($0.status) }.map { ($0, e) } }
            .sorted { ($0.1.date ?? .distantPast) > ($1.1.date ?? .distantPast) }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: OrisSpacing.s16) {
                entete

                Button {
                    Task { await commencer() }
                } label: {
                    Label("Commencer une consultation", systemImage: "waveform")
                }
                .buttonStyle(BoutonPrincipal())

                if let erreur {
                    Label(erreur, systemImage: "exclamationmark.triangle")
                        .font(Police.note)
                        .foregroundStyle(Teinte.alerte)
                        .carte(rembourrage: OrisSpacing.s12, fond: Teinte.alerteDouce)
                }

                if let note = fiche?.note, !note.isEmpty {
                    Label(note, systemImage: "note.text")
                        .font(Police.interface(14, .medium))
                        .foregroundStyle(Teinte.encreDouce)
                        .carte(rembourrage: OrisSpacing.s12, fond: Teinte.surface2)
                }

                CorrespondantsPatient(client: client, patientId: patient.id, toast: $toast)

                Onglets(selection: $volet, choix: [
                    (.consultations, "Consultations · \(consultations.count)"),
                    (.documents, "Documents · \(documentsValides.count)"),
                    (.photos, "Documentation · \(photos.filter(\.estImage).count)"),
                ])

                if chargement {
                    ProgressView().tint(Teinte.accent).frame(maxWidth: .infinity).padding(.top, OrisSpacing.s24)
                } else {
                    switch volet {
                    case .consultations: voletConsultations
                    case .documents: voletDocuments
                    case .photos: voletPhotos
                    }
                }
            }
            .padding(.horizontal, OrisSpacing.s16)
            .padding(.bottom, OrisSpacing.s32)
        }
        .pageOris()
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button("Modifier") { edition = true }
                    .disabled(fiche == nil)
            }
        }
        .sheet(isPresented: $edition) {
            if let fiche {
                EditionPatientView(client: client, fiche: fiche) { nouvelle in
                    self.fiche = nouvelle
                    toast = "Fiche enregistrée."
                }
            }
        }
        .navigationDestination(item: $nouvelle) { encounter in
            ListeningView(client: client, encounter: encounter) {
                nouvelle = nil
                Task { await charger() }
            }
        }
        .sheet(item: $pdf, onDismiss: { pdf?.effacer() }) { ouvert in
            ApercuPDF(fichier: ouvert.url).ignoresSafeArea()
        }
        .sheet(item: $photoOuverte) { photo in
            PhotoPleinEcran(client: client, photo: photo)
        }
        .confirmationDialog("Supprimer cette consultation ?", isPresented: Binding(
            get: { aSupprimer != nil }, set: { if !$0 { aSupprimer = nil } }
        ), titleVisibility: .visible) {
            Button("Supprimer", role: .destructive) {
                if let e = aSupprimer { Task { await supprimer(e) } }
            }
        } message: {
            Text("La transcription, le dossier clinique et ses documents seront effacés, sans retour possible.")
        }
        .toast($toast)
        .refreshable { await charger() }
        .task { await charger() }
    }

    // MARK: En-tête

    private var entete: some View {
        HStack(spacing: OrisSpacing.s12) {
            Vignette(initiales: (fiche?.resume ?? patient).initiales, taille: 54)
            VStack(alignment: .leading, spacing: 4) {
                NomPatient(patient: fiche?.resume ?? patient, taille: 22)
                Text(identite)
                    .font(Police.interface(13, .medium))
                    .foregroundStyle(Teinte.encreTresDouce)
                    .lineLimit(2)
            }
            Spacer(minLength: 0)
        }
        .padding(.top, OrisSpacing.s8)
    }

    private var identite: String {
        var morceaux: [String] = []
        if let naissance = fiche?.birthDate, let date = DateOris.lireJour(naissance) {
            let age = Calendar.current.dateComponents([.year], from: date, to: Date()).year ?? 0
            morceaux.append("né(e) le \(DateOris.court(date)) · \(age) ans")
        } else {
            morceaux.append("date de naissance non renseignée")
        }
        if let email = fiche?.email, !email.isEmpty { morceaux.append(email) }
        if let numero = fiche?.externalId, !numero.isEmpty { morceaux.append("dossier \(numero)") }
        return morceaux.joined(separator: " · ")
    }

    // MARK: Volets

    @ViewBuilder
    private var voletConsultations: some View {
        if consultations.isEmpty {
            MessageVide(icone: "waveform", titre: "Aucune consultation",
                        texte: "Commencez la première avec le bouton ci-dessus.")
        } else {
            VStack(spacing: 0) {
                ForEach(consultations.sorted { ($0.date ?? .distantPast) > ($1.date ?? .distantPast) }) { e in
                    NavigationLink(value: RoutePatients.consultation(e.id)) {
                        LigneConsultationPatient(encounter: e)
                    }
                    .buttonStyle(.plain)
                    .supprimable(e.supprimable) { aSupprimer = e }
                    if e.id != consultations.last?.id {
                        Divider().overlay(Teinte.trait).padding(.leading, 14)
                    }
                }
            }
            .carte(rembourrage: 0)
        }
    }

    @ViewBuilder
    private var voletDocuments: some View {
        if documentsValides.isEmpty {
            MessageVide(icone: "doc.text", titre: "Aucun document validé",
                        texte: "Un document apparaît ici dès que vous le validez.")
        } else {
            VStack(spacing: 0) {
                ForEach(documentsValides, id: \.document.id) { ligne in
                    Button {
                        Task { await ouvrirPDF(ligne.document) }
                    } label: {
                        HStack(spacing: OrisSpacing.s12) {
                            Image(systemName: "doc.richtext.fill")
                                .font(.system(size: 20))
                                .foregroundStyle(Teinte.document(ligne.document.documentType).encre)
                                .frame(width: 40, height: 40)
                                .background(Teinte.document(ligne.document.documentType).fond,
                                            in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                            VStack(alignment: .leading, spacing: 3) {
                                Text(Labels.documentTitle(ligne.document.documentType))
                                    .font(Police.interface(15, .bold))
                                    .foregroundStyle(Teinte.encre)
                                Text(sousTitre(ligne.document, ligne.consultation))
                                    .font(Police.interface(12.5, .medium))
                                    .foregroundStyle(Teinte.encreTresDouce)
                                    .lineLimit(2)
                            }
                            Spacer(minLength: 4)
                            if pdfEnCours == ligne.document.id {
                                ProgressView().tint(Teinte.accent)
                            } else {
                                Text("PDF")
                                    .font(Police.interface(12, .heavy))
                                    .foregroundStyle(Teinte.accent)
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 5)
                                    .background(Teinte.accentDouce, in: Capsule())
                            }
                        }
                        .padding(.horizontal, 14)
                        .padding(.vertical, 12)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    if ligne.document.id != documentsValides.last?.document.id {
                        Divider().overlay(Teinte.trait).padding(.leading, 66)
                    }
                }
            }
            .carte(rembourrage: 0)
        }
    }

    private func sousTitre(_ document: DocumentSummary, _ consultation: EncounterSummary) -> String {
        var texte = consultation.date.map { "Consultation du \(DateOris.court($0))" } ?? ""
        if let partis = document.sentTo, !partis.isEmpty {
            texte += " · " + Labels.envoyeA(partis)
        }
        return texte
    }

    private var voletPhotos: some View {
        VStack(spacing: OrisSpacing.s16) {
            CarteSmileCloud(client: client, patientId: patient.id) {
                Task { photos = (try? await client.piecesJointes(patientId: patient.id)) ?? photos }
            }
            voletPhotosDuDossier
        }
    }

    private var voletPhotosDuDossier: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
            BoutonAjoutPhoto { jpegs in await deposer(jpegs) }
            let images = photos.filter(\.estImage)
            if images.isEmpty {
                Text("Aucune photo dans le dossier.")
                    .font(Police.note)
                    .foregroundStyle(Teinte.encreTresDouce)
            }
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 100), spacing: 8)], spacing: 8) {
                ForEach(images) { photo in
                    Button { photoOuverte = photo } label: {
                        PhotoDistante(client: client, pieceJointeId: photo.id)
                            .frame(height: 104)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(photo.label.isEmpty ? photo.filename : photo.label)
                }
            }
        }
        .carte()
    }

    // MARK: Actions

    private func charger() async {
        defer { chargement = false }
        do {
            async let f = client.patient(id: patient.id)
            async let c = client.encounters(patientId: patient.id)
            async let p = client.piecesJointes(patientId: patient.id)
            fiche = try await f
            consultations = try await c
            photos = (try? await p) ?? []
            erreur = nil
        } catch {
            erreur = "Dossier indisponible. " + Connexion.pourquoi(error, adresse: client.baseURL)
        }
    }

    private func supprimer(_ e: EncounterSummary) async {
        do {
            try await client.supprimerConsultation(id: e.id)
            consultations.removeAll { $0.id == e.id }
            toast = "Consultation supprimée."
        } catch {
            erreur = Labels.erreur(error)
        }
    }

    private func commencer() async {
        do {
            nouvelle = try await client.createEncounter(patientId: patient.id)
        } catch {
            erreur = "Création de la consultation impossible."
        }
    }

    private func ouvrirPDF(_ document: DocumentSummary) async {
        pdfEnCours = document.id
        defer { pdfEnCours = nil }
        do {
            pdf = try PDFOuvert.poser(try await client.pdf(documentId: document.id))
        } catch {
            erreur = "PDF indisponible. " + Connexion.pourquoi(error, adresse: client.baseURL)
        }
    }

    private func deposer(_ jpegs: [Data]) async {
        var n = 0
        for (i, jpeg) in jpegs.enumerated() {
            let nom = "photo-\(Int(Date().timeIntervalSince1970))-\(i + 1).jpg"
            if (try? await client.deposerPhoto(patientId: patient.id, encounterId: nil, jpeg: jpeg, nom: nom)) != nil {
                n += 1
            }
        }
        if n < jpegs.count { erreur = "\(jpegs.count - n) photo(s) n’ont pas pu être envoyées." }
        if n > 0 { toast = n > 1 ? "\(n) photos ajoutées au dossier." : "Photo ajoutée au dossier." }
        photos = (try? await client.piecesJointes(patientId: patient.id)) ?? photos
    }
}

/// Une consultation dans le dossier : date, statut, documents.
private struct LigneConsultationPatient: View {
    let encounter: EncounterSummary

    var body: some View {
        HStack(alignment: .top, spacing: OrisSpacing.s12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(encounter.date.map { "\(DateOris.jour($0).capitalizedPremiere) · \(DateOris.heure($0))" } ?? "—")
                    .font(Police.interface(15, .bold))
                    .foregroundStyle(Teinte.encre)
                Flux(espace: 10) {
                    StatutLeger(texte: Labels.encounterStatus(encounter.status), ton: encounter.status.ton)
                    if !encounter.documents.isEmpty {
                        DocumentsLegers(documents: encounter.documents)
                    }
                }
            }
            Spacer(minLength: 4)
            Image(systemName: "chevron.right")
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(Teinte.traitFort)
                .padding(.top, 4)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
    }
}

/// Une photo en grand, sur fond noir.
struct PhotoPleinEcran: View {
    let client: APIClient
    let photo: PieceJointe
    @Environment(\.dismiss) private var fermer

    var body: some View {
        NavigationStack {
            PhotoDistante(client: client, pieceJointeId: photo.id, remplir: false)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color.black)
                .toolbar {
                    ToolbarItem(placement: .confirmationAction) { Button("Fermer") { fermer() } }
                }
                .navigationTitle(photo.label.isEmpty ? "" : photo.label)
                .navigationBarTitleDisplayMode(.inline)
        }
    }
}

/// Les chemins de l'onglet Patients.
enum RoutePatients: Hashable {
    case patient(PatientSummary)
    case consultation(String)
}

extension PatientSummary: Hashable {
    func hash(into hasher: inout Hasher) { hasher.combine(id) }
}

extension String {
    var capitalizedPremiere: String { prefix(1).uppercased() + dropFirst() }
}
