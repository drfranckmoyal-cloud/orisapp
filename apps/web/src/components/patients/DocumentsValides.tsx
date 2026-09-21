"use client";

import Link from "next/link";
import { useState } from "react";

import { TypeDocument } from "@/components/documents/TypeDocument";
import { Icone } from "@/components/Icones";
import { EtatVide } from "@/components/ui";
import { ApiError, type Encounter, fetchDocumentExport } from "@/lib/api";
import { errorMessage, formatDate } from "@/lib/labels";

import styles from "./documentsValides.module.css";

type Ligne = {
  id: string;
  type: Encounter["documents"][number]["document_type"];
  quand: string;
  consultation: string;
  envoyeA: string[];
};

/** Les documents validés du patient, toutes consultations confondues, à télécharger.
 *
 * Seuls les documents validés y figurent : un brouillon n'a pas sa place dans le dossier.
 */
export function DocumentsValides({
  consultations,
}: {
  consultations: Encounter[];
}) {
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState<string | null>(null);

  const lignes: Ligne[] = consultations
    .flatMap((encounter) =>
      encounter.documents
        .filter((d) => d.status === "validated" || d.status === "exported")
        .map((d) => ({
          id: d.id,
          type: d.document_type,
          quand: encounter.started_at ?? encounter.created_at,
          consultation: encounter.id,
          envoyeA: d.sent_to ?? [],
        })),
    )
    .sort((a, b) => b.quand.localeCompare(a.quand));

  async function telecharger(ligne: Ligne) {
    setErreur(null);
    setEnCours(ligne.id);
    try {
      const { blob, filename } = await fetchDocumentExport(ligne.id, "pdf");
      const url = URL.createObjectURL(blob);
      const lien = window.document.createElement("a");
      lien.href = url;
      lien.download = filename;
      lien.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setErreur(
        errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"),
      );
    } finally {
      setEnCours(null);
    }
  }

  if (lignes.length === 0) {
    return (
      <div style={{ padding: "var(--espace-6)" }}>
        <EtatVide titre="Aucun document validé">
          Un document apparaît ici dès que vous l’avez validé dans sa
          consultation.
        </EtatVide>
      </div>
    );
  }

  return (
    <div>
      <ul className={styles.liste}>
        {lignes.map((ligne) => (
          <li key={ligne.id} className={styles.ligne}>
            <TypeDocument type={ligne.type} valide />
            <span className={styles.quand}>{formatDate(ligne.quand)}</span>
            <span className={styles.envoi}>
              {ligne.envoyeA.length > 0 ? (
                <>
                  <Icone nom="envoi" taille={13} /> Envoyé à{" "}
                  {ligne.envoyeA.join(", ")}
                </>
              ) : (
                "Pas encore envoyé"
              )}
            </span>
            <span className={styles.actions}>
              <Link
                href={`/consultations/${ligne.consultation}`}
                className={styles.ouvrir}
              >
                Ouvrir
              </Link>
              <button
                type="button"
                className={styles.telecharger}
                disabled={enCours === ligne.id}
                onClick={() => void telecharger(ligne)}
              >
                {enCours === ligne.id ? "…" : "Télécharger le PDF"}
              </button>
            </span>
          </li>
        ))}
      </ul>
      {erreur && <p className={styles.erreur}>{erreur}</p>}
    </div>
  );
}
