import SwiftUI

/// Le carnet de correspondants, comme la page Correspondants du site.
struct CarnetView: View {
    let client: APIClient

    @State private var carnet: [Correspondant] = []
    @State private var recherche = ""
    @State private var chargement = true
    @State private var erreur: String?
    @State private var creation = false
    @State private var toast: String?

    private var filtres: [Correspondant] {
        let cherche = recherche.sansAccents
        return carnet
            .filter { cherche.isEmpty || "\($0.nomCourt) \($0.specialty) \($0.practice) \($0.email)".sansAccents.contains(cherche) }
            .sorted { ($0.favorite ? 0 : 1, $0.lastName.sansAccents) < ($1.favorite ? 0 : 1, $1.lastName.sansAccents) }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: OrisSpacing.s16) {
                    HStack(alignment: .bottom) {
                        EnTetePage(surtitre: "Carnet", titre: "Correspondants")
                        Button("Nouveau") { creation = true }
                            .buttonStyle(BoutonSecondaire(compact: true))
                    }
                    ChampRecherche(texte: $recherche)
                    if let erreur {
                        Label(erreur, systemImage: "exclamationmark.triangle")
                            .font(Police.note).foregroundStyle(Teinte.alerte)
                            .carte(rembourrage: OrisSpacing.s12, fond: Teinte.alerteDouce)
                    }
                    if chargement {
                        ProgressView().tint(Teinte.accent).frame(maxWidth: .infinity).padding(.top, OrisSpacing.s24)
                    } else if filtres.isEmpty {
                        MessageVide(icone: "person.crop.rectangle.stack", titre: "Aucun correspondant",
                                    texte: recherche.isEmpty ? "Ajoutez vos confrères avec « Nouveau »." : "Aucun nom ne correspond.")
                    } else {
                        VStack(spacing: 0) {
                            ForEach(filtres) { c in
                                NavigationLink(value: c) {
                                    HStack {
                                        LigneCorrespondant(correspondant: c)
                                        Image(systemName: "chevron.right")
                                            .font(.system(size: 12, weight: .bold))
                                            .foregroundStyle(Teinte.traitFort)
                                    }
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 10)
                                }
                                .buttonStyle(.plain)
                                if c.id != filtres.last?.id {
                                    Divider().overlay(Teinte.trait).padding(.leading, 64)
                                }
                            }
                        }
                        .carte(rembourrage: 0)
                    }
                }
                .padding(.horizontal, OrisSpacing.s16)
                .padding(.bottom, OrisSpacing.s32)
            }
            .pageOris()
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(for: Correspondant.self) { c in
                FicheCorrespondantView(client: client, fiche: c) { resultat in
                    toast = resultat == nil ? "Correspondant supprimé." : "Fiche enregistrée."
                    Task { await charger() }
                }
            }
            .sheet(isPresented: $creation) {
                NavigationStack {
                    FicheCorrespondantView(client: client, fiche: .nouveau()) { _ in
                        toast = "Correspondant ajouté au carnet."
                        Task { await charger() }
                    }
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) { Button("Annuler") { creation = false } }
                    }
                }
            }
            .toast($toast)
            .refreshable { await charger() }
            .task { await charger() }
        }
    }

    private func charger() async {
        defer { chargement = false }
        do {
            carnet = try await client.correspondants()
            erreur = nil
        } catch {
            erreur = "Carnet indisponible. " + Connexion.pourquoi(error, adresse: client.baseURL)
        }
    }
}

extension String {
    /// Pour chercher « Stéphanie » en tapant « stephanie ».
    var sansAccents: String {
        folding(options: [.diacriticInsensitive, .caseInsensitive], locale: Locale(identifier: "fr_FR"))
            .trimmingCharacters(in: .whitespaces)
    }
}
