import SwiftUI

// SmileCloud dans le dossier patient, comme sur le site : relier le dossier, voir les
// galeries, cocher, rapatrier. L'extension Chrome du Mac fait le travail dans SmileCloud.

struct EtatSmileCloud: Codable, Equatable, Sendable {
    struct Candidat: Codable, Equatable, Sendable, Identifiable {
        let caseId: String
        let nom: String
        let pourCent: Int
        var id: String { caseId }
        enum CodingKeys: String, CodingKey {
            case nom
            case caseId = "case_id"
            case pourCent = "pour_cent"
        }
    }

    struct Fichier: Codable, Equatable, Sendable, Identifiable {
        let resId: String
        let nom: String
        let nature: String
        let rapatriable: Bool
        var pourquoi: String? = nil
        var id: String { resId }
        enum CodingKeys: String, CodingKey {
            case nom, nature, rapatriable, pourquoi
            case resId = "res_id"
        }
    }

    struct Galerie: Codable, Equatable, Sendable, Identifiable {
        let id: String
        let nom: String
        let date: String
        let fichiers: [Fichier]
    }

    struct Ecart: Codable, Equatable, Sendable {
        let resId: String
        let raison: String
        enum CodingKeys: String, CodingKey {
            case raison
            case resId = "res_id"
        }
    }

    struct Recuperation: Codable, Equatable, Sendable {
        let total: Int
        let recus: Int
        let ecartes: [Ecart]
        let termine: Bool
    }

    let caseId: String?
    let nom: String?
    let etat: String
    let candidats: [Candidat]
    let galeries: [Galerie]?
    let galeriesLuesLe: String?
    let lectureEnCours: Bool
    let recuperation: Recuperation?

    enum CodingKeys: String, CodingKey {
        case nom, etat, candidats, galeries, recuperation
        case caseId = "case_id"
        case galeriesLuesLe = "galeries_lues_le"
        case lectureEnCours = "lecture_en_cours"
    }
}

extension APIClient {
    func smileCloud(patientId: String) async throws -> EtatSmileCloud {
        try await get("patients/\(patientId)/smilecloud")
    }

    func relierSmileCloud(patientId: String, caseId: String?) async throws -> EtatSmileCloud {
        try await send("patients/\(patientId)/smilecloud", method: "PUT", body: ["case_id": caseId ?? NSNull()])
    }

    func lireGaleries(patientId: String) async throws -> EtatSmileCloud {
        try await send("patients/\(patientId)/smilecloud/galeries", method: "POST", body: [:])
    }

    func rapatrier(patientId: String, fichiers: [String]) async throws -> EtatSmileCloud {
        try await send("patients/\(patientId)/smilecloud/recuperer", method: "POST", body: ["fichiers": fichiers])
    }
}

struct CarteSmileCloud: View {
    let client: APIClient
    let patientId: String
    /// Appelé quand des fichiers arrivent : les photos du dossier se rechargent.
    var arrives: () -> Void = {}

    @State private var etat: EtatSmileCloud?
    @State private var coches: Set<String> = []
    @State private var erreur: String?

    private static let natures = ["photo": "photo", "radio": "radio", "scan3d": "scan 3D", "pdf": "PDF",
                                  "video": "vidéo", "cbct": "CBCT", "autre": "autre"]
    private static let raisons = ["video": "vidéo, non reprise", "cbct": "CBCT, non repris",
                                  "inconnu": "fichier introuvable",
                                  "UNSUPPORTED_ATTACHMENT_FORMAT": "format non reconnu",
                                  "ATTACHMENT_TOO_LARGE": "trop lourd"]

    private var enAttente: Bool {
        guard let etat else { return false }
        return etat.lectureEnCours || (etat.recuperation.map { !$0.termine } ?? false)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
            HStack(spacing: 10) {
                Text("SC")
                    .font(Police.interface(12, .heavy))
                    .foregroundStyle(.white)
                    .frame(width: 34, height: 34)
                    .background(LinearGradient(colors: [Color(hex: 0x2F6FB0), Color(hex: 0x1F5A8C)],
                                               startPoint: .topLeading, endPoint: .bottomTrailing),
                                in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                VStack(alignment: .leading, spacing: 1) {
                    Text("Récupération SmileCloud").font(Police.titreCarte).foregroundStyle(Teinte.encre)
                    Text(etat?.etat == "relie" ? "Dossier relié : \(etat?.nom ?? "SmileCloud")"
                         : "Photos, radios, scans et PDF du dossier SmileCloud.")
                        .font(Police.interface(12.5, .medium)).foregroundStyle(Teinte.encreTresDouce)
                        .lineLimit(2)
                }
            }
            contenu
            if let erreur {
                Text(erreur).font(Police.note).foregroundStyle(Teinte.alerte)
            }
        }
        .carte()
        .task(id: patientId) { await charger() }
        .task(id: enAttente) {
            // Tant que l'extension travaille, on regarde toutes les 4 s.
            while enAttente && !Task.isCancelled {
                try? await Task.sleep(for: .seconds(4))
                await charger()
            }
        }
        .onChange(of: etat?.recuperation?.recus) { _, recus in
            if (recus ?? 0) > 0 { arrives() }
        }
    }

    @ViewBuilder
    private var contenu: some View {
        if let etat {
            switch etat.etat {
            case "sans_liste":
                Text("La liste des dossiers SmileCloud n’est pas encore arrivée : l’extension Chrome du Mac la livrera.")
                    .font(Police.note).foregroundStyle(Teinte.encreDouce)
            case "absent":
                Text("Aucun dossier SmileCloud ne ressemble à ce nom.")
                    .font(Police.note).foregroundStyle(Teinte.encreDouce)
            case "relie":
                relie(etat)
            default:
                candidats(etat)
            }
        } else {
            ProgressView().tint(Teinte.accent)
        }
    }

