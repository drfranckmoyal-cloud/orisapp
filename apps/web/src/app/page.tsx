"use client";

import Link from "next/link";

import { ApiStatus } from "@/components/ApiStatus";
import { EncounterTable } from "@/components/EncounterTable";
import type { Encounter } from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

export default function HomePage() {
  const [toReview] = useApi<Encounter[]>("/encounters?status=review");

  return (
    <div className="page">
      <header>
        <p className="subtitle">Écouter. Comprendre. Documenter.</p>
        <h1>Bonjour</h1>
      </header>

      <div>
        <Link href="/consultations/nouvelle" className="button button-large">
          Nouvelle consultation
        </Link>
      </div>

      <section className="card" aria-labelledby="review-heading">
        <h2 id="review-heading">À valider</h2>
        {toReview.state === "loading" && <p className="muted">Chargement…</p>}
        {toReview.state === "error" && <p className="muted">{errorMessage(toReview.code)}</p>}
        {toReview.state === "ready" && <EncounterTable encounters={toReview.data} />}
      </section>

      <section className="card" aria-labelledby="server-heading">
        <h2 id="server-heading">État du service</h2>
        <ApiStatus />
      </section>
    </div>
  );
}
