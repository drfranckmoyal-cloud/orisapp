"use client";

import { useMemo, useState } from "react";

import {
  Carte,
  Champ,
  EnTetePage,
  EtatVide,
  Ligne,
  Lignes,
  Onglets,
  Pastille,
  Squelette,
} from "@/components/ui";
import type { Encounter } from "@/lib/api";
import { DOCUMENT_TYPE, errorMessage, formatDateTime } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

type Filtre = "tous" | "consultation_note" | "treatment_plan_text" | "operative_note";

const ETAT_DOCUMENT: Record<string, { mot: string; ton: "neutre" | "valide" | "attention" }> = {
  draft_ai: { mot: "brouillon", ton: "neutre" },
  needs_review: { mot: "à vérifier", ton: "attention" },
  validated: { mot: "validé", ton: "valide" },
  exported: { mot: "exporté", ton: "valide" },
  outdated: { mot: "périmé", ton: "attention" },
  superseded: { mot: "remplacé", ton: "neutre" },
};

/** Tous les documents produits, par type et par patient. */
export default function DocumentsPage() {
  const [encounters] = useApi<Encounter[]>("/encounters");
  const [filtre, setFiltre] = useState<Filtre>("tous");
  const [recherche, setRecherche] = useState("");

  const documents = useMemo(() => {
    const consultations = encounters.state === "ready" ? encounters.data : [];
    return consultations
      .flatMap((encounter) =>
        encounter.documents
          .filter((document) => document.status !== "superseded")
          .map((document) => ({
            ...document,
            encounter,
            patient: `${encounter.patient.first_name} ${encounter.patient.last_name}`,
            quand: encounter.started_at ?? encounter.created_at,
          })),
      )
      .filter((document) => filtre === "tous" || document.document_type === filtre)
      .filter((document) =>
        recherche.trim()
          ? document.patient.toLowerCase().includes(recherche.trim().toLowerCase())
          : true,
      )
      .sort((a, b) => b.quand.localeCompare(a.quand));
  }, [encounters, filtre, recherche]);

  return (
    <div className="page">
      <EnTetePage surTitre="Historique" titre="Documents" />

      <Onglets
        valeur={filtre}
        onChange={setFiltre}
        options={[
          { valeur: "tous", libelle: "Tous" },
          { valeur: "consultation_note", libelle: "Comptes rendus" },
          { valeur: "treatment_plan_text", libelle: "Plans de traitement" },
          { valeur: "operative_note", libelle: "Comptes rendus de soins" },
        ]}
      />

      <Carte
        titre={`${documents.length} document${documents.length > 1 ? "s" : ""}`}
        action={
          <Champ
            type="search"
            value={recherche}
            placeholder="Rechercher un patient…"
            aria-label="Rechercher un patient"
            style={{ width: 240 }}
            onChange={(event) => setRecherche(event.target.value)}
          />
        }
      >
        {encounters.state === "loading" && <Squelette lignes={4} />}
        {encounters.state === "error" && <EtatVide titre={errorMessage(encounters.code)} />}
        {encounters.state === "ready" && documents.length === 0 && (
          <EtatVide titre="Aucun document">
            Les comptes rendus apparaissent ici dès qu’une consultation est traitée.
          </EtatVide>
        )}
        {documents.length > 0 && (
          <Lignes>
            {documents.map((document) => (
              <Ligne
                key={document.id}
                href={`/consultations/${document.encounter.id}`}
                titre={`${DOCUMENT_TYPE[document.document_type]} — ${document.patient}`}
                detail={formatDateTime(document.quand)}
                fin={
                  <Pastille ton={ETAT_DOCUMENT[document.status]?.ton ?? "neutre"}>
                    {ETAT_DOCUMENT[document.status]?.mot ?? document.status}
                  </Pastille>
                }
              />
            ))}
          </Lignes>
        )}
      </Carte>
    </div>
  );
}
