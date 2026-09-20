"use client";

import { Carte, EnTetePage, Pastille } from "@/components/ui";
import type { ClientConfig } from "@/lib/api";
import { useApi } from "@/lib/useApi";

type Sante = {
  status: string;
  version: string;
  environment: string;
  providers: Record<string, string>;
};

const MOTEURS: Record<string, string> = {
  mock: "simulateur interne",
  deepgram: "Deepgram Nova-3",
  azure_speech: "Azure AI Speech",
  anthropic: "Claude (Anthropic)",
};

/** Paramètres : ce qui est réglé, et ce qui ne l'est pas encore. */
export default function ParametresPage() {
  const [sante] = useApi<Sante>("/health");
  const [config] = useApi<ClientConfig>("/config/client");
  const moteurs = sante.state === "ready" ? sante.data.providers : {};

  return (
    <div className="page">
      <EnTetePage surTitre="Réglages" titre="Paramètres" />

      <div className="grille-reglages">
        <Carte titre="Praticien et cabinet">
          <dl className="fiches">
            <div>
              <dt>Praticien</dt>
              <dd>Dr Franck Moyal</dd>
            </div>
            <div>
              <dt>Cabinet</dt>
              <dd className="muted">à renseigner (fichier config/cabinet.json)</dd>
            </div>
            <div>
              <dt>En-tête des documents</dt>
              <dd className="muted">logo Oris tant que celui du cabinet n’est pas fourni</dd>
            </div>
          </dl>
        </Carte>

        <Carte titre="Moteurs">
          <dl className="fiches">
            <div>
              <dt>Transcription</dt>
              <dd>{MOTEURS[moteurs.speech_to_text ?? ""] ?? moteurs.speech_to_text ?? "—"}</dd>
            </div>
            <div>
              <dt>Extraction clinique</dt>
              <dd>
                {MOTEURS[moteurs.clinical_extraction ?? ""] ?? moteurs.clinical_extraction ?? "—"}
              </dd>
            </div>
            <div>
              <dt>Rédaction et vérification</dt>
              <dd>règles déterministes d’Oris</dd>
            </div>
          </dl>
        </Carte>

        <Carte titre="Écoute">
          <dl className="fiches">
            <div>
              <dt>Durée maximale</dt>
              <dd>
                {config.state === "ready" ? `${config.data.max_session_minutes} minutes` : "—"}
              </dd>
            </div>
            <div>
              <dt>Information du patient</dt>
              <dd>
                {config.state === "ready" && config.data.patient_information_mode === "confirm"
                  ? "confirmation demandée avant chaque écoute"
                  : "non demandée"}
              </dd>
            </div>
            <div>
              <dt>Son</dt>
              <dd>supprimé dès que la transcription a abouti</dd>
            </div>
          </dl>
        </Carte>

        <Carte titre="Sécurité">
          <dl className="fiches">
            <div>
              <dt>Accès</dt>
              <dd>
                jeton personnel <Pastille ton="valide">en place</Pastille>
              </dd>
            </div>
            <div>
              <dt>Deuxième facteur</dt>
              <dd>
                <Pastille ton="attention">à faire</Pastille> viendra du fournisseur d’identité
              </dd>
            </div>
            <div>
              <dt>Hébergement agréé santé</dt>
              <dd>
                <Pastille ton="alerte">absent</Pastille> aucun patient réel
              </dd>
            </div>
            <div>
              <dt>Journal</dt>
              <dd>actions tracées, sans contenu clinique</dd>
            </div>
          </dl>
        </Carte>
      </div>
    </div>
  );
}
