"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { TypeDocument } from "@/components/documents/TypeDocument";
import { Icone } from "@/components/Icones";
import { JetonPraticien } from "@/components/JetonPraticien";
import { NouvelleConsultationLien } from "@/components/patients/CommencerConsultation";
import {
  Carte,
  Champ,
  EnTetePage,
  EtatVide,
  Onglets,
  Pastille,
  Squelette,
} from "@/components/ui";
import { aujourdhuiISO, enISO, jourDecale } from "@/app/journee/dates";
import type { Encounter } from "@/lib/api";
import { ENCOUNTER_STATUS, errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./consultations.module.css";

type Filtre = "toutes" | "a_relire" | "terminees" | "a_reprendre";

const EN_ECOUTE = new Set(["draft", "recording", "paused"]);
const EN_COURS = new Set(["recording", "paused", "finalizing", "processing"]);
const TERMINEES = new Set(["validated", "exported", "archived"]);
const EN_ECHEC = new Set([
  "transcription_failed",
  "generation_failed",
  "audio_error",
  "upload_interrupted",
]);

function ton(statut: string): "neutre" | "attention" | "valide" | "alerte" {
  if (statut === "review") return "attention";
  if (TERMINEES.has(statut)) return "valide";
  if (EN_ECHEC.has(statut)) return "alerte";
  return "neutre";
}

function moment(encounter: Encounter): Date {
  return new Date(encounter.started_at ?? encounter.created_at);
}

/** Le jour en heure locale : `toISOString` renverrait la veille après minuit. */
function jour(encounter: Encounter): string {
  return enISO(moment(encounter));
}

function heure(encounter: Encounter): string {
  return moment(encounter).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** « Aujourd'hui » en gros, la date exacte à côté : on cherche d'abord un jour relatif. */
function Bandeau({ iso, nombre }: { iso: string; nombre: number }) {
  const aujourdhui = aujourdhuiISO();
  const relatif =
    iso === aujourdhui
      ? "Aujourd’hui"
      : iso === jourDecale(aujourdhui, -1)
        ? "Hier"
        : null;
  const date = new Date(`${iso}T12:00:00`).toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: iso.slice(0, 4) === aujourdhui.slice(0, 4) ? undefined : "numeric",
  });
  return (
    <h2 className={styles.bandeau}>
      <span className={styles.relatif}>{relatif ?? date}</span>
      {relatif && <span className={styles.dateExacte}>{date}</span>}
      <span className={styles.filet} aria-hidden="true" />
      <span className={styles.nombre}>
        {nombre} consultation{nombre > 1 ? "s" : ""}
      </span>
    </h2>
  );
}

/** À qui les documents sont partis, d'après ce que le praticien a noté. */
function Envoi({ encounter }: { encounter: Encounter }) {
  const destinataires = [
    ...new Set(encounter.documents.flatMap((d) => d.sent_to ?? [])),
  ];
  if (destinataires.length > 0) {
    return (
      <span
        className={styles.envoye}
        title={`Envoyé à ${destinataires.join(", ")}`}
      >
        <Icone nom="envoi" taille={14} />
        <span className={styles.coupe}>
          Envoyé à {destinataires.join(", ")}
        </span>
      </span>
    );
  }
  if (encounter.documents.length === 0 || EN_COURS.has(encounter.status)) {
    return <span className={styles.rien}>—</span>;
  }
  return <span className={styles.rien}>Pas encore envoyé</span>;
}

