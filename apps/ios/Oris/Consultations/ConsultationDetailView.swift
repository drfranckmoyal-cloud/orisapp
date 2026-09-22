import SwiftUI

/// Révision iPhone (docs/DESIGN_SYSTEM.md) : Compte rendu | Plan, et « À vérifier ».
struct ConsultationDetailView: View {
    enum Tab: Hashable {
        case document(DocumentDocumentType)
        case review
    }

    @State var model: ConsultationDetailViewModel
    @State private var tab: Tab = .document(.consultationNote)
    @State private var toast: String?
    @State private var redaction = false
    @State private var erreur: String?
    @Environment(\.dismiss) private var fermer

    var body: some View {
        Group {
            switch model.state {
            case .loading:
                ProgressView("Chargement…").tint(Teinte.accent)
            case .failed:
                MessageVide(icone: "exclamationmark.triangle", titre: "Consultation indisponible",
                            texte: "Tirez vers le bas pour réessayer.")
                    .padding(OrisSpacing.s16)
            case .loaded(let content):
                loaded(content)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .pageOris()
        .navigationBarTitleDisplayMode(.inline)
        .toast($toast)
        .refreshable { await model.refresh() }
        .task { await model.refresh() }
    }

    @ViewBuilder
    private func loaded(_ content: ConsultationDetailViewModel.Content) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: OrisSpacing.s16) {
                EnTeteConsultation(encounter: content.encounter)

                ForEach(content.criticalWarnings, id: \.code) { warning in
                    Label {
                        Text("\(warning.message) Le compte rendu n’est pas exhaustif.")
                    } icon: {
                        Image(systemName: "exclamationmark.octagon.fill")
                    }
                    .font(Police.note)
                    .foregroundStyle(Teinte.alerte)
                    .carte(rembourrage: OrisSpacing.s12, fond: Teinte.alerteDouce)
                }

                if content.documents.isEmpty {
                    NoDocumentCard(encounter: content.encounter) {
                        Task { await supprimerConsultation(content) }
                    }
                }

                if !content.documents.isEmpty {
                    Intercalaires(tab: $tab, documents: content.documents, aVerifier: content.reviewItemCount)
                }

                if !content.documents.isEmpty,
                   !content.documents.contains(where: { $0.documentType == .referralLetter }) {
                    Button {
                        Task { await redigerCourrier(content) }
                    } label: {
                        Label(redaction ? "Rédaction du courrier…" : "Rédiger un courrier d’adressage", systemImage: "plus")
                            .font(Police.interface(14, .bold))
                            .foregroundStyle(Teinte.document(.referralLetter).encre)
                    }
                    .disabled(redaction)
                }
                if let erreur {
                    Text(erreur).font(Police.note).foregroundStyle(Teinte.alerte)
                }

                switch tab {
                case .document(let type):
                    if let document = content.documents.first(where: { $0.documentType == type }) {
                        TraitementDocument(client: model.client, content: content, document: document,
                                           recharger: { await model.refresh() }, toast: $toast,
                                           supprime: { tab = .document(.consultationNote) })
                        DocumentCard(document: document)
                        DocumentationClinique(client: model.client, patientId: content.encounter.patient.id,
                                              encounterId: content.encounter.id, document: document, toast: $toast)
                    }
                case .review:
                    ReviewCard(content: content)
                }
            }
            .padding(.horizontal, OrisSpacing.s16)
            .padding(.bottom, OrisSpacing.s32)
        }
    }
}

extension ConsultationDetailView {
    /// Rien n'a été entendu : rien à perdre, la consultation s'efface d'un geste.
    fileprivate func supprimerConsultation(_ content: ConsultationDetailViewModel.Content) async {
        do {
            try await model.client.supprimerConsultation(id: content.encounter.id)
            fermer()
        } catch {
            erreur = Labels.erreur(error)
        }
    }

    fileprivate func redigerCourrier(_ content: ConsultationDetailViewModel.Content) async {
        redaction = true
        erreur = nil
        defer { redaction = false }
        do {
            _ = try await model.client.rediger(encounterId: content.encounter.id, courrier: true)
            await model.refresh()
            tab = .document(.referralLetter)
            toast = "Courrier d’adressage rédigé."
        } catch {
            erreur = Labels.erreur(error)
        }
    }
}

