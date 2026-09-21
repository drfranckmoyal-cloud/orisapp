import SwiftUI

/// L'app iPhone parle la même langue visuelle que le site (apps/web/src/app/theme.css) :
/// neutres chauds, vert profond, Manrope pour l'interface, Fraunces pour la marque.
/// Les écrans n'utilisent que ces noms — jamais une couleur brute.
enum Teinte {
    static let fond = Color(hex: 0xF5F2EC)
    static let surface = Color.white
    static let surface2 = Color(hex: 0xFDFBF8)
    static let surfaceDouce = Color(hex: 0xEBE5DB)

    static let encre = Color(hex: 0x1A1815)
    static let encreDouce = Color(hex: 0x544D44)
    static let encreTresDouce = Color(hex: 0x8A8073)

    static let trait = Color(hex: 0xE3DCCF)
    static let traitFort = Color(hex: 0xCDC4B3)

    static let accent = Color(hex: 0x14533B)
    static let accentVif = Color(hex: 0x1A6B4C)
    static let accentFonce = Color(hex: 0x0E3A29)
    static let accentDouce = Color(hex: 0xE5EFE9)
    static let accentClair = Color(hex: 0xBFDCCF)

    static let attention = Color(hex: 0xA8540A)
    static let attentionDouce = Color(hex: 0xFBEEDD)
    static let alerte = Color(hex: 0x9C2A1C)
    static let alerteDouce = Color(hex: 0xFBEAE7)

    /// Une teinte par type de document, comme sur le site.
    static func document(_ type: DocumentDocumentType) -> (encre: Color, fond: Color) {
        switch type {
        case .consultationNote: (Color(hex: 0x14533B), Color(hex: 0xE3EFE8))
        case .treatmentPlanText: (Color(hex: 0x1F5A8C), Color(hex: 0xE4EEF8))
        case .operativeNote: (Color(hex: 0x9A4A0B), Color(hex: 0xFBECDC))
        case .patientSummary: (Color(hex: 0x6B3F8F), Color(hex: 0xF0E8F7))
        case .referralLetter: (Color(hex: 0x4A5561), Color(hex: 0xECEEF1))
        }
    }
}

extension Color {
    init(hex: UInt32) {
        self.init(
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255
        )
    }
}

/// Manrope pour tout ; Fraunces pour le nom « Oris » et les grands titres de marque.
enum Police {
    static func interface(_ taille: CGFloat, _ graisse: Font.Weight = .regular, relativeTo style: Font.TextStyle = .body) -> Font {
        .custom("Manrope", size: taille, relativeTo: style).weight(graisse)
    }

    static func marque(_ taille: CGFloat, relativeTo style: Font.TextStyle = .title) -> Font {
        .custom("Fraunces", size: taille, relativeTo: style).weight(.semibold)
    }

    static let petit = interface(12, .bold, relativeTo: .caption)
    static let note = interface(13.5, .medium, relativeTo: .footnote)
    static let texte = interface(15.5, .regular, relativeTo: .body)
    static let texteFort = interface(15.5, .bold, relativeTo: .body)
    static let titreCarte = interface(17.5, .bold, relativeTo: .headline)
    static let titrePage = interface(30, .heavy, relativeTo: .largeTitle)
}

// MARK: - Cartes

/// La carte du site : blanche, filet chaud, relief doux en trois couches.
struct Carte: ViewModifier {
    var rembourrage: CGFloat = OrisSpacing.s16
    var fond: Color = Teinte.surface

    func body(content: Content) -> some View {
        content
            .padding(rembourrage)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(fond, in: RoundedRectangle(cornerRadius: OrisRadius.card, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: OrisRadius.card, style: .continuous)
                    .strokeBorder(Teinte.trait, lineWidth: 1)
            )
            .shadow(color: Teinte.encre.opacity(0.05), radius: 1, y: 1)
            .shadow(color: Teinte.encre.opacity(0.08), radius: 14, y: 8)
    }
}

extension View {
    func carte(rembourrage: CGFloat = OrisSpacing.s16, fond: Color = Teinte.surface) -> some View {
        modifier(Carte(rembourrage: rembourrage, fond: fond))
    }

