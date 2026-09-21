import SwiftUI

/// Paramètres de l'iPhone, rangés comme l'app Réglages : la carte du praticien en tête,
/// puis des rubriques groupées — les mêmes que la page Paramètres du site.
struct SettingsView: View {
    @State var model: HomeViewModel
    let client: APIClient
    var reconnect: () -> Void = {}

    @State private var cabinet: Cabinet?
    @State private var connecteurs: EtatConnecteurs?
    @State private var appareilsActifs = 0

    var body: some View {
        NavigationStack {
            List {
                EnTetePage(surtitre: "Réglages", titre: "Paramètres")
                    .listRowInsets(EdgeInsets(top: 4, leading: 4, bottom: 0, trailing: 4))
                    .listRowBackground(Color.clear)

                Section {
                    NavigationLink {
                        ProfilView(client: client, cabinet: $cabinet)
                    } label: {
                        BanniereProfil(cabinet: cabinet)
                    }
                }

                Section("Vous") {
                    ligne("Rédaction", "text.alignleft", Teinte.document(.consultationNote).encre) {
                        RedactionView(client: client)
                    }
                }

                Section("Cabinet") {
                    ligne("Cabinet et en-tête", "building.2", Color(hex: 0x2C4A6B)) {
                        CabinetView(client: client, cabinet: $cabinet)
                    }
                    ligne("Envoi des documents", "paperplane", Color(hex: 0x1F5A8C)) {
                        EnvoiReglageView(client: client, cabinet: $cabinet)
                    }
                }

                Section("Consultation") {
                    ligne("Écoute et micro", "mic", Teinte.accent) {
                        EcouteView(client: client)
                    }
                }

                Section("Connexions") {
                    ligne("Connexion à Oris", "network", Color(hex: 0x1D5B58), detail: etatServeur) {
                        ConnexionView(model: model, client: client, reconnect: reconnect)
                    }
                    ligne("Appareils connectés", "iphone", Color(hex: 0x403A75),
                          detail: appareilsActifs > 0 ? "\(appareilsActifs)" : nil) {
                        AppareilsView(client: client)
                    }
                    ligne("Doctolib et SmileCloud", "link", Color(hex: 0x7A5A12),
                          detail: connecteurs.map { "Doctolib : \($0.doctolib.etat)" }) {
                        ConnecteursView(client: client)
                    }
                }

                Section("Oris") {
                    ligne("Sécurité", "lock.shield", Teinte.alerte) {
                        SecuriteView()
                    }
                    ligne("À propos", "info.circle", Teinte.encreDouce) {
                        AProposView(model: model)
                    }
                }
            }
            .listStyle(.insetGrouped)
            .font(Police.interface(15.5, .medium))
            .tint(Teinte.accent)
            .pageOris()
            .toolbar(.hidden, for: .navigationBar)
            .refreshable { await charger() }
            .task { await charger() }
        }
    }

    private var etatServeur: String {
        switch model.serverState {
        case .reachable: "connecté"
        case .unreachable: "injoignable"
        case .checking: "…"
        }
    }

    private func ligne<Destination: View>(
        _ titre: String, _ icone: String, _ couleur: Color, detail: String? = nil,
        @ViewBuilder destination: @escaping () -> Destination
    ) -> some View {
        NavigationLink(destination: destination) {
            HStack(spacing: 12) {
                Image(systemName: icone)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(.white)
                    .frame(width: 30, height: 30)
                    .background(couleur.gradient, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                Text(titre)
                    .font(Police.interface(16, .semibold))
                    .foregroundStyle(Teinte.encre)
                Spacer(minLength: 4)
                if let detail {
                    Text(detail)
                        .font(Police.interface(14, .medium))
                        .foregroundStyle(Teinte.encreTresDouce)
                        .lineLimit(1)
                }
            }
            .padding(.vertical, 2)
        }
    }

    private func charger() async {
        await model.refresh()
        cabinet = (try? await client.cabinet()) ?? cabinet
        connecteurs = try? await client.connecteurs()
        appareilsActifs = ((try? await client.appareils()) ?? []).filter(\.actif).count
    }
}

/// La carte du praticien, en tête — comme l'identifiant Apple dans Réglages.
private struct BanniereProfil: View {
    let cabinet: Cabinet?

