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

    func deverrouiller() async {
        guard verrouille else { return }
        let contexte = LAContext()
        contexte.localizedCancelTitle = "Annuler"
        var erreur: NSError?
        // Ni Face ID ni code sur l'appareil (simulateur) : rien à demander.
        guard contexte.canEvaluatePolicy(.deviceOwnerAuthentication, error: &erreur) else {
            verrouille = false
            return
        }
        do {
            if try await contexte.evaluatePolicy(.deviceOwnerAuthentication,
                                                 localizedReason: "Ouvrir les dossiers de vos patients") {
                verrouille = false
                message = nil
            }
        } catch {
            message = "Oris reste verrouillé. Touchez « Déverrouiller » pour réessayer."
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
            Spacer()
        }
        .padding(OrisSpacing.s16)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Teinte.fond.ignoresSafeArea())
    }
}
