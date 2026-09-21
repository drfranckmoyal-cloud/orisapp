"use client";

import type { Jour } from "@/lib/api";
import {
  aujourdhuiISO,
  enFrancais,
  estWeekend,
  libelleSemaine,
  nomDuJour,
} from "./dates";
import styles from "./journee.module.css";

/** Ce qu'il reste à faire pour un jour : c'est ce qui lui donne sa couleur. */
function etatDuJour(jour: Jour): { mot: string; classe: string } {
  if (!jour.lu) return { mot: "pas encore lue", classe: styles.jourNonLu ?? "" };
  if (!jour.patients) return { mot: "aucun patient", classe: styles.jourVide ?? "" };
  if (jour.a_creer) {
    const s = jour.a_creer > 1 ? "s" : "";
    return { mot: `${jour.a_creer} dossier${s} à créer`, classe: styles.jourACreer ?? "" };
  }
  return { mot: "tout est prêt", classe: styles.jourPret ?? "" };
}

/** La semaine, à gauche : on la lit d'un coup d'œil, on saute d'un jour à l'autre. */
export function Semaine({
  jours,
  debut,
  choisi,
  onChoisir,
  onSemaine,
}: {
  jours: Jour[];
  debut: string;
  choisi: string;
  onChoisir: (jour: string) => void;
  onSemaine: (pas: number) => void;
}) {
  const today = aujourdhuiISO();
  const dansLaSemaine = jours.some((jour) => jour.jour === today);

  return (
    <aside className={styles.semaine}>
      <div className={styles.navigation}>
        <button type="button" title="Semaine précédente" onClick={() => onSemaine(-1)}>
          ‹
        </button>
        <span className={styles.periode}>{libelleSemaine(debut, jours.length || 7)}</span>
        <button type="button" title="Semaine suivante" onClick={() => onSemaine(1)}>
          ›
        </button>
      </div>

      {!dansLaSemaine && (
        <div className={styles.retour}>
          <button type="button" onClick={() => onChoisir(today)}>
            Revenir à aujourd’hui
          </button>
        </div>
      )}

      {jours.map((jour) => {
        const etat = etatDuJour(jour);
        const classes = [
          styles.jour,
          etat.classe,
          jour.jour === choisi ? styles.jourChoisi : "",
          jour.jour === today ? styles.jourCeJour : "",
          estWeekend(jour.jour) ? styles.jourWeekend : "",
        ];
        return (
          <button
            key={jour.jour}
            type="button"
            className={classes.filter(Boolean).join(" ")}
            aria-current={jour.jour === choisi ? "true" : undefined}
            onClick={() => onChoisir(jour.jour)}
          >
            <span className={styles.pastilleJour} aria-hidden="true" />
            <span className={styles.quand}>
              <span className={styles.titreJour}>
                <span>{nomDuJour(jour.jour)}</span>
                <span className={styles.num}>
                  {enFrancais(jour.jour, { day: "numeric", month: "short" })}
                </span>
              </span>
              <span className={styles.etatJour}>{etat.mot}</span>
            </span>
            <span className={styles.compteJour}>{jour.lu && jour.patients ? jour.patients : "—"}</span>
          </button>
        );
      })}

      <div className={styles.autre}>
        <input
          type="date"
          value={choisi}
          title="Aller à une autre date"
          aria-label="Aller à une autre date"
          onChange={(event) => event.target.value && onChoisir(event.target.value)}
        />
      </div>
    </aside>
  );
}
