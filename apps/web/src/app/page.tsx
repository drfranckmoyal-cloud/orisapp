"use client";

import Link from "next/link";

import { EncounterTable } from "@/components/EncounterTable";
import type { Encounter } from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

/** Accueil : une seule chose à faire, et ce qui attend votre relecture. */
export default function HomePage() {
  const [toReview] = useApi<Encounter[]>("/encounters?status=review");
  const waiting = toReview.state === "ready" ? toReview.data : [];

  return (
    <div className="page">
      <header>
        <p className="subtitle">Écouter. Comprendre. Documenter.</p>
        <h1>Bonjour</h1>
      </header>

      <section className="card" style={{ alignItems: "flex-start", gap: 12 }}>
        <h2 style={{ margin: 0 }}>Vous allez recevoir un patient ?</h2>
        <p className="muted" style={{ margin: 0 }}>
          Oris écoute la consultation et prépare le compte rendu. Vous relisez, vous
          corrigez, vous validez — rien n’est écrit sans votre accord.
        </p>
        <Link href="/consultations/nouvelle" className="button button-large">
          Démarrer une consultation
        </Link>
      </section>

      <section className="card" aria-labelledby="review-heading">
        <h2 id="review-heading">
          À relire {waiting.length > 0 && <span className="chip">{waiting.length}</span>}
        </h2>
        {toReview.state === "loading" && <p className="muted">Chargement…</p>}
        {toReview.state === "error" && <p className="muted">{errorMessage(toReview.code)}</p>}
        {toReview.state === "ready" && waiting.length === 0 && (
          <p className="muted">
            Rien en attente. Les consultations terminées apparaîtront ici, prêtes à être
            relues.
          </p>
        )}
        {waiting.length > 0 && <EncounterTable encounters={waiting.slice(0, 8)} />}
      </section>
    </div>
  );
}
