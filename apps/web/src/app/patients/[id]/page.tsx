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
import { ApiError, apiRequest, type Encounter, type Patient } from "@/lib/api";
import {
  DOCUMENT_TYPE,
  ENCOUNTER_STATUS,
  errorMessage,
  formatDate,
  formatDateTime,
} from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./fiche.module.css";

type Onglet = "consultations" | "documents";

const TERMINEES = new Set(["validated", "exported", "archived"]);
const NOTE_MAX = 500;

function tonStatut(statut: string): "neutre" | "attention" | "valide" | "alerte" {
  if (statut === "review") return "attention";
  if (TERMINEES.has(statut)) return "valide";
  if (statut.includes("failed") || statut.includes("error")) return "alerte";
  return "neutre";
}

function age(naissance: string): string {
  const jour = new Date(naissance);
  const maintenant = new Date();
  let ans = maintenant.getFullYear() - jour.getFullYear();
  const mois = maintenant.getMonth() - jour.getMonth();
  if (mois < 0 || (mois === 0 && maintenant.getDate() < jour.getDate())) ans -= 1;
  return `${ans} ans`;
}

function Info({ cle, children }: { cle: string; children: React.ReactNode }) {
  return (
    <div className={styles.ligne}>
      <span className={styles.cle}>{cle}</span>
      <span className={styles.valeur}>{children}</span>
    </div>
  );
}

function Absent({ quoi }: { quoi: string }) {
  return <span className={styles.vide}>{quoi}</span>;
}

