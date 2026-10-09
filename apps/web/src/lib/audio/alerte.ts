/**
 * Prévenir le praticien, tout de suite, que l'écoute s'est arrêtée.
 *
 * Une consultation coupée sans que personne ne le voie, c'est une consultation perdue.
 * Le signal est volontairement inhabituel — trois notes qui descendent, répétées — et il
 * insiste jusqu'à ce que l'écoute reprenne : rien ne ressemble à ça dans un navigateur,
 * et c'est le but. Jumeau du son de l'app iPhone (`Oris/Resources/ecoute-coupee.wav`).
 */

/** Les trois notes, en hertz, et leur durée en secondes. */
const MOTIF: ReadonlyArray<readonly [number, number]> = [
  [988, 0.16],
  [740, 0.16],
  [554, 0.3],
];
const REPETITIONS = 2;
const SILENCE_ENTRE_NOTES = 0.04;
const SILENCE_ENTRE_MOTIFS = 0.18;
/** Le motif dure moins de deux secondes : on le rejoue, sinon il passe inaperçu. */
export const INTERVALLE_MS = 5_000;
/** Au-delà, le praticien n'est pas devant son écran : insister ne sert plus à rien. */
export const RAPPELS_MAX = 12;

export interface AlerteCapture {
  /** Demande l'autorisation de prévenir, au début : trop tard au moment de la coupure. */
  preparer(): void;
  couper(motif: "micro_perdu"): void;
  taire(): void;
}

/** Alerte qui ne fait rien : tests et rendu serveur. */
export class AlerteMuette implements AlerteCapture {
  readonly coupures: string[] = [];
  tues = 0;
  preparee = false;

  preparer(): void {
    this.preparee = true;
  }
  couper(motif: "micro_perdu"): void {
    this.coupures.push(motif);
  }
  taire(): void {
    this.tues += 1;
  }
}

const TITRE = "Oris a perdu le micro";
const MESSAGE =
  "Plus rien n’est enregistré. Revenez sur Oris et cliquez Reprendre.";

export class AlerteNavigateur implements AlerteCapture {
  private rappel: ReturnType<typeof setInterval> | null = null;
  private restants = 0;
  private contexte: AudioContext | null = null;
  private titreInitial: string | null = null;

  preparer(): void {
    // L'autorisation ne se demande qu'une fois, et seulement si elle n'a pas été refusée.
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      void Notification.requestPermission().catch(() => undefined);
    }
  }

  couper(_motif: "micro_perdu"): void {
    if (this.rappel !== null) return; // déjà en train d'alerter
    this.restants = RAPPELS_MAX;
    this.avertir();
    this.clignoter();
    this.sonner();
    this.rappel = setInterval(() => {
      this.restants -= 1;
      if (this.restants <= 0) {
        this.arreterLeRappel();
        return;
      }
      this.sonner();
    }, INTERVALLE_MS);
  }

  taire(): void {
    this.arreterLeRappel();
    if (this.titreInitial !== null && typeof document !== "undefined") {
      document.title = this.titreInitial;
      this.titreInitial = null;
    }
  }

  private arreterLeRappel(): void {
    if (this.rappel !== null) {
      clearInterval(this.rappel);
      this.rappel = null;
    }
    this.restants = 0;
  }

  /** L'onglet le dit même quand il n'est pas celui qu'on regarde. */
  private clignoter(): void {
    if (typeof document === "undefined") return;
    this.titreInitial ??= document.title;
    document.title = `⚠ ${TITRE}`;
  }

  private avertir(): void {
    if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
    try {
      new Notification(TITRE, { body: MESSAGE, tag: "oris-ecoute-coupee" });
    } catch {
      // Un navigateur qui refuse l'avis ne doit pas faire tomber l'écoute.
    }
  }

  private sonner(): void {
    const Contexte =
      typeof window === "undefined"
        ? undefined
        : window.AudioContext ?? (window as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Contexte) return;
    try {
      this.contexte ??= new Contexte();
      const contexte = this.contexte;
      void contexte.resume().catch(() => undefined);
      let depart = contexte.currentTime + 0.02;
      for (let repetition = 0; repetition < REPETITIONS; repetition += 1) {
        for (const [frequence, duree] of MOTIF) {
          this.note(contexte, frequence, depart, duree);
          depart += duree + SILENCE_ENTRE_NOTES;
        }
        depart += SILENCE_ENTRE_MOTIFS;
      }
    } catch {
      // Pas de son possible (onglet sans geste utilisateur) : le titre et l'avis restent.
    }
  }

  /** Fondamentale + quinte : un timbre franc, qui perce une pièce bruyante. */
  private note(contexte: AudioContext, frequence: number, depart: number, duree: number): void {
    for (const [rapport, volume] of [
      [1, 0.28],
      [1.5, 0.12],
    ] as const) {
      const oscillateur = contexte.createOscillator();
      const gain = contexte.createGain();
      oscillateur.frequency.value = frequence * rapport;
      gain.gain.setValueAtTime(0.0001, depart);
      gain.gain.exponentialRampToValueAtTime(volume, depart + 0.006);
      gain.gain.exponentialRampToValueAtTime(0.0001, depart + duree);
      oscillateur.connect(gain).connect(contexte.destination);
      oscillateur.start(depart);
      oscillateur.stop(depart + duree + 0.02);
    }
  }
}
