import SwiftUI

/// Paramètres iPhone : à quel serveur l'app parle, avec quel jeton, et dans quel état il est.
/// Le reste des réglages (cabinet, titres, vocabulaire) se fait sur l'ordinateur.
struct SettingsView: View {
    @State var model: HomeViewModel
    let apiURL: URL
    var reconnect: () -> Void = {}

    @State private var serveur = Connexion.serveurSaisi
    @State private var jeton = ""
    @State private var jetonPresent = Connexion.jeton != nil
    @State private var message: String?
    @State private var verrouActif = Verrou.actif

    private var appVersion: String {
        let info = Bundle.main.infoDictionary
        let version = info?["CFBundleShortVersionString"] as? String ?? "—"
        let build = info?["CFBundleVersion"] as? String ?? "—"
        return "\(version) (\(build))"
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    ServerStatusCard(state: model.serverState, diagnostic: model.diagnostic)
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                }

                Section {
                    TextField("http://localhost:8000", text: $serveur)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField(jetonPresent ? "Jeton enregistré — saisir pour remplacer" : "Jeton d’accès (oris_…)", text: $jeton)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    Button("Enregistrer et se reconnecter", action: enregistrer)
                        .font(Police.interface(15.5, .bold))
                    if jetonPresent {
                        Button("Oublier le jeton", role: .destructive) {
                            Connexion.oublierJeton()
                            jetonPresent = false
                            reconnect()
                        }
                    }
                    if let message {
                        Text(message).font(Police.note).foregroundStyle(Teinte.alerte)
                    }
                } header: {
                    Text("Connexion à Oris")
                } footer: {
                    Text("Sur l’iPhone : l’adresse du Mac sur le Wi-Fi du cabinet (par exemple 192.168.1.20:8000) et un jeton créé sur le Mac. Laissez l’adresse vide pour revenir à « localhost ».")
                }

                Section {
                    Toggle("Verrouiller avec \(Verrou.nomMethode)", isOn: $verrouActif)
                        .onChange(of: verrouActif) { _, actif in
                            UserDefaults.standard.set(actif, forKey: Verrou.reglage)
                        }
                } header: {
                    Text("Sécurité")
                } footer: {
                    Text("Demandé à l’ouverture d’Oris et au retour après deux minutes d’absence.")
                }

                Section("Cet appareil") {
                    LabeledContent("Serveur utilisé", value: apiURL.absoluteString)
                    LabeledContent("Version de l’app", value: appVersion)
                }

                Section {
                    Text("Le cabinet, vos titres, le vocabulaire et les préférences de rédaction se règlent sur l’ordinateur, dans Oris › Paramètres.")
                        .font(Police.note)
                        .foregroundStyle(Teinte.encreDouce)
                }
            }
            .font(Police.interface(15.5, .medium))
            .foregroundStyle(Teinte.encre)
            .tint(Teinte.accent)
            .pageOris()
            .navigationTitle("Paramètres")
            .refreshable { await model.refresh() }
            .task { await model.refresh() }
        }
    }

    private func enregistrer() {
        message = nil
        if !serveur.trimmingCharacters(in: .whitespaces).isEmpty, Connexion.adresse(serveur) == nil {
            message = "Adresse du serveur non reconnue."
            return
        }
        Connexion.enregistrer(serveur: serveur)
        let saisi = jeton.trimmingCharacters(in: .whitespacesAndNewlines)
        if !saisi.isEmpty {
            guard Connexion.enregistrer(jeton: saisi) else {
                message = "Le jeton n’a pas pu être rangé dans le trousseau."
                return
            }
            jeton = ""
            jetonPresent = true
        }
        reconnect()
    }
}
