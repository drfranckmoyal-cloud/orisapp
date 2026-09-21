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
                .font(Police.interface(11, .heavy, relativeTo: .caption))
                .tracking(0.9)
                .foregroundStyle(Teinte.accent.opacity(compact ? 0.6 : 1))
                .padding(.bottom, compact ? 2 : 4)
            ForEach(Array(kind.rubriques.enumerated()), id: \.offset) { index, rubrique in
                HStack(alignment: .firstTextBaseline, spacing: OrisSpacing.s8) {
                    Text("\(index + 1)")
                        .font(Police.interface(11, .heavy).monospacedDigit())
                        .foregroundStyle(Teinte.accent.opacity(compact ? 0.5 : 0.8))
                        .frame(minWidth: 14, alignment: .trailing)
                    Text(rubrique)
                        .font(Police.interface(compact ? 12.5 : 14.5, compact ? .medium : .semibold))
                }
            }
        }
        .foregroundStyle(compact ? Teinte.encreTresDouce : Teinte.encreDouce)
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Déroulé du \(kind.documentTitle.lowercased())")
    }
}
