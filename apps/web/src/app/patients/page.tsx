"use client";

import { type FormEvent, useState } from "react";

import { EncounterTable } from "@/components/EncounterTable";
import { ApiError, apiRequest, type Encounter, type Patient } from "@/lib/api";
import { errorMessage, formatDateTime } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

export default function PatientsPage() {
  const [patients, reload] = useApi<Patient[]>("/patients");
  const [selected, setSelected] = useState<Patient | null>(null);
  const [encounters] = useApi<Encounter[]>(selected ? `/encounters?patient_id=${selected.id}` : null);
  const [message, setMessage] = useState<string | null>(null);

  async function createPatient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      await apiRequest<Patient>("/patients", {
        method: "POST",
        body: { first_name: data.get("first_name"), last_name: data.get("last_name") },
      });
      form.reset();
      setMessage("Patient créé.");
      reload();
    } catch (error) {
      setMessage(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
  }

  return (
    <div className="page">
      <header>
        <h1>Patients</h1>
        <p className="subtitle">Patients fictifs uniquement tant qu’Oris n’est pas hébergé en HDS.</p>
      </header>

      <section className="card" aria-labelledby="new-patient">
        <h2 id="new-patient">Nouveau patient</h2>
        <form className="form-row" onSubmit={createPatient}>
          <label className="field">
            Prénom
            <input className="input" name="first_name" required maxLength={200} />
          </label>
          <label className="field">
            Nom
            <input className="input" name="last_name" required maxLength={200} />
          </label>
          <button type="submit" className="button button-primary">
            Créer
          </button>
        </form>
        {message && <p role="status" className="muted">{message}</p>}
      </section>

      <section className="card" aria-labelledby="patient-list">
        <h2 id="patient-list">Liste</h2>
        {patients.state === "loading" && <p className="muted">Chargement…</p>}
        {patients.state === "error" && <p className="muted">{errorMessage(patients.code)}</p>}
        {patients.state === "ready" && patients.data.length === 0 && (
          <p className="muted">Aucun patient.</p>
        )}
        {patients.state === "ready" && patients.data.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Nom</th>
                <th scope="col">Créé le</th>
              </tr>
            </thead>
            <tbody>
              {patients.data.map((patient) => (
                <tr key={patient.id}>
                  <td>
                    <button type="button" className="link-button" onClick={() => setSelected(patient)}>
                      {patient.last_name} {patient.first_name}
                    </button>
                  </td>
                  <td>{formatDateTime(patient.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {selected && (
        <section className="card" aria-labelledby="patient-encounters">
          <h2 id="patient-encounters">
            Consultations de {selected.first_name} {selected.last_name}
          </h2>
          {encounters.state === "ready" && <EncounterTable encounters={encounters.data} />}
        </section>
      )}
    </div>
  );
}