    var body: some View {
        HStack(spacing: 14) {
            Vignette(initiales: cabinet?.initiales ?? "—", taille: 58)
            VStack(alignment: .leading, spacing: 3) {
                Text(cabinet?.praticien ?? "Praticien")
                    .font(Police.interface(19, .heavy))
                    .foregroundStyle(Teinte.encre)
                Text(cabinet.map { "\($0.name) · profil, titres, RPPS" } ?? "Chargement…")
                    .font(Police.interface(13, .medium))
                    .foregroundStyle(Teinte.encreTresDouce)
                    .lineLimit(1)
            }
        }
        .padding(.vertical, 6)
    }
}

// MARK: - Sous-pages

/// Une sous-page de réglages : fond crème, polices d'Oris, message de confirmation.
private struct PageReglage<Contenu: View>: View {
    let titre: String
    @Binding var message: String?
    @ViewBuilder var contenu: () -> Contenu

    var body: some View {
        Form {
            contenu()
            if let message {
                Section {
                    Label(message, systemImage: "checkmark.circle.fill")
                        .font(Police.note)
                        .foregroundStyle(Teinte.accent)
                }
            }
        }
        .font(Police.interface(15.5, .medium))
        .foregroundStyle(Teinte.encre)
        .tint(Teinte.accent)
        .pageOris()
        .navigationTitle(titre)
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct ProfilView: View {
    let client: APIClient
    @Binding var cabinet: Cabinet?
    @State private var brouillon: Cabinet?
    @State private var message: String?

    var body: some View {
        PageReglage(titre: "Mon profil", message: $message) {
            if brouillon != nil {
                Section {
                    Picker("Civilité", selection: lien(\.practitionerTitle)) {
                        ForEach(["Dr", "Pr", "M.", "Mme", ""], id: \.self) { Text($0.isEmpty ? "—" : $0).tag($0) }
                    }
                    LabeledContent("Nom", value: brouillon?.practitionerName ?? "")
                } footer: {
                    Text("Le nom se change avec la gestion des comptes, plus tard.")
                }
                Section("Titres, une ligne chacun") {
                    TextField("Chirurgien-dentiste…", text: lien(\.qualifications), axis: .vertical)
                        .lineLimit(2...6)
                }
                Section("RPPS et mention légale") {
                    TextField("RPPS", text: lien(\.legal))
                }
                BoutonEnregistrer { await enregistrer("Profil enregistré : vos prochains documents porteront ces titres.") }
            } else {
                ProgressView()
            }
        }
        .onAppear { brouillon = cabinet }
    }

    private func lien(_ chemin: WritableKeyPath<Cabinet, String>) -> Binding<String> {
        Binding(get: { brouillon?[keyPath: chemin] ?? "" }, set: { brouillon?[keyPath: chemin] = $0 })
    }

    private func enregistrer(_ texte: String) async {
        guard let brouillon else { return }
        if let nouveau = try? await client.enregistrer(brouillon) {
            cabinet = nouveau
            message = texte
        }
    }
}

private struct CabinetView: View {
    let client: APIClient
    @Binding var cabinet: Cabinet?
    @State private var brouillon: Cabinet?
    @State private var message: String?

    var body: some View {
        PageReglage(titre: "Cabinet et en-tête", message: $message) {
            if let b = brouillon {
                Section {
                    ApercuEnTete(cabinet: b)
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                } footer: {
                    Text("Ce qui s’imprime en haut de chaque compte rendu et de chaque courrier.")
                }
                Section("Cabinet") {
                    ChampFiche(titre: "Nom", texte: lien(\.name))
                    ChampFiche(titre: "Adresse", texte: lien(\.address), long: true)
                    ChampFiche(titre: "Ville", texte: lien(\.city))
                }
                Section("Coordonnées") {
                    ChampFiche(titre: "Téléphone", texte: lien(\.phone), clavier: .phonePad, brut: true)
                    ChampFiche(titre: "Courriel", texte: lien(\.email), clavier: .emailAddress, brut: true)
                }
                BoutonEnregistrer {
                    if let nouveau = try? await client.enregistrer(b) {
                        cabinet = nouveau
                        message = "Cabinet enregistré : l’en-tête des prochains documents est à jour."
                    }
                }
            } else {
                ProgressView()
            }
        }
        .onAppear { brouillon = cabinet }
    }

    private func lien(_ chemin: WritableKeyPath<Cabinet, String>) -> Binding<String> {
        Binding(get: { brouillon?[keyPath: chemin] ?? "" }, set: { brouillon?[keyPath: chemin] = $0 })
    }
}

/// L'en-tête tel qu'il sortira sur le PDF : texte à gauche, en caractères du document.
private struct ApercuEnTete: View {
    let cabinet: Cabinet

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(cabinet.praticien)
                .font(.custom("Times New Roman", size: 18).bold())
                .foregroundStyle(Teinte.accentFonce)
            ForEach(cabinet.qualifications.split(separator: "\n").map(String.init), id: \.self) { ligne in
                Text(ligne).font(.custom("Times New Roman", size: 12))
            }
            Text(cabinet.legal).font(.custom("Times New Roman", size: 11)).foregroundStyle(Teinte.encreDouce)
            Text([cabinet.name, cabinet.address].filter { !$0.isEmpty }.joined(separator: " · "))
                .font(.custom("Times New Roman", size: 11)).foregroundStyle(Teinte.encreDouce)
            Text([cabinet.email, cabinet.phone].filter { !$0.isEmpty }.joined(separator: " · "))
                .font(.custom("Times New Roman", size: 11)).foregroundStyle(Teinte.encreDouce)
        }
        .foregroundStyle(Teinte.encre)
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(.white, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).strokeBorder(Teinte.trait))
    }
}

