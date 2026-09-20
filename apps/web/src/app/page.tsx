"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Symbole } from "@/components/Marque";
import { Carte, Champ, EnTetePage, EtatVide, Ligne, Lignes, Pastille, Squelette } from "@/components/ui";
import type { Encounter, GlossaryTerm, LearningSuggestion, Patient } from "@/lib/api";
import { errorMessage, formatDate, formatDateTime } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./accueil.module.css";

/** Minutes de rédaction évitées par consultation traitée.
 *
 * C'est une moyenne, pas une mesure. L'écran le dit en toutes lettres : un chiffre
 * dont on ne donne pas la méthode est un chiffre qu'on ne peut pas contredire.
 */
const MINUTES_PAR_COMPTE_RENDU = 11;
const LETTRES = ["L", "M", "M", "J", "V", "S", "D"];
const TERMINEES = new Set(["validated", "exported", "archived"]);

function sansAccents(texte: string): string {
  return texte
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function quand(encounter: Encounter): Date {
  return new Date(encounter.started_at ?? encounter.created_at);
}

function nomDe(encounter: Encounter): string {
  return `${encounter.patient.first_name} ${encounter.patient.last_name}`.trim();
}

function documentsDe(encounter: Encounter): string {
  const total = encounter.documents.length;
  if (total === 0) return "aucun document";
  return total === 1 ? "1 document" : `${total} documents`;
}

/** Lundi de la semaine en cours, à minuit. */
function debutDeSemaine(): Date {
  const jour = new Date();
  jour.setHours(0, 0, 0, 0);
  const depuisLundi = (jour.getDay() + 6) % 7;
  jour.setDate(jour.getDate() - depuisLundi);
  return jour;
}

function dureeLisible(minutes: number): string {
  const heures = Math.floor(minutes / 60);
  const reste = minutes % 60;
  if (heures === 0) return `${reste} min`;
  return reste === 0 ? `${heures} h` : `${heures} h ${String(reste).padStart(2, "0")}`;
}

/** Accueil : ce qui attend, ce qui s'est passé, et un seul geste qui compte. */
export default function HomePage() {
  const [encounters] = useApi<Encounter[]>("/encounters");
  const [patients] = useApi<Patient[]>("/patients");
  const [suggestions] = useApi<LearningSuggestion[]>("/me/learning/suggestions");
  const [glossaire] = useApi<GlossaryTerm[]>("/glossary");
  const [recherche, setRecherche] = useState("");

  const toutes = useMemo(
    () => (encounters.state === "ready" ? encounters.data : []),
    [encounters],
  );
  const aRelire = toutes.filter((e) => e.status === "review");

  const semaine = useMemo(() => {
    const lundi = debutDeSemaine();
    const compte = [0, 0, 0, 0, 0, 0, 0];
    for (const encounter of toutes) {
      const jour = quand(encounter);
      const index = Math.floor((jour.getTime() - lundi.getTime()) / 86_400_000);
      if (index >= 0 && index < 7) compte[index] = (compte[index] ?? 0) + 1;
    }
    return compte;
  }, [toutes]);

  const totalSemaine = semaine.reduce((somme, jour) => somme + jour, 0);
  const traiteesSemaine = useMemo(() => {
    const lundi = debutDeSemaine();
    return toutes.filter(
      (e) => quand(e) >= lundi && (e.status === "review" || TERMINEES.has(e.status)),
    ).length;
  }, [toutes]);
  const validees = toutes.filter((e) => TERMINEES.has(e.status)).length;
  const aujourdhuiIndex = (new Date().getDay() + 6) % 7;

  const trouves = useMemo(() => {
    const cherche = sansAccents(recherche.trim());
    if (!cherche) return [];
    const liste = patients.state === "ready" ? patients.data : [];
    return liste
      .filter((patient) =>
        sansAccents(`${patient.first_name} ${patient.last_name}`).includes(cherche),
      )
      .slice(0, 6);
  }, [patients, recherche]);

  const propositions = suggestions.state === "ready" ? suggestions.data : [];
  const motsRetenus = glossaire.state === "ready" ? glossaire.data.length : 0;
  const maxJour = Math.max(1, ...semaine);

  return (
    <div className="page">
      <EnTetePage
        surTitre={new Date().toLocaleDateString("fr-FR", {
          weekday: "long",
          day: "numeric",
          month: "long",
        })}
        titre="Votre journée"
        action={
          <div style={{ minWidth: 280 }}>
            <Champ
              type="search"
              placeholder="Retrouver un patient"
              value={recherche}
              onChange={(event) => setRecherche(event.target.value)}
            />
          </div>
        }
      />

      {recherche.trim() !== "" && (
        <Carte serree>
          {trouves.length === 0 ? (
            <EtatVide titre="Aucun patient à ce nom">
              Vous pourrez le créer au moment de démarrer la consultation.
            </EtatVide>
          ) : (
            <Lignes>
              {trouves.map((patient) => (
                <Ligne
                  key={patient.id}
                  href={`/patients/${patient.id}`}
                  titre={`${patient.first_name} ${patient.last_name}`}
                  detail={
                    patient.birth_date ? `né(e) le ${formatDate(patient.birth_date)}` : undefined
                  }
                />
              ))}
            </Lignes>
          )}
        </Carte>
      )}

      <div className={styles.haut}>
        <Link href="/consultations/nouvelle" className={styles.demarrer}>
          <span className={styles.disque}>
            <Symbole taille={48} />
          </span>
          <span>
            <span className={styles.titreDemarrer}>Commencer une consultation</span>
            <span className={styles.sousDemarrer}>
              {/* Le slogan vit déjà sous le logo : ici, on dit la promesse concrète. */}
              Oris écoute. Le dossier sera prêt avant la fin du rendez-vous.
            </span>
          </span>
        </Link>

        <Carte
          titre="Cette semaine"
          action={
            <Pastille>
              {totalSemaine === 1 ? "1 consultation" : `${totalSemaine} consultations`}
            </Pastille>
          }
        >
          {encounters.state === "loading" && <Squelette lignes={3} />}
          {encounters.state === "ready" && (
            <div className={styles.semaine}>
              {semaine.map((nombre, index) => (
                <div
                  key={index}
                  className={`${styles.jour} ${index === aujourdhuiIndex ? styles.aujourdhui : ""}`}
                  title={`${LETTRES[index]} : ${nombre}`}
                >
                  <span
                    className={styles.barre}
                    style={{ height: `${Math.max(4, (nombre / maxJour) * 100)}%` }}
                  />
                  <span className={styles.lettre}>{LETTRES[index]}</span>
                </div>
              ))}
            </div>
          )}
        </Carte>
      </div>

      <div className={styles.grille}>
        <Carte
          titre="À relire"
          action={aRelire.length > 0 ? <Pastille ton="attention">{aRelire.length}</Pastille> : null}
        >
          {encounters.state === "loading" && <Squelette lignes={3} />}
          {encounters.state === "error" && <EtatVide titre={errorMessage(encounters.code)} />}
          {encounters.state === "ready" && aRelire.length === 0 && (
            <EtatVide titre="Rien à relire">
              Les comptes rendus apparaissent ici dès qu’une consultation est traitée.
            </EtatVide>
          )}
          {aRelire.length > 0 && (
            <Lignes>
              {aRelire.slice(0, 5).map((encounter) => (
                <Ligne
                  key={encounter.id}
                  href={`/consultations/${encounter.id}`}
                  titre={nomDe(encounter)}
                  detail={`${formatDateTime(encounter.started_at ?? encounter.created_at)} · ${documentsDe(encounter)}`}
                  fin={<Pastille ton="attention">à relire</Pastille>}
                />
              ))}
            </Lignes>
          )}
        </Carte>

        <Carte titre="Saisie évitée">
          <p className={styles.chiffre}>
            {dureeLisible(traiteesSemaine * MINUTES_PAR_COMPTE_RENDU)}{" "}
            <small>cette semaine</small>
          </p>
          <p className="muted" style={{ margin: 0 }}>
            Estimation :{" "}
            {traiteesSemaine === 1
              ? "1 consultation traitée"
              : `${traiteesSemaine} consultations traitées`}
            , à {MINUTES_PAR_COMPTE_RENDU} minutes de compte rendu chacune. Elle vaut ce
            que vaut la moyenne.
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Pastille ton="valide">
              {validees === 1 ? "1 validée" : `${validees} validées`}
            </Pastille>
            <Pastille>
              {aRelire.length === 1 ? "1 en attente" : `${aRelire.length} en attente`}
            </Pastille>
          </div>
        </Carte>

        <Carte
          titre="Oris apprend"
          action={
            propositions.length > 0 ? (
              <Pastille ton="attention">{propositions.length}</Pastille>
            ) : null
          }
        >
          {suggestions.state === "loading" && <Squelette lignes={2} />}
          {suggestions.state === "ready" && propositions.length === 0 && (
            <EtatVide titre="Rien à proposer">
              Oris ne propose une règle qu’après plusieurs corrections allant dans le même
              sens.
            </EtatVide>
          )}
          {propositions.slice(0, 2).map((suggestion) => (
            <p key={suggestion.key} style={{ margin: 0 }}>
              {suggestion.message}
            </p>
          ))}
          <p className="muted" style={{ margin: 0 }}>
            {motsRetenus === 0
              ? "Aucun mot dans votre dictionnaire."
              : motsRetenus === 1
                ? "1 mot dans votre dictionnaire."
                : `${motsRetenus} mots dans votre dictionnaire.`}{" "}
            <Link href="/apprentissage" className="link-button">
              Tout voir
            </Link>
          </p>
        </Carte>
      </div>
    </div>
  );
}
