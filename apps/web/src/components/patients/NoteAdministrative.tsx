"use client";

import { useState } from "react";

import { Bouton, Carte, Zone } from "@/components/ui";
import { ApiError, apiRequest, type Patient } from "@/lib/api";
import { errorMessage } from "@/lib/labels";

const LONGUEUR_MAX = 500;

/** Note administrative de la fiche patient (§9).
 *
 * Administrative, et l'écran le dit : un rappel d'organisation, pas un dossier
 * médical. Oris ne la lit pas — elle n'entre dans aucun compte rendu et ne produit
 * aucun fait clinique. Le champ est court exprès : long, il inviterait à y écrire du
 * clinique qui ne serait jamais repris nulle part.
 */
export function NoteAdministrative({
  patient,
  onSaved,
}: {
  patient: Patient;
  onSaved: () => void;
}) {
  const [texte, setTexte] = useState(patient.note);
  const [message, setMessage] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const modifie = texte.trim() !== patient.note.trim();

  async function enregistrer() {
    setEnvoi(true);
    setMessage(null);
    try {
      await apiRequest<Patient>(`/patients/${patient.id}`, {
        method: "PATCH",
        body: { note: texte.trim() },
      });
      setMessage("Note enregistrée.");
      onSaved();
    } catch (error) {
      setMessage(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <Carte titre="Note">
      <p className="muted" style={{ marginTop: 0 }}>
        Un rappel pratique pour vous : horaires, rappel à passer, préférence du patient.
        Oris ne la lit pas et ne la reprend dans aucun compte rendu.
      </p>
      <Zone
        compacte
        value={texte}
        rows={3}
        maxLength={LONGUEUR_MAX}
        placeholder="Préfère les rendez-vous du matin."
        aria-label="Note administrative"
        onChange={(event) => setTexte(event.target.value)}
      />
      <div style={{ display: "flex", alignItems: "center", gap: "var(--espace-3)" }}>
        <Bouton
          variante="secondaire"
          disabled={!modifie || envoi}
          onClick={() => void enregistrer()}
        >
          {envoi ? "Enregistrement…" : "Enregistrer la note"}
        </Bouton>
        <span className="muted">
          {texte.length} / {LONGUEUR_MAX}
        </span>
        {message && <span className="muted">{message}</span>}
      </div>
    </Carte>
  );
}
