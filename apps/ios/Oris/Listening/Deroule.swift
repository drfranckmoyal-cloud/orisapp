import SwiftUI

/// Consultation ou acte : choisi avant l'écoute, il fixe le modèle de compte rendu.
enum VisitKind: String, CaseIterable, Identifiable, Sendable, Codable {
    case consultation
    case procedure

    var id: String { rawValue }

    var label: String {
        switch self {
        case .consultation: "Consultation"
        case .procedure: "Acte"
        }
    }

    var documentTitle: String {
        switch self {
        case .consultation: "Compte rendu de consultation"
        case .procedure: "Compte rendu opératoire"
        }
    }

    /// Rubriques des modèles du Dr Moyal, dans leur ordre (docs/MODELES_CR.md) — les
    /// mêmes que sur le site (apps/web/src/lib/modeles.ts).
    var rubriques: [String] {
        switch self {
        case .consultation:
            [
                "Motif de la consultation",
                "Examen clinique",
                "Diagnostic / analyse",
                "Proposition thérapeutique",
                "Informations données au patient",
                "Actes réalisés",
                "Suite de la prise en charge",
                "Points d’attention / coordination",
            ]
        case .procedure:
            [
                "Indication",
                "Situation pré-opératoire",
                "Intervention réalisée",
                "Protocole / éléments techniques",
                "Résultat immédiat",
                "Suites et consignes",
                "Coordination / prochaine étape",
            ]
        }
    }
}

/// Le déroulé attendu : un aide-mémoire pâle, qui ne coche rien — il ne prétend pas
/// savoir ce qui a été dit.
struct DerouleView: View {
    let kind: VisitKind
    var compact = false

    var body: some View {
        VStack(alignment: .leading, spacing: compact ? 3 : OrisSpacing.s8) {
            Text(kind.documentTitle.uppercased())
                .font(.caption2.bold())
                .tracking(0.8)
            ForEach(Array(kind.rubriques.enumerated()), id: \.offset) { index, rubrique in
                HStack(alignment: .firstTextBaseline, spacing: OrisSpacing.s8) {
                    Text("\(index + 1)").font(.caption2).monospacedDigit()
                    Text(rubrique).font(compact ? .caption : .subheadline.weight(.semibold))
                }
            }
        }
        .foregroundStyle(OrisColor.ink.opacity(0.55))
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Déroulé du \(kind.documentTitle.lowercased())")
    }
}
