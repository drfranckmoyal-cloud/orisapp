"use client";

import Link from "next/link";

import { EncounterTable } from "@/components/EncounterTable";
import type { Encounter } from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

export default function ConsultationsPage() {
  const [encounters] = useApi<Encounter[]>("/encounters");
  return (
    <div className="page">
      <header className="page-header">
        <h1>Consultations</h1>
        <Link href="/consultations/nouvelle" className="button button-primary">
          Nouvelle consultation
        </Link>
      </header>
      <section className="card">
        {encounters.state === "loading" && <p className="muted">Chargement…</p>}
        {encounters.state === "error" && <p className="muted">{errorMessage(encounters.code)}</p>}
        {encounters.state === "ready" && <EncounterTable encounters={encounters.data} />}
      </section>
    </div>
  );
}
