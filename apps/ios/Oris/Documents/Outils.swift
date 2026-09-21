import PhotosUI
import QuickLook
import SwiftUI
import UIKit

// MARK: - Aperçu d'un PDF : lire, imprimer, partager (AirDrop, Mail…)

/// Le PDF s'ouvre dans l'aperçu d'iOS, qui porte déjà Imprimer et Partager.
/// Le fichier n'existe que le temps de l'aperçu, dans le dossier temporaire de l'app.
struct ApercuPDF: UIViewControllerRepresentable {
    let fichier: URL

    func makeUIViewController(context: Context) -> UINavigationController {
        let apercu = QLPreviewController()
        apercu.dataSource = context.coordinator
        return UINavigationController(rootViewController: apercu)
    }

    func updateUIViewController(_ controller: UINavigationController, context: Context) {}

    func makeCoordinator() -> Source { Source(fichier: fichier) }

    final class Source: NSObject, QLPreviewControllerDataSource {
        let fichier: URL
        init(fichier: URL) { self.fichier = fichier }
        func numberOfPreviewItems(in controller: QLPreviewController) -> Int { 1 }
        func previewController(_ controller: QLPreviewController, previewItemAt index: Int) -> QLPreviewItem {
            fichier as NSURL
        }
    }
}

/// Un PDF posé le temps de l'aperçu, effacé ensuite.
struct PDFOuvert: Identifiable {
    let url: URL
    var id: String { url.path }

    static func poser(_ fichier: Fichier) throws -> PDFOuvert {
        let dossier = FileManager.default.temporaryDirectory.appending(path: "apercus", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: dossier, withIntermediateDirectories: true)
        let url = dossier.appending(path: fichier.nom)
        try fichier.donnees.write(to: url, options: [.atomic, .completeFileProtection])
        return PDFOuvert(url: url)
    }

    func effacer() {
        try? FileManager.default.removeItem(at: url)
    }
}

// MARK: - Photos

/// L'appareil photo de l'iPhone.
struct AppareilPhoto: UIViewControllerRepresentable {
    let prise: (UIImage) -> Void
    @Environment(\.dismiss) private var fermer

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ controller: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Delegue { Delegue(parent: self) }

    final class Delegue: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let parent: AppareilPhoto
        init(parent: AppareilPhoto) { self.parent = parent }

        func imagePickerController(_ picker: UIImagePickerController,
                                   didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            if let image = info[.originalImage] as? UIImage { parent.prise(image) }
            parent.fermer()
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.fermer()
        }
    }
}

/// « Ajouter une photo » : l'appareil photo ou la photothèque, en JPEG prêt à envoyer.
struct BoutonAjoutPhoto: View {
    var titre = "Ajouter une photo"
    let ajout: ([Data]) async -> Void

    @State private var choix: [PhotosPickerItem] = []
    @State private var photothequeOuverte = false
    @State private var appareilOuvert = false
    @State private var envoi = false

    var body: some View {
        Menu {
            if UIImagePickerController.isSourceTypeAvailable(.camera) {
                Button { appareilOuvert = true } label: { Label("Prendre une photo", systemImage: "camera") }
            }
            Button { photothequeOuverte = true } label: { Label("Choisir dans la photothèque", systemImage: "photo.on.rectangle") }
        } label: {
            Label(envoi ? "Envoi…" : titre, systemImage: "camera.fill")
                .font(Police.interface(15, .bold))
                .foregroundStyle(Teinte.accent)
                .frame(maxWidth: .infinity, minHeight: 46)
                .background(Teinte.accentDouce, in: RoundedRectangle(cornerRadius: OrisRadius.button, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: OrisRadius.button, style: .continuous)
                        .strokeBorder(Teinte.accent.opacity(0.25), style: StrokeStyle(lineWidth: 1.2, dash: [5, 4]))
                )
        }
        .disabled(envoi)
        .photosPicker(isPresented: $photothequeOuverte, selection: $choix, maxSelectionCount: 8, matching: .images)
        .fullScreenCover(isPresented: $appareilOuvert) {
            AppareilPhoto { image in
                Task { await envoyer([image]) }
            }
            .ignoresSafeArea()
        }
        .onChange(of: choix) { _, elements in
            guard !elements.isEmpty else { return }
            Task {
                var images: [UIImage] = []
                for element in elements {
                    if let data = try? await element.loadTransferable(type: Data.self), let image = UIImage(data: data) {
                        images.append(image)
                    }
                }
                choix = []
                await envoyer(images)
            }
        }
    }

