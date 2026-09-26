import SwiftUI

/// « D'où vient cette phrase ? » (spec §30) — ce que le site montre dans son rail de
/// révision, l'iPhone le montre dans une feuille : les faits d'appui, puis les paroles
/// réellement prononcées, avec qui parlait et à quel moment.
///
/// Rien n'est reconstitué ici : la jointure phrase → faits → paroles vient du serveur
/// (`GET /documents/{id}/preuve`), la même pour les deux clients.
struct PreuveView: View {
    let phrase: PreuvePhrase
    let transcriptionDisponible: Bool
    @Environment(\.dismiss) private var fermer

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: OrisSpacing.s16) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(phrase.section.uppercased())
                            .font(Police.interface(11, .heavy))
                            .tracking(0.8)
                            .foregroundStyle(Teinte.encreTresDouce)
                        // Le document met ses mots-clés en gras (**…**) : la citation aussi.
                        Text(texteRiche("« \(phrase.text) »"))
                            .font(Police.interface(16, .semibold))
                            .foregroundStyle(Teinte.encre)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .carte(rembourrage: OrisSpacing.s16, fond: Teinte.accentDouce)

                    ForEach(phrase.alertes) { alerte in
                        Label(alerte.message, systemImage: "exclamationmark.triangle")
                            .font(Police.note)
                            .foregroundStyle(Teinte.attention)
                    }

                    if !phrase.faits.isEmpty {
                        VStack(alignment: .leading, spacing: OrisSpacing.s12) {
                            Titre("Ce qu’Oris a retenu")
                            ForEach(phrase.faits) { fait in
                                FaitLigne(fait: fait)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .carte()
                    }

                    VStack(alignment: .leading, spacing: OrisSpacing.s12) {
                        Titre("Ce qui a été dit")
                        if phrase.passages.isEmpty {
                            Text(explication)
                                .font(Police.note)
                                .foregroundStyle(Teinte.encreDouce)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        ForEach(phrase.passages) { passage in
                            PassageLigne(passage: passage)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .carte()
                }
                .padding(OrisSpacing.s16)
            }
            .pageOris()
            .navigationTitle("D’où vient cette phrase ?")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Fermer") { fermer() }
                }
            }
        }
    }

    /// Une phrase sans parole source n'est pas une anomalie à masquer : elle s'explique.
    private var explication: String {
        if phrase.saisiALaMain {
            return "Fait saisi par le praticien : il n’y a pas de parole source à montrer."
        }
        if !transcriptionDisponible {
            return "La transcription de cette consultation n’est plus disponible."
        }
        if phrase.faits.isEmpty {
            return "Cette phrase vient d’une alerte d’Oris, pas d’un fait clinique."
        }
        return "Aucune parole rattachée : vérifiez cette phrase avant de valider."
    }
}

private struct Titre: View {
    let texte: String
    init(_ texte: String) { self.texte = texte }

    var body: some View {
        Text(texte)
            .font(Police.interface(13, .heavy))
            .tracking(0.4)
            .foregroundStyle(Teinte.encreTresDouce)
    }
}

private struct FaitLigne: View {
    let fait: PreuveFait

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(intitule)
                .font(Police.interface(14.5, .bold))
                .foregroundStyle(Teinte.encre)
                .fixedSize(horizontal: false, vertical: true)
            Flux(espace: 6) {
                if !fait.teeth.isEmpty {
                    Etiquette(texte: "dent \(fait.teeth.joined(separator: ", "))")
                }
                Etiquette(texte: Labels.assertion(fait.assertion), alerte: fait.assertion != .present)
                Etiquette(texte: Labels.clinicalStatus(fait.clinicalStatus))
                Etiquette(texte: Labels.certainty(fait.certainty), alerte: fait.certainty != .certain)
                if fait.manuallyValidated {
                    Etiquette(texte: "vérifié par vous")
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
    }

    private var intitule: String {
        fait.valeur.isEmpty ? fait.libelle : "\(fait.libelle) : \(fait.valeur)"
    }
}

private struct Etiquette: View {
    let texte: String
    var alerte: Bool = false

    var body: some View {
        Text(texte)
            .font(Police.interface(12, .semibold))
            .foregroundStyle(alerte ? Teinte.attention : Teinte.encreDouce)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(alerte ? Teinte.attentionDouce : Teinte.surfaceDouce, in: Capsule())
    }
}

private struct PassageLigne: View {
    let passage: PreuvePassage

    var body: some View {
        HStack(alignment: .top, spacing: OrisSpacing.s12) {
            Rectangle()
                .fill(Teinte.accent.opacity(0.35))
                .frame(width: 3)
                .clipShape(Capsule())
            VStack(alignment: .leading, spacing: 3) {
                Text("\(Labels.locuteur(passage.speakerRole)) — \(PreuvePassage.horloge(passage.startMs))")
                    .font(Police.interface(12, .semibold))
                    .foregroundStyle(Teinte.encreTresDouce)
                Text("« \(passage.text) »")
                    .font(Police.interface(15, .regular))
                    .foregroundStyle(Teinte.encre)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
    }
}
