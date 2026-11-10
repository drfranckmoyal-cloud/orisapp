"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { Fiche, VIDE, type Brouillon } from "@/app/correspondants/Fiche";
import { Champ } from "@/components/ui";
import { ApiError, apiRequest, type Correspondant, type Rattachement } from "@/lib/api";
import { ROLE_CORRESPONDANT, errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./relecture.module.css";

/** Le correspondant du patient, choisi ou créé sans quitter le compte rendu.
 *
 * Franck, le 10/11/2026 : « il faut un lien rapide pour choisir le correspondant sur
 * cette page, et un bouton pop-up de création le cas échéant ». Avant, il fallait ouvrir
 * la fiche du patient, rattacher le confrère, puis revenir. Le correspondant rattaché ici
 * est le même que sur la fiche : il sera proposé comme destinataire à l'envoi.
 */

const ROLES: Rattachement["role"][] = ["referred_by", "referred_to", "also_follows"];

function nomCourt(c: Correspondant): string {
  if (c.kind === "organisation") return c.last_name;
  const civilite = c.title ? `${c.title} ` : "";
  return `${civilite}${c.first_name} ${c.last_name.toLocaleUpperCase("fr-FR")}`
    .replace(/\s+/g, " ")
    .trim();
}

function initiales(c: Correspondant): string {
  if (c.kind === "organisation") return c.last_name.slice(0, 2).toLocaleUpperCase("fr-FR");
  return `${c.first_name[0] ?? ""}${c.last_name[0] ?? ""}`.toLocaleUpperCase("fr-FR");
}

function sansAccents(texte: string): string {
  return texte
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

export function CorrespondantRapide({
  patientId,
  onChange,
}: {
  patientId: string;
  /** Un correspondant a été rattaché ou retiré : l'envoi recharge ses destinataires. */
  onChange: () => void;
}) {
  const [liens, recharger] = useApi<Rattachement[]>(`/patients/${patientId}/correspondents`);
  const [liste, setListe] = useState(false);
  const [creation, setCreation] = useState(false);
  const [carnet] = useApi<Correspondant[]>(liste ? "/correspondents" : null);
  const [specialites] = useApi<string[]>(creation ? "/correspondents/specialties" : null);
  const [recherche, setRecherche] = useState("");
  const [role, setRole] = useState<Rattachement["role"]>("referred_by");
  const [occupe, setOccupe] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const fenetre = useRef<HTMLDialogElement | null>(null);

  const rattaches = useMemo(() => (liens.state === "ready" ? liens.data : []), [liens]);
  const dejaLa = useMemo(() => new Set(rattaches.map((l) => l.correspondent.id)), [rattaches]);
  const proposes = useMemo(() => {
    const tout = carnet.state === "ready" ? carnet.data : [];
    const cherche = sansAccents(recherche.trim());
    const restants = tout.filter((c) => !dejaLa.has(c.id));
    if (!cherche) return restants.slice(0, 8);
    return restants
      .filter((c) => sansAccents(`${nomCourt(c)} ${c.practice} ${c.specialty}`).includes(cherche))
      .slice(0, 8);
  }, [carnet, recherche, dejaLa]);

  // La fenêtre de création est une vraie boîte modale : elle garde le clavier et se
  // ferme à Échap, par-dessus la page.
  useEffect(() => {
    const boite = fenetre.current;
    if (!boite) return;
    if (creation && !boite.open) boite.showModal?.();
    if (!creation && boite.open) boite.close?.();
  }, [creation]);

  function echec(caught: unknown) {
    setErreur(errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"));
  }

  async function rattacher(correspondentId: string) {
    setOccupe(true);
    setErreur(null);
    try {
      await apiRequest(`/patients/${patientId}/correspondents`, {
        method: "POST",
        body: { correspondent_id: correspondentId, role },
      });
      setListe(false);
      setRecherche("");
      recharger();
      onChange();
    } catch (caught) {
      echec(caught);
    } finally {
      setOccupe(false);
    }
  }

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
      onChange();
    } catch (caught) {
      echec(caught);
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
      onChange();
    } catch (caught) {
      echec(caught);
    }
  }

  const choixDuLien = (
    <div className={styles.roles} role="group" aria-label="Lien avec le patient">
      {ROLES.map((valeur) => (
        <button
          key={valeur}
          type="button"
          aria-pressed={role === valeur}
          onClick={() => setRole(valeur)}
        >
          {ROLE_CORRESPONDANT[valeur]}
        </button>
      ))}
    </div>
  );

  return (
    <div className={styles.corresp}>
      <span className={styles.correspLib}>
        {rattaches.length > 1 ? "Correspondants" : "Correspondant"}
      </span>

      <div className={styles.puces}>
        {rattaches.map((lien) => (
          <span key={lien.correspondent.id} className={styles.puce}>
            <i aria-hidden="true">{initiales(lien.correspondent)}</i>
            {nomCourt(lien.correspondent)}
            <small>· {ROLE_CORRESPONDANT[lien.role]}</small>
            <button
              type="button"
              title="Retirer ce correspondant du patient"
              aria-label={`Retirer ${nomCourt(lien.correspondent)}`}
              onClick={() => void detacher(lien.correspondent.id)}
            >
              ×
            </button>
          </span>
        ))}
        {liens.state === "ready" && rattaches.length === 0 && (
          <span className={styles.aucun}>aucun pour ce patient</span>
        )}
      </div>

      <div className={styles.correspActions}>
        <div className={styles.ancre}>
          <button
            type="button"
            className={styles.petit}
            aria-expanded={liste}
            onClick={() => setListe((ouvert) => !ouvert)}
          >
            {rattaches.length === 0 ? "Choisir un correspondant" : "Ajouter"} ▾
          </button>
          {liste && (
            <div className={styles.volet} role="dialog" aria-label="Choisir un correspondant">
              {choixDuLien}
              <Champ
                type="search"
                autoFocus
                value={recherche}
                placeholder="Chercher dans le carnet…"
                aria-label="Chercher un correspondant"
                onChange={(event) => setRecherche(event.target.value)}
              />
              <div className={styles.propositions}>
                {carnet.state === "loading" && <span className={styles.aucun}>chargement…</span>}
                {carnet.state === "ready" && proposes.length === 0 && (
                  <span className={styles.aucun}>
                    {recherche ? "Personne à ce nom dans le carnet." : "Tout le carnet est déjà rattaché."}
                  </span>
                )}
                {proposes.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    disabled={occupe}
                    onClick={() => void rattacher(c.id)}
                  >
                    <b>{nomCourt(c)}</b>
                    <span>
                      {c.kind === "organisation" ? "structure" : c.specialty || "spécialité non renseignée"}
                      {c.practice && ` · ${c.practice}`}
                    </span>
                  </button>
                ))}
              </div>
              <button
                type="button"
                className={styles.creerDepuisListe}
                onClick={() => {
                  setListe(false);
                  setCreation(true);
                }}
              >
                + Nouveau correspondant{recherche.trim() ? ` « ${recherche.trim()} »` : ""}
              </button>
            </div>
          )}
        </div>
        <button type="button" className={styles.petit} onClick={() => setCreation(true)}>
          + Nouveau
        </button>
      </div>

      {erreur && (
        <p className={styles.correspErreur} role="alert">
          {erreur}
        </p>
      )}

      <dialog
        ref={fenetre}
        className={styles.fenetre}
        aria-label="Nouveau correspondant"
        onClose={() => setCreation(false)}
        onClick={(event) => {
          // Un clic sur le voile, hors de la fenêtre, la ferme.
          if (event.target === event.currentTarget) setCreation(false);
        }}
      >
        {creation && (
          <div className={styles.fenetreCorps}>
            <h2>Nouveau correspondant</h2>
            <p>Il est ajouté au carnet et rattaché à ce patient d’un seul geste.</p>
            {choixDuLien}
            <Fiche
              depart={{ ...VIDE, last_name: recherche.trim() }}
              specialites={specialites.state === "ready" ? specialites.data : []}
              occupe={occupe}
              onValider={(brouillon) => void creerEtRattacher(brouillon)}
              onAnnuler={() => setCreation(false)}
            />
            {erreur && (
              <p className={styles.correspErreur} role="alert">
                {erreur}
              </p>
            )}
          </div>
        )}
      </dialog>
    </div>
  );
}
