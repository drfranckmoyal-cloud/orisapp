"use client";

import { useMemo, useState } from "react";

import {
  Bouton,
  Carte,
  Champ,
  EnTetePage,
  EtatVide,
  Ligne,
  Lignes,
  Pastille,
  Squelette,
} from "@/components/ui";
import { ApiError, apiRequest, type Patient } from "@/lib/api";
import { errorMessage, formatDate, nomPatient } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

function sansAccents(texte: string): string {
  return texte
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

/** Liste des patients : recherche d'abord, création ensuite (S02). */
export default function PatientsPage() {
  const [patients, reload] = useApi<Patient[]>("/patients");
  const [recherche, setRecherche] = useState("");
  const [creation, setCreation] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const trouves = useMemo(() => {
    const liste = patients.state === "ready" ? patients.data : [];
    const cherche = sansAccents(recherche.trim());
    if (!cherche) return liste;
    return liste.filter((patient) =>
      sansAccents(`${patient.first_name} ${patient.last_name} ${patient.external_id ?? ""}`).includes(
        cherche,
      ),
    );
  }, [patients, recherche]);

  async function creer(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setMessage(null);
    try {
      await apiRequest<Patient>("/patients", {
        method: "POST",
        body: {
          first_name: String(data.get("first_name") ?? "").trim(),
          last_name: String(data.get("last_name") ?? "").trim(),
          birth_date: String(data.get("birth_date") ?? "") || null,
          external_id: String(data.get("external_id") ?? "").trim() || null,
          email: String(data.get("email") ?? "").trim(),
        },
      });
      form.reset();
      setCreation(false);
      setMessage("Patient créé.");
      reload();
    } catch (error) {
      setMessage(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
  }

  return (
    <div className="page">
      <EnTetePage
        surTitre="Données fictives uniquement"
        titre="Patients"
        action={
          <Bouton onClick={() => setCreation((ouvert) => !ouvert)} variante="secondaire">
            {creation ? "Annuler" : "Nouveau patient"}
          </Bouton>
        }
      />

      {creation && (
        <Carte titre="Nouveau patient">
          <form className="form-row" onSubmit={creer}>
            <label className="field">
              Prénom
              <Champ name="first_name" required autoFocus />
            </label>
            <label className="field">
              Nom
              <Champ name="last_name" required />
            </label>
            <label className="field">
              Date de naissance
              <Champ name="birth_date" type="date" />
            </label>
            <label className="field">
              Identifiant du cabinet
              <Champ name="external_id" placeholder="facultatif" />
            </label>
            <label className="field">
              Courriel
              <Champ name="email" type="email" placeholder="facultatif" />
            </label>
            <Bouton type="submit">Créer</Bouton>
          </form>
        </Carte>
      )}

      {message && (
        <div className="banner banner-info" role="status">
          {message}
        </div>
      )}

      <Carte
        titre={`${trouves.length} patient${trouves.length > 1 ? "s" : ""}`}
        action={
          <Champ
            type="search"
            value={recherche}
            placeholder="Rechercher un nom…"
            aria-label="Rechercher un patient"
            style={{ width: 260 }}
            onChange={(event) => setRecherche(event.target.value)}
          />
        }
      >
        {patients.state === "loading" && <Squelette lignes={4} />}
        {patients.state === "error" && <EtatVide titre={errorMessage(patients.code)} />}
        {patients.state === "ready" && trouves.length === 0 && (
          <EtatVide titre={recherche ? "Aucun patient à ce nom" : "Aucun patient"}>
            {recherche
              ? "Vérifiez l’orthographe, ou créez ce patient."
              : "Créez votre premier patient pour démarrer une consultation."}
          </EtatVide>
        )}
        {trouves.length > 0 && (
          <Lignes>
            {trouves.map((patient) => (
              <Ligne
                key={patient.id}
                href={`/patients/${patient.id}`}
                titre={nomPatient(patient)}
                detail={
                  patient.birth_date
                    ? `né(e) le ${formatDate(patient.birth_date)}`
                    : "date de naissance non renseignée"
                }
                fin={patient.external_id ? <Pastille>{patient.external_id}</Pastille> : undefined}
              />
            ))}
          </Lignes>
        )}
      </Carte>
    </div>
  );
}
