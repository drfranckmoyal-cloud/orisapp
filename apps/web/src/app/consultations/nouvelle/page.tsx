"use client";

import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Bouton, Carte, Champ, EnTetePage, Squelette } from "@/components/ui";
import {
  ApiError,
  apiRequest,
  type Encounter,
  type Patient,
  type SyntheticCase,
} from "@/lib/api";
import { DOMAIN, errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

function sansAccents(texte: string): string {
  return texte
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

/** Démarrer une consultation : choisir le patient, appuyer sur Commencer (S04). */
function Formulaire() {
  const router = useRouter();
  const parametres = useSearchParams();
  const [cases] = useApi<SyntheticCase[]>("/synthetic-cases");
  const [patients] = useApi<Patient[]>("/patients");
  const [patientChoisi, setPatientChoisi] = useState(parametres.get("patient") ?? "");
  const [recherche, setRecherche] = useState("");
  const [prenom, setPrenom] = useState("");
  const [nom, setNom] = useState("");
  const [nouveau, setNouveau] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const liste = useMemo(
    () => (patients.state === "ready" ? patients.data : []),
    [patients],
  );
  const trouves = useMemo(() => {
    const cherche = sansAccents(recherche.trim());
    if (!cherche) return liste.slice(0, 8);
    return liste
      .filter((patient) =>
        sansAccents(`${patient.first_name} ${patient.last_name}`).includes(cherche),
      )
      .slice(0, 8);
  }, [liste, recherche]);
  const selectionne = liste.find((patient) => patient.id === patientChoisi);
  const pret = Boolean(patientChoisi) || (nouveau && prenom.trim() !== "" && nom.trim() !== "");

  async function commencer() {
    setBusy(true);
    setError(null);
    try {
      const patientId =
        patientChoisi ||
        (
          await apiRequest<Patient>("/patients", {
            method: "POST",
            body: { first_name: prenom.trim(), last_name: nom.trim() },
          })
        ).id;
      const encounter = await apiRequest<Encounter>("/encounters", {
        method: "POST",
        body: { patient_id: patientId },
      });
      router.push(`/consultations/${encounter.id}/ecoute`);
    } catch (caught) {
      setError(errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"));
      setBusy(false);
    }
  }

  async function rejouer(caseId: string) {
    setBusy(true);
    setError(null);
    try {
      const encounter = await apiRequest<Encounter>(`/synthetic-cases/${caseId}/encounters`, {
        method: "POST",
      });
      router.push(`/consultations/${encounter.id}`);
    } catch (caught) {
      setError(errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"));
      setBusy(false);
    }
  }

  const parDomaine = new Map<string, SyntheticCase[]>();
  if (cases.state === "ready") {
    for (const item of cases.data) {
      parDomaine.set(item.domain, [...(parDomaine.get(item.domain) ?? []), item]);
    }
  }

  return (
    <>
      <EnTetePage surTitre="Données fictives uniquement" titre="Nouvelle consultation" />

      <Carte titre="Qui allez-vous recevoir ?">
        {patients.state === "loading" && <Squelette lignes={3} />}
        {patients.state === "ready" && !nouveau && (
          <div style={{ display: "grid", gap: "var(--espace-3)" }}>
            <Champ
              type="search"
              placeholder="Chercher un patient"
              value={recherche}
              autoFocus
              onChange={(event) => setRecherche(event.target.value)}
            />
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {trouves.map((patient) => (
                <Bouton
                  key={patient.id}
                  type="button"
                  variante={patient.id === patientChoisi ? "principal" : "secondaire"}
                  onClick={() => setPatientChoisi(patient.id)}
                >
                  {patient.first_name} {patient.last_name}
                </Bouton>
              ))}
              {trouves.length === 0 && (
                <p className="muted" style={{ margin: 0 }}>
                  Aucun patient à ce nom.
                </p>
              )}
            </div>
            <Bouton
              type="button"
              variante="discret"
              onClick={() => {
                setNouveau(true);
                setPatientChoisi("");
              }}
            >
              C’est un nouveau patient
            </Bouton>
          </div>
        )}
        {nouveau && (
          <div style={{ display: "grid", gap: "var(--espace-3)", maxWidth: 420 }}>
            <label className="field">
              Prénom
              <Champ value={prenom} autoFocus onChange={(e) => setPrenom(e.target.value)} />
            </label>
            <label className="field">
              Nom
              <Champ value={nom} onChange={(e) => setNom(e.target.value)} />
            </label>
            <Bouton type="button" variante="discret" onClick={() => setNouveau(false)}>
              Revenir à la liste
            </Bouton>
          </div>
        )}
      </Carte>

      <Carte>
        <div style={{ display: "grid", gap: "var(--espace-3)" }}>
          <p className="muted" style={{ margin: 0 }}>
            Oris écoute, transcrit, puis rédige le compte rendu.
            {selectionne
              ? ` Consultation de ${selectionne.first_name} ${selectionne.last_name}.`
              : ""}{" "}
            Le son est supprimé dès que la transcription a abouti.
          </p>
          <div>
            <Bouton
              type="button"
              grand
              disabled={busy || !pret}
              onClick={() => void commencer()}
            >
              {busy ? "Préparation…" : "Commencer"}
            </Bouton>
          </div>
          {!pret && (
            <p className="muted" style={{ margin: 0 }}>
              Choisissez d’abord un patient.
            </p>
          )}
          {error && (
            <div className="banner banner-critical" role="alert">
              {error}
            </div>
          )}
        </div>
      </Carte>

      <Carte titre="Essayer sans parler">
        <p className="muted" style={{ marginTop: 0 }}>
          Une consultation fictive, écrite pour les tests, qu’Oris traite comme une vraie :
          transcription, faits, documents. Utile pour voir le résultat sans micro.
        </p>
        {[...parDomaine.entries()].map(([domaine, items]) => (
          <div key={domaine} style={{ marginTop: "var(--espace-3)" }}>
            <h3 style={{ margin: "0 0 8px" }}>{DOMAIN[domaine] ?? domaine}</h3>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {items.slice(0, 6).map((item) => (
                <Bouton
                  key={item.case_id}
                  type="button"
                  variante="secondaire"
                  disabled={busy}
                  onClick={() => void rejouer(item.case_id)}
                >
                  {item.patient_first_name} {item.patient_last_name}
                </Bouton>
              ))}
            </div>
          </div>
        ))}
      </Carte>
    </>
  );
}

export default function NouvelleConsultationPage() {
  return (
    <Suspense fallback={<Squelette lignes={5} />}>
      <Formulaire />
    </Suspense>
  );
}
