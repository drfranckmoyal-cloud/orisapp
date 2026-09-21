"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Icone, type NomIcone } from "@/components/Icones";
import { Symbole } from "@/components/Marque";
import {
  Carte,
  Champ,
  EtatVide,
  Ligne,
  Lignes,
  Pastille,
  Squelette,
} from "@/components/ui";
import type {
  Cabinet,
  Encounter,
  GlossaryTerm,
  Journee,
  LearningSuggestion,
  Patient,
} from "@/lib/api";
import { errorMessage, formatDate, nomPatient } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./accueil.module.css";

/** Minutes de rédaction évitées par consultation traitée. Une moyenne, pas une mesure :
 *  la tuile le dit en toutes lettres. */
const MINUTES_PAR_COMPTE_RENDU = 11;
const LETTRES = ["L", "M", "M", "J", "V", "S", "D"];
const TERMINEES = new Set(["validated", "exported", "archived"]);

function sansAccents(texte: string): string {
  return texte.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function quand(encounter: Encounter): Date {
  return new Date(encounter.started_at ?? encounter.created_at);
}

function debutDeSemaine(): Date {
  const jour = new Date();
  jour.setHours(0, 0, 0, 0);
  jour.setDate(jour.getDate() - ((jour.getDay() + 6) % 7));
  return jour;
}

function aujourdhuiISO(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function dureeLisible(minutes: number): string {
  const heures = Math.floor(minutes / 60);
  const reste = minutes % 60;
  if (heures === 0) return `${reste} min`;
  return reste === 0
    ? `${heures} h`
    : `${heures} h ${String(reste).padStart(2, "0")}`;
}

function momentDuJour(): string {
  const h = new Date().getHours();
  return h < 18 ? "Bonjour" : "Bonsoir";
}

/** Une tuile du tableau de bord : une teinte, un chiffre, une phrase. Cliquable. */
function Tuile({
  href,
  teinte,
  icone,
  titre,
  chiffre,
  detail,
  children,
}: {
  href: string;
  teinte: "orange" | "ocre" | "vert" | "lagune";
  icone: NomIcone;
  titre: string;
  chiffre: string;
  detail: string;
  children?: React.ReactNode;
}) {
  return (
    <Link href={href} className={styles.tuile} data-teinte={teinte}>
      <span className={styles.tuileHaut}>
        <span className={styles.tuileIcone}>
          <Icone nom={icone} taille={17} />
        </span>
        <span className={styles.tuileTitre}>{titre}</span>
      </span>
      <span className={styles.tuileChiffre}>{chiffre}</span>
      <span className={styles.tuileDetail}>{detail}</span>
      {children}
    </Link>
  );
}

/** Accueil : un tableau de bord léger autour d'un seul geste — commencer une consultation. */
export default function HomePage() {
  const [cabinet] = useApi<Cabinet>("/me/cabinet");
  const [encounters] = useApi<Encounter[]>("/encounters");
  const [patients] = useApi<Patient[]>("/patients");
  const [journee] = useApi<Journee>(`/journee?jour=${aujourdhuiISO()}`);
  const [suggestions] = useApi<LearningSuggestion[]>(
    "/me/learning/suggestions",
  );
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
      const index = Math.floor(
        (quand(encounter).getTime() - lundi.getTime()) / 86_400_000,
      );
      if (index >= 0 && index < 7) compte[index] = (compte[index] ?? 0) + 1;
    }
    return compte;
  }, [toutes]);
  const totalSemaine = semaine.reduce((a, b) => a + b, 0);
  const maxJour = Math.max(1, ...semaine);
  const aujourdhuiIndex = (new Date().getDay() + 6) % 7;
  const traiteesSemaine = useMemo(() => {
    const lundi = debutDeSemaine();
    return toutes.filter(
      (e) =>
        quand(e) >= lundi && (e.status === "review" || TERMINEES.has(e.status)),
    ).length;
  }, [toutes]);

  // La journée Doctolib : combien de rendez-vous, et le prochain.
  const rendezvous =
    journee.state === "ready" && journee.data.disponible
      ? journee.data.rendezvous
      : [];
  const maintenant = new Date();
  const heureActuelle = `${String(maintenant.getHours()).padStart(2, "0")}:${String(maintenant.getMinutes()).padStart(2, "0")}`;
  const prochain = rendezvous.find((r) => r.heure >= heureActuelle);

  const trouves = useMemo(() => {
    const cherche = sansAccents(recherche.trim());
    if (!cherche) return [];
    const liste = patients.state === "ready" ? patients.data : [];
    return liste
      .filter((p) =>
        sansAccents(`${p.first_name} ${p.last_name}`).includes(cherche),
      )
      .slice(0, 6);
  }, [patients, recherche]);

  const propositions = suggestions.state === "ready" ? suggestions.data : [];
  const motsRetenus = glossaire.state === "ready" ? glossaire.data.length : 0;
  const praticien =
    cabinet.state === "ready"
      ? `${cabinet.data.practitioner_title} ${cabinet.data.practitioner_name.split(" ").slice(-1)[0]}`
      : "";

  return (
    <div className="page">
      <header className={styles.salut}>
        <div>
          <p className={styles.date}>
            {new Date().toLocaleDateString("fr-FR", {
              weekday: "long",
              day: "numeric",
              month: "long",
            })}
          </p>
          <h1 className={styles.bonjour}>
            {momentDuJour()}
            {praticien ? `, ${praticien}` : ""}
          </h1>
        </div>
        <div className={styles.recherche}>
          <Champ
            type="search"
            placeholder="Retrouver un patient"
            value={recherche}
            onChange={(event) => setRecherche(event.target.value)}
          />
        </div>
      </header>

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
                  titre={nomPatient(patient)}
                  detail={
                    patient.birth_date
                      ? `né(e) le ${formatDate(patient.birth_date)}`
                      : undefined
                  }
                />
              ))}
            </Lignes>
          )}
        </Carte>
      )}

      {/* Le cœur : le bouton au centre, quatre tuiles autour. */}
      <section className={styles.coeur}>
        <div className={styles.colonne}>
          <Tuile
            href="/consultations"
            teinte="orange"
            icone="documents"
            titre="À relire"
            chiffre={String(aRelire.length)}
            detail={
              aRelire.length === 0
                ? "rien n’attend, tout est à jour"
                : `compte${aRelire.length > 1 ? "s" : ""} rendu${aRelire.length > 1 ? "s" : ""} à valider`
            }
          />
          <Tuile
            href="/journee"
            teinte="ocre"
            icone="journee"
            titre="Votre journée"
            chiffre={
              journee.state === "ready" && journee.data.disponible
                ? String(rendezvous.length)
                : "—"
            }
            detail={
              journee.state === "ready" && !journee.data.disponible
                ? "agenda Doctolib pas encore lu"
                : prochain
                  ? `prochain à ${prochain.heure} · ${prochain.prenom} ${prochain.nom}`
                  : rendezvous.length
                    ? "plus de rendez-vous aujourd’hui"
                    : "aucun rendez-vous aujourd’hui"
            }
          />
        </div>

        <Link
          href="/consultations/nouvelle"
          className={styles.bouton}
          aria-label="Commencer une consultation"
        >
          <span className={styles.halo} aria-hidden="true" />
          <span className={styles.halo2} aria-hidden="true" />
          <span className={styles.disque}>
            <Symbole taille={92} />
          </span>
          <span className={styles.boutonTitre}>Commencer une consultation</span>
          <span className={styles.boutonSous}>
            Oris écoute. Le dossier sera prêt avant la fin du rendez-vous.
          </span>
        </Link>

        <div className={styles.colonne}>
          <Tuile
            href="/consultations"
            teinte="vert"
            icone="consultations"
            titre="Cette semaine"
            chiffre={String(totalSemaine)}
            detail={`consultation${totalSemaine > 1 ? "s" : ""} depuis lundi`}
          >
            <span className={styles.barres} aria-hidden="true">
              {semaine.map((n, i) => (
                <span
                  key={i}
                  className={`${styles.barre} ${i === aujourdhuiIndex ? styles.barreAujourdhui : ""}`}
                  style={{ height: `${Math.max(8, (n / maxJour) * 100)}%` }}
                  title={`${LETTRES[i]} : ${n}`}
                />
              ))}
            </span>
          </Tuile>
          <Tuile
            href="/consultations"
            teinte="lagune"
            icone="valide"
            titre="Saisie évitée"
            chiffre={dureeLisible(traiteesSemaine * MINUTES_PAR_COMPTE_RENDU)}
            detail={`estimation : ${MINUTES_PAR_COMPTE_RENDU} min par compte rendu`}
          />
        </div>
      </section>

      <div className={styles.bas}>
        <Carte
          titre="À relire"
          action={
            aRelire.length > 0 ? (
              <Pastille ton="attention">{aRelire.length}</Pastille>
            ) : null
          }
        >
          {encounters.state === "loading" && <Squelette lignes={3} />}
          {encounters.state === "error" && (
            <EtatVide titre={errorMessage(encounters.code)} />
          )}
          {encounters.state === "ready" && aRelire.length === 0 && (
            <EtatVide titre="Rien à relire" />
          )}
          {aRelire.length > 0 && (
            <Lignes>
              {aRelire.slice(0, 4).map((encounter) => (
                <Ligne
                  key={encounter.id}
                  href={`/consultations/${encounter.id}`}
                  compacte
                  titre={nomPatient(encounter.patient)}
                  fin={
                    <span className={styles.finRelire}>
                      {quand(encounter).toLocaleDateString("fr-FR", {
                        day: "numeric",
                        month: "short",
                      })}
                    </span>
                  }
                />
              ))}
            </Lignes>
          )}
        </Carte>

        <Carte
          titre="Oris apprend"
          action={
            propositions.length > 0 ? (
              <Pastille ton="attention">{propositions.length}</Pastille>
            ) : null
          }
        >
          {propositions.length === 0 ? (
            <p className={styles.doux}>
              Rien à proposer pour l’instant : Oris attend plusieurs corrections
              dans le même sens avant de suggérer une règle.
            </p>
          ) : (
            propositions.slice(0, 2).map((s) => (
              <p key={s.key} className={styles.doux}>
                {s.message}
              </p>
            ))
          )}
          <p className={styles.doux}>
            {motsRetenus === 0
              ? "Aucun mot"
              : `${motsRetenus} mot${motsRetenus > 1 ? "s" : ""}`}{" "}
            dans votre dictionnaire.{" "}
            <Link href="/apprentissage" className="link-button">
              Tout voir
            </Link>
          </p>
        </Carte>
      </div>
    </div>
  );
}
