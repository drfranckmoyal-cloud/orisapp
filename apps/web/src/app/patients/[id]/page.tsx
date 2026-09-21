"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useState } from "react";

import {
  Carte,
  EnTetePage,
  EtatVide,
  Onglets,
  Pastille,
  Squelette,
} from "@/components/ui";
import { Icone } from "@/components/Icones";
import { JetonPraticien } from "@/components/JetonPraticien";
import { CommencerConsultation } from "@/components/patients/CommencerConsultation";
import { Correspondants } from "@/components/patients/Correspondants";
import { NoteDictee } from "@/components/patients/NoteDictee";
import { DocumentsValides } from "@/components/patients/DocumentsValides";
import { PiecesJointes } from "@/components/patients/PiecesJointes";
import { SmileCloud } from "@/components/patients/SmileCloud";
import {
  apiRequest,
  type ClientConfig,
  type Encounter,
  type Patient,
} from "@/lib/api";
import {
  DOCUMENT_TYPE,
  ENCOUNTER_STATUS,
  errorMessage,
  formatDate,
  formatDateTime,
  nomPatient,
} from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./fiche.module.css";

type Onglet = "consultations" | "documents" | "pieces";

const TERMINEES = new Set(["validated", "exported", "archived"]);

function tonStatut(
  statut: string,
): "neutre" | "attention" | "valide" | "alerte" {
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
  if (mois < 0 || (mois === 0 && maintenant.getDate() < jour.getDate()))
    ans -= 1;
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
  const [config] = useApi<ClientConfig>("/config/client");
  const [onglet, setOnglet] = useState<Onglet>("consultations");
  // Les fichiers rapatriés de SmileCloud rechargent la liste des pièces jointes.
  const [versionPieces, setVersionPieces] = useState(0);
  const rafraichirPieces = useCallback(() => setVersionPieces((v) => v + 1), []);
  const smilecloud =
    config.state === "ready" && config.data.smilecloud_connected;
  const [note, setNote] = useState<string | null>(null);

  const consultations = encounters.state === "ready" ? encounters.data : [];
  const validesCount = consultations
    .flatMap((e) => e.documents)
    .filter((d) => d.status === "validated" || d.status === "exported").length;

  /** Le champ de note rapporte lui-même l'échec : on le laisse remonter. */
  async function enregistrerNote(valeur: string) {
    await apiRequest<Patient>(`/patients/${id}`, {
      method: "PATCH",
      body: { note: valeur.trim() },
    });
    rechargerPatient();
  }

  if (patient.state === "error")
    return <p className="muted">{errorMessage(patient.code)}</p>;

  const fiche = patient.state === "ready" ? patient.data : null;
  const valeurNote = note ?? fiche?.note ?? "";

  return (
    <div className="page">
      <div>
        <Link href="/patients" className={styles.retour}>
          <Icone nom="retour" taille={16} />
          Tous les patients
        </Link>
      </div>
      <EnTetePage
        surTitre="Patient"
        titre={
          fiche ? (
            <span className={styles.nomPatient}>
              {nomPatient(fiche)}
              {fiche.birth_date && (
                <span className={styles.age}> ({age(fiche.birth_date)})</span>
              )}
            </span>
          ) : (
            "Chargement…"
          )
        }
        action={<CommencerConsultation patientId={id} />}
      />

      <Carte titre="Informations" bords className={styles.carteInfos}>
        {patient.state === "loading" && (
          <div style={{ padding: "var(--espace-6)" }}>
            <Squelette lignes={4} />
          </div>
        )}
        {fiche && (
          <div className={styles.cadre}>
            {/* Une information par ligne, dans l'ordre où on les cherche. */}
            <Info cle="Nom">{nomPatient(fiche)}</Info>
            <Info cle="Courriel">
              {fiche.email ? (
                <a href={`mailto:${fiche.email}`} className="link-button">
                  {fiche.email}
                </a>
              ) : (
                <Absent quoi="non renseigné" />
              )}
            </Info>
            <Info cle="Date de naissance">
              {fiche.birth_date ? (
                formatDate(fiche.birth_date)
              ) : (
                <Absent quoi="non renseignée" />
              )}
            </Info>

            <Info cle="Correspondants">
              <Correspondants patientId={id} />
            </Info>
            <Info cle="SmileCloud">
              <Pastille ton={smilecloud ? "valide" : "attention"} point>
                {smilecloud ? "connecté" : "non connecté"}
              </Pastille>
            </Info>

            <Info cle="Note">
              <NoteDictee
                patientId={id}
                valeur={valeurNote}
                onChange={setNote}
                onEnregistrer={enregistrerNote}
                initiale={fiche.note ?? ""}
              />
            </Info>
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
            libelle: `Documents validés${validesCount ? ` (${validesCount})` : ""}`,
          },
          { valeur: "pieces", libelle: "Documentation / Pièces jointes" },
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
                  <Link
                    href={`/consultations/${encounter.id}`}
                    className={styles.rangLien}
                  >
                    <span className={styles.rangTitre}>
                      {formatDateTime(
                        encounter.started_at ?? encounter.created_at,
                      )}
                    </span>
                    <span className={styles.rangDetail}>
                      {encounter.documents.length === 0
                        ? "aucun document"
                        : encounter.documents
                            .map(
                              (document) =>
                                DOCUMENT_TYPE[document.document_type],
                            )
                            .join(" · ")}
                    </span>
                  </Link>
                  <span className={styles.rangFin}>
                    <JetonPraticien
                      nom={encounter.practitioner.name}
                      titre={encounter.practitioner.title}
                      taille="petit"
                    />
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
          <DocumentsValides consultations={consultations} />
        </Carte>
      )}

      {onglet === "pieces" && (
        <Carte bords>
          <SmileCloud patientId={id} rapatries={rafraichirPieces} />
          <PiecesJointes key={versionPieces} patientId={id} />
        </Carte>
      )}
    </div>
  );
}
