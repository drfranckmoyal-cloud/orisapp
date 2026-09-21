import SwiftUI

/// S02 — choix du patient, puis écoute (au plus un écran avant l'écoute, S03).
struct NewConsultationView: View {
    let client: APIClient
    let onClose: () -> Void

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
            List {
                if let errorText {
                    Text(errorText).foregroundStyle(OrisColor.danger)
                }
                Section {
                    Button {
                        showCreate = true
                    } label: {
                        Label("Nouveau patient", systemImage: "person.badge.plus")
                    }
                }
                Section("Patients") {
                    if loading {
                        ProgressView()
                    }
                    ForEach(filtered) { patient in
                        Button(patient.displayName) {
                            Task { await prepare(patientId: patient.id) }
                        }
                        .foregroundStyle(OrisColor.deepGreen)
                    }
                }
            }
            .searchable(text: $search, prompt: "Rechercher un patient")
            .navigationTitle("Nouvelle consultation")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Fermer", action: onClose)
                }
            }
            .navigationDestination(item: $encounter) { encounter in
                ListeningView(client: client, encounter: encounter, onClose: onClose)
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
        } catch {
            errorText = "Serveur Oris injoignable."
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

extension EncounterSummary: Hashable {
    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
}
