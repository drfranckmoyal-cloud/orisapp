import LocalAuthentication
import SwiftUI

/// Face ID (ou le code de l'iPhone) à l'ouverture, et au retour après deux minutes :
/// un téléphone posé au fauteuil ne donne pas accès aux dossiers.
@MainActor
@Observable
final class Verrou {
    static let reglage = "oris.verrou.faceid"
    static let delaiRetour: TimeInterval = 120

    private(set) var verrouille: Bool
    private(set) var message: String?
    private var parti: Date?

    static var actif: Bool {
        UserDefaults.standard.object(forKey: reglage) as? Bool ?? true
    }

    /// « Face ID », « Touch ID » ou « le code » : ce que l'iPhone sait faire.
    static var nomMethode: String {
        let contexte = LAContext()
        _ = contexte.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: nil)
        switch contexte.biometryType {
        case .faceID: return "Face ID"
        case .touchID: return "Touch ID"
        case .opticID: return "Optic ID"
        default: return "le code de l’iPhone"
        }
    }

    init() {
        verrouille = Self.actif
    }

    private var enCours = false

    /// Face ID d'abord, seul : iOS ne passe au code que si on le demande (« Utiliser le
    /// code ») ou si Face ID est bloqué. Demander « Face ID ou code » d'emblée, pendant
    /// l'ouverture de l'app, faisait sauter iOS directement au code.
    func deverrouiller(avecCode: Bool = false) async {
        guard verrouille, !enCours else { return }
        enCours = true
        defer { enCours = false }
        // Laisser l'app finir de passer au premier plan : iOS refuse Face ID avant.
        try? await Task.sleep(for: .milliseconds(350))

        let contexte = LAContext()
        contexte.localizedCancelTitle = "Annuler"
        contexte.localizedFallbackTitle = "Utiliser le code"
        var erreur: NSError?
        let biometrie = contexte.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &erreur)
        let politique: LAPolicy = (biometrie && !avecCode)
            ? .deviceOwnerAuthenticationWithBiometrics : .deviceOwnerAuthentication

        if !biometrie, let code = (erreur as? LAError)?.code, !avecCode {
            switch code {
            case .biometryNotAvailable:
                message = "Face ID n’est pas autorisé pour Oris. Réglages › Oris › Face ID : activez-le. En attendant, déverrouillez avec le code."
            case .biometryNotEnrolled:
                message = "Face ID n’est pas configuré sur cet iPhone : déverrouillez avec le code."
            case .biometryLockout:
                message = "Face ID est bloqué après plusieurs échecs : saisissez le code de l’iPhone."
            default:
                break
            }
        }
        // Ni Face ID ni code sur l'appareil (simulateur) : rien à demander.
        guard contexte.canEvaluatePolicy(politique, error: nil) else {
            verrouille = false
            return
        }
        do {
            if try await contexte.evaluatePolicy(politique, localizedReason: "Ouvrir les dossiers de vos patients") {
                verrouille = false
                message = nil
            }
        } catch let erreur as LAError where erreur.code == .userFallback {
            enCours = false
            await deverrouiller(avecCode: true)
        } catch {
            if message == nil {
                message = "Oris reste verrouillé. Touchez « Déverrouiller » pour réessayer."
            }
        }
    }

    func changement(_ phase: ScenePhase) {
        switch phase {
        case .background:
            parti = Date()
        case .active:
            if Self.actif, let parti, Date().timeIntervalSince(parti) > Self.delaiRetour {
                verrouille = true
            }
            parti = nil
        default:
            break
        }
    }
}

/// L'écran posé sur l'app tant qu'elle est verrouillée.
struct EcranVerrou: View {
    let verrou: Verrou

    var body: some View {
        VStack(spacing: OrisSpacing.s24) {
            Spacer()
            SymboleOris(couleur: Teinte.accent)
                .frame(width: 84, height: 84)
            Text("Oris est verrouillé")
                .font(Police.marque(28))
                .foregroundStyle(Teinte.accentFonce)
            if let message = verrou.message {
                Text(message)
                    .font(Police.note)
                    .foregroundStyle(Teinte.encreDouce)
                    .multilineTextAlignment(.center)
            }
            Button {
                Task { await verrou.deverrouiller() }
            } label: {
                Label("Déverrouiller avec \(Verrou.nomMethode)", systemImage: "faceid")
            }
            .buttonStyle(BoutonPrincipal())
            .padding(.horizontal, OrisSpacing.s32)
            Button("Utiliser le code de l’iPhone") {
                Task { await verrou.deverrouiller(avecCode: true) }
            }
            .font(Police.interface(15, .semibold))
            .foregroundStyle(Teinte.accent)
            Spacer()
        }
        .padding(OrisSpacing.s16)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Teinte.fond.ignoresSafeArea())
        // Face ID part tout seul dès que l'écran s'affiche : pas besoin de toucher.
        .task { await verrou.deverrouiller() }
    }
}
