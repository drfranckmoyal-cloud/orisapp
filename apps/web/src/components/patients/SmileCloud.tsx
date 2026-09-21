"use client";

import { useEffect, useMemo, useState } from "react";

import { Bouton, Pastille } from "@/components/ui";
import { ApiError, apiRequest } from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./smilecloud.module.css";

type Fichier = {
  res_id: string;
  nom: string;
  nature: string;
  rapatriable: boolean;
  pourquoi?: string | null;
};
type Galerie = { id: string; nom: string; date: string; fichiers: Fichier[] };
type Recuperation = {
  demande: string;
  total: number;
  recus: number;
  ecartes: { res_id: string; raison: string }[];
  termine: boolean;
  demande_le: string;
};
type Etat = {
  case_id: string | null;
  nom: string | null;
  etat: "relie" | "trouve" | "a_confirmer" | "ambigu" | "absent" | "sans_liste";
  candidats: { case_id: string; nom: string; pour_cent: number }[];
  galeries: Galerie[] | null;
  galeries_lues_le: string | null;
  lecture_en_cours: boolean;
  recuperation: Recuperation | null;
};

const NATURE: Record<string, string> = {
  photo: "photo",
  radio: "radio",
  scan3d: "scan 3D",
  pdf: "PDF",
  video: "vidéo",
  cbct: "CBCT",
  autre: "autre",
};

const RAISON: Record<string, string> = {
  video: "vidéo, non reprise",
  cbct: "CBCT, non repris",
  inconnu: "fichier introuvable",
  UNSUPPORTED_ATTACHMENT_FORMAT: "format non reconnu",
  ATTACHMENT_TOO_LARGE: "trop lourd (plus de 80 Mo)",
  EMPTY_ATTACHMENT: "fichier vide",
};

/** SmileCloud dans le dossier patient : relier le dossier, voir ses galeries, cocher,
 *  rapatrier. C'est l'extension Chrome qui fait le travail dans SmileCloud ; Oris pose la
 *  demande et montre où elle en est. Voir docs/PIECES_JOINTES_SMILECLOUD.md. */
