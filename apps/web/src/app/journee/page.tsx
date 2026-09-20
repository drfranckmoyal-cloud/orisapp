"use client";

import Link from "next/link";
import { useState } from "react";

import {
  Bouton,
  Carte,
  Champ,
  EnTetePage,
  EtatVide,
  Pastille,
  Squelette,
} from "@/components/ui";
import { ApiError, apiRequest, type Journee, type RendezVous } from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";
import styles from "./journee.module.css";

/** Votre journée : l'agenda du jour, repris de Dental Lens.
 *
 * Oris ne lit pas Doctolib. C'est Dental Lens, l'autre outil du cabinet, qui lit
 * l'agenda dans le navigateur et dépose la journée sur le poste ; Oris vient la
 * chercher. Chaque ligne mène à deux gestes et deux seulement : ouvrir le dossier,
 * ou commencer l'écoute. Le dossier n'est jamais créé sans un clic.
 */

const ETAT_SMILECLOUD: Record<RendezVous["smilecloud"], { texte: string; ton: Ton }> = {
  trouve: { texte: "dossier SmileCloud", ton: "valide" },
  absent: { texte: "pas de dossier SmileCloud", ton: "attention" },
  demande: { texte: "dossier SmileCloud demandé", ton: "accent" },
  a_verifier: { texte: "SmileCloud non interrogé", ton: "neutre" },
  ambigu: { texte: "plusieurs dossiers SmileCloud", ton: "alerte" },
  inconnu: { texte: "SmileCloud non interrogé", ton: "neutre" },
};

type Ton = "neutre" | "accent" | "valide" | "attention" | "alerte";

/** Un rendez-vous annulé ou manqué n'est pas une consultation qui attend. */
function passe(statut: string): boolean {
  const mot = statut.toLowerCase();
  return mot.includes("absent") || mot.includes("annul");
}

/** Le jour **ici**, pas à Greenwich : après minuit, `toISOString` renvoie la veille. */
function aujourdhui(): string {
  const maintenant = new Date();
  const mois = String(maintenant.getMonth() + 1).padStart(2, "0");
  const jour = String(maintenant.getDate()).padStart(2, "0");
  return `${maintenant.getFullYear()}-${mois}-${jour}`;
}

function enLettres(jour: string): string {
  const date = new Date(`${jour}T12:00:00`);
  if (Number.isNaN(date.getTime())) return jour;
  return date.toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function JourneePage() {
  const [jour, setJour] = useState(aujourdhui());
  const [journee, reload] = useApi<Journee>(`/journee?jour=${jour}`);
  const [message, setMessage] = useState<string | null>(null);
  const [encours, setEncours] = useState<string | null>(null);

  /** Faire entrer un patient de l'agenda dans Oris — sur ce clic, jamais avant. */
  async function creer(rdv: RendezVous) {
    const cle = `${rdv.heure}-${rdv.nom}`;
    setEncours(cle);
    setMessage(null);
    try {
      await apiRequest("/patients", {
        method: "POST",
        body: { first_name: rdv.prenom, last_name: rdv.nom },
      });
      setMessage(`Dossier créé pour ${rdv.prenom} ${rdv.nom}.`);
      reload();
    } catch (error) {
      setMessage(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setEncours(null);
    }
  }

  const donnees = journee.state === "ready" ? journee.data : null;
  const attendus = donnees?.rendezvous.filter((rdv) => !passe(rdv.statut)).length ?? 0;

  return (
    <div className="page">
      <EnTetePage
        surTitre={donnees?.agenda || "Agenda du cabinet"}
        titre="Votre journée"
        action={
          <Champ
            type="date"
            value={jour}
            aria-label="Jour affiché"
            style={{ width: 180 }}
            onChange={(event) => setJour(event.target.value || aujourdhui())}
          />
        }
      />

      {message && (
        <div className="banner banner-info" role="status">
          {message}
        </div>
      )}

      {donnees?.disponible && (
        <div className="banner banner-review">
          {/* `.banner` est une grille : toute la phrase tient dans un seul enfant,
              sinon le passage en gras part à la ligne tout seul. */}
          <span>
            Ces noms viennent de votre agenda : ce sont de <strong>vrais patients</strong>.
            Créer un dossier les fait entrer dans Oris — à garder sur ce poste tant que
            l’hébergement de santé n’est pas en place.
          </span>
        </div>
      )}

      <Carte
        titre={enLettres(jour)}
        action={
          donnees?.disponible && donnees.rendezvous.length > 0 ? (
            <span className={styles.compte}>
              {attendus} consultation{attendus > 1 ? "s" : ""} attendue
              {attendus > 1 ? "s" : ""}
            </span>
          ) : undefined
        }
      >
        {journee.state === "loading" && <Squelette lignes={5} />}
        {journee.state === "error" && <EtatVide titre={errorMessage(journee.code)} />}

        {donnees && !donnees.disponible && (
          <EtatVide titre="Cette journée n’a pas encore été lue">
            L’agenda est lu par <strong>Dental Lens</strong>, pas par Oris. Ouvrez Doctolib
            avec Dental Lens actif pour ce jour : la journée arrivera ici toute seule.
          </EtatVide>
        )}

        {donnees && donnees.disponible && donnees.rendezvous.length === 0 && (
          <EtatVide titre="Aucun rendez-vous ce jour-là">
            L’agenda a bien été lu, il est vide.
          </EtatVide>
        )}

        {donnees && donnees.rendezvous.length > 0 && (
          <div className={styles.rdvs}>
            {donnees.rendezvous.map((rdv) => {
              const cle = `${rdv.heure}-${rdv.nom}`;
              const etat = ETAT_SMILECLOUD[rdv.smilecloud];
              return (
                <div
                  key={cle}
                  className={`${styles.rdv} ${passe(rdv.statut) ? styles.rdvPasse : ""}`}
                >
                  <span className={styles.heure}>{rdv.heure || "—"}</span>

                  <span className={styles.qui}>
                    <span className={styles.nom}>
                      {rdv.nom} <span className={styles.prenom}>{rdv.prenom}</span>
                    </span>
                    <span className={styles.motif}>{rdv.motif || "motif non précisé"}</span>
                  </span>

                  <span className={styles.etats}>
                    {passe(rdv.statut) && <Pastille ton="neutre">{rdv.statut}</Pastille>}
                    <Pastille ton={etat.ton} point>
                      {etat.texte}
                    </Pastille>
                  </span>

                  <span className={styles.gestes}>
                    {rdv.patient_id ? (
                      <>
                        <Link
                          href={`/patients/${rdv.patient_id}`}
                          className={styles.lienFiche}
                        >
                          dossier
                        </Link>
                        <Link
                          href={`/consultations/nouvelle?patient=${rdv.patient_id}`}
                          className={styles.commencer}
                        >
                          Commencer
                        </Link>
                      </>
                    ) : (
                      <Bouton
                        variante="secondaire"
                        onClick={() => void creer(rdv)}
                        disabled={encours === cle}
                      >
                        {encours === cle ? "Création…" : "Créer le dossier"}
                      </Bouton>
                    )}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {donnees?.disponible && (
          <p className={styles.provenance}>
            Lu par Dental Lens
            {donnees.lu_le ? ` le ${new Date(donnees.lu_le).toLocaleString("fr-FR")}` : ""}
            {donnees.source === "fichier" ? " — Dental Lens n’est pas lancé" : ""}.
          </p>
        )}
      </Carte>
    </div>
  );
}