/// Le patient, la date et le statut, comme l'en-tête de la page consultation du site.
private struct EnTeteConsultation: View {
    let encounter: EncounterSummary

    var body: some View {
        HStack(alignment: .center, spacing: OrisSpacing.s12) {
            Vignette(initiales: encounter.patient.initiales, taille: 46)
            VStack(alignment: .leading, spacing: 4) {
                NomPatient(patient: encounter.patient, taille: 20)
                if let date = encounter.date {
                    Text("\(DateOris.jour(date).capitalizedPremiere) · \(DateOris.heure(date))")
                        .font(Police.interface(13, .medium))
                        .foregroundStyle(Teinte.encreTresDouce)
                }
                StatutLeger(texte: Labels.encounterStatus(encounter.status), ton: encounter.status.ton)
            }
            Spacer(minLength: 4)
        }
        .padding(.top, OrisSpacing.s8)
        .accessibilityElement(children: .combine)
    }
}

/// Un intercalaire par document, à la teinte de son type ; puis « À vérifier ».
private struct Intercalaires: View {
    @Binding var tab: ConsultationDetailView.Tab
    let documents: [DocumentDetail]
    let aVerifier: Int

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(documents) { document in
                    let teinte = Teinte.document(document.documentType)
                    onglet(Labels.documentType(document.documentType), .document(document.documentType),
                           encre: teinte.encre, fond: teinte.fond)
                }
                onglet("À vérifier · \(aVerifier)", .review,
                       encre: aVerifier > 0 ? Teinte.attention : Teinte.encreDouce,
                       fond: aVerifier > 0 ? Teinte.attentionDouce : Teinte.surfaceDouce)
            }
        }
    }

    private func onglet(_ titre: String, _ cible: ConsultationDetailView.Tab, encre: Color, fond: Color) -> some View {
        let actif = tab == cible
        return Button { tab = cible } label: {
            Text(titre)
                .font(Police.interface(14, .bold))
                .foregroundStyle(actif ? .white : encre)
                .padding(.horizontal, 14)
                .frame(minHeight: 36)
                .background(actif ? encre : fond, in: Capsule())
                .overlay(Capsule().strokeBorder(encre.opacity(actif ? 0 : 0.2), lineWidth: 1))
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(actif ? .isSelected : [])
    }
}

/// Le texte du site garde ses mots-clés en gras (**…**).
func texteRiche(_ brut: String) -> AttributedString {
    (try? AttributedString(markdown: brut, options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)))
        ?? AttributedString(brut)
}

private struct DocumentCard: View {
    let document: DocumentDetail

    private var sections: [(title: String, claims: [DocumentClaim])] {
        var result: [(title: String, claims: [DocumentClaim])] = []
        for claim in document.claims {
            if let last = result.last, last.title == claim.section {
                result[result.count - 1].claims.append(claim)
            } else {
                result.append((claim.section, [claim]))
            }
        }
        return result
    }

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s16) {
            HStack(spacing: OrisSpacing.s8) {
                Pastille(texte: Labels.documentStatus(document.status),
                         ton: [.validated, .exported].contains(document.status) ? .valide : .attention)
                Text("Version \(document.version)")
                    .font(Police.interface(12, .semibold))
                    .foregroundStyle(Teinte.encreTresDouce)
            }
            if !document.isCurrent {
                Label("Rédigé avant la dernière correction : à régénérer.", systemImage: "arrow.triangle.2.circlepath")
                    .font(Police.note)
                    .foregroundStyle(Teinte.attention)
            }
            ForEach(sections, id: \.title) { section in
                VStack(alignment: .leading, spacing: 6) {
                    Text(section.title)
                        .font(Police.interface(14.5, .heavy))
                        .foregroundStyle(Teinte.document(document.documentType).encre)
                        .padding(.bottom, 2)
                        .overlay(alignment: .bottom) {
                            Rectangle().fill(Teinte.document(document.documentType).encre.opacity(0.25))
                                .frame(height: 1.5).offset(y: 2)
                        }
                    ForEach(Array(section.claims.enumerated()), id: \.offset) { _, claim in
                        Text(texteRiche(claim.text))
                            .font(Police.interface(15.5, .regular))
                            .lineSpacing(4)
                            .foregroundStyle(Teinte.encre)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .padding(.top, 4)
            }
        }
        .carte(rembourrage: 20)
    }
}

