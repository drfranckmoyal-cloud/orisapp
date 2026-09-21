import Foundation
import Network

/// Fait apparaître la question d'iOS « Autoriser Oris à accéder au réseau local ? ».
///
/// Une simple requête vers le Mac ne la déclenche pas toujours : iOS refuse alors en
/// silence. Une recherche d'appareils sur le Wi-Fi (Bonjour), elle, la déclenche à coup
/// sûr. On ne se sert pas du résultat : la recherche s'arrête au bout de quelques secondes.
@MainActor
enum ReseauLocal {
    private static var navigateur: NWBrowser?

    static func demanderLAutorisation() {
        guard navigateur == nil else { return }
        let parametres = NWParameters()
        parametres.includePeerToPeer = true
        let recherche = NWBrowser(for: .bonjour(type: "_oris._tcp", domain: nil), using: parametres)
        navigateur = recherche
        recherche.start(queue: .main)
        Task { @MainActor in
            try? await Task.sleep(for: .seconds(8))
            recherche.cancel()
            navigateur = nil
        }
    }
}
