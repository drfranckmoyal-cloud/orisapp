import SwiftUI

/// Modifier la fiche d'un patient : identité, naissance, mail, numéro de dossier, note.
struct EditionPatientView: View {
    let client: APIClient
    let fiche: PatientFiche
    let enregistree: (PatientFiche) -> Void

    @Environment(\.dismiss) private var fermer
    @State private var prenom = ""
    @State private var nom = ""
    @State private var avecNaissance = false
    @State private var naissance = Calendar.current.date(from: DateComponents(year: 1980, month: 1, day: 1)) ?? Date()
    @State private var email = ""
    @State private var dossier = ""
    @State private var note = ""
    @State private var enCours = false
    @State private var erreur: String?

    private var complete: Bool {
        !prenom.trimmingCharacters(in: .whitespaces).isEmpty && !nom.trimmingCharacters(in: .whitespaces).isEmpty
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Identité") {
                    ChampFiche(titre: "Prénom", texte: $prenom)
                    ChampFiche(titre: "Nom", texte: $nom)
                    Toggle("Date de naissance connue", isOn: $avecNaissance)
                    if avecNaissance {
                        DatePicker("Naissance", selection: $naissance, in: ...Date(), displayedComponents: .date)
                            .environment(\.locale, Locale(identifier: "fr_FR"))
                    }
                }
                Section {
                    ChampFiche(titre: "Mail", texte: $email, clavier: .emailAddress, brut: true)
                    ChampFiche(titre: "N° de dossier", texte: $dossier, brut: true)
                } header: {
                    Text("Coordonnées")
                } footer: {
                    Text("L’adresse mail sert à envoyer ses documents au patient.")
                }
                Section("Note") {
                    TextField("Note sur le patient", text: $note, axis: .vertical).lineLimit(2...6)
                }
                if let erreur {
                    Text(erreur).font(Police.note).foregroundStyle(Teinte.alerte)
                }
            }
            .font(Police.interface(15.5, .medium))
            .foregroundStyle(Teinte.encre)
            .tint(Teinte.accent)
            .pageOris()
            .navigationTitle("Fiche patient")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Annuler") { fermer() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button(enCours ? "…" : "Enregistrer") { Task { await enregistrer() } }
                        .disabled(enCours || !complete)
                }
            }
            .onAppear {
                prenom = fiche.firstName
                nom = fiche.lastName
                email = fiche.email
                dossier = fiche.externalId ?? ""
                note = fiche.note
                if let texte = fiche.birthDate, let date = DateOris.lireJour(texte) {
                    avecNaissance = true
                    naissance = date
                }
            }
        }
    }

    private func enregistrer() async {
        enCours = true
        erreur = nil
        defer { enCours = false }
        do {
            let nouvelle = try await client.modifierPatient(
                id: fiche.id, prenom: prenom, nom: nom, naissance: avecNaissance ? naissance : nil,
                email: email, dossier: dossier, note: note
            )
            enregistree(nouvelle)
            fermer()
        } catch {
            erreur = Labels.erreur(error)
        }
    }
}

/// Les correspondants d'un patient : qui l'a adressé, à qui on l'adresse, qui le suit.
/// Le destinataire coché d'office à l'envoi vient d'ici.
struct CorrespondantsPatient: View {
    let client: APIClient
    let patientId: String
    @Binding var toast: String?