private struct EnvoiReglageView: View {
    let client: APIClient
    @Binding var cabinet: Cabinet?
    @State private var adresse = ""
    @State private var boite: BoiteEnvoi?
    @State private var message: String?

    var body: some View {
        PageReglage(titre: "Envoi des documents", message: $message) {
            Section {
                if let boite {
                    HStack {
                        Circle().fill(boite.configure ? Teinte.accent : Teinte.attention).frame(width: 9, height: 9)
                        Text(boite.configure ? "Boîte branchée" : "Boîte non branchée")
                            .font(Police.interface(15, .bold))
                        Spacer()
                    }
                    Text(boite.configure ? "\(boite.adresse) · \(boite.serveur)"
                         : "Il manque le mot de passe d’application de la messagerie, sur le Mac.")
                        .font(Police.note).foregroundStyle(Teinte.encreDouce)
                }
            } header: {
                Text("État")
            }
            Section("Adresse d’envoi") {
                TextField("prenom.nom@exemple.fr", text: $adresse)
                    .keyboardType(.emailAddress).textInputAutocapitalization(.never).autocorrectionDisabled()
            }
            BoutonEnregistrer {
                guard var c = cabinet else { return }
                c.sendingEmail = adresse
                if let nouveau = try? await client.enregistrer(c) {
                    cabinet = nouveau
                    boite = try? await client.boiteEnvoi()
                    message = "Adresse d’envoi enregistrée."
                }
            }
        }
        .task {
            adresse = cabinet?.sendingEmail ?? ""
            boite = try? await client.boiteEnvoi()
        }
    }
}

private struct RedactionView: View {
    let client: APIClient
    @State private var preferences: PreferencesRedaction?
    @State private var message: String?