    /// Fond crème de toutes les pages, en mode clair quoi qu'il arrive.
    func pageOris() -> some View {
        self
            .scrollContentBackground(.hidden)
            .background(Teinte.fond.ignoresSafeArea())
    }
}

// MARK: - En-tête de page

/// Petit surtitre en capitales, puis le titre — comme en haut de chaque page du site.
struct EnTetePage: View {
    let surtitre: String
    let titre: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(surtitre.uppercased())
                .font(Police.interface(11.5, .bold, relativeTo: .caption))
                .tracking(1.1)
                .foregroundStyle(Teinte.encreTresDouce)
            Text(titre)
                .font(Police.titrePage)
                .tracking(-0.6)
                .foregroundStyle(Teinte.encre)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isHeader)
    }
}

/// Le symbole et le nom, comme dans le menu du site.
struct MarqueOris: View {
    var body: some View {
        HStack(spacing: 8) {
            Image("Symbole-vert")
                .resizable()
                .interpolation(.high)
                .frame(width: 26, height: 26)
            Text("Oris")
                .font(Police.marque(26))
                .foregroundStyle(Teinte.accentFonce)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Oris")
    }
}

// MARK: - Boutons

/// Bouton principal : vert profond en dégradé, texte blanc.
struct BoutonPrincipal: ButtonStyle {
    @Environment(\.isEnabled) private var actif

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(Police.interface(17, .bold, relativeTo: .headline))
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity, minHeight: 54)
            .background(
                LinearGradient(colors: [Teinte.accentVif, Teinte.accent, Teinte.accentFonce],
                               startPoint: .topLeading, endPoint: .bottomTrailing),
                in: RoundedRectangle(cornerRadius: OrisRadius.button, style: .continuous)
            )
            .shadow(color: Teinte.accentFonce.opacity(0.35), radius: 10, y: 6)
            .opacity(actif ? (configuration.isPressed ? 0.85 : 1) : 0.45)
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

/// Bouton secondaire : blanc, filet, texte vert — « Nouveau patient » du site.
struct BoutonSecondaire: ButtonStyle {
    var compact = false
    @Environment(\.isEnabled) private var actif

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(Police.interface(compact ? 14 : 16, .bold, relativeTo: .subheadline))
            .foregroundStyle(Teinte.accent)
            .padding(.horizontal, compact ? 14 : 18)
            .frame(maxWidth: compact ? nil : .infinity, minHeight: compact ? 38 : 50)
            .background(Teinte.surface, in: RoundedRectangle(cornerRadius: OrisRadius.button, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: OrisRadius.button, style: .continuous)
                    .strokeBorder(Teinte.traitFort, lineWidth: 1)
            )
            .shadow(color: Teinte.encre.opacity(0.06), radius: 3, y: 2)
            .opacity(actif ? (configuration.isPressed ? 0.8 : 1) : 0.45)
    }
}

// MARK: - Pastilles

/// Pastille de statut : le mot dit l'état, la couleur ne fait qu'aider.
struct Pastille: View {
    enum Ton { case neutre, valide, attention, alerte, calme }

    let texte: String
    var ton: Ton = .neutre

    private var couleurs: (encre: Color, fond: Color) {
        switch ton {
        case .neutre: (Teinte.encreDouce, Teinte.surfaceDouce)
        case .valide: (Teinte.accent, Teinte.accentDouce)
        case .attention: (Teinte.attention, Teinte.attentionDouce)
        case .alerte: (Teinte.alerte, Teinte.alerteDouce)
        case .calme: (Teinte.encreDouce, Teinte.surface2)
        }
    }

    var body: some View {
        Text(texte)
            .font(Police.interface(12, .bold, relativeTo: .caption))
            .foregroundStyle(couleurs.encre)
            .lineLimit(1)
            .padding(.horizontal, 9)
            .padding(.vertical, 4)
            .background(couleurs.fond, in: Capsule())
    }
}

/// Pastille d'un type de document (« ✓ Compte rendu »), teinte du type.
struct PastilleDocument: View {
    let type: DocumentDocumentType
    var valide = false

