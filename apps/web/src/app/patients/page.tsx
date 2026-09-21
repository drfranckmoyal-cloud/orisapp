"use client";

import { useMemo, useState } from "react";

import Link from "next/link";

import { Bouton, Carte, Champ, EnTetePage, EtatVide, Pastille, Squelette } from "@/components/ui";
import { Icone } from "@/components/Icones";
import { ApiError, apiRequest, type Patient } from "@/lib/api";
import { errorMessage, formatDate } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./patients.module.css";

function initiales(patient: Patient): string {
  return `${patient.first_name.trim()[0] ?? ""}${patient.last_name.trim()[0] ?? ""}`.toLocaleUpperCase(
    "fr-FR",
  );
}

function age(naissance: string): number | null {
  const jour = new Date(naissance);
  if (Number.isNaN(jour.getTime())) return null;
  const maintenant = new Date();
  let ans = maintenant.getFullYear() - jour.getFullYear();
  const mois = maintenant.getMonth() - jour.getMonth();
  if (mois < 0 || (mois === 0 && maintenant.getDate() < jour.getDate())) ans -= 1;
  return ans;
}

/** Un dossier dans la liste : les initiales, le nom, et ce qui manque encore. */
function Dossier({ patient }: { patient: Patient }) {
  const ans = patient.birth_date ? age(patient.birth_date) : null;
  return (
    <Link href={`/patients/${patient.id}`} className={styles.dossier}>
      <span className={styles.jeton} aria-hidden="true">
        {initiales(patient)}
      </span>
      <span className={styles.qui}>
        <span className={styles.nom}>
          {patient.last_name.toLocaleUpperCase("fr-FR")}{" "}
          <span className={styles.prenom}>{patient.first_name}</span>
          {ans !== null && <span className={styles.prenom}> ({ans} ans)</span>}
        </span>
        <span className={styles.dessous}>
          {patient.birth_date ? (
            `né(e) le ${formatDate(patient.birth_date)}`
          ) : (
            <span className={styles.manque}>date de naissance non renseignée</span>
          )}
        </span>
      </span>
      <span className={styles.marques}>
        {patient.external_id && <Pastille>{patient.external_id}</Pastille>}
      </span>
      <span className={styles.chevron} aria-hidden="true">
        <Icone nom="suivant" taille={16} />
      </span>
    </Link>
  );
}

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
          <div className={styles.liste}>
            {trouves.map((patient) => (
              <Dossier key={patient.id} patient={patient} />
            ))}
          </div>
        )}
      </Carte>
    </div>
  );
}
