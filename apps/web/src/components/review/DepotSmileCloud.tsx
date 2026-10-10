"use client";

import { useEffect, useState } from "react";

import styles from "@/components/review/depotSmileCloud.module.css";
import { Carte } from "@/components/ui";
import { ApiError, apiRequest } from "@/lib/api";

interface Depot {
  etat: "absent" | "en_attente" | "depose" | "impossible";
  demande_le: string | null;
  depose_le: string | null;
  raison: string;
}

const REFUS: Record<string, string> = {
  SMILECLOUD_NON_RELIE: "Patient non relié à un dossier SmileCloud.",
  DOCUMENT_NOT_VALIDATED: "Validez le compte rendu d’abord.",
  DOCUMENT_EMPTY: "Ce document n’a pas encore de texte.",
};

/**
 * « Envoyer vers SmileCloud » : une ligne, un bouton aux couleurs de SmileCloud.
 *
 * Le document part dans le dossier du patient, porté par l'extension Chrome — rien à
 * télécharger ni à téléverser. **Un brouillon ne part pas** : ce qui entre dans
 * SmileCloud y reste, et Oris ne pourra pas l'en retirer (Franck, 10/10/2026).
 */
export function DepotSmileCloud({
  documentId,
  relie,
  valide,
}: {
  documentId: string;
  relie: boolean;
  valide: boolean;
}) {
  const [depot, setDepot] = useState<Depot | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    let vivant = true;
    apiRequest<Depot>(`/documents/${documentId}/smilecloud`)
      .then((etat) => {
        if (!vivant) return;
        setDepot(etat);
        setErreur(null);
      })
      .catch(() => undefined);
    return () => {
      vivant = false;
    };
  }, [documentId]);

  async function deposer() {
    setEnvoi(true);
    setErreur(null);
    try {
      setDepot(
        await apiRequest<Depot>(`/documents/${documentId}/smilecloud`, {
          method: "POST",
        }),
      );
    } catch (caught) {
      const code = caught instanceof ApiError ? caught.code : "";
      setErreur(REFUS[code] ?? "Oris n’a pas pu poser la demande.");
    } finally {
      setEnvoi(false);
    }
  }

  const etat = depot?.etat ?? "absent";
  const empeche = !valide
    ? REFUS.DOCUMENT_NOT_VALIDATED
    : !relie
      ? REFUS.SMILECLOUD_NON_RELIE
      : null;

  return (
    <Carte serree className={styles.carte}>
      <button
        type="button"
        className={styles.bouton}
        disabled={Boolean(empeche) || envoi || etat === "en_attente"}
        onClick={() => void deposer()}
      >
        {etat === "depose" || etat === "impossible"
          ? "Envoyer à nouveau"
          : "Envoyer vers SmileCloud"}
      </button>
      <p className={styles.mot}>
        {erreur ? (
          <span className={styles.refus}>{erreur}</span>
        ) : empeche ? (
          empeche
        ) : etat === "depose" ? (
          <span className={styles.fait}>Rangé dans le dossier du patient.</span>
        ) : etat === "en_attente" ? (
          "Demandé : l’extension Chrome le dépose à son prochain passage."
        ) : etat === "impossible" ? (
          <span className={styles.refus}>Pas déposé — {depot?.raison}</span>
        ) : (
          "Range le compte rendu dans la documentation du patient."
        )}
      </p>
    </Carte>
  );
}