    private func candidats(_ etat: EtatSmileCloud) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(etat.etat == "trouve" ? "Un dossier porte exactement ce nom : confirmez que c’est bien ce patient."
                 : etat.etat == "ambigu" ? "Plusieurs dossiers portent ce nom : choisissez le bon."
                 : "Des dossiers ressemblent à ce nom, sans certitude : à vous de trancher.")
                .font(Police.note).foregroundStyle(Teinte.encreDouce)
            ForEach(etat.candidats) { c in
                HStack {
                    Text(c.nom).font(Police.interface(15, .bold)).foregroundStyle(Teinte.encre)
                    Pastille(texte: "\(c.pourCent) %", ton: c.pourCent >= 100 ? .valide : .attention)
                    Spacer()
                    Button("C’est lui") { Task { await agir { try await client.relierSmileCloud(patientId: patientId, caseId: c.caseId) } } }
                        .buttonStyle(BoutonSecondaire(compact: true))
                }
            }
        }
    }

    @ViewBuilder
    private func relie(_ etat: EtatSmileCloud) -> some View {
        Button {
            Task { await agir { try await client.lireGaleries(patientId: patientId) } }
        } label: {
            Label(etat.lectureEnCours ? "Lecture demandée…" : etat.galeries == nil ? "Voir les galeries" : "Relire les galeries",
                  systemImage: "photo.stack")
        }
        .buttonStyle(BoutonSecondaire())
        .disabled(etat.lectureEnCours)
        if etat.lectureEnCours {
            Label("L’extension va lire les galeries dans SmileCloud, sur le Mac (Chrome ouvert). Elles s’afficheront ici.",
                  systemImage: "hourglass")
                .font(Police.note).foregroundStyle(Teinte.accent)
        }
        if let galeries = etat.galeries {
            if galeries.isEmpty {
                Text("Aucune galerie dans ce dossier.").font(Police.note).foregroundStyle(Teinte.encreDouce)
            }
            ForEach(galeries) { g in
                VStack(alignment: .leading, spacing: 6) {
                    let ids = g.fichiers.filter(\.rapatriable).map(\.resId)
                    Button {
                        let toutes = !ids.isEmpty && ids.allSatisfy(coches.contains)
                        if toutes { coches.subtract(ids) } else { coches.formUnion(ids) }
                    } label: {
                        HStack {
                            Image(systemName: !ids.isEmpty && ids.allSatisfy(coches.contains) ? "checkmark.square.fill" : "square")
                                .foregroundStyle(Teinte.accent)
                            Text(g.nom.isEmpty ? "Galerie" : g.nom).font(Police.interface(15, .bold)).foregroundStyle(Teinte.encre)
                            Spacer()
                            Text("\(g.date) · \(g.fichiers.count)").font(Police.interface(12, .medium)).foregroundStyle(Teinte.encreTresDouce)
                        }
                    }
                    .buttonStyle(.plain)
                    ForEach(g.fichiers) { f in
                        Button {
                            if coches.contains(f.resId) { coches.remove(f.resId) } else { coches.insert(f.resId) }
                        } label: {
                            HStack(spacing: 8) {
                                Image(systemName: coches.contains(f.resId) ? "checkmark.circle.fill" : "circle")
                                    .foregroundStyle(f.rapatriable ? Teinte.accent : Teinte.traitFort)
                                Text(f.nom.isEmpty ? String(f.resId.prefix(8)) : f.nom)
                                    .font(Police.interface(13.5, .medium))
                                    .foregroundStyle(f.rapatriable ? Teinte.encre : Teinte.encreTresDouce)
                                    .lineLimit(1)
                                Spacer()
                                Text(f.rapatriable ? (Self.natures[f.nature] ?? f.nature)
                                     : "\(Self.natures[f.nature] ?? f.nature) · \(f.pourquoi ?? "non repris")")
                                    .font(Police.interface(11.5, .bold)).foregroundStyle(Teinte.document(.treatmentPlanText).encre)
                            }
                            .padding(.leading, 22)
                        }
                        .buttonStyle(.plain)
                        .disabled(!f.rapatriable)
                    }
                }
                .padding(10)
                .background(Teinte.surface2, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
            }
            if !coches.isEmpty {
                Button {
                    let choix = Array(coches)
                    Task {
                        await agir { try await client.rapatrier(patientId: patientId, fichiers: choix) }
                        coches = []
                    }
                } label: {
                    Label("Rapatrier \(coches.count) fichier\(coches.count > 1 ? "s" : "")", systemImage: "square.and.arrow.down")
                }
                .buttonStyle(BoutonPrincipal())
            }
        }
        if let r = etat.recuperation {
            VStack(alignment: .leading, spacing: 4) {
                Text("\(r.termine ? "Récupération terminée" : "Récupération en cours") : \(r.recus) / \(r.total) reçu\(r.recus > 1 ? "s" : "")")
                    .font(Police.interface(14, .bold)).foregroundStyle(Teinte.accent)
                ForEach(Array(r.ecartes.enumerated()), id: \.offset) { _, e in
                    Text("1 fichier non repris : \(Self.raisons[e.raison] ?? e.raison)")
                        .font(Police.interface(12.5, .medium)).foregroundStyle(Teinte.attention)
                }
            }
            .padding(10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Teinte.accentDouce, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
    }

    private func charger() async {
        if let nouvel = try? await client.smileCloud(patientId: patientId) { etat = nouvel }
    }

    private func agir(_ faire: () async throws -> EtatSmileCloud) async {
        erreur = nil
        do {
            etat = try await faire()
        } catch {
            erreur = Labels.erreur(error)
        }
    }
}
