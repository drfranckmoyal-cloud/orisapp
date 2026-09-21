import SwiftUI

/// Une étiquette légère : un point de couleur et le mot, sans bulle.
struct StatutLeger: View {
    let texte: String
    let ton: Pastille.Ton

    private var couleur: Color {
        switch ton {
        case .neutre, .calme: Teinte.encreTresDouce
        case .valide: Teinte.accent
        case .attention: Teinte.attention
        case .alerte: Teinte.alerte
        }
    }

    var body: some View {
        HStack(spacing: 5) {
            Circle().fill(couleur).frame(width: 6, height: 6)
            Text(texte)
        }
        .font(Police.interface(12, .bold))
        .foregroundStyle(couleur)
        .lineLimit(1)
    }
}

/// Les documents d'une consultation en texte léger : « ✓ Compte rendu · Plan ».
struct DocumentsLegers: View {
    let documents: [DocumentSummary]

    var body: some View {
        HStack(spacing: 5) {
            ForEach(Array(documents.enumerated()), id: \.element.id) { i, d in
                if i > 0 { Text("·").foregroundStyle(Teinte.traitFort) }
                HStack(spacing: 2) {
                    if [.validated, .exported].contains(d.status) {
                        Image(systemName: "checkmark").font(.system(size: 9, weight: .heavy))
                    }
                    Text(Labels.documentType(d.documentType))
                }
                .foregroundStyle(Teinte.document(d.documentType).encre)
            }
        }
        .font(Police.interface(12, .semibold))
        .lineLimit(1)
    }
}