export function SmileCloud({
  patientId,
  rapatries,
}: {
  patientId: string;
  rapatries: () => void;
}) {
  const [etat, recharger] = useApi<Etat>(`/patients/${patientId}/smilecloud`);
  const [coches, setCoches] = useState<Set<string>>(new Set());
  const [erreur, setErreur] = useState<string | null>(null);

  const attente =
    etat.state === "ready" &&
    (etat.data.lecture_en_cours ||
      (etat.data.recuperation !== null && !etat.data.recuperation.termine));

  // Tant que l'extension travaille, on regarde toutes les 4 s si c'est arrivé.
  useEffect(() => {
    if (!attente) return;
    const minuterie = window.setInterval(recharger, 4000);
    return () => window.clearInterval(minuterie);
  }, [attente, recharger]);

  // Les fichiers arrivés apparaissent dans les pièces jointes au fur et à mesure.
  const recus =
    etat.state === "ready" ? (etat.data.recuperation?.recus ?? 0) : 0;
  useEffect(() => {
    if (recus > 0) rapatries();
  }, [recus, rapatries]);

  const rapatriables = useMemo(
    () =>
      etat.state === "ready"
        ? (etat.data.galeries ?? []).flatMap((g) =>
            g.fichiers.filter((f) => f.rapatriable).map((f) => f.res_id),
          )
        : [],
    [etat],
  );

  async function agir(
    chemin: string,
    methode: "POST" | "PUT",
    corps?: unknown,
  ) {
    setErreur(null);
    try {
      await apiRequest(chemin, { method: methode, body: corps });
      recharger();
    } catch (error) {
      setErreur(
        errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"),
      );
    }
  }

  function basculer(ids: string[], cocher: boolean) {
    setCoches((avant) => {
      const apres = new Set(avant);
      for (const id of ids) {
        if (cocher) apres.add(id);
        else apres.delete(id);
      }
      return apres;
    });
  }

  if (etat.state !== "ready") return null;
  const e = etat.data;

  return (
    <section className={styles.carte} aria-labelledby="sc-titre">
      <header className={styles.enTete}>
        <span className={styles.logo} aria-hidden="true">
          SC
        </span>
        <div>
          <h3 id="sc-titre" className={styles.titre}>
            Récupération SmileCloud
          </h3>
          <p className={styles.sous}>
            {e.etat === "relie"
              ? `Dossier relié : ${e.nom ?? "dossier SmileCloud"}`
              : "Photos, radios, scans et PDF du dossier SmileCloud du patient."}
          </p>
        </div>
        {e.etat === "relie" && (
          <button
            type="button"
            className={styles.lienDiscret}
            onClick={() =>
              void agir(`/patients/${patientId}/smilecloud`, "PUT", {
                case_id: null,
              })
            }
          >
            délier
          </button>
        )}
      </header>

      {e.etat === "sans_liste" && (
        <p className={styles.aide}>
          La liste des dossiers SmileCloud n’est pas encore arrivée :
          l’extension Chrome de Dental Lens la livrera. Rien à faire ici en
          attendant.
        </p>
      )}

      {e.etat === "absent" && (
        <p className={styles.aide}>
          Aucun dossier SmileCloud ne ressemble à ce nom.
        </p>
      )}

      {(e.etat === "trouve" ||
        e.etat === "a_confirmer" ||
        e.etat === "ambigu") && (
        <div className={styles.candidats}>
          <p className={styles.aide}>
            {e.etat === "trouve"
              ? "Un dossier porte exactement ce nom. Confirmez que c’est bien ce patient :"
              : e.etat === "ambigu"
                ? "Plusieurs dossiers portent ce nom : choisissez le bon."
                : "Des dossiers ressemblent à ce nom, sans certitude : c’est à vous de trancher."}
          </p>
          {e.candidats.map((c) => (
            <div key={c.case_id} className={styles.candidat}>
              <strong>{c.nom}</strong>
              <Pastille ton={c.pour_cent >= 100 ? "valide" : "attention"}>
                {c.pour_cent} %
              </Pastille>
              <Bouton
                variante="secondaire"
                onClick={() =>
                  void agir(`/patients/${patientId}/smilecloud`, "PUT", {
                    case_id: c.case_id,
                  })
                }
              >
                C’est ce patient
              </Bouton>
            </div>
          ))}
        </div>
      )}

      {e.etat === "relie" && (
        <>
          <div className={styles.barre}>
            <Bouton
              variante={e.galeries ? "secondaire" : "principal"}
              disabled={e.lecture_en_cours}
              onClick={() =>
                void agir(`/patients/${patientId}/smilecloud/galeries`, "POST")
              }
            >
              {e.lecture_en_cours
                ? "Lecture demandée…"
                : e.galeries
                  ? "Relire les galeries"
                  : "Voir les galeries"}
            </Bouton>
            {e.galeries_lues_le && (
              <span className={styles.aide}>
                lues le {new Date(e.galeries_lues_le).toLocaleString("fr-FR")}
              </span>
            )}
          </div>
          {e.lecture_en_cours && (
            <p className={styles.attente}>
              <span className={styles.point} aria-hidden="true" /> L’extension
              va lire les galeries dans SmileCloud : Chrome doit être ouvert.
              Elles s’afficheront ici d’elles-mêmes.
            </p>
          )}

          {e.galeries && e.galeries.length === 0 && (
            <p className={styles.aide}>Aucune galerie dans ce dossier.</p>
          )}
          {e.galeries && e.galeries.length > 0 && (
            <div className={styles.galeries}>
              {e.galeries.map((g) => {
                const ids = g.fichiers
                  .filter((f) => f.rapatriable)
                  .map((f) => f.res_id);
                const toutes =
                  ids.length > 0 && ids.every((id) => coches.has(id));
                return (
                  <fieldset key={g.id || g.nom} className={styles.galerie}>
                    <legend className={styles.legende}>
                      <label>
                        <input
                          type="checkbox"
                          checked={toutes}
                          disabled={ids.length === 0}
                          onChange={(ev) => basculer(ids, ev.target.checked)}
                        />
                        <strong>{g.nom || "Galerie"}</strong>
                      </label>
                      <span className={styles.aide}>
                        {g.date} · {g.fichiers.length} fichier
                        {g.fichiers.length > 1 ? "s" : ""}
                      </span>
                    </legend>
                    <ul className={styles.fichiers}>
                      {g.fichiers.map((f) => (
                        <li key={f.res_id}>
                          <label className={f.rapatriable ? "" : styles.exclu}>
                            <input
                              type="checkbox"
                              disabled={!f.rapatriable}
                              checked={coches.has(f.res_id)}
                              onChange={(ev) =>
                                basculer([f.res_id], ev.target.checked)
                              }
                            />
                            {f.nom || f.res_id.slice(0, 8)}
                            <span className={styles.nature}>
                              {NATURE[f.nature] ?? f.nature}
                            </span>
                            {!f.rapatriable && (
                              <span className={styles.aide}>
                                {" "}
                                — {f.pourquoi ?? "non repris"}
                              </span>
                            )}
                          </label>
                        </li>
                      ))}
                    </ul>
                  </fieldset>
                );
              })}
            </div>
          )}

          {rapatriables.length > 0 && (
            <div className={styles.barre}>
              <Bouton
                disabled={coches.size === 0}
                onClick={() => {
                  void agir(
                    `/patients/${patientId}/smilecloud/recuperer`,
                    "POST",
                    { fichiers: [...coches] },
                  ).then(() => setCoches(new Set()));
                }}
              >
                Rapatrier{" "}
                {coches.size > 0
                  ? `${coches.size} fichier${coches.size > 1 ? "s" : ""}`
                  : "la sélection"}
              </Bouton>
              <button
                type="button"
                className={styles.lienDiscret}
                onClick={() => basculer(rapatriables, true)}
              >
                tout cocher
              </button>
            </div>
          )}

          {e.recuperation && (
            <div
              className={styles.suivi}
              data-termine={e.recuperation.termine || undefined}
            >
              <strong>
                {e.recuperation.termine
                  ? "Récupération terminée"
                  : "Récupération en cours"}{" "}
                : {e.recuperation.recus} / {e.recuperation.total} reçu
                {e.recuperation.recus > 1 ? "s" : ""}
              </strong>
              {!e.recuperation.termine && (
                <span className={styles.aide}>
                  {" "}
                  — l’extension lit les images plein écran dans SmileCloud, une
                  par une.
                </span>
              )}
              {e.recuperation.ecartes.length > 0 && (
                <ul className={styles.ecartes}>
                  {e.recuperation.ecartes.map((x) => (
                    <li key={x.res_id}>
                      1 fichier non repris : {RAISON[x.raison] ?? x.raison}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
      {erreur && <p className={styles.erreur}>{erreur}</p>}
    </section>
  );
}
