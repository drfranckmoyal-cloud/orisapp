"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Symbole } from "@/components/Marque";
import { ApiError, apiRequest, type Encounter } from "@/lib/api";
import { errorMessage } from "@/lib/labels";

import styles from "./commencer.module.css";

/** Commencer une consultation pour ce patient — et **commencer** veut dire écouter.
 *
 * Le bouton ouvrait jusqu'ici l'écran de création, où il fallait rechoisir le patient
 * qu'on venait justement d'ouvrir. Depuis une fiche, le patient est connu : la
 * consultation se crée à la volée et l'écoute démarre. C'est le cœur du produit, il ne
 * doit pas y avoir d'écran entre l'intention et le micro.
 */
export function CommencerConsultation({
  patientId,
  variante = "principal",
  libelle = variante === "ligne"
    ? "Commencer l’enregistrement de la consultation"
    : "Nouvelle consultation",
}: {
  patientId: string;
  /** `ligne` : au bout d'un rendez-vous, le symbole seul. Une liste de onze lignes
   *  n'a pas besoin de lire onze fois le même mot ; le survol dit ce que fait le geste. */
  variante?: "principal" | "ligne";
  libelle?: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function commencer() {
    setBusy(true);
    setErreur(null);
    try {
      const encounter = await apiRequest<Encounter>("/encounters", {
        method: "POST",
        body: { patient_id: patientId },
      });
      router.push(`/consultations/${encounter.id}/ecoute`);
    } catch (caught) {
      setErreur(errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"));
      setBusy(false);
    }
  }

  const ligne = variante === "ligne";

  return (
    <div className={`${styles.bloc} ${ligne ? styles.blocLigne : ""}`}>
      <button
        type="button"
        className={`${styles.bouton} ${ligne ? styles.boutonLigne : ""}`}
        onClick={() => void commencer()}
        disabled={busy}
        title={ligne ? libelle : undefined}
        aria-label={ligne ? libelle : undefined}
      >
        <span className={styles.disque} aria-hidden="true">
          <Symbole taille={ligne ? 17 : 20} />
        </span>
        {!ligne && (busy ? "Ouverture…" : libelle)}
      </button>
      {erreur && (
        <span className={styles.erreur} role="alert">
          {erreur}
        </span>
      )}
    </div>
  );
}
