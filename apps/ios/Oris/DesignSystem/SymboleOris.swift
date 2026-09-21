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

    /// Hauteur d'une barre (0,35…1) à l'instant t : trois ondes lentes de périodes
    /// différentes par barre, qui ne se répètent jamais à l'identique — une voix, pas
    /// un métronome.
    static func niveau(barre i: Int, temps t: Double) -> CGFloat {
        let d = Double(i)
        let onde = sin(t * 1.3 + d * 1.7) * 0.45
            + sin(t * 2.1 + d * 2.9) * 0.35
            + sin(t * 0.7 + d * 0.8) * 0.20
        return CGFloat(0.675 + 0.325 * onde)
    }

    var body: some View {
        GeometryReader { geo in
            let k = min(geo.size.width, geo.size.height) / 120
            TimelineView(.animation(paused: !anime || sansMouvement)) { contexte in
                let t = contexte.date.timeIntervalSinceReferenceDate
                ZStack(alignment: .topLeading) {
                    ForEach(Self.barres.indices, id: \.self) { i in
                        let barre = Self.barres[i]
                        let echelle = anime && !sansMouvement ? Self.niveau(barre: i, temps: t) : 1
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
