"use client";

import { useEffect, useState } from "react";

import { Bouton, Carte, Pastille } from "@/components/ui";
import { ApiError, apiRequest } from "@/lib/api";

interface Depot {
  etat: "absent" | "en_attente" | "depose" | "impossible";
  demande_le: string | null;
  depose_le: string | null;
  raison: string;
}

const REFUS: Record<string, string> = {
  SMILECLOUD_NON_RELIE:
    "Ce patient n’est pas relié à un dossier SmileCloud. Ouvrez sa fiche pour faire le lien, une fois pour toutes.",
  DOCUMENT_EMPTY: "Ce document n’a pas encore de texte.",
};

/**
 * « Ranger dans SmileCloud » : le compte rendu va se classer là où le praticien
 * regarde ses photos, sans téléchargement ni téléversement à la main.
 *
 * Oris ne dépose rien lui-même : il pose la demande, et l'extension Chrome la sert à
 * son prochain passage — comme elle sert déjà les récupérations de photos. L'écran dit
 * donc toujours où ça en est, y compris quand l'extension est éteinte.
 */
export function DepotSmileCloud({
  documentId,
  relie,
}: {
  documentId: string;
  relie: boolean;
}) {
  const [depot, setDepot] = useState<Depot | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    let vivant = true;
    apiRequest<Depot>(`/documents/${documentId}/smilecloud`)
      .then((etat) => vivant && setDepot(etat))
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
  return (
    <Carte titre="Dans SmileCloud">
      {etat === "depose" && (
        <p style={{ marginTop: 0 }}>
          <Pastille ton="valide">rangé</Pastille> Le document est dans la
          documentation du patient, sur SmileCloud.
        </p>
      )}
      {etat === "en_attente" && (
        <p className="muted" style={{ marginTop: 0 }}>
          Demandé. Le dépôt se fera au prochain passage de l’extension Chrome —
          elle doit tourner, et vous être connecté à SmileCloud.
        </p>
      )}
      {etat === "impossible" && (
        <p style={{ marginTop: 0 }}>
          <Pastille ton="alerte">pas déposé</Pastille> {depot?.raison}
        </p>
      )}
      {etat === "absent" && (
        <p className="muted" style={{ marginTop: 0 }}>
          Ranger ce compte rendu dans la documentation du patient, sur
          SmileCloud. Rien à télécharger : Oris le fait porter par l’extension.
        </p>
      )}
      {!relie && (
        <p className="muted" style={{ marginTop: 0 }}>
          Ce patient n’est pas encore relié à un dossier SmileCloud : le lien se
          fait sur sa fiche, une fois pour toutes.
        </p>
      )}
      {erreur && <p className="banner banner-review">{erreur}</p>}
      <Bouton
        variante="secondaire"
        disabled={!relie || envoi || etat === "en_attente"}
        onClick={() => void deposer()}
      >
        {etat === "depose" || etat === "impossible"
          ? "Déposer à nouveau"
          : "Envoyer vers SmileCloud"}
      </Bouton>
    </Carte>
  );
}
