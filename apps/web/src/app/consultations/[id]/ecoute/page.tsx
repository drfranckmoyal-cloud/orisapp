"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { ListeningScreen } from "@/components/listening/ListeningScreen";
import type { AudioSessionView, ClientConfig, Encounter } from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

const CAPTURE_STATUSES = new Set(["draft", "recording", "paused"]);

export default function ListeningPage() {
  const { id } = useParams<{ id: string }>();
  const [encounter] = useApi<Encounter>(`/encounters/${id}`);
  const [config] = useApi<ClientConfig>("/config/client");
  const [audio] = useApi<AudioSessionView>(`/encounters/${id}/audio`);

  if (encounter.state === "error") return <p className="muted">{errorMessage(encounter.code)}</p>;
  if (config.state === "error") return <p className="muted">{errorMessage(config.code)}</p>;
  if (encounter.state !== "ready" || config.state !== "ready" || audio.state === "loading") {
    return <p className="muted">Chargement…</p>;
  }
  if (!CAPTURE_STATUSES.has(encounter.data.status)) {
    return (
      <div className="page">
        <p>L’écoute de cette consultation est terminée.</p>
        <Link href={`/consultations/${id}`} className="button button-primary">
          Voir la consultation
        </Link>
      </div>
    );
  }
  return (
    <div className="page">
      <ListeningScreen
        encounter={encounter.data}
        config={config.data}
        audio={audio.state === "ready" ? audio.data : null}
      />
    </div>
  );
}