function Rangee({ encounter }: { encounter: Encounter }) {
  const documents = encounter.documents.filter(
    (d) => d.status !== "superseded",
  );
  return (
    <Link
      href={
        EN_ECOUTE.has(encounter.status)
          ? `/consultations/${encounter.id}/ecoute`
          : `/consultations/${encounter.id}`
      }
      className={styles.rangee}
    >
      <time className={styles.heure}>{heure(encounter)}</time>
      {/* Le praticien juste après l'heure : à gauche, rien ne le pousse, et les
          vignettes restent alignées quelle que soit la longueur du statut. */}
      <span className={styles.praticien}>
        <JetonPraticien
          nom={encounter.practitioner.name}
          titre={encounter.practitioner.title}
          taille="petit"
        />
      </span>
      <span className={styles.qui}>
        <span className={styles.nom}>
          {encounter.patient.last_name.toLocaleUpperCase("fr-FR")}{" "}
          <span className={styles.prenom}>{encounter.patient.first_name}</span>
        </span>
        <span className={styles.documents}>
          {documents.map((d) => (
            <TypeDocument
              key={d.id}
              type={d.document_type}
              valide={d.status === "validated" || d.status === "exported"}
              taille="petit"
            />
          ))}
          {encounter.mode === "shadow" && (
            <span className={styles.ombre}>mode ombre</span>
          )}
        </span>
      </span>
      <Envoi encounter={encounter} />
      <span className={styles.statut}>
        <Pastille ton={ton(encounter.status)}>
          {ENCOUNTER_STATUS[encounter.status]}
        </Pastille>
      </span>
      <Icone nom="suivant" taille={14} className={styles.chevron} />
    </Link>
  );
}

/** Toutes les consultations, jour par jour : on retrouve sa journée d'un coup d'œil. */
export default function ConsultationsPage() {
  const [encounters] = useApi<Encounter[]>("/encounters");
  const [filtre, setFiltre] = useState<Filtre>("toutes");
  const [recherche, setRecherche] = useState("");

  const groupes = useMemo(() => {
    const toutes = encounters.state === "ready" ? encounters.data : [];
    const cherche = recherche.trim().toLowerCase();
    const retenues = toutes
      .filter((encounter) => {
        if (filtre === "a_relire") return encounter.status === "review";
        if (filtre === "terminees") return TERMINEES.has(encounter.status);
        if (filtre === "a_reprendre") return EN_ECHEC.has(encounter.status);
        return true;
      })
      .filter((encounter) => {
        const nom =
          `${encounter.patient.first_name} ${encounter.patient.last_name}`.toLowerCase();
        return cherche ? nom.includes(cherche) : true;
      })
      .sort((a, b) => moment(b).getTime() - moment(a).getTime());

    const parJour = new Map<string, Encounter[]>();
    for (const encounter of retenues) {
      const cle = jour(encounter);
      parJour.set(cle, [...(parJour.get(cle) ?? []), encounter]);
    }
    return [...parJour.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  }, [encounters, filtre, recherche]);

  const total = groupes.reduce((somme, [, liste]) => somme + liste.length, 0);

  return (
    <div className="page">
      <EnTetePage
        surTitre="Historique"
        titre="Consultations"
        action={<NouvelleConsultationLien />}
      />

      <div className="barre-filtres">
        <Onglets
          valeur={filtre}
          onChange={setFiltre}
          options={[
            { valeur: "toutes", libelle: "Toutes" },
            { valeur: "a_relire", libelle: "À relire" },
            { valeur: "terminees", libelle: "Terminées" },
            { valeur: "a_reprendre", libelle: "À reprendre" },
          ]}
        />
        <Champ
          type="search"
          value={recherche}
          placeholder="Rechercher un patient…"
          aria-label="Rechercher un patient"
          style={{ width: 240 }}
          onChange={(event) => setRecherche(event.target.value)}
        />
      </div>

      {encounters.state === "loading" && (
        <Carte>
          <Squelette lignes={5} />
        </Carte>
      )}
      {encounters.state === "error" && (
        <Carte>
          <EtatVide titre={errorMessage(encounters.code)} />
        </Carte>
      )}
      {encounters.state === "ready" && total === 0 && (
        <Carte>
          <EtatVide titre="Aucune consultation">
            {recherche || filtre !== "toutes"
              ? "Aucune consultation ne correspond à ce filtre."
              : "Démarrez-en une : Oris écoute et prépare le compte rendu."}
          </EtatVide>
        </Carte>
      )}

      <div className={styles.jours}>
        {groupes.map(([date, liste]) => (
          <section key={date} className={styles.jour}>
            <Bandeau iso={date} nombre={liste.length} />
            <div className={styles.liste}>
              {liste.map((encounter) => (
                <Rangee key={encounter.id} encounter={encounter} />
              ))}
            </div>
          </section>
        ))}
      </div>

      {total > 0 && (
        <p className="muted" style={{ margin: 0 }}>
          {total} consultation{total > 1 ? "s" : ""} · l’heure est celle du
          début de l’écoute.
        </p>
      )}
    </div>
  );
}
