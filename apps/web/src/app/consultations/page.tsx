"use client";

import { useMemo, useState } from "react";

import {
  Carte,
  Champ,
  EnTetePage,
  EtatVide,
  Ligne,
  Lignes,
  LienBouton,
  Onglets,
  Pastille,
  Squelette,
} from "@/components/ui";
import type { Encounter } from "@/lib/api";
import { DOCUMENT_TYPE, ENCOUNTER_STATUS, errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

type Filtre = "toutes" | "a_relire" | "terminees" | "a_reprendre";

const EN_ECOUTE = new Set(["draft", "recording", "paused"]);
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

function jour(encounter: Encounter): string {
  return (encounter.started_at ?? encounter.created_at).slice(0, 10);
}

function titreDuJour(iso: string): string {
  const aujourdhui = new Date().toISOString().slice(0, 10);
  const hier = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);
  if (iso === aujourdhui) return "Aujourd’hui";
  if (iso === hier) return "Hier";
  return new Date(iso).toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

function heure(encounter: Encounter): string {
  return new Date(encounter.started_at ?? encounter.created_at).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Toutes les consultations, groupées par jour : on retrouve sa journée d'un coup d'œil. */
export default function ConsultationsPage() {
  const [encounters] = useApi<Encounter[]>("/encounters");
  const [filtre, setFiltre] = useState<Filtre>("toutes");
  const [recherche, setRecherche] = useState("");

  const groupes = useMemo(() => {
    const toutes = encounters.state === "ready" ? encounters.data : [];
    const retenues = toutes
      .filter((encounter) => {
        if (filtre === "a_relire") return encounter.status === "review";
        if (filtre === "terminees") return TERMINEES.has(encounter.status);
        if (filtre === "a_reprendre") return EN_ECHEC.has(encounter.status);
        return true;
      })
      .filter((encounter) => {
        const nom = `${encounter.patient.first_name} ${encounter.patient.last_name}`.toLowerCase();
        return recherche.trim() ? nom.includes(recherche.trim().toLowerCase()) : true;
      });

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
        action={<LienBouton href="/consultations/nouvelle">Nouvelle consultation</LienBouton>}
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

      {groupes.map(([date, liste]) => (
        <Carte key={date} titre={titreDuJour(date)} action={<span className="muted">{liste.length}</span>}>
          <Lignes>
            {liste.map((encounter) => (
              <Ligne
                key={encounter.id}
                href={
                  EN_ECOUTE.has(encounter.status)
                    ? `/consultations/${encounter.id}/ecoute`
                    : `/consultations/${encounter.id}`
                }
                titre={`${encounter.patient.first_name} ${encounter.patient.last_name}`}
                detail={
                  <>
                    <time>{heure(encounter)}</time>
                    {encounter.documents.length > 0 && (
                      <>
                        {" · "}
                        {encounter.documents
                          .map((document) => DOCUMENT_TYPE[document.document_type])
                          .join(", ")}
                      </>
                    )}
                    {encounter.mode === "shadow" && " · mode ombre"}
                  </>
                }
                fin={
                  <Pastille ton={ton(encounter.status)}>
                    {ENCOUNTER_STATUS[encounter.status]}
                  </Pastille>
                }
              />
            ))}
          </Lignes>
        </Carte>
      ))}

      {total > 0 && (
        <p className="muted" style={{ margin: 0 }}>
          {total} consultation{total > 1 ? "s" : ""} · les dates sont celles du début de
          l’écoute.
        </p>
      )}
    </div>
  );
}