/** Fiche patient : qui il est, et tout ce qui s'est passé (§9). */
export default function PatientPage() {
  const { id } = useParams<{ id: string }>();
  const [patient, rechargerPatient] = useApi<Patient>(`/patients/${id}`);
  const [encounters] = useApi<Encounter[]>(`/encounters?patient_id=${id}`);
  const [onglet, setOnglet] = useState<Onglet>("consultations");
  const [note, setNote] = useState<string | null>(null);
  const [etatNote, setEtatNote] = useState<string | null>(null);

  const consultations = encounters.state === "ready" ? encounters.data : [];
  const documents = consultations.flatMap((encounter) =>
    encounter.documents.map((document) => ({ ...document, encounter })),
  );
  const derniere = consultations[0];

  async function enregistrerNote(valeur: string) {
    setEtatNote(null);
    try {
      await apiRequest<Patient>(`/patients/${id}`, {
        method: "PATCH",
        body: { note: valeur.trim() },
      });
      setEtatNote("enregistrée");
      rechargerPatient();
    } catch (error) {
      setEtatNote(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
  }

  if (patient.state === "error") return <p className="muted">{errorMessage(patient.code)}</p>;

  const fiche = patient.state === "ready" ? patient.data : null;
  const valeurNote = note ?? fiche?.note ?? "";

  return (
    <div className="page">
      <EnTetePage
        surTitre="Patient"
        titre={fiche ? `${fiche.first_name} ${fiche.last_name}` : "Chargement…"}
        action={
          <LienBouton href={`/consultations/nouvelle?patient=${id}`}>
            Nouvelle consultation
          </LienBouton>
        }
      />

      <Carte titre="Informations" bords>
        {patient.state === "loading" && (
          <div style={{ padding: "var(--espace-6)" }}>
            <Squelette lignes={4} />
          </div>
        )}
        {fiche && (
          <div className={styles.cadre}>
            <div className={styles.colonne}>
              <Info cle="Nom">
                {fiche.first_name} {fiche.last_name}
              </Info>
              <Info cle="Naissance">
                {fiche.birth_date ? (
                  <>
                    {formatDate(fiche.birth_date)} · {age(fiche.birth_date)}
                  </>
                ) : (
                  <Absent quoi="non renseignée" />
                )}
              </Info>
              <Info cle="Dossier">
                {fiche.external_id || <Absent quoi="aucun identifiant externe" />}
              </Info>
              <Info cle="Correspondants">
                {/* Le rattachement à un correspondant viendra avec l'écran dédié. */}
                <Absent quoi="aucun — à venir" />
              </Info>
            </div>

            <div className={styles.colonne}>
              <Info cle="Consultations">
                {consultations.length === 0
                  ? "aucune"
                  : consultations.length === 1
                    ? "1 consultation"
                    : `${consultations.length} consultations`}
              </Info>
              <Info cle="Dernière">
                {derniere ? (
                  <Link href={`/consultations/${derniere.id}`} className="link-button">
                    {formatDateTime(derniere.started_at ?? derniere.created_at)}
                  </Link>
                ) : (
                  <Absent quoi="jamais vue" />
                )}
              </Info>
              <Info cle="Suivi depuis">{formatDate(fiche.created_at)}</Info>
              <Info cle="Note">
                <textarea
                  className={styles.note}
                  rows={2}
                  maxLength={NOTE_MAX}
                  placeholder="Rappel pratique — horaires, rappel à passer…"
                  aria-label="Note administrative"
                  value={valeurNote}
                  onChange={(event) => setNote(event.target.value)}
                  onBlur={(event) => {
                    if (event.target.value.trim() !== (fiche.note ?? "").trim()) {
                      void enregistrerNote(event.target.value);
                    }
                  }}
                />
                <span className={styles.noteBas}>
                  <span>Oris ne la lit pas. Enregistrée en quittant le champ.</span>
                  {etatNote && <span>{etatNote}</span>}
                </span>
              </Info>
            </div>
          </div>
        )}
      </Carte>

      <Onglets
        valeur={onglet}
        onChange={setOnglet}
        options={[
          {
            valeur: "consultations",
            libelle: `Historique${consultations.length ? ` (${consultations.length})` : ""}`,
          },
          {
            valeur: "documents",
            libelle: `Documents${documents.length ? ` (${documents.length})` : ""}`,
          },
        ]}
      />

      {onglet === "consultations" && (
        <Carte bords>
          {encounters.state === "loading" && (
            <div style={{ padding: "var(--espace-6)" }}>
              <Squelette lignes={3} />
            </div>
          )}
          {consultations.length === 0 && encounters.state === "ready" && (
            <div style={{ padding: "var(--espace-6)" }}>
              <EtatVide titre="Aucune consultation">
                Démarrez la première : Oris écoute et prépare le compte rendu.
              </EtatVide>
            </div>
          )}
          {consultations.length > 0 && (
            <div className={styles.rangs}>
              {consultations.map((encounter) => (
                <div key={encounter.id} className={styles.rang}>
                  <Link href={`/consultations/${encounter.id}`} className={styles.rangLien}>
                    <span className={styles.rangTitre}>
                      {formatDateTime(encounter.started_at ?? encounter.created_at)}
                    </span>
                    <span className={styles.rangDetail}>
                      {encounter.documents.length === 0
                        ? "aucun document"
                        : encounter.documents
                            .map((document) => DOCUMENT_TYPE[document.document_type])
                            .join(" · ")}
                    </span>
                  </Link>
                  <span className={styles.rangFin}>
                    {/* Le brut reste accessible, sans jamais attirer l'œil. */}
                    <Link
                      href={`/consultations/${encounter.id}/transcription`}
                      className={styles.brut}
                    >
                      transcription brute
                    </Link>
                    <Pastille ton={tonStatut(encounter.status)}>
                      {ENCOUNTER_STATUS[encounter.status]}
                    </Pastille>
                  </span>
                </div>
              ))}
            </div>
          )}
        </Carte>
      )}

      {onglet === "documents" && (
        <Carte bords>
          {documents.length === 0 && (
            <div style={{ padding: "var(--espace-6)" }}>
              <EtatVide titre="Aucun document">
                Les comptes rendus apparaissent ici dès la première consultation traitée.
              </EtatVide>
            </div>
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
    </div>
  );
}
