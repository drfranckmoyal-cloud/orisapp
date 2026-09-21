import Foundation
import SwiftUI

struct ResultatEssaiMicro: Codable, Equatable, Sendable {
    let texte: String
    let crete: Double
    let moyen: Double
    let muet: Bool
}

extension APIClient {
    /// Quelques secondes de son, transcrites aussitôt par le serveur et oubliées.
    func essaiMicro(pcm: Data, tauxEntree: Int, entree: String) async throws -> ResultatEssaiMicro {
        var request = URLRequest(url: baseURL.appending(path: "diagnostic/micro"))
        request.httpMethod = "POST"
        request.setValue(AudioFormat.contentType, forHTTPHeaderField: "Content-Type")
        request.setValue(String(tauxEntree), forHTTPHeaderField: "X-Taux-Entree")
        request.setValue(entree, forHTTPHeaderField: "X-Entree")
        request.httpBody = pcm
        request.timeoutInterval = 60
        return try await perform(request)
    }
}

/// « Tester le micro » : on parle six secondes, Oris dit ce qu'il a compris. Rien n'est
/// gardé, ni sur l'iPhone ni sur le serveur.
@MainActor
@Observable
final class EssaiMicro {
    enum Etat: Equatable {
        case pret
        case ecoute(restant: Int)
        case analyse
        case resultat(ResultatEssaiMicro, entree: String, taux: Int)
        case echec(String)
    }

    static let duree = 6

    private(set) var etat: Etat = .pret
    private(set) var niveau: Double = 0
    private let client: APIClient

    init(client: APIClient) {
        self.client = client
    }

    func lancer() async {
        let micro = MicrophoneInput()
        let flux: AsyncStream<AudioInputEvent>
        do {
            flux = try await micro.start()
        } catch {
            etat = .echec("Le micro n’a pas pu démarrer. Vérifiez qu’Oris y a accès dans Réglages › Confidentialité › Micro.")
            return
        }
        let (entree, taux) = MicrophoneInput.entreeActuelle
        var resampler: Resampler?
        var pcm = Data()
        let fin = Date().addingTimeInterval(Double(Self.duree))
        etat = .ecoute(restant: Self.duree)
        for await evenement in flux {
            guard case .samples(let echantillons, let rythme) = evenement else { continue }
            if resampler?.inputRate != rythme { resampler = Resampler(inputRate: rythme) }
            pcm.append(PCM.bytes(PCM.toInt16(resampler!.process(echantillons))))
            niveau = PCM.level(echantillons)
            let reste = Int(fin.timeIntervalSinceNow.rounded(.up))
            if reste <= 0 { break }
            etat = .ecoute(restant: reste)
        }
        micro.stop()
        niveau = 0
        etat = .analyse
        do {
            let resultat = try await client.essaiMicro(pcm: pcm, tauxEntree: taux, entree: entree)
            etat = .resultat(resultat, entree: entree, taux: taux)
        } catch {
            etat = .echec(Labels.erreur(error))
        }
    }
}

/// La carte « Tester le micro » des Paramètres.
struct CarteEssaiMicro: View {
    @State var essai: EssaiMicro

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
            HStack(spacing: 12) {
                SymboleOris(couleur: Teinte.accent, niveauVoix: enCours ? essai.niveau : nil)
                    .frame(width: 34, height: 34)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Tester le micro").font(Police.titreCarte).foregroundStyle(Teinte.encre)
                    Text("Dites une phrase pendant \(EssaiMicro.duree) secondes : Oris affiche ce qu’il a compris. Rien n’est gardé.")
                        .font(Police.note).foregroundStyle(Teinte.encreDouce)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            switch essai.etat {
            case .pret:
                EmptyView()
            case .ecoute(let restant):
                Text("Parlez… \(restant) s").font(Police.interface(15, .bold)).foregroundStyle(Teinte.accent)
            case .analyse:
                HStack { ProgressView().tint(Teinte.accent); Text("Oris écoute l’enregistrement…").font(Police.note) }
            case .resultat(let r, let entree, let taux):
                VStack(alignment: .leading, spacing: 6) {
                    if r.muet {
                        Label("Aucun son capté : le micro n’a rien enregistré.", systemImage: "mic.slash")
                            .foregroundStyle(Teinte.alerte)
                    } else if r.texte.isEmpty {
                        Label("Du son a été capté, mais aucune parole reconnue.", systemImage: "waveform.badge.exclamationmark")
                            .foregroundStyle(Teinte.attention)
                    } else {
                        Label("Oris vous entend :", systemImage: "checkmark.circle.fill").foregroundStyle(Teinte.accent)
                        Text("« \(r.texte) »").font(Police.interface(15, .medium)).foregroundStyle(Teinte.encre)
                    }
                    Text("Micro : \(entree) · \(taux) Hz · volume \(Int(r.crete * 100)) %")
                        .font(Police.interface(11.5, .medium)).foregroundStyle(Teinte.encreTresDouce)
                }
                .font(Police.interface(14.5, .semibold))
            case .echec(let message):
                Text(message).font(Police.note).foregroundStyle(Teinte.alerte)
            }
            Button {
                Task { await essai.lancer() }
            } label: {
                Label(enCours ? "Écoute…" : "Lancer l’essai", systemImage: "mic.fill")
            }
            .buttonStyle(BoutonSecondaire())
            .disabled(enCours)
        }
    }

    private var enCours: Bool {
        switch essai.etat {
        case .ecoute, .analyse: true
        default: false
        }
    }
}