private struct ReviewCard: View {
    let content: ConsultationDetailViewModel.Content

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s16) {
            if content.reviewItemCount == 0 {
                Text("Aucun point signalé. La validation reste une action du praticien.")
                    .font(Police.note)
                    .foregroundStyle(Teinte.encreDouce)
            }
            ForEach(content.warnings, id: \.code) { warning in
                Label(warning.message, systemImage: warning.severity == .critical ? "exclamationmark.octagon" : "exclamationmark.triangle")
            }
            ForEach(content.documents) { document in
                ForEach(Array(document.validationIssues.enumerated()), id: \.offset) { _, issue in
                    Label("\(Labels.documentType(document.documentType)) : \(Labels.issue(issue.code))", systemImage: "exclamationmark.triangle")
                }
            }

            Text("Faits cliniques (\(content.facts.count))")
                .font(Police.titreCarte)
                .foregroundStyle(Teinte.encre)
            ForEach(content.facts, id: \.factId) { fact in
                VStack(alignment: .leading, spacing: OrisSpacing.s4) {
                    Text(fact.concept + (fact.teeth.isEmpty ? "" : " — dent \(fact.teeth.joined(separator: ", "))"))
                        .font(Police.interface(14.5, .bold))
                        .foregroundStyle(Teinte.encre)
                    Text([Labels.assertion(fact.assertion), Labels.clinicalStatus(fact.clinicalStatus), Labels.certainty(fact.certainty)].joined(separator: " · "))
                        .font(Police.interface(12.5, .medium))
                        .foregroundStyle(Teinte.encreTresDouce)
                }
                .accessibilityElement(children: .combine)
            }
        }
        .font(Police.interface(14.5, .semibold))
        .foregroundStyle(Teinte.attention)
        .carte()
    }
}


/// Pas de compte rendu : on dit pourquoi, et ce qu'on peut faire.
private struct NoDocumentCard: View {
    let encounter: EncounterSummary
    var supprimer: () -> Void = {}

    private var rules: Set<String> { Set(encounter.processingErrors.map(\.rule)) }

    private var rienEntendu: Bool {
        rules.contains("NO_TRANSCRIPT") || rules.contains("AUDIO_SILENT") || rules.contains("AUDIO_TEST_TONE")
    }

    private var reason: String {
        if rules.contains("AUDIO_TEST_TONE") {
            return "Ce n’est pas la consultation qui a été enregistrée, mais le son de test d’Oris (une note continue). Rien n’a pu être rédigé."
        }
        if rules.contains("AUDIO_SILENT") {
            return "Le micro n’a capté aucun son : l’enregistrement est muet. Vérifiez que le micro n’est pas couvert ou coupé, puis refaites un essai."
        }
        if rules.contains("NO_TRANSCRIPT") {
            return "Aucune parole n’a été reconnue dans l’enregistrement : il n’y a rien à rédiger."
        }
        if rules.contains("STT_UNAVAILABLE") {
            return "La transcription était indisponible. Relancez le traitement depuis l’ordinateur, dans la consultation."
        }
        if encounter.status == .processing || encounter.status == .finalizing {
            return "Oris prépare le dossier… Tirez vers le bas pour actualiser."
        }
        return "Oris n’a pas pu préparer le dossier de cette consultation. Le détail est sur l’ordinateur."
    }

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
            Label(reason, systemImage: rules.contains("AUDIO_SILENT") ? "mic.slash" : "doc.questionmark")
                .font(Police.interface(15, .medium))
                .foregroundStyle(Teinte.encreDouce)
            if rienEntendu {
                Button(role: .destructive, action: supprimer) {
                    Label("Supprimer cette consultation", systemImage: "trash")
                        .font(Police.interface(15, .bold))
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity, minHeight: 46)
                        .background(Teinte.alerte, in: RoundedRectangle(cornerRadius: OrisRadius.button, style: .continuous))
                }
                .buttonStyle(.plain)
            }
        }
        .carte()
    }
}
