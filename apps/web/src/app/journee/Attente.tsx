"use client";

import { useEffect, useState } from "react";

import styles from "./journee.module.css";

/** L'attente d'une relecture, montrée honnêtement.
 *
 * On ne sait pas où en est l'extension : elle se réveille **toutes les minutes**, ouvre
 * Doctolib dans un onglet de fond, lit la liste, puis livre. Une barre qui prétendrait
 * connaître l'avancement mentirait ; celle-ci dit seulement « ça travaille », et le
 * temps écoulé, lui, est vrai. Passé deux minutes, on arrête de faire semblant.
 */

const ABANDON_S = 120;

function etape(secondes: number): string {
  if (secondes >= ABANDON_S) {
    return "Toujours rien après deux minutes.";
  }
  if (secondes < 12) return "Demande posée. L’extension Chrome se réveille toutes les minutes.";
  if (secondes < 45) return "En attente de l’extension — elle ouvre Doctolib en arrière-plan.";
  return "Doctolib met du temps à répondre. On patiente.";
}

function chrono(secondes: number): string {
  return `${Math.floor(secondes / 60)}:${String(secondes % 60).padStart(2, "0")}`;
}

export function Attente({ depuis, onAnnuler }: { depuis: string; onAnnuler: () => void }) {
  const debut = new Date(depuis).getTime();
  const [secondes, setSecondes] = useState(() => Math.max(0, Math.round((Date.now() - debut) / 1000)));

  useEffect(() => {
    const battement = setInterval(
      () => setSecondes(Math.max(0, Math.round((Date.now() - debut) / 1000))),
      1000,
    );
    return () => clearInterval(battement);
  }, [debut]);

  const perdue = secondes >= ABANDON_S;

  return (
    <div className={`${styles.attente} ${perdue ? styles.attentePerdue : ""}`} role="status">
      <div className={styles.attenteHaut}>
        <span className={styles.attenteTexte}>{etape(secondes)}</span>
        <span className={styles.chrono}>{chrono(secondes)}</span>
        <button type="button" className={styles.annuler} onClick={onAnnuler}>
          Annuler
        </button>
      </div>

      <div className={styles.barre} aria-hidden="true">
        <span className={perdue ? styles.barreArretee : styles.barreGlisse} />
      </div>

      {perdue && (
        <span className={styles.attenteAide}>
          Chrome est-il ouvert, avec l’extension Dental Lens active ? Et Oris est-il
          déclaré comme destinataire dans ses réglages ?
        </span>
      )}
    </div>
  );
}