    var body: some View {
        PageReglage(titre: "Rédaction", message: $message) {
            Section {
                Picker("Longueur", selection: Binding(
                    get: { preferences?.documentLength ?? "standard" },
                    set: { valeur in Task { await changer(valeur) } }
                )) {
                    Text("Standard").tag("standard")
                    Text("Concise").tag("concise")
                }
                .pickerStyle(.segmented)
            } header: {
                Text("Longueur des comptes rendus")
            } footer: {
                Text("Standard : phrases rédigées. Concise : l’essentiel, plus court. Le fond vient toujours de ce qui a été dit.")
            }
            Section("Mots préférés") {
                let n = preferences?.terminology.count ?? 0
                Text(n == 0 ? "Aucun : Oris emploie ses propres mots." : "\(n) mot\(n > 1 ? "s" : "") remplacé\(n > 1 ? "s" : "") par les vôtres.")
                    .font(Police.note).foregroundStyle(Teinte.encreDouce)
                Text("Le dictionnaire se gère sur l’ordinateur, dans « Oris apprend ».")
                    .font(Police.note).foregroundStyle(Teinte.encreTresDouce)
            }
        }
        .task { preferences = try? await client.preferences() }
    }

    private func changer(_ valeur: String) async {
        if let nouvelles = try? await client.longueurDocuments(valeur) {
            preferences = nouvelles
            message = "Enregistré : s’applique aux prochains documents."
        }
    }
}

private struct EcouteView: View {
    let client: APIClient
    @State private var config: ClientConfig?
    @State private var message: String?

    var body: some View {
        PageReglage(titre: "Écoute et micro", message: $message) {
            Section {
                CarteEssaiMicro(essai: EssaiMicro(client: client))
            }
            Section("Comment Oris écoute") {
                LabeledContent("Durée maximale", value: config.map { "\($0.maxSessionMinutes) min" } ?? "—")
                LabeledContent("Information du patient",
                               value: config?.patientInformationMode == "confirm" ? "confirmée à chaque écoute" : "non demandée")
                LabeledContent("Micro", value: "celui de l’iPhone")
                LabeledContent("Son enregistré", value: "supprimé après transcription")
            }
        }
        .task { config = try? await client.clientConfig() }
    }
}

/// Connexion au serveur Oris : adresse du Mac et jeton (réglages d'avant, déplacés ici).
private struct ConnexionView: View {
    @State var model: HomeViewModel
    let client: APIClient
    var reconnect: () -> Void

    @State private var serveur = Connexion.serveurSaisi
    @State private var jeton = ""
    @State private var jetonPresent = Connexion.jeton != nil
    @State private var message: String?
    @State private var erreur: String?

    var body: some View {
        PageReglage(titre: "Connexion à Oris", message: $message) {
            Section {
                ServerStatusCard(state: model.serverState, diagnostic: model.diagnostic)
                    .listRowInsets(EdgeInsets())
                    .listRowBackground(Color.clear)
            }
            Section {
                TextField("http://localhost:8000", text: $serveur)
                    .keyboardType(.URL).textInputAutocapitalization(.never).autocorrectionDisabled()
                SecureField(jetonPresent ? "Jeton enregistré — saisir pour remplacer" : "Jeton d’accès (oris_…)", text: $jeton)
                    .textInputAutocapitalization(.never).autocorrectionDisabled()
                Button("Enregistrer et se reconnecter", action: enregistrer)
                    .font(Police.interface(15.5, .bold))
                if jetonPresent {
                    Button("Oublier le jeton", role: .destructive) {
                        Connexion.oublierJeton()
                        jetonPresent = false
                        reconnect()
                    }
                }
                if let erreur {
                    Text(erreur).font(Police.note).foregroundStyle(Teinte.alerte)
                }
            } header: {
                Text("Adresse du Mac et jeton")
            } footer: {
                Text("L’adresse du Mac sur le Wi-Fi du cabinet (par exemple 10.0.0.7:8000) et le jeton de cet iPhone. Serveur utilisé : \(client.baseURL.absoluteString)")
            }
        }
        .task { await model.refresh() }
    }

