import SwiftUI

/// Le symbole Oris dessiné en barres (design/marque/oris-symbole-barres.svg) : de loin un
/// niveau sonore, de près une molaire. Animé, les barres respirent comme une voix.
struct SymboleOris: View {
    var couleur: Color = Teinte.accent
    var anime = false

    @Environment(\.accessibilityReduceMotion) private var sansMouvement

    /// x, y, hauteur des cinq barres dans un carré de 120.
    private static let barres: [(x: CGFloat, y: CGFloat, h: CGFloat)] = [
        (13, 38, 34), (31, 20, 76), (49, 30, 48), (67, 20, 76), (85, 38, 34),
    ]

    var body: some View {
        GeometryReader { geo in
            let k = min(geo.size.width, geo.size.height) / 120
            TimelineView(.animation(paused: !anime || sansMouvement)) { contexte in
                let t = contexte.date.timeIntervalSinceReferenceDate
                ZStack(alignment: .topLeading) {
                    ForEach(Self.barres.indices, id: \.self) { i in
                        let barre = Self.barres[i]
                        let echelle = anime && !sansMouvement
                            ? 0.73 + 0.27 * cos((t / 1.15 + Double(i) * 0.14) * 2 * .pi)
                            : 1
                        RoundedRectangle(cornerRadius: 5 * k)
                            .fill(couleur)
                            .frame(width: 10 * k, height: barre.h * k)
                            .scaleEffect(x: 1, y: echelle)
                            .offset(x: barre.x * k, y: barre.y * k)
                    }
                }
                .frame(width: 120 * k, height: 120 * k, alignment: .topLeading)
            }
            .frame(width: geo.size.width, height: geo.size.height)
        }
        .aspectRatio(1, contentMode: .fit)
        .accessibilityHidden(true)
    }
}

/// L'ouverture de l'app : le symbole et le nom en grand, le slogan dessous.
struct EcranOuverture: View {
    var body: some View {
        VStack(spacing: 18) {
            SymboleOris(couleur: Teinte.accent, anime: true)
                .frame(width: 128, height: 128)
            Text("Oris")
                .font(Police.marque(64))
                .foregroundStyle(Teinte.accentFonce)
            Text("Vous soignez. Oris documente.")
                .font(Police.interface(17, .semibold))
                .foregroundStyle(Teinte.encreDouce)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Teinte.fond.ignoresSafeArea())
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Oris. Vous soignez. Oris documente.")
    }
}
