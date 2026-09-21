import SwiftUI

/// S02 — choix du patient, puis écoute (au plus un écran avant l'écoute, S03).
struct NewConsultationView: View {
    let client: APIClient
    let onClose: () -> Void
    /// Onglet « Patients » : même liste, sans bouton Fermer ; finir une consultation
    /// ramène à la liste au lieu de fermer l'écran.
    var embedded = false

    @State private var patients: [PatientSummary] = []
    @State private var search = ""
    @State private var loading = true
    @State private var errorText: String?
    @State private var encounter: EncounterSummary?
    @State private var showCreate = false
    @State private var firstName = ""
    @State private var lastName = ""

    private var filtered: [PatientSummary] {
        search.isEmpty ? patients : patients.filter {
            $0.displayName.localizedCaseInsensitiveContains(search)
        }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: OrisSpacing.s16) {
                    HStack(alignment: .bottom) {
                        EnTetePage(
                            surtitre: embedded ? "Données fictives uniquement" : "Nouvelle consultation",
                            titre: embedded ? "Patients" : "Quel patient ?"
                        )
                        Button("Nouveau patient") { showCreate = true }
                            .buttonStyle(BoutonSecondaire(compact: true))
                    }

                    ChampRecherche(texte: $search)

                    if let errorText {
                        Label(errorText, systemImage: "exclamationmark.triangle")
                            .font(Police.note)
                            .foregroundStyle(Teinte.alerte)
                            .carte(fond: Teinte.alerteDouce)
                    }

                    VStack(alignment: .leading, spacing: OrisSpacing.s12) {
                        Text(loading ? "Chargement…" : "\(filtered.count) patient\(filtered.count > 1 ? "s" : "")")
                            .font(Police.titreCarte)
                            .foregroundStyle(Teinte.encre)
                        if loading {
                            ProgressView().tint(Teinte.accent)
                        }
                        ForEach(filtered) { patient in
                            if embedded {
                                // Onglet Patients : on ouvre le dossier.
                                NavigationLink(value: RoutePatients.patient(patient)) {
                                    LignePatient(patient: patient)
                                }
                                .buttonStyle(.plain)
                            } else {
                                // Depuis « Commencer une consultation » : on part écouter.
                                Button {
                                    Task { await prepare(patientId: patient.id) }
                                } label: {
                                    LignePatient(patient: patient)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                    .carte(rembourrage: 12, fond: Teinte.surface2)
                }
                .padding(.horizontal, OrisSpacing.s16)
                .padding(.bottom, OrisSpacing.s32)
            }
            .pageOris()
            .refreshable { await load() }
            .toolbar {
                if !embedded {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Fermer", action: onClose)
                    }
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: RoutePatients.self) { route in
                switch route {
                case .patient(let patient):
                    PatientDossierView(client: client, patient: patient)
                case .consultation(let id):
                    ConsultationDetailView(model: ConsultationDetailViewModel(encounterId: id, client: client))
                }
            }
            .navigationDestination(item: $encounter) { encounter in
                ListeningView(client: client, encounter: encounter) {
                    if embedded { self.encounter = nil } else { onClose() }
                }
            }
            .alert("Nouveau patient", isPresented: $showCreate) {
                TextField("Prénom", text: $firstName)
                TextField("Nom", text: $lastName)
                Button("Annuler", role: .cancel) {}
                Button("Créer") { Task { await createPatient() } }
            } message: {
                Text("Patients fictifs uniquement pendant le développement.")
            }
            .task { await load() }
        }
    }

    private func load() async {
        loading = true
        defer { loading = false }
        do {
            patients = try await client.patients()
            errorText = nil
        } catch {
            errorText = "Serveur Oris injoignable. " + Connexion.pourquoi(error, adresse: client.baseURL)
        }
    }

    private func createPatient() async {
        let first = firstName.trimmingCharacters(in: .whitespaces)
        let last = lastName.trimmingCharacters(in: .whitespaces)
        guard !first.isEmpty, !last.isEmpty else { return }
        do {
            let patient = try await client.createPatient(firstName: first, lastName: last)
            firstName = ""
            lastName = ""
            await prepare(patientId: patient.id)
        } catch {
            errorText = "Création du patient impossible."
        }
    }

    private func prepare(patientId: String) async {
        do {
            encounter = try await client.createEncounter(patientId: patientId)
        } catch {
            errorText = "Création de la consultation impossible."
        }
    }
}

/// Une ligne de la liste des patients, comme sur le site : initiales, NOM Prénom,
/// nombre de comptes rendus, et ce qui attend une relecture.
struct LignePatient: View {
    let patient: PatientSummary

    private var resume: String {
        guard let n = patient.consultations else { return "" }
        if n == 0 { return "aucune consultation" }
        return "\(n) compte\(n > 1 ? "s" : "") rendu\(n > 1 ? "s" : "")"
    }

    var body: some View {
        HStack(spacing: OrisSpacing.s12) {
            Vignette(initiales: patient.initiales)
            VStack(alignment: .leading, spacing: 3) {
                NomPatient(patient: patient)
                Text([resume, DateOris.lire(patient.derniereConsultation).map(DateOris.court)]
                    .compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " · "))
                .lineLimit(1)
                .minimumScaleFactor(0.85)
                .font(Police.interface(12.5, .medium, relativeTo: .caption))
                .foregroundStyle(Teinte.encreTresDouce)
            }
            Spacer(minLength: OrisSpacing.s8)
            if let n = patient.aRelire, n > 0 {
                Pastille(texte: "\(n) à relire", ton: .attention)
            }
            Image(systemName: "chevron.right")
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(Teinte.traitFort)
        }
        .padding(12)
        .background(Teinte.surface, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).strokeBorder(Teinte.trait, lineWidth: 1))
        .shadow(color: Teinte.encre.opacity(0.05), radius: 3, y: 2)
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
    }
}

/// Le champ « Rechercher un nom… » du site.
struct ChampRecherche: View {
    @Binding var texte: String

    var body: some View {
        HStack(spacing: OrisSpacing.s8) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(Teinte.encreTresDouce)
            TextField("Rechercher un nom…", text: $texte)
                .font(Police.texte)
                .foregroundStyle(Teinte.encre)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
            if !texte.isEmpty {
                Button { texte = "" } label: {
                    Image(systemName: "xmark.circle.fill").foregroundStyle(Teinte.traitFort)
                }
                .accessibilityLabel("Effacer la recherche")
            }
        }
        .padding(.horizontal, 14)
        .frame(minHeight: 46)
        .background(Teinte.surface, in: RoundedRectangle(cornerRadius: OrisRadius.button, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: OrisRadius.button, style: .continuous).strokeBorder(Teinte.trait, lineWidth: 1))
    }
}

extension EncounterSummary: Hashable {
    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
}
