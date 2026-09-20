import type { ClinicalFactView } from "@/lib/api";

export type Fiabilite = "fiable" | "a_verifier";

/** Graduation affichée sur un fait (§31).
 *
 * Ce n'est **pas** une probabilité médicale : c'est une lecture des signaux déjà
 * présents dans le fait. Un doute quelconque range le fait dans « à vérifier » — on
 * préfère signaler trop que masquer.
 */
export function fiabiliteDe(
  fact: ClinicalFactView,
  conceptConnu: boolean,
): { niveau: Fiabilite; raison: string } {
  if (!conceptConnu) {
    return { niveau: "a_verifier", raison: "terme non reconnu par Oris" };
  }
  if (fact.speaker_role === "unknown") {
    return { niveau: "a_verifier", raison: "on ne sait pas qui l’a dit" };
  }
  if (fact.assertion === "uncertain" || fact.certainty !== "certain") {
    return { niveau: "a_verifier", raison: "information donnée comme incertaine" };
  }
  if (typeof fact.confidence === "number" && fact.confidence < 0.7) {
    return { niveau: "a_verifier", raison: "reconnaissance peu sûre" };
  }
  return { niveau: "fiable", raison: "dit clairement, par une voix identifiée" };
}
