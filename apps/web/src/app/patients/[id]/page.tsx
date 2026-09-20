"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import {
  Carte,
  EnTetePage,
  EtatVide,
  Ligne,
  Lignes,
  LienBouton,
  Onglets,
  Pastille,
  Squelette,
} from "@/components/ui";
import { NoteAdministrative } from "@/components/patients/NoteAdministrative";
import type { ClinicalObjectView, Encounter, Patient } from "@/lib/api";
import {
  DOCUMENT_TYPE,
  ENCOUNTER_STATUS,
  PLAN_STATUS,
  errorMessage,
  formatDate,
  formatDateTime,
} from "@/lib/labels";
import { useApi } from "@/lib/useApi";

type Onglet = "consultations" | "documents" | "plan";

const TERMINEES = new Set(["validated", "exported", "archived"]);

function tonStatut(statut: string): "neutre" | "attention" | "valide" | "alerte" {
  if (statut === "review") return "attention";
  if (TERMINEES.has(statut)) return "valide";
  if (statut.includes("failed") || statut.includes("error")) return "alerte";
  return "neutre";
}

/** Fiche patient : la continuité entre les consultations (§9, votre cahier). */
export default function PatientPage() {
  const { id } = useParams<{ id: string }>();
  const [patient, rechargerPatient] = useApi<Patient>(`/patients/${id}`);
  const [encounters] = useApi<Encounter[]>(`/encounters?patient_id=${id}`);
  const [onglet, setOnglet] = useState<Onglet>("consultations");

  const consultations = encounters.state === "ready" ? encounters.data : [];
  const derniere = consultations.find((encounter) => encounter.documents.length > 0);
  const [clinique] = useApi<ClinicalObjectView>(
    derniere ? `/encounters/${derniere.id}/clinical-object` : null,
  );
  const plan = clinique.state === "ready" ? clinique.data.clinical_object.treatment_plan : null;
  const documents = consultations.flatMap((encounter) =>
    encounter.documents.map((document) => ({ ...document, encounter })),
  );

  if (patient.state === "error") return <p className="muted">{errorMessage(patient.code)}</p>;

  return (
    <div className="page">
      <EnTetePage
        surTitre="Patient"
        titre={
          patient.state === "ready"
            ? `${patient.data.first_name} ${patient.data.last_name}`
            : "Chargement…"
        }
        action={
          <LienBouton href={`/consultations/nouvelle?patient=${id}`}>
            Nouvelle consultation
          </LienBouton>
        }
      />

      {patient.state === "ready" && (
        <div className="bandeau-identite">
          <span>
            {patient.data.birth_date
              ? `Né(e) le ${formatDate(patient.data.birth_date)}`
              : "Date de naissance non renseignée"}
          </span>
          {patient.data.external_id && <span>Dossier {patient.data.external_id}</span>}
          <span>
            {consultations.length === 0
              ? "Aucune consultation"
              : `${consultations.length} consultation${consultations.length > 1 ? "s" : ""}`}
          </span>
        </div>
      )}

      {patient.state === "ready" && (
        <NoteAdministrative patient={patient.data} onSaved={rechargerPatient} />
      )}

      <Onglets
        valeur={onglet}
        onChange={setOnglet}
        options={[
          { valeur: "consultations", libelle: "Consultations" },
          { valeur: "documents", libelle: `Documents${documents.length ? ` (${documents.length})` : ""}` },
          { valeur: "plan", libelle: "Plan de traitement" },
        ]}
      />

      {onglet === "consultations" && (
        <Carte titre="Historique">
          {encounters.state === "loading" && <Squelette lignes={3} />}
          {consultations.length === 0 && encounters.state === "ready" && (
            <EtatVide titre="Aucune consultation">
              Démarrez la première : Oris écoute et prépare le compte rendu.
            </EtatVide>
          )}
          {consultations.length > 0 && (
            <Lignes>
              {consultations.map((encounter) => (
                <Ligne
                  key={encounter.id}
                  href={`/consultations/${encounter.id}`}
                  titre={formatDateTime(encounter.started_at ?? encounter.created_at)}
                  detail={
                    encounter.documents.length === 0
                      ? "aucun document"
                      : encounter.documents
                          .map((document) => DOCUMENT_TYPE[document.document_type])
                          .join(" · ")
                  }
                  fin={
                    <Pastille ton={tonStatut(encounter.status)}>
                      {ENCOUNTER_STATUS[encounter.status]}
                    </Pastille>
                  }
                />
              ))}
            </Lignes>
          )}
        </Carte>
      )}

      {onglet === "documents" && (
        <Carte titre="Documents">
          {documents.length === 0 && (
            <EtatVide titre="Aucun document">
              Les comptes rendus apparaissent ici dès la première consultation traitée.
            </EtatVide>
          )}
          {documents.length > 0 && (
            <Lignes>
              {documents.map((document) => (
                <Ligne
                  key={document.id}
                  href={`/consultations/${document.encounter.id}`}
                  titre={DOCUMENT_TYPE[document.document_type]}
                  detail={formatDateTime(
                    document.encounter.started_at ?? document.encounter.created_at,
                  )}
                  fin={
                    <Pastille ton={document.status === "validated" ? "valide" : "neutre"}>
                      {document.status === "validated" ? "validé" : "brouillon"}
                    </Pastille>
                  }
                />
              ))}
            </Lignes>
          )}
        </Carte>
      )}

      {onglet === "plan" && (
        <Carte
          titre="Plan de traitement en cours"
          action={
            derniere ? (
              <Link href={`/consultations/${derniere.id}`} className="lien">
                Voir la consultation
              </Link>
            ) : null
          }
        >
          {!plan && <EtatVide titre="Aucun plan de traitement" />}
          {plan?.items.map((item) => (
            <div key={item.item_id} className="ligne-plan">
              <span>
                {item.teeth.length > 0 && <Pastille>dent {item.teeth.join(", ")}</Pastille>}{" "}
                <strong>{item.action}</strong>
              </span>
              <Pastille ton={item.status === "completed" ? "valide" : "neutre"}>
                {PLAN_STATUS[item.status]}
              </Pastille>
            </div>
          ))}
        </Carte>
      )}
    </div>
  );
}