    @State private var liens: [Rattachement] = []
    @State private var ajout = false
    @State private var ouverte: Correspondant?
    @State private var erreur: String?

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
            HStack {
                Text("Correspondants").font(Police.titreCarte).foregroundStyle(Teinte.encre)
                Spacer()
                Button { ajout = true } label: {
                    Label("Rattacher", systemImage: "plus")
                        .font(Police.interface(14, .bold))
                        .foregroundStyle(Teinte.accent)
                }
            }
            if liens.isEmpty {
                Text("Aucun correspondant rattaché.")
                    .font(Police.note).foregroundStyle(Teinte.encreTresDouce)
            }
            ForEach(liens) { lien in
                HStack(spacing: 4) {
                    Button { ouverte = lien.correspondent } label: {
                        LigneCorrespondant(correspondant: lien.correspondent, role: lien.role)
                    }
                    .buttonStyle(.plain)
                    Menu {
                        ForEach(RoleCorrespondant.allCases) { role in
                            Button {
                                Task { await rattacher(lien.correspondent.id, role) }
                            } label: {
                                if role == lien.role { Label(role.libelle, systemImage: "checkmark") } else { Text(role.libelle) }
                            }
                        }
                        Divider()
                        Button("Retirer de cette fiche", role: .destructive) {
                            Task { await detacher(lien.correspondent) }
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                            .font(.system(size: 20))
                            .foregroundStyle(Teinte.encreTresDouce)
                            .frame(width: 44, height: 44)
                    }
                    .accessibilityLabel("Rôle de \(lien.correspondent.nomCourt)")
                }
                if lien.id != liens.last?.id { Divider().overlay(Teinte.trait) }
            }
            if let erreur {
                Text(erreur).font(Police.note).foregroundStyle(Teinte.alerte)
            }
        }
        .carte()
        .sheet(isPresented: $ajout) {
            RattacherView(client: client, patientId: patientId, dejaLa: Set(liens.map(\.id))) { nouveaux, nom in
                liens = nouveaux
                toast = "\(nom) rattaché."
            }
        }
        .sheet(item: $ouverte) { c in
            NavigationStack {
                FicheCorrespondantView(client: client, fiche: c) { _ in
                    Task { await charger() }
                }
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) { Button("Fermer") { ouverte = nil } }
                }
            }
        }
        .task { await charger() }
    }

    private func charger() async {
        liens = (try? await client.rattachements(patientId: patientId)) ?? liens
    }

    private func rattacher(_ id: String, _ role: RoleCorrespondant) async {
        do {
            liens = try await client.rattacher(patientId: patientId, correspondantId: id, role: role)
        } catch {
            erreur = Labels.erreur(error)
        }
    }

    private func detacher(_ c: Correspondant) async {
        do {
            try await client.detacher(patientId: patientId, correspondantId: c.id)
            liens.removeAll { $0.id == c.id }
            toast = "\(c.nomCourt) retiré de la fiche."
        } catch {
            erreur = Labels.erreur(error)
        }
    }
}

/// Rattacher un correspondant : choisir le rôle, puis chercher dans le carnet — ou créer
/// le confrère sur place, rattaché dans le même geste.
struct RattacherView: View {
    let client: APIClient
    let patientId: String
    let dejaLa: Set<String>
    let fait: ([Rattachement], String) -> Void

    @Environment(\.dismiss) private var fermer
    @State private var role: RoleCorrespondant = .referredBy
    @State private var carnet: [Correspondant] = []
    @State private var recherche = ""
    @State private var creation = false
    @State private var erreur: String?

    private var proposes: [Correspondant] {
        let cherche = recherche.sansAccents
        return carnet.filter { !dejaLa.contains($0.id) }
            .filter { cherche.isEmpty || "\($0.nomCourt) \($0.specialty) \($0.practice)".sansAccents.contains(cherche) }
            .sorted { ($0.favorite ? 0 : 1, $0.lastName.sansAccents) < ($1.favorite ? 0 : 1, $1.lastName.sansAccents) }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: OrisSpacing.s16) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Ce correspondant…").font(Police.petit).foregroundStyle(Teinte.encreTresDouce)
                        Onglets(selection: $role, choix: RoleCorrespondant.allCases.map { ($0, $0.court) })
                        Text(role.libelle)
                            .font(Police.note).foregroundStyle(Teinte.accent)
                    }
                    ChampRecherche(texte: $recherche)
                    Button { creation = true } label: {
                        Label("Nouveau correspondant", systemImage: "person.badge.plus")
                    }
                    .buttonStyle(BoutonSecondaire())
                    if let erreur {
                        Text(erreur).font(Police.note).foregroundStyle(Teinte.alerte)
                    }
                    VStack(spacing: 0) {
                        ForEach(proposes) { c in
                            Button { Task { await rattacher(c) } } label: {
                                HStack {
                                    LigneCorrespondant(correspondant: c)
                                    Image(systemName: "plus.circle.fill")
                                        .font(.system(size: 22)).foregroundStyle(Teinte.accent)
                                }
                                .padding(.horizontal, 14).padding(.vertical, 10)
                            }
                            .buttonStyle(.plain)
                            if c.id != proposes.last?.id { Divider().overlay(Teinte.trait).padding(.leading, 64) }
                        }
                    }
                    .carte(rembourrage: 0)
                }
                .padding(OrisSpacing.s16)
            }
            .pageOris()
            .navigationTitle("Rattacher")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Annuler") { fermer() } }
            }
            .navigationDestination(isPresented: $creation) {
                FicheCorrespondantView(client: client, fiche: .nouveau()) { cree in
                    if let cree { Task { await rattacher(cree) } }
                }
            }
            .task { carnet = (try? await client.correspondants()) ?? [] }
        }
        .tint(Teinte.accent)
    }

    private func rattacher(_ c: Correspondant) async {
        do {
            let liens = try await client.rattacher(patientId: patientId, correspondantId: c.id, role: role)
            fait(liens, c.nomCourt)
            fermer()
        } catch {
            erreur = Labels.erreur(error)
        }
    }
}