    var body: some View {
        let t = Teinte.document(type)
        HStack(spacing: 3) {
            if valide { Image(systemName: "checkmark").font(.system(size: 9, weight: .heavy)) }
            Text(Labels.documentType(type))
        }
        .font(Police.interface(11.5, .bold, relativeTo: .caption))
        .foregroundStyle(t.encre)
        .lineLimit(1)
        .padding(.horizontal, 8)
        .padding(.vertical, 3)
        .background(t.fond, in: Capsule())
        .overlay(Capsule().strokeBorder(t.encre.opacity(0.18), lineWidth: 1))
    }
}

/// Initiales dans un rond : vert pâle par défaut (patient, praticien), ou dans la teinte
/// de la spécialité pour un correspondant.
struct Vignette: View {
    let initiales: String
    var taille: CGFloat = 38
    var teinte: TeinteVignette = .standard

    var body: some View {
        Text(initiales)
            .font(Police.interface(taille * 0.34, .heavy, relativeTo: .caption))
            .foregroundStyle(teinte.encre)
            .frame(width: taille, height: taille)
            .background(teinte.fond, in: Circle())
            .overlay(Circle().strokeBorder(teinte.bord, lineWidth: 1))
            .accessibilityHidden(true)
    }
}

struct TeinteVignette: Equatable {
    let fond: Color
    let bord: Color
    let encre: Color

    static let standard = TeinteVignette(fond: Teinte.accentDouce, bord: Teinte.accent.opacity(0.12), encre: Teinte.accent)
    static let neutre = TeinteVignette(fond: Teinte.surfaceDouce, bord: Teinte.traitFort, encre: Teinte.encreDouce)

    /// Les teintes du carnet, les mêmes que sur le site (correspondants.module.css).
    static let palette: [TeinteVignette] = [
        .init(fond: Color(hex: 0xE5EFE9), bord: Color(hex: 0xC9DED4), encre: Color(hex: 0x14533B)), // vert
        .init(fond: Color(hex: 0xE4E9F0), bord: Color(hex: 0xC9D4E2), encre: Color(hex: 0x2C4A6B)), // ardoise
        .init(fond: Color(hex: 0xF6E6DA), bord: Color(hex: 0xE6CDB8), encre: Color(hex: 0x8A4213)), // terre
        .init(fond: Color(hex: 0xEDE2EE), bord: Color(hex: 0xDBC8DE), encre: Color(hex: 0x5E3566)), // prune
        .init(fond: Color(hex: 0xF5ECD4), bord: Color(hex: 0xE5D6AD), encre: Color(hex: 0x7A5A12)), // ocre
        .init(fond: Color(hex: 0xDCEFEE), bord: Color(hex: 0xBFDEDB), encre: Color(hex: 0x1D5B58)), // lagune
        .init(fond: Color(hex: 0xE7EEE0), bord: Color(hex: 0xD2DDC6), encre: Color(hex: 0x45602F)), // sauge
        .init(fond: Color(hex: 0xE5E4F2), bord: Color(hex: 0xCDCAE4), encre: Color(hex: 0x403A75)), // indigo
        .init(fond: Color(hex: 0xFADDE6), bord: Color(hex: 0xEEB8C9), encre: Color(hex: 0xA03A58)), // rose
    ]

    /// Spécialités dont la couleur est arrêtée (comme sur le site).
    static let fixes: [String: Int] = ["Omnipraticien": 0, "ODF": 1, "CMF": 2, "Pédodontie": 8]

    /// Même règle que le site : couleur fixe, sinon rang parmi les spécialités du cabinet.
    static func specialite(_ specialite: String, connues: [String]) -> TeinteVignette {
        guard !specialite.isEmpty else { return .neutre }
        if let fixe = fixes[specialite] { return palette[fixe] }
        let libres = palette.indices.filter { !fixes.values.contains($0) }.map { palette[$0] }
        let autres = connues.filter { fixes[$0] == nil }
        if let rang = autres.firstIndex(of: specialite) { return libres[rang % libres.count] }
        var somme = 0
        for lettre in specialite.unicodeScalars { somme = (somme * 31 + Int(lettre.value)) % 100_000 }
        return libres[somme % libres.count]
    }
}

