import AVFoundation
import Foundation
import UserNotifications
#if canImport(UIKit)
import UIKit
#endif

/// Pourquoi l'écoute s'est arrêtée toute seule.
enum CoupureEcoute: String, Sendable {
    /// Appel entrant, Siri, alarme : le système a pris le micro.
    case interruption
    /// Le micro n'est plus là du tout (écouteurs débranchés, service audio redémarré).
    case microPerdu

    var titre: String {
        switch self {
        case .interruption: "Oris a cessé d'écouter"
        case .microPerdu: "Oris a perdu le micro"
        }
    }

    var message: String {
        switch self {
        case .interruption:
            "Un appel ou une alarme a coupé l'écoute. Oris reprend dès que c'est fini ; "
                + "le silence sera signalé dans le dossier."
        case .microPerdu:
            "Plus rien n'est enregistré. Ouvrez Oris et touchez Reprendre."
        }
    }
}

/// Prévenir le praticien, tout de suite, que l'écoute s'est arrêtée.
///
/// Une consultation coupée sans que personne ne le voie, c'est une consultation perdue :
/// Franck a laissé passer la moitié d'une séance parce que son téléphone avait sonné
/// (09/10/2026). L'alerte ne s'arrête pas d'elle-même — elle insiste jusqu'à ce que
/// l'écoute reprenne ou que le praticien la coupe.
@MainActor
protocol AlerteCapture: AnyObject {
    /// Demande l'autorisation de prévenir, au début de la consultation : trop tard sinon.
    func preparer()
    func couper(_ motif: CoupureEcoute)
    func taire()
}

/// L'alerte réelle : vibration insistante, son distinctif, avis sur l'écran verrouillé.
///
/// Les trois ensemble, et pas l'un ou l'autre : pendant qu'un appel sonne, le système
/// interdit à Oris de jouer le moindre son — seuls la vibration et l'avis passent. Et
/// quand le téléphone est en silencieux, c'est la vibration qui reste.
@MainActor
final class AlerteSysteme: AlerteCapture {
    /// Le son dure moins de deux secondes : on le rejoue, sinon il passe inaperçu.
    static let intervalle: TimeInterval = 5
    /// Au-delà, le praticien n'est pas près de son téléphone : insister davantage ne
    /// sert plus à rien, et l'avis reste sur l'écran verrouillé.
    static let rappelsMax = 12
    static let nomDuSon = "ecoute-coupee.wav"
    static let identifiantAvis = "oris.ecoute.coupee"

    private var rappel: Timer?
    private var restants = 0
    private var lecteur: AVAudioPlayer?

    func preparer() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
    }

    func couper(_ motif: CoupureEcoute) {
        guard rappel == nil else { return }  // déjà en train d'alerter
        restants = Self.rappelsMax
        avertir(motif)
        sonner()
        rappel = Timer.scheduledTimer(withTimeInterval: Self.intervalle, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self else { return }
                self.restants -= 1
                guard self.restants > 0 else { return self.arreterLeRappel() }
                self.sonner()
            }
        }
    }

    func taire() {
        arreterLeRappel()
        lecteur?.stop()
        lecteur = nil
        let centre = UNUserNotificationCenter.current()
        centre.removePendingNotificationRequests(withIdentifiers: [Self.identifiantAvis])
        centre.removeDeliveredNotifications(withIdentifiers: [Self.identifiantAvis])
    }

    /// L'avis sur l'écran verrouillé : le seul signal qui reste si le praticien n'a pas
    /// le téléphone en main. Il porte le son distinctif d'Oris, joué par le système —
    /// donc même pendant qu'un appel sonne.
    private func avertir(_ motif: CoupureEcoute) {
        let contenu = UNMutableNotificationContent()
        contenu.title = motif.titre
        contenu.body = motif.message  // aucun nom de patient : un avis se lit écran verrouillé
        contenu.sound = UNNotificationSound(named: UNNotificationSoundName(Self.nomDuSon))
        contenu.interruptionLevel = .timeSensitive
        UNUserNotificationCenter.current().add(
            UNNotificationRequest(identifier: Self.identifiantAvis, content: contenu, trigger: nil)
        )
    }

    private func arreterLeRappel() {
        rappel?.invalidate()
        rappel = nil
        restants = 0
    }

    /// Vibration d'abord : c'est le seul signal qui traverse le silencieux et un appel.
    private func sonner() {
        #if canImport(UIKit)
        let retour = UINotificationFeedbackGenerator()
        retour.prepare()
        retour.notificationOccurred(.error)
        #endif
        jouerLeSon()
    }

    private func jouerLeSon() {
        guard let url = Bundle.main.url(forResource: "ecoute-coupee", withExtension: "wav") else { return }
        // La session d'écoute est fermée quand on arrive ici : on la passe en lecture le
        // temps du signal. Si le système la refuse (un appel sonne), tant pis : la
        // vibration et l'avis ont déjà fait le travail.
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .default, options: [.duckOthers])
        try? session.setActive(true)
        lecteur = try? AVAudioPlayer(contentsOf: url)
        lecteur?.volume = 1
        lecteur?.play()
    }
}

/// Alerte qui ne fait rien : aperçus SwiftUI et tests.
@MainActor
final class AlerteMuette: AlerteCapture {
    private(set) var coupures: [CoupureEcoute] = []
    private(set) var tues = 0
    private(set) var preparee = false

    func preparer() { preparee = true }
    func couper(_ motif: CoupureEcoute) { coupures.append(motif) }
    func taire() { tues += 1 }
}
