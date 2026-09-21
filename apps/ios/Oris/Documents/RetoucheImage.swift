import SwiftUI
import UIKit

/// Retoucher une photo du document, comme sur le site : recadrer en tirant les bords (huit
/// poignées, ou le cadre entier), retourner en miroir horizontal ou vertical. Le résultat
/// remplace la photo dans le document ; l'originale reste dans le dossier du patient.
struct RetoucheImageView: View {
    let client: APIClient
    let pieceJointeId: String
    /// L'image corrigée, en JPEG, ou nil si rien n'a changé.
    let valider: (Data?) async -> Void

    @Environment(\.dismiss) private var fermer
    @State private var image: UIImage?
    @State private var cadre = CGRect(x: 0, y: 0, width: 1, height: 1) // en fractions de l'image
    @State private var depart: CGRect?
    @State private var miroirH = false
    @State private var miroirV = false
    @State private var enCours = false

    private var modifie: Bool {
        miroirH || miroirV || cadre != CGRect(x: 0, y: 0, width: 1, height: 1)
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: OrisSpacing.s16) {
                if let image {
                    GeometryReader { geo in
                        let zone = Self.ajuster(image.size, dans: geo.size)
                        ZStack(alignment: .topLeading) {
                            Image(uiImage: image)
                                .resizable()
                                .scaleEffect(x: miroirH ? -1 : 1, y: miroirV ? -1 : 1)
                                .frame(width: zone.width, height: zone.height)
                            cache(zone.size)
                            cadreDeRecadrage(zone.size)
                        }
                        .frame(width: zone.width, height: zone.height)
                        .position(x: geo.size.width / 2, y: geo.size.height / 2)
                    }
                    .padding(.horizontal, 20)
                } else {
                    Spacer()
                    ProgressView().tint(.white)
                    Spacer()
                }

                HStack(spacing: 10) {
                    outil("Miroir ↔", "arrow.left.and.right.righttriangle.left.righttriangle.right", actif: miroirH) { miroirH.toggle() }
                    outil("Miroir ↕", "arrow.up.and.down.righttriangle.up.righttriangle.down", actif: miroirV) { miroirV.toggle() }
                    outil("Rétablir", "arrow.counterclockwise", actif: false) {
                        withAnimation {
                            cadre = CGRect(x: 0, y: 0, width: 1, height: 1)
                            miroirH = false
                            miroirV = false
                        }
                    }
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 8)
            }
            .background(Color.black.ignoresSafeArea())
            .navigationTitle("Retoucher")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(Color.black, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Annuler") { fermer() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button(enCours ? "…" : "Valider") { Task { await terminer() } }
                        .bold()
                        .disabled(enCours || image == nil)
                }
            }
            .tint(.white)
            .task {
                if let fichier = try? await client.apercu(pieceJointeId: pieceJointeId),
                   let lue = UIImage(data: fichier.donnees) {
                    image = Self.redressee(lue)
                }
            }
        }
    }

    // MARK: Cadre et poignées

    /// Le voile sombre hors du cadre : on voit ce qui sera gardé.
    private func cache(_ taille: CGSize) -> some View {
        let r = Self.enPoints(cadre, taille)
        return Path { p in
            p.addRect(CGRect(origin: .zero, size: taille))
            p.addRect(r)
        }
        .fill(Color.black.opacity(0.55), style: FillStyle(eoFill: true))
        .allowsHitTesting(false)
    }

    private func cadreDeRecadrage(_ taille: CGSize) -> some View {
        let r = Self.enPoints(cadre, taille)
        return ZStack(alignment: .topLeading) {
            // Le cadre entier se déplace.
            Rectangle()
                .strokeBorder(.white, lineWidth: 2)
                .background(Color.white.opacity(0.001))
                .frame(width: r.width, height: r.height)
                .offset(x: r.minX, y: r.minY)
                .gesture(glisser(taille) { d, c in
                    CGRect(x: min(max(0, c.minX + d.width), 1 - c.width),
                           y: min(max(0, c.minY + d.height), 1 - c.height),
                           width: c.width, height: c.height)
                })
            ForEach(Poignee.allCases, id: \.self) { p in
                Circle()
                    .fill(.white)
                    .frame(width: 22, height: 22)
                    .shadow(radius: 2)
                    .frame(width: 44, height: 44) // zone de toucher confortable
                    .contentShape(Rectangle())
                    .position(p.point(dans: r))
                    .gesture(glisser(taille) { d, c in p.tirer(c, de: d) })
            }
        }
    }

    private func glisser(_ taille: CGSize, _ calcul: @escaping (CGSize, CGRect) -> CGRect) -> some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { v in
                let debut = depart ?? cadre
                depart = debut
                let d = CGSize(width: v.translation.width / taille.width, height: v.translation.height / taille.height)
                cadre = calcul(d, debut)
            }
            .onEnded { _ in depart = nil }
    }

    enum Poignee: CaseIterable {
        case hautGauche, haut, hautDroite, droite, basDroite, bas, basGauche, gauche

        func point(dans r: CGRect) -> CGPoint {
            switch self {
            case .hautGauche: CGPoint(x: r.minX, y: r.minY)
            case .haut: CGPoint(x: r.midX, y: r.minY)
            case .hautDroite: CGPoint(x: r.maxX, y: r.minY)
            case .droite: CGPoint(x: r.maxX, y: r.midY)
            case .basDroite: CGPoint(x: r.maxX, y: r.maxY)
            case .bas: CGPoint(x: r.midX, y: r.maxY)
            case .basGauche: CGPoint(x: r.minX, y: r.maxY)
            case .gauche: CGPoint(x: r.minX, y: r.midY)
            }
        }

        /// Tirer une poignée déplace son ou ses bords ; le cadre garde au moins 8 %.
        func tirer(_ c: CGRect, de d: CGSize) -> CGRect {
            let mini = 0.08
            var gauche = c.minX, droite = c.maxX, haut = c.minY, bas = c.maxY
            if [.hautGauche, .gauche, .basGauche].contains(self) { gauche = min(max(0, gauche + d.width), droite - mini) }
            if [.hautDroite, .droite, .basDroite].contains(self) { droite = max(min(1, droite + d.width), gauche + mini) }
            if [.hautGauche, .haut, .hautDroite].contains(self) { haut = min(max(0, haut + d.height), bas - mini) }
            if [.basGauche, .bas, .basDroite].contains(self) { bas = max(min(1, bas + d.height), haut + mini) }
            return CGRect(x: gauche, y: haut, width: droite - gauche, height: bas - haut)
        }
    }

    // MARK: Outils

    private func outil(_ titre: String, _ icone: String, actif: Bool, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Image(systemName: icone).font(.system(size: 18, weight: .semibold))
                Text(titre).font(Police.interface(12, .bold))
            }
            .foregroundStyle(actif ? Teinte.accentClair : .white)
            .frame(maxWidth: .infinity, minHeight: 56)
            .background(Color.white.opacity(actif ? 0.18 : 0.08), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
        .buttonStyle(.plain)
    }

    // MARK: Rendu

    private func terminer() async {
        enCours = true
        defer { enCours = false }
        guard modifie, let image else {
            await valider(nil)
            fermer()
            return
        }
        await valider(Self.rendre(image, cadre: cadre, miroirH: miroirH, miroirV: miroirV))
        fermer()
    }

    /// Miroir d'abord, puis recadrage — comme le site : le cadre s'entend sur l'image vue.
    static func rendre(_ image: UIImage, cadre: CGRect, miroirH: Bool, miroirV: Bool) -> Data? {
        let taille = image.size
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        let retournee = UIGraphicsImageRenderer(size: taille, format: format).image { ctx in
            let c = ctx.cgContext
            c.translateBy(x: miroirH ? taille.width : 0, y: miroirV ? taille.height : 0)
            c.scaleBy(x: miroirH ? -1 : 1, y: miroirV ? -1 : 1)
            image.draw(in: CGRect(origin: .zero, size: taille))
        }
        let coupe = CGRect(x: cadre.minX * taille.width, y: cadre.minY * taille.height,
                           width: cadre.width * taille.width, height: cadre.height * taille.height).integral
        let finale = UIGraphicsImageRenderer(size: coupe.size, format: format).image { _ in
            retournee.draw(at: CGPoint(x: -coupe.minX, y: -coupe.minY))
        }
        return finale.jpegData(compressionQuality: 0.92)
    }

    static func redressee(_ image: UIImage) -> UIImage {
        guard image.imageOrientation != .up else { return image }
        let format = UIGraphicsImageRendererFormat()
        format.scale = image.scale
        return UIGraphicsImageRenderer(size: image.size, format: format).image { _ in
            image.draw(in: CGRect(origin: .zero, size: image.size))
        }
    }

    static func ajuster(_ image: CGSize, dans zone: CGSize) -> CGRect {
        guard image.width > 0, image.height > 0 else { return .zero }
        let echelle = min(zone.width / image.width, zone.height / image.height)
        return CGRect(x: 0, y: 0, width: image.width * echelle, height: image.height * echelle)
    }

    static func enPoints(_ fraction: CGRect, _ taille: CGSize) -> CGRect {
        CGRect(x: fraction.minX * taille.width, y: fraction.minY * taille.height,
               width: fraction.width * taille.width, height: fraction.height * taille.height)
    }
}
