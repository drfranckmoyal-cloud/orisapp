import SwiftUI

/// La fiche d'un correspondant : la lire, l'appeler, lui écrire, la corriger.
/// Sert aussi à créer un correspondant (id vide).
struct FicheCorrespondantView: View {
    let client: APIClient
    @State var fiche: Correspondant
    /// Appelé avec la fiche enregistrée (créée ou modifiée), ou nil si elle a été supprimée.
    var termine: (Correspondant?) -> Void = { _ in }

    @Environment(\.dismiss) private var fermer
    @Environment(\.openURL) private var ouvrir
    @State private var specialites: [String] = []
    @State private var enCours = false
    @State private var erreur: String?
    @State private var confirmerSuppression = false

    private var creation: Bool { fiche.id.isEmpty }
    private var complete: Bool { !fiche.lastName.trimmingCharacters(in: .whitespaces).isEmpty }

    var body: some View {
        Form {
            if !creation {
                Section {
                    HStack(spacing: OrisSpacing.s12) {
                        Vignette(initiales: fiche.initiales, taille: 50, teinte: fiche.teinte(specialites))
                        VStack(alignment: .leading, spacing: 3) {
                            Text(fiche.nomCourt).font(Police.interface(19, .heavy)).foregroundStyle(Teinte.encre)
                            Text([fiche.specialty, fiche.practice].filter { !$0.isEmpty }.joined(separator: " · "))
                                .font(Police.note).foregroundStyle(Teinte.encreTresDouce)
                        }
                    }
                    HStack(spacing: 8) {
                        contact("Appeler", "phone.fill", fiche.phone.isEmpty ? nil : URL(string: "tel:\(fiche.phone.filter { !$0.isWhitespace })"))
                        contact("Écrire", "envelope.fill", fiche.email.isEmpty ? nil : URL(string: "mailto:\(fiche.email)"))
                    }
                }
                .listRowBackground(Color.clear)
                .listRowInsets(EdgeInsets())
            }

            Section("Identité") {
                Picker("Type", selection: $fiche.kind) {
                    Text("Praticien").tag("practitioner")
                    Text("Structure").tag("organisation")
                }
                .pickerStyle(.segmented)
                if !fiche.estStructure {
                    Picker("Civilité", selection: $fiche.title) {
                        ForEach(["Dr", "Pr", "M.", "Mme", ""], id: \.self) { Text($0.isEmpty ? "—" : $0).tag($0) }
                    }
                    ChampFiche(titre: "Prénom", texte: $fiche.firstName)
                }
                ChampFiche(titre: fiche.estStructure ? "Structure" : "Nom", texte: $fiche.lastName)
                Picker("Spécialité", selection: $fiche.specialty) {
                    Text("—").tag("")
                    ForEach(specialites + (specialites.contains(fiche.specialty) || fiche.specialty.isEmpty ? [] : [fiche.specialty]),
                            id: \.self) { Text($0).tag($0) }
                }
                ChampFiche(titre: "Cabinet", texte: $fiche.practice)
                Toggle("Favori", isOn: $fiche.favorite)
            }

            Section("Coordonnées") {
                ChampFiche(titre: "Mail", texte: $fiche.email, clavier: .emailAddress, brut: true)
                ChampFiche(titre: "Téléphone", texte: $fiche.phone, clavier: .phonePad, brut: true)
                ChampFiche(titre: "Autre mail", texte: $fiche.secondaryEmail, clavier: .emailAddress, brut: true)
                ChampFiche(titre: "Autre tél.", texte: $fiche.secondaryPhone, clavier: .phonePad, brut: true)
                ChampFiche(titre: "Adresse", texte: $fiche.address, long: true)
            }

            Section("Note") {
                TextField("Note", text: $fiche.note, axis: .vertical).lineLimit(2...6)
            }

            if let erreur {
                Text(erreur).font(Police.note).foregroundStyle(Teinte.alerte)
            }

            if !creation {
                Section {
                    Button("Supprimer du carnet", role: .destructive) { confirmerSuppression = true }
                }
            }
        }
        .font(Police.interface(15.5, .medium))
        .foregroundStyle(Teinte.encre)
        .tint(Teinte.accent)
        .pageOris()
        .navigationTitle(creation ? "Nouveau correspondant" : "Correspondant")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button(enCours ? "…" : "Enregistrer") { Task { await enregistrer() } }
                    .disabled(enCours || !complete)
            }
        }
        .confirmationDialog("Supprimer \(fiche.nomCourt) du carnet ?", isPresented: $confirmerSuppression,
                            titleVisibility: .visible) {
            Button("Supprimer", role: .destructive) { Task { await supprimer() } }
        } message: {
            Text("Il disparaît aussi des fiches patients où il est rattaché. Les documents déjà envoyés ne changent pas.")
        }
        .task { specialites = (try? await client.specialites()) ?? [] }
    }

    private func contact(_ titre: String, _ icone: String, _ url: URL?) -> some View {
        Button {
            if let url { ouvrir(url) }
        } label: {
            Label(titre, systemImage: icone)
        }
        .buttonStyle(BoutonSecondaire())
        .disabled(url == nil)
    }

    private func enregistrer() async {
        enCours = true
        erreur = nil
        defer { enCours = false }
        do {
            let enregistree = creation ? try await client.creer(fiche) : try await client.modifier(fiche)
            fiche = enregistree
            termine(enregistree)
            fermer()
        } catch {
            erreur = Labels.erreur(error)
        }
    }

    private func supprimer() async {
        do {
            try await client.supprimer(correspondantId: fiche.id)
            termine(nil)
            fermer()
        } catch {
            erreur = Labels.erreur(error)
        }
    }
}

/// Une ligne du carnet : initiales, nom, spécialité, favori.
struct LigneCorrespondant: View {
    let correspondant: Correspondant
    var role: RoleCorrespondant? = nil
    /// Les spécialités du cabinet, pour la couleur de la vignette (même règle que le site).
    var specialites: [String] = []

    var body: some View {
        HStack(spacing: OrisSpacing.s12) {
            Vignette(initiales: correspondant.initiales, taille: 38, teinte: correspondant.teinte(specialites))
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 5) {
                    Text(correspondant.nomCourt)
                        .font(Police.interface(15.5, .bold))
                        .foregroundStyle(Teinte.encre)
                        .lineLimit(1)
                    if correspondant.favorite {
                        Image(systemName: "star.fill").font(.system(size: 10)).foregroundStyle(Teinte.attention)
                    }
                }
                let detail = [role?.libelle, correspondant.specialty, correspondant.practice, correspondant.email]
                    .compactMap { $0 }.filter { !$0.isEmpty }
                Text(detail.prefix(2).joined(separator: " · "))
                    .font(Police.interface(12.5, .medium))
                    .foregroundStyle(role == nil ? Teinte.encreTresDouce : Teinte.accent)
                    .lineLimit(1)
            }
            Spacer(minLength: 4)
        }
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
    }
}