    private func envoyer(_ images: [UIImage]) async {
        envoi = true
        defer { envoi = false }
        await ajout(images.compactMap { $0.enJPEG() })
    }
}

extension UIImage {
    /// JPEG redressé et ramené à 2400 px au plus : assez pour le PDF, léger sur le Wi-Fi.
    func enJPEG(cote: CGFloat = 2400) -> Data? {
        let echelle = min(1, cote / max(size.width, size.height))
        let taille = CGSize(width: size.width * echelle, height: size.height * echelle)
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        let redessinee = UIGraphicsImageRenderer(size: taille, format: format).image { _ in
            draw(in: CGRect(origin: .zero, size: taille))
        }
        return redessinee.jpegData(compressionQuality: 0.85)
    }
}

/// Une photo du dossier, chargée depuis le serveur.
struct PhotoDistante: View {
    let client: APIClient
    let pieceJointeId: String
    var remplir = true

    @State private var image: UIImage?
    @State private var echec = false

    var body: some View {
        // Le cadre décide de la taille ; la photo s'y loge sans jamais l'élargir.
        Rectangle()
            .fill(Teinte.surfaceDouce)
            .overlay {
                if let image {
                    if remplir {
                        Image(uiImage: image).resizable().scaledToFill()
                    } else {
                        Image(uiImage: image).resizable().scaledToFit()
                    }
                } else if echec {
                    Image(systemName: "photo").foregroundStyle(Teinte.encreTresDouce)
                } else {
                    ProgressView().tint(Teinte.accent)
                }
            }
            .clipped()
        .task(id: pieceJointeId) {
            do {
                image = UIImage(data: try await client.apercu(pieceJointeId: pieceJointeId).donnees)
            } catch {
                echec = true
            }
        }
    }
}

// MARK: - Bandeau de confirmation

/// « Compte rendu validé. » : un bandeau qui descend du haut et repart seul.
struct Toast: ViewModifier {
    @Binding var message: String?

    func body(content: Content) -> some View {
        content.overlay(alignment: .top) {
            if let message {
                Label(message, systemImage: "checkmark.circle.fill")
                    .font(Police.interface(15, .bold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 18)
                    .padding(.vertical, 12)
                    .background(Teinte.accent, in: Capsule())
                    .shadow(color: Teinte.accentFonce.opacity(0.35), radius: 12, y: 6)
                    .padding(.top, 8)
                    .transition(.move(edge: .top).combined(with: .opacity))
                    .task {
                        try? await Task.sleep(for: .seconds(2.8))
                        withAnimation { self.message = nil }
                    }
                    .accessibilityAddTraits(.isStaticText)
            }
        }
        .animation(.spring(duration: 0.35), value: message)
    }
}

extension View {
    func toast(_ message: Binding<String?>) -> some View { modifier(Toast(message: message)) }
}

/// Deux à quatre onglets en pilules, sur le fond sable — comme les filtres du site.
struct Onglets<Valeur: Hashable>: View {
    @Binding var selection: Valeur
    let choix: [(Valeur, String)]

    var body: some View {
        HStack(spacing: 4) {
            ForEach(choix, id: \.0) { valeur, titre in
                Button { selection = valeur } label: {
                    Text(titre)
                        .font(Police.interface(14, valeur == selection ? .bold : .semibold))
                        .foregroundStyle(valeur == selection ? Teinte.accent : Teinte.encreDouce)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                        .frame(maxWidth: .infinity, minHeight: 36)
                        .background {
                            if valeur == selection {
                                RoundedRectangle(cornerRadius: 10, style: .continuous)
                                    .fill(Teinte.surface)
                                    .shadow(color: Teinte.encre.opacity(0.1), radius: 3, y: 1)
                            }
                        }
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(valeur == selection ? .isSelected : [])
            }
        }
        .padding(4)
        .background(Teinte.surfaceDouce, in: RoundedRectangle(cornerRadius: 13, style: .continuous))
    }
}