/// Le bouton d'ajout, flottant en bas à droite, sous le pouce — comme « Nouveau
/// message » dans Mail : on le trouve sans chercher.
struct BoutonFlottant: View {
    let titre: String
    var icone = "plus"
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(titre, systemImage: icone)
                .font(Police.interface(16, .heavy))
                .foregroundStyle(.white)
                .padding(.horizontal, 20)
                .frame(height: 54)
                .background(
                    LinearGradient(colors: [Teinte.accentVif, Teinte.accent, Teinte.accentFonce],
                                   startPoint: .topLeading, endPoint: .bottomTrailing),
                    in: Capsule()
                )
                .overlay(Capsule().strokeBorder(.white.opacity(0.15), lineWidth: 1))
                .shadow(color: Teinte.accentFonce.opacity(0.4), radius: 14, y: 8)
        }
        .buttonStyle(.plain)
        .padding(.trailing, OrisSpacing.s16)
        .padding(.bottom, OrisSpacing.s12)
    }
}

/// « NOM Prénom » : le nom de famille en capitales grasses, comme sur le site.
struct NomPatient: View {
    let patient: PatientSummary
    var taille: CGFloat = 16

    var body: some View {
        (Text(patient.lastName.uppercased()).font(Police.interface(taille, .heavy))
            + Text(" \(patient.firstName)").font(Police.interface(taille, .medium)))
            .foregroundStyle(Teinte.encre)
            .lineLimit(1)
    }
}

extension PatientSummary {
    var initiales: String {
        "\(firstName.prefix(1))\(lastName.prefix(1))".uppercased()
    }
}

// MARK: - Statut d'une consultation

extension ClinicalEncounterStatus {
    var ton: Pastille.Ton {
        switch self {
        case .review: .attention
        case .validated, .exported: .valide
        case .audioError, .uploadInterrupted, .transcriptionFailed, .generationFailed: .alerte
        case .recording, .paused, .processing, .finalizing: .valide
        case .draft, .archived: .neutre
        }
    }
}

// MARK: - Apparence des barres système

enum ApparenceOris {
    /// Titres de navigation et barre d'onglets aux couleurs et polices du site.
    @MainActor
    static func appliquer() {
        let barre = UINavigationBarAppearance()
        barre.configureWithTransparentBackground()
        barre.backgroundColor = UIColor(Teinte.fond)
        barre.shadowColor = .clear
        let encre = UIColor(Teinte.encre)
        barre.largeTitleTextAttributes = [.font: UIFont.manrope(32, .heavy), .foregroundColor: encre]
        barre.titleTextAttributes = [.font: UIFont.manrope(17, .bold), .foregroundColor: encre]
        UINavigationBar.appearance().standardAppearance = barre
        UINavigationBar.appearance().scrollEdgeAppearance = barre
        UINavigationBar.appearance().compactAppearance = barre
        UINavigationBar.appearance().tintColor = UIColor(Teinte.accent)
    }
}

private extension UIFont {
    /// Manrope à la graisse voulue, par sa famille : la police est variable, on laisse iOS
    /// choisir la bonne instance. Repli sur la police système si Manrope manque.
    static func manrope(_ taille: CGFloat, _ graisse: UIFont.Weight) -> UIFont {
        let descripteur = UIFontDescriptor(fontAttributes: [
            .family: "Manrope",
            .traits: [UIFontDescriptor.TraitKey.weight: graisse],
        ])
        let police = UIFont(descriptor: descripteur, size: taille)
        return police.familyName == "Manrope" ? police : .systemFont(ofSize: taille, weight: graisse)
    }
}

/// Une ligne de formulaire : le nom du champ à gauche, toujours visible, la saisie à droite.
struct ChampFiche: View {
    let titre: String
    @Binding var texte: String
    var clavier: UIKeyboardType = .default
    var brut = false
    /// Plusieurs lignes (adresse postale) : le nom reste en haut.
    var long = false

    var body: some View {
        HStack(alignment: long ? .top : .center, spacing: OrisSpacing.s12) {
            Text(titre)
                .font(Police.interface(14, .semibold))
                .foregroundStyle(Teinte.encreTresDouce)
                .frame(width: 104, alignment: .leading)
            TextField(titre, text: $texte, axis: long ? .vertical : .horizontal)
                .keyboardType(clavier)
                .textInputAutocapitalization(brut ? .never : .sentences)
                .autocorrectionDisabled(brut)
                .foregroundStyle(Teinte.encre)
        }
    }
}