    private func enregistrer() {
        erreur = nil
        if !serveur.trimmingCharacters(in: .whitespaces).isEmpty, Connexion.adresse(serveur) == nil {
            erreur = "Adresse du serveur non reconnue."
            return
        }
        Connexion.enregistrer(serveur: serveur)
        let saisi = jeton.trimmingCharacters(in: .whitespacesAndNewlines)
        if !saisi.isEmpty {
            guard Connexion.enregistrer(jeton: saisi) else {
                erreur = "Le jeton n’a pas pu être rangé dans le trousseau."
                return
            }
            jeton = ""
            jetonPresent = true
        }
        reconnect()
    }
}

private struct AppareilsView: View {
    let client: APIClient
    @State private var appareils: [Appareil] = []
    @State private var aDeconnecter: Appareil?
    @State private var message: String?

    var body: some View {
        PageReglage(titre: "Appareils connectés", message: $message) {
            Section {
                let actifs = appareils.filter(\.actif)
                if actifs.isEmpty {
                    Text("Aucun appareil connecté en dehors du Mac.").font(Police.note).foregroundStyle(Teinte.encreDouce)
                }
                ForEach(actifs) { a in
                    HStack(spacing: 12) {
                        Image(systemName: "iphone")
                            .font(.system(size: 17, weight: .semibold))
                            .foregroundStyle(Teinte.encreDouce)
                            .frame(width: 34, height: 34)
                            .background(Teinte.surfaceDouce, in: RoundedRectangle(cornerRadius: 9, style: .continuous))
                        VStack(alignment: .leading, spacing: 2) {
                            Text(a.nom).font(Police.interface(15.5, .bold))
                            Text("utilisé \(Self.depuis(a.dernierUsage))")
                                .font(Police.interface(12.5, .medium)).foregroundStyle(Teinte.encreTresDouce)
                        }
                        Spacer()
                        Button("Déconnecter", role: .destructive) { aDeconnecter = a }
                            .font(Police.interface(14, .bold))
                            .buttonStyle(.borderless)
                    }
                }
            } footer: {
                Text("Un iPhone perdu se déconnecte ici : il ne lit plus rien. Autoriser un nouvel appareil se fait depuis le Mac, dans Paramètres › Appareils connectés.")
            }
        }
        .confirmationDialog("Déconnecter « \(aDeconnecter?.nom ?? "") » ?", isPresented: Binding(
            get: { aDeconnecter != nil }, set: { if !$0 { aDeconnecter = nil } }
        ), titleVisibility: .visible) {
            Button("Déconnecter", role: .destructive) {
                if let a = aDeconnecter { Task { await deconnecter(a) } }
            }
        } message: {
            Text("Si c’est cet iPhone, il faudra un nouveau code d’accès pour se reconnecter.")
        }
        .task { appareils = (try? await client.appareils()) ?? [] }
        .refreshable { appareils = (try? await client.appareils()) ?? appareils }
    }

    private func deconnecter(_ a: Appareil) async {
        do {
            try await client.deconnecter(appareilId: a.id)
            appareils = (try? await client.appareils()) ?? appareils
            message = "« \(a.nom) » est déconnecté."
        } catch {}
    }

    static func depuis(_ iso: String?) -> String {
        guard let date = DateOris.lire(iso) else { return "jamais" }
        let minutes = Int(Date().timeIntervalSince(date) / 60)
        if minutes < 2 { return "à l’instant" }
        if minutes < 60 { return "il y a \(minutes) min" }
        if minutes < 24 * 60 { return "il y a \(minutes / 60) h" }
        return "le \(DateOris.court(date))"
    }
}

private struct ConnecteursView: View {
    let client: APIClient
    @State private var etat: EtatConnecteurs?
    @State private var message: String?

