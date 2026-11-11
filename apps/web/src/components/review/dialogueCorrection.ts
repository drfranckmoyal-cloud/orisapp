import type { LectureAssistant, PropositionRelecture } from "@/lib/api";
import type { components } from "@/contracts/api";

/** Le dialogue « Corriger avec Claude » d'une consultation.
 *
 * La conversation vit **sur le serveur** (Franck, 11/11/2026 : « garder l'historique, ne pas
 * en remettre une vierge » — y compris l'app fermée, et d'un appareil à l'autre). Ici ne
 * vit que ce qui part à l'instant : la demande en route, la correction qu'on vient de
 * confirmer, les cases cochées. Le tout tient en mémoire, par consultation, pour survivre
 * à un aller-retour vers une autre page pendant que Claude travaille.
 */

export type DemandeServeur = components["schemas"]["DemandeCorrectionOut"];

export type Echange =
  | { id: string; qui: "moi"; texte: string }
  | { id: string; qui: "oris"; sorte: "attente"; texte: string }
  | { id: string; qui: "oris"; sorte: "application"; depuis: number }
  | { id: string; qui: "oris"; sorte: "erreur"; texte: string }
  | { id: string; qui: "oris"; sorte: "fait"; texte: string }
  | { id: string; qui: "oris"; sorte: "annule"; texte: string }
  | { id: string; qui: "oris"; sorte: "lecture"; lecture: LectureAssistant }
  | { id: string; qui: "oris"; sorte: "relecture"; propositions: PropositionRelecture[] };

export type EtatDialogue = {
  /** Les demandes qui partent, avant que le serveur ne les ait enregistrées. */
  enVol: Echange[];
  /** Ce qu'on vient de faire sur une demande du serveur, en attendant sa relecture. */
  surcharges: Record<string, Echange>;
  /** Relecture : les propositions cochées, par demande. */
  coches: Record<string, number[]>;
  compteur: number;
};

export type Marque = { texte: string; ton: "neutre" | "attention" | "valide" | "alerte" };

const VIDE: EtatDialogue = { enVol: [], surcharges: {}, coches: {}, compteur: 0 };
const memoire = new Map<string, EtatDialogue>();
const abonnes = new Map<string, Set<() => void>>();

export function lireDialogue(encounterId: string): EtatDialogue {
  return memoire.get(encounterId) ?? VIDE;
}

export function modifierDialogue(
  encounterId: string,
  changement: (etat: EtatDialogue) => EtatDialogue,
): void {
  memoire.set(encounterId, changement(lireDialogue(encounterId)));
  abonnes.get(encounterId)?.forEach((prevenir) => prevenir());
}

export function abonnerDialogue(encounterId: string, prevenir: () => void): () => void {
  const liste = abonnes.get(encounterId) ?? new Set<() => void>();
  liste.add(prevenir);
  abonnes.set(encounterId, liste);
  return () => liste.delete(prevenir);
}

/** L'accord est donné : la demande passe « en cours », horodatée pour la barre. */
export function lancerApplication(encounterId: string, id: string): void {
  modifierDialogue(encounterId, (etat) => ({
    ...etat,
    surcharges: {
      ...etat.surcharges,
      [id]: { id, qui: "oris", sorte: "application", depuis: Date.now() },
    },
  }));
}

/** La réponse d'Oris à une demande gardée par le serveur. */
export function reponseDe(
  demande: DemandeServeur,
  message: (code: string) => string,
): Echange {
  const id = demande.id;
  switch (demande.etat) {
    case "proposee":
    case "incomprise":
      return demande.lecture
        ? { id, qui: "oris", sorte: "lecture", lecture: demande.lecture }
        : { id, qui: "oris", sorte: "erreur", texte: demande.message };
    case "relecture":
      return { id, qui: "oris", sorte: "relecture", propositions: demande.propositions };
    case "application":
      return { id, qui: "oris", sorte: "application", depuis: Date.parse(demande.depuis) };
    case "traitee":
      return { id, qui: "oris", sorte: "fait", texte: demande.message || "Fait." };
    case "annulee":
      return { id, qui: "oris", sorte: "annule", texte: "Annulé : rien n’a changé." };
    case "echec":
      return {
        id,
        qui: "oris",
        sorte: "erreur",
        texte: demande.code ? message(demande.code) : demande.message,
      };
    default:
      return { id, qui: "oris", sorte: "attente", texte: "Je lis votre demande…" };
  }
}

/** La conversation à l'écran : celle du serveur, plus ce qui part à l'instant. */
export function filDe(
  historique: DemandeServeur[],
  etat: EtatDialogue,
  message: (code: string) => string,
): Echange[] {
  const fil: Echange[] = [];
  for (const demande of historique) {
    fil.push({ id: `${demande.id}:q`, qui: "moi", texte: demande.texte });
    fil.push(etat.surcharges[demande.id] ?? reponseDe(demande, message));
  }
  return [...fil, ...etat.enVol];
}

/** Le dialogue est-il en train de travailler ? (lecture, relecture, application) */
export function occupe(fil: Echange[]): boolean {
  return fil.some(
    (echange) =>
      echange.qui === "oris" && (echange.sorte === "attente" || echange.sorte === "application"),
  );
}

/** Ce qu'est devenue une demande : on le lit sous la bulle, d'un mot. */
export function marqueDe(reponse: Echange | undefined): Marque | null {
  if (!reponse || reponse.qui !== "oris") return null;
  switch (reponse.sorte) {
    case "attente":
      return { texte: "Lecture…", ton: "neutre" };
    case "application":
      return { texte: "En cours", ton: "attention" };
    case "lecture":
      return reponse.lecture.nature === "incompris"
        ? { texte: "À préciser", ton: "neutre" }
        : { texte: "À confirmer", ton: "attention" };
    case "relecture":
      return { texte: "À confirmer", ton: "attention" };
    case "fait":
      return { texte: "Traitée", ton: "valide" };
    case "annule":
      return { texte: "Annulée", ton: "neutre" };
    case "erreur":
      return { texte: "Non aboutie", ton: "alerte" };
  }
}

/** La part parcourue après `secondes` : la moitié vers 30 s, 90 % vers 100 s, jamais 100 %.
 *
 * Oris ne sait pas à l'avance combien Claude mettra : la barre avance sur le temps écoulé,
 * vite au début puis plus lentement, sans jamais prétendre être arrivée. Même règle que
 * sur l'iPhone. */
export function part(secondes: number): number {
  return Math.min(0.95, 1 - Math.exp(-Math.max(0, secondes) / 43));
}

export function duree(secondes: number): string {
  const entier = Math.floor(Math.max(0, secondes));
  return `${Math.floor(entier / 60)}:${String(entier % 60).padStart(2, "0")}`;
}
