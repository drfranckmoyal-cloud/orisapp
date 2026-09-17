import SwiftUI

/// Révision iPhone (docs/DESIGN_SYSTEM.md) : Compte rendu | Plan, et « À vérifier ».
struct ConsultationDetailView: View {
    enum Tab: Hashable {
        case document(DocumentDocumentType)
        case review
    }

    @State var model: ConsultationDetailViewModel
    @State private var tab: Tab = .document(.consultationNote)

    var body: some View {
        Group {
            switch model.state {
            case .loading:
                ProgressView("Chargement…")
            case .failed:
                ContentUnavailableView("Consultation indisponible", systemImage: "exclamationmark.triangle")
            case .loaded(let content):
                loaded(content)
            }
        }
        .background(OrisColor.cloud)
        .navigationBarTitleDisplayMode(.inline)
        .refreshable { await model.refresh() }
        .task { await model.refresh() }
    }

    @ViewBuilder
    private func loaded(_ content: ConsultationDetailViewModel.Content) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: OrisSpacing.s16) {
                VStack(alignment: .leading, spacing: OrisSpacing.s4) {
                    Text(content.encounter.patient.displayName)
                        .font(.title2.bold())
                        .foregroundStyle(OrisColor.deepBlue)
                    Text("\(Labels.encounterStatus(content.encounter.status)) · dossier clinique v\(content.encounter.objectVersion)")
                        .font(.subheadline)
                }

                ForEach(content.criticalWarnings, id: \.code) { warning in
                    Label {
                        Text("\(warning.message) Le compte rendu n’est pas exhaustif.")
                    } icon: {
                        Image(systemName: "exclamationmark.octagon.fill")
                    }
                    .foregroundStyle(OrisColor.danger)
                    .padding(OrisSpacing.s12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(OrisColor.white, in: RoundedRectangle(cornerRadius: OrisRadius.card))
                }

                Picker("Vue", selection: $tab) {
                    ForEach(content.documents) { document in
                        Text(Labels.documentType(document.documentType)).tag(Tab.document(document.documentType))
                    }
                    Text("À vérifier (\(content.reviewItemCount))").tag(Tab.review)
                }
                .pickerStyle(.segmented)

                switch tab {
                case .document(let type):
                    if let document = content.documents.first(where: { $0.documentType == type }) {
                        DocumentCard(document: document)
                    }
                case .review:
                    ReviewCard(content: content)
                }
            }
            .padding(OrisSpacing.s16)
        }
    }
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
        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
            HStack {
                Text(Labels.documentStatus(document.status))
                    .font(.caption.bold())
                    .padding(.horizontal, OrisSpacing.s8)
                    .padding(.vertical, OrisSpacing.s4)
                    .background(OrisColor.cloud, in: Capsule())
                Text("Version \(document.version)")
                    .font(.caption)
            }
            if !document.isCurrent {
                Label("Rédigé avant la dernière correction : à régénérer.", systemImage: "arrow.triangle.2.circlepath")
                    .font(.footnote)
                    .foregroundStyle(OrisColor.warning)
            }
            ForEach(sections, id: \.title) { section in
                VStack(alignment: .leading, spacing: OrisSpacing.s4) {
                    Text(section.title.uppercased())
                        .font(.caption.bold())
                        .foregroundStyle(OrisColor.deepBlue)
                    ForEach(Array(section.claims.enumerated()), id: \.offset) { _, claim in
                        Text(claim.text)
                            .font(.body)
                            .foregroundStyle(OrisColor.graphite)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        }
        .padding(OrisSpacing.s16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(OrisColor.white, in: RoundedRectangle(cornerRadius: OrisRadius.card))
    }
}

private struct ReviewCard: View {
    let content: ConsultationDetailViewModel.Content

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s16) {
            if content.reviewItemCount == 0 {
                Text("Aucun point signalé. La validation reste une action du praticien.")
                    .font(.subheadline)
            }
            ForEach(content.clinicalObject.warnings, id: \.code) { warning in
                Label(warning.message, systemImage: warning.severity == .critical ? "exclamationmark.octagon" : "exclamationmark.triangle")
            }
            ForEach(content.documents) { document in
                ForEach(Array(document.validationIssues.enumerated()), id: \.offset) { _, issue in
                    Label("\(Labels.documentType(document.documentType)) : \(Labels.issue(issue.code))", systemImage: "exclamationmark.triangle")
                }
            }

            Text("Faits cliniques (\(content.clinicalObject.facts.count))")
                .font(.headline)
                .foregroundStyle(OrisColor.deepBlue)
            ForEach(content.clinicalObject.facts, id: \.factId) { fact in
                VStack(alignment: .leading, spacing: OrisSpacing.s4) {
                    Text(fact.concept + (fact.teeth.isEmpty ? "" : " — dent \(fact.teeth.joined(separator: ", "))"))
                        .font(.subheadline.bold())
                    Text([Labels.assertion(fact.assertion), Labels.clinicalStatus(fact.clinicalStatus), Labels.certainty(fact.certainty)].joined(separator: " · "))
                        .font(.caption)
                }
                .accessibilityElement(children: .combine)
            }
        }
        .padding(OrisSpacing.s16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(OrisColor.white, in: RoundedRectangle(cornerRadius: OrisRadius.card))
    }
}
