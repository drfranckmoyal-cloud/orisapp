import type { LectureAssistant, PropositionRelecture } from "@/lib/api";

/** Le dialogue « Corriger avec Claude » d'une consultation, gardé hors de l'écran.
 *
 * Franck, le 11/11/2026 : « si je sors et que je reviens dans Corriger avec Claude, garder
 * l'historique, ne pas en remettre une vierge ». Le fil vit ici, par consultation : quitter
 * la page ne l'efface pas, et une correction lancée continue d'arriver. Une copie est
 * gardée dans l'onglet (sessionStorage) pour survivre à un rechargement ; rien ne quitte
 * le navigateur, et tout s'efface avec l'onglet.
 */

export type Echange =
  | { id: number; qui: "moi"; texte: string }
  | { id: number; qui: "oris"; sorte: "attente"; texte: string }
  | { id: number; qui: "oris"; sorte: "application"; depuis: number }
  | { id: number; qui: "oris"; sorte: "erreur"; texte: string }
  | { id: number; qui: "oris"; sorte: "fait"; texte: string }
  | { id: number; qui: "oris"; sorte: "annule"; texte: string }
  | { id: number; qui: "oris"; sorte: "lecture"; lecture: LectureAssistant }
  | { id: number; qui: "oris"; sorte: "relecture"; propositions: PropositionRelecture[] };

export type EtatDialogue = {
  fil: Echange[];
  compteur: number;
  /** Relecture : les propositions cochées, par échange. */
  coches: Record<number, number[]>;
};

export type Marque = { texte: string; ton: "neutre" | "attention" | "valide" | "alerte" };

const VIDE: EtatDialogue = { fil: [], compteur: 0, coches: {} };
const memoire = new Map<string, EtatDialogue>();
const abonnes = new Map<string, Set<() => void>>();

function cle(encounterId: string): string {
  return `oris.dialogue.${encounterId}`;
}

/** Relu après un rechargement : ce qui tournait alors ne reviendra pas dans cette page. */
function rouvrir(etat: EtatDialogue): EtatDialogue {
  return {
    ...etat,
    fil: etat.fil.map((echange) =>
      echange.qui === "oris" && (echange.sorte === "attente" || echange.sorte === "application")
        ? {
            id: echange.id,
            qui: "oris",
            sorte: "erreur",
            texte:
              "Interrompu par le rechargement de la page. Si c’était une correction, regardez le document : elle a pu aboutir.",
          }
        : echange,
    ),
  };
}

export function lireDialogue(encounterId: string): EtatDialogue {
  const present = memoire.get(encounterId);
  if (present) return present;
  let etat = VIDE;
  try {
    const garde = window.sessionStorage.getItem(cle(encounterId));
    if (garde) etat = rouvrir(JSON.parse(garde) as EtatDialogue);
  } catch {
    // Stockage refusé ou illisible : on repart d'un fil vide, sans plus.
  }
  memoire.set(encounterId, etat);
  return etat;
}

export function modifierDialogue(
  encounterId: string,
  changement: (etat: EtatDialogue) => EtatDialogue,
): void {
  const suivant = changement(lireDialogue(encounterId));
  memoire.set(encounterId, suivant);
  try {
    window.sessionStorage.setItem(cle(encounterId), JSON.stringify(suivant));
  } catch {
    // Sans stockage, le fil tient quand même tant que l'onglet reste ouvert.
  }
  abonnes.get(encounterId)?.forEach((prevenir) => prevenir());
}

export function abonnerDialogue(encounterId: string, prevenir: () => void): () => void {
  const liste = abonnes.get(encounterId) ?? new Set<() => void>();
  liste.add(prevenir);
  abonnes.set(encounterId, liste);
  return () => liste.delete(prevenir);
}

/** L'accord est donné : la demande passe « en cours », horodatée pour la barre. */
export function lancerApplication(encounterId: string, id: number): void {
  modifierDialogue(encounterId, (etat) => ({
    ...etat,
    fil: etat.fil.map((e) =>
      e.id === id ? { id, qui: "oris", sorte: "application", depuis: Date.now() } : e,
    ),
  }));
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
