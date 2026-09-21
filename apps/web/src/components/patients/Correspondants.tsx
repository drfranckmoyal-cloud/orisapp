"use client";

import { useMemo, useState } from "react";

import { Champ } from "@/components/ui";
import { ApiError, apiRequest, type Correspondant, type Rattachement } from "@/lib/api";
import { ROLE_CORRESPONDANT, errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";
import { Fiche, VIDE, type Brouillon } from "@/app/correspondants/Fiche";

import styles from "./correspondants.module.css";

/** Les correspondants d'un patient, sur sa fiche.
 *
 * Le rôle est porté par le lien et non par le correspondant : le même confrère adresse
 * un patient et en reçoit un autre. Il est donc choisi ici, au moment du rattachement,
 * et se lit sur chaque jeton — « nous l'a adressé » n'est pas « nous lui adressons ».
 */

const ROLES: Rattachement["role"][] = ["referred_by", "referred_to", "also_follows"];

function nomCourt(c: Correspondant): string {
  if (c.kind === "organisation") return c.last_name;
  const civilite = c.title ? `${c.title} ` : "";
  return `${civilite}${c.first_name} ${c.last_name.toLocaleUpperCase("fr-FR")}`
    .replace(/\s+/g, " ")
    .trim();
}

function sansAccents(texte: string): string {
  return texte
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

export function Correspondants({ patientId }: { patientId: string }) {
  const [liens, recharger] = useApi<Rattachement[]>(`/patients/${patientId}/correspondents`);
  const [ouvert, setOuvert] = useState(false);
  const [carnet] = useApi<Correspondant[]>(ouvert ? "/correspondents" : null);
  const [recherche, setRecherche] = useState("");
  const [role, setRole] = useState<Rattachement["role"]>("referred_by");
  const [occupe, setOccupe] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  /** Le confrère n'est pas encore dans le carnet : on le crée sans quitter la fiche. */
  const [creation, setCreation] = useState(false);
  const [specialites] = useApi<string[]>(creation ? "/correspondents/specialties" : null);

  const rattaches = useMemo(() => (liens.state === "ready" ? liens.data : []), [liens]);
  const dejaLa = useMemo(
    () => new Set(rattaches.map((lien) => lien.correspondent.id)),
    [rattaches],
  );

  const proposes = useMemo(() => {
    const tout = carnet.state === "ready" ? carnet.data : [];
    const cherche = sansAccents(recherche.trim());
    const restants = tout.filter((c) => !dejaLa.has(c.id));
    if (!cherche) return restants.slice(0, 6);
    return restants
      .filter((c) => sansAccents(`${nomCourt(c)} ${c.practice} ${c.specialty}`).includes(cherche))
      .slice(0, 6);
  }, [carnet, recherche, dejaLa]);

  async function rattacher(correspondentId: string) {
    setOccupe(true);
    setErreur(null);
    try {
      await apiRequest(`/patients/${patientId}/correspondents`, {
        method: "POST",
        body: { correspondent_id: correspondentId, role },
      });
      setRecherche("");
      recharger();
    } catch (error) {
      setErreur(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setOccupe(false);
    }
  }

  /** Créer la fiche dans le carnet, puis la rattacher avec le rôle choisi.
   *
   * Un seul geste : on crée un correspondant depuis une fiche patient précisément parce
   * qu'il est lié à ce patient. Le renvoyer ensuite chercher dans la liste serait un
   * aller-retour inutile. */
  async function creerEtRattacher(brouillon: Brouillon) {
    setOccupe(true);
    setErreur(null);
    try {
      const fiche = await apiRequest<Correspondant>("/correspondents", {
        method: "POST",
        body: brouillon,
      });
      await apiRequest(`/patients/${patientId}/correspondents`, {
        method: "POST",
        body: { correspondent_id: fiche.id, role },
      });
      setCreation(false);
      setRecherche("");
      recharger();
    } catch (error) {
      setErreur(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setOccupe(false);
    }
  }

  async function detacher(correspondentId: string) {
    setErreur(null);
    try {
      await apiRequest(`/patients/${patientId}/correspondents/${correspondentId}`, {
        method: "DELETE",
      });
      recharger();
    } catch (error) {
      setErreur(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
  }

  return (
    <div className={styles.bloc}>
      <div className={styles.jetons}>
        {rattaches.map((lien) => (
          <span key={lien.correspondent.id} className={styles.jeton}>
            <span className={styles.nom}>{nomCourt(lien.correspondent)}</span>
            <span className={styles.role}>{ROLE_CORRESPONDANT[lien.role]}</span>
            <button
              type="button"
              className={styles.retirer}
              title="Retirer de cette fiche"
              aria-label={`Retirer ${nomCourt(lien.correspondent)} de cette fiche`}
              onClick={() => void detacher(lien.correspondent.id)}
            >
              ×
            </button>
          </span>
        ))}

        {liens.state === "ready" && rattaches.length === 0 && !ouvert && (
          <span className={styles.aucun}>aucun</span>
        )}

        <button type="button" className={styles.ajouter} onClick={() => setOuvert((o) => !o)}>
          {ouvert ? "fermer" : "+ rattacher"}
        </button>
      </div>

      {ouvert && (
        <div className={styles.choix}>
          <div className={styles.roles}>
            {ROLES.map((valeur) => (
              <button
                key={valeur}
                type="button"
                aria-pressed={role === valeur}
                className={`${styles.roleChoix} ${role === valeur ? styles.roleRetenu : ""}`}
                onClick={() => setRole(valeur)}
              >
                {ROLE_CORRESPONDANT[valeur]}
              </button>
            ))}
          </div>

          <Champ
            type="search"
            value={recherche}
            placeholder="Chercher dans le carnet…"
            aria-label="Chercher un correspondant"
            onChange={(event) => setRecherche(event.target.value)}
          />

          {creation ? (
            <div className={styles.creation}>
              <Fiche
                depart={{ ...VIDE, last_name: recherche.trim() }}
                specialites={specialites.state === "ready" ? specialites.data : []}
                occupe={occupe}
                onValider={(brouillon) => void creerEtRattacher(brouillon)}
                onAnnuler={() => setCreation(false)}
              />
            </div>
          ) : (
          <div className={styles.propositions}>
            {carnet.state === "loading" && <span className={styles.aucun}>chargement…</span>}
            {carnet.state === "ready" && proposes.length === 0 && (
              <span className={styles.aucun}>
                {recherche ? "aucun correspondant à ce nom" : "tout le carnet est déjà rattaché"}
              </span>
            )}
            {proposes.map((c) => (
              <button
                key={c.id}
                type="button"
                className={styles.proposition}
                disabled={occupe}
                onClick={() => void rattacher(c.id)}
              >
                <span className={styles.nom}>{nomCourt(c)}</span>
                <span className={styles.detail}>
                  {c.kind === "organisation" ? "structure" : c.specialty || "spécialité non renseignée"}
                  {c.practice && ` · ${c.practice}`}
                </span>
              </button>
            ))}
            {/* Toujours proposé, et pas seulement quand la recherche est vide : un homonyme
                dans le carnet n'est pas forcément le bon confrère. */}
            <button type="button" className={styles.creer} onClick={() => setCreation(true)}>
              + Créer un correspondant{recherche.trim() ? ` « ${recherche.trim()} »` : ""}
            </button>
          </div>
          )}

          {!creation && (
            <p className={styles.aide}>
              Choisissez d’abord ce que le lien veut dire, puis le confrère — ou créez-le s’il
              n’est pas encore dans le carnet : il y sera ajouté et rattaché d’un seul geste.
            </p>
          )}
        </div>
      )}

      {erreur && (
        <span className={styles.erreur} role="alert">
          {erreur}
        </span>
      )}
    </div>
  );
}