    var body: some View {
        PageReglage(titre: "Doctolib et SmileCloud", message: $message) {
            Section {
                if let etat {
                    ligne("Doctolib", etat.doctolib)
                    ligne("SmileCloud", etat.smilecloud)
                } else {
                    ProgressView()
                }
            } footer: {
                Text("Lus par l’extension Chrome de Dental Lens, sur le Mac. Pour reconnecter Doctolib, utilisez le bouton « reconnecter » dans la colonne de gauche d’Oris sur le Mac.")
            }
        }
        .task { etat = try? await client.connecteurs() }
        .refreshable { etat = try? await client.connecteurs() }
    }

    private func ligne(_ nom: String, _ v: Voyant) -> some View {
        let couleur: Color = switch v.ton {
        case "actif": Teinte.accent
        case "alerte": Teinte.attention
        case "travail": Teinte.accentVif
        default: Teinte.traitFort
        }
        return VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Circle().fill(couleur).frame(width: 9, height: 9)
                Text(nom).font(Police.interface(15.5, .bold))
                Spacer()
                Text(v.etat).font(Police.interface(14, .bold)).foregroundStyle(couleur == Teinte.traitFort ? Teinte.encreDouce : couleur)
            }
            Text(v.detail).font(Police.note).foregroundStyle(Teinte.encreDouce)
        }
        .padding(.vertical, 4)
    }
}

private struct SecuriteView: View {
    @State private var verrouActif = Verrou.actif
    @State private var message: String?

    var body: some View {
        PageReglage(titre: "Sécurité", message: $message) {
            Section {
                Toggle("Verrouiller avec \(Verrou.nomMethode)", isOn: $verrouActif)
                    .onChange(of: verrouActif) { _, actif in
                        UserDefaults.standard.set(actif, forKey: Verrou.reglage)
                    }
            } footer: {
                Text("Demandé à l’ouverture d’Oris et au retour après deux minutes d’absence.")
            }
            Section("Protection des dossiers") {
                LabeledContent("Accès", value: "code d’accès personnel")
                LabeledContent("Deuxième facteur", value: "avec l’hébergeur agréé")
                LabeledContent("Hébergement agréé santé", value: "pas encore")
                LabeledContent("Journal", value: "sans contenu clinique")
            }
        }
    }
}

private struct AProposView: View {
    @State var model: HomeViewModel
    @State private var message: String?

    private var appVersion: String {
        let info = Bundle.main.infoDictionary
        return "\(info?["CFBundleShortVersionString"] as? String ?? "—") (\(info?["CFBundleVersion"] as? String ?? "—"))"
    }

    var body: some View {
        PageReglage(titre: "À propos", message: $message) {
            Section {
                VStack(spacing: 8) {
                    SymboleOris(couleur: Teinte.accent, anime: true).frame(width: 56, height: 56)
                    Text("Oris").font(Police.marque(30)).foregroundStyle(Teinte.accentFonce)
                    Text("Vous soignez. Oris documente.").font(Police.note).foregroundStyle(Teinte.encreDouce)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
            }
            Section("Versions") {
                LabeledContent("App iPhone", value: appVersion)
                if case .reachable(let sante) = model.serverState {
                    LabeledContent("Serveur", value: sante.version)
                    LabeledContent("Transcription", value: Self.moteur(sante.providers.speechToText))
                    LabeledContent("Rédaction", value: Self.moteur(sante.providers.documentGeneration))
                }
            }
        }
        .task { await model.refresh() }
    }

    static func moteur(_ code: String) -> String {
        ["deepgram": "Deepgram", "anthropic": "Claude", "mock": "simulateur", "azure_speech": "Azure"][code] ?? code
    }
}

/// Le bouton « Enregistrer » des sous-pages.
private struct BoutonEnregistrer: View {
    let action: () async -> Void
    @State private var enCours = false

    var body: some View {
        Section {
            Button {
                Task {
                    enCours = true
                    await action()
                    enCours = false
                }
            } label: {
                Text(enCours ? "Enregistrement…" : "Enregistrer")
            }
            .buttonStyle(BoutonPrincipal())
            .disabled(enCours)
            .listRowInsets(EdgeInsets())
            .listRowBackground(Color.clear)
        }
    }
}
