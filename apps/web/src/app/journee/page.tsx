"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Bouton, EnTetePage, EtatVide, Squelette } from "@/components/ui";
import { CommencerConsultation } from "@/components/patients/CommencerConsultation";
import { ApiError, apiRequest, type Journee, type Jour, type RendezVous } from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";
import { aujourdhuiISO, enFrancais, jourDecale, lundiDe } from "./dates";
import { Attente } from "./Attente";
import { Semaine } from "./Semaine";
import styles from "./journee.module.css";

/** Votre journée : l'agenda du jour, repris de Dental Lens.
 *
 * Même mise en page que l'écran « Préparer la journée » de Dental Lens — la semaine
 * navigable à gauche, les patients à droite — parce qu'elle a fait ses preuves entre
 * deux rendez-vous. Une différence de fond : ici, « Créer le dossier » crée le dossier
 * **dans Oris**, pas dans SmileCloud.
 */

const JOURS_AFFICHES = 7;

/** Un rendez-vous annulé ou manqué n'est pas une consultation qui attend. */
function passe(statut: string): boolean {
  const mot = statut.toLowerCase();
  return mot.includes("absent") || mot.includes("annul");
}

export default function JourneePage() {
  const [jour, setJour] = useState(aujourdhuiISO);
  const [debutSemaine, setDebutSemaine] = useState(() => lundiDe(aujourdhuiISO()));
  const [message, setMessage] = useState<string | null>(null);
  const [encours, setEncours] = useState<string | null>(null);

  const [journee, rechargerJournee] = useApi<Journee>(`/journee?jour=${jour}`);
  const [semaine, rechargerSemaine] = useApi<Jour[]>(
    `/journee/semaine?depuis=${debutSemaine}&jours=${JOURS_AFFICHES}`,
  );

  /** La semaine affichée suit le jour choisi, sans sauter si on y est déjà. */
  const choisirJour = useCallback(
    (nouveau: string) => {
      setJour(nouveau);
      setDebutSemaine((debut) =>
        nouveau < debut || nouveau > jourDecale(debut, JOURS_AFFICHES - 1)
          ? lundiDe(nouveau)
          : debut,
      );
    },
    [],
  );

  const donnees = journee.state === "ready" ? journee.data : null;
  const jours = semaine.state === "ready" ? semaine.data : [];
  const rendezvous = useMemo(() => donnees?.rendezvous ?? [], [donnees]);
  const manquants = useMemo(
    () => rendezvous.filter((rdv) => !rdv.patient_id && !passe(rdv.statut)),
    [rendezvous],
  );

  const recharger = useCallback(() => {
    rechargerJournee();
    rechargerSemaine();
  }, [rechargerJournee, rechargerSemaine]);

  /* Revenir de Chrome suffit à rafraîchir : on va lire Doctolib dans l'autre fenêtre,
     on revient, la journée est là. Sans ça il faudrait recharger la page à la main. */
  useEffect(() => {
    const auRetour = () => {
      if (document.visibilityState === "visible") recharger();
    };
    document.addEventListener("visibilitychange", auRetour);
    window.addEventListener("focus", auRetour);
    return () => {
      document.removeEventListener("visibilitychange", auRetour);
      window.removeEventListener("focus", auRetour);
    };
  }, [recharger]);

  /* Tant qu'une relecture est attendue, l'écran va voir tout seul si elle est arrivée :
     l'extension peut mettre quelques secondes comme une minute. */
  const attendue = donnees?.demande_le ?? null;
  useEffect(() => {
    if (!attendue) return;
    const minuteur = setInterval(recharger, 8000);
    return () => clearInterval(minuteur);
  }, [attendue, recharger]);

  /** Demander à l'extension de (re)lire cet agenda. Oris ne va rien chercher lui-même. */
  async function demander() {
    setEncours("demande");
    setMessage(null);
    try {
      await apiRequest("/journee/demande", { method: "POST", body: { jour } });
      recharger();
    } catch (error) {
      setMessage(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setEncours(null);
    }
  }

  async function annuler() {
    setMessage(null);
    try {
      await apiRequest(`/journee/demande?jour=${jour}`, { method: "DELETE" });
      recharger();
    } catch (error) {
      setMessage(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
  }

  async function creer(rdv: RendezVous) {
    await apiRequest("/patients", {
      method: "POST",
      body: { first_name: rdv.prenom, last_name: rdv.nom },
    });
  }

  async function creerUn(rdv: RendezVous) {
    const cle = `${rdv.heure}-${rdv.nom}`;
    setEncours(cle);
    setMessage(null);
    try {
      await creer(rdv);
      setMessage(`Dossier créé pour ${rdv.prenom} ${rdv.nom}.`);
      recharger();
    } catch (error) {
      setMessage(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setEncours(null);
    }
  }

  /** Les dossiers manquants, l'un après l'autre : une erreur n'emporte pas les autres. */
  async function creerTous() {
    setEncours("tous");
    setMessage(null);
    let faits = 0;
    for (const rdv of manquants) {
      try {
        await creer(rdv);
        faits += 1;
      } catch {
        /* comptabilisé plus bas : on continue la liste */
      }
    }
    const restants = manquants.length - faits;
    setMessage(
      restants === 0
        ? `${faits} dossier${faits > 1 ? "s" : ""} créé${faits > 1 ? "s" : ""}.`
        : `${faits} créé${faits > 1 ? "s" : ""}, ${restants} en échec — réessayez ligne par ligne.`,
    );
    setEncours(null);
    recharger();
  }

  return (
    <div className="page">
      <EnTetePage
        surTitre={donnees?.agenda || "Agenda du cabinet"}
        titre="Votre journée"
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

      <div className={styles.plan}>
        {semaine.state === "loading" ? (
          <aside className={styles.semaine}>
            <div className={styles.chargement}>
              <Squelette lignes={7} />
            </div>
          </aside>
        ) : (
          <Semaine
            jours={jours}
            debut={debutSemaine}
            choisi={jour}
            onChoisir={choisirJour}
            onSemaine={(pas) =>
              setDebutSemaine((debut) => jourDecale(debut, pas * JOURS_AFFICHES))
            }
          />
        )}

        <section className={styles.journee}>
          <header className={styles.haut}>
            <h2>
              {enFrancais(jour, { weekday: "long", day: "numeric", month: "long" })}
            </h2>
            {donnees?.disponible && (
              <span className={styles.compte}>
                {rendezvous.length} patient{rendezvous.length > 1 ? "s" : ""}
              </span>
            )}
            <div className={styles.actions}>
              <Bouton
                variante="secondaire"
                onClick={() => void demander()}
                disabled={encours !== null || attendue !== null}
              >
                {encours === "demande"
                  ? "Demande…"
                  : attendue
                    ? "Relecture demandée"
                    : donnees?.disponible
                      ? "Mettre à jour"
                      : "Charger la journée"}
              </Bouton>
              {manquants.length > 0 && (
                <Bouton onClick={() => void creerTous()} disabled={encours !== null}>
                  {encours === "tous"
                    ? "Création…"
                    : `Créer ${manquants.length} dossier${manquants.length > 1 ? "s" : ""}`}
                </Bouton>
              )}
            </div>
          </header>

          {attendue && (
            <Attente
              depuis={attendue}
              livraison={donnees?.derniere_livraison ?? null}
              onAnnuler={() => void annuler()}
            />
          )}

          {journee.state === "loading" && (
            <div className={styles.chargement}>
              <Squelette lignes={5} />
            </div>
          )}
          {journee.state === "error" && (
            <div className={styles.creux}>
              <EtatVide titre={errorMessage(journee.code)} />
            </div>
          )}

          {donnees && !donnees.disponible && (
            <div className={styles.creux}>
              <EtatVide titre="Cette journée n’a pas encore été relevée">
                {attendue ? (
                  <>
                    Oris l’a demandée. L’<strong>extension Chrome</strong> se réveille toutes
                    les minutes : au réveil suivant, elle ouvrira Doctolib sur ce jour en
                    arrière-plan, lira la liste et la déposera ici. Gardez Chrome ouvert.
                  </>
                ) : (
                  <>
                    L’agenda est relevé par l’<strong>extension Chrome</strong>, qui dépose
                    ensuite la journée dans Oris. Appuyez sur <strong>Charger la journée</strong>,
                    ou ouvrez simplement Doctolib sur ce jour avec l’extension active.
                  </>
                )}
              </EtatVide>
            </div>
          )}

          {donnees?.disponible && rendezvous.length === 0 && (
            <div className={styles.creux}>
              <EtatVide titre="Aucun rendez-vous ce jour-là">
                L’agenda a bien été lu, il est vide.
              </EtatVide>
            </div>
          )}

          {rendezvous.map((rdv) => {
            const cle = `${rdv.heure}-${rdv.nom}`;
            const annule = passe(rdv.statut);
            return (
              <div
                key={cle}
                className={`${styles.rang} ${rdv.patient_id ? styles.rangFait : ""} ${
                  annule ? styles.rangAnnule : ""
                }`}
              >
                <span className={styles.heure}>{rdv.heure || "—"}</span>
                <span className={styles.nom}>
                  {rdv.prenom} {rdv.nom}
                </span>
                <span className={styles.motif}>
                  {rdv.motif || "motif non précisé"}
                  {annule && <span className={styles.statut}> · {rdv.statut}</span>}
                </span>
                <span className={styles.agir}>
                  {rdv.patient_id ? (
                    <>
                      <Link href={`/patients/${rdv.patient_id}`} className={styles.marqueOk}>
                        ✓ dossier existant
                      </Link>
                      {!annule && (
                        <CommencerConsultation patientId={rdv.patient_id} variante="ligne" />
                      )}
                    </>
                  ) : (
                    <button
                      type="button"
                      className={styles.creerLigne}
                      disabled={encours !== null}
                      onClick={() => void creerUn(rdv)}
                    >
                      {encours === cle ? "Création…" : "Créer le dossier"}
                    </button>
                  )}
                </span>
              </div>
            );
          })}

          {donnees?.disponible && (
            <p className={styles.provenance}>
              Journée déposée par l’extension Chrome
              {donnees.recu_le ? ` le ${new Date(donnees.recu_le).toLocaleString("fr-FR")}` : ""}.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
