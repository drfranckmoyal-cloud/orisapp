"use client";

import { useState } from "react";

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
import {
  ApiError,
  apiRequest,
  type Cabinet,
  type ClientConfig,
  type EngineVersion,
} from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

type Sante = {
  status: string;
  version: string;
  environment: string;
  providers: Record<string, string>;
};

const COMPOSANT: Record<string, string> = {
  speech_to_text: "Transcription",
  clinical_extraction: "Extraction clinique",
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
  const [cabinet, rechargerCabinet] = useApi<Cabinet>("/me/cabinet");
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const moteurs = sante.state === "ready" ? sante.data.providers : {};
  const smilecloud = config.state === "ready" && config.data.smilecloud_connected;
  const [versions] = useApi<EngineVersion[]>("/system/versions");

  async function enregistrerCabinet(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const donnees = new FormData(event.currentTarget);
    setMessage(null);
    try {
      await apiRequest("/me/cabinet", {
        method: "PATCH",
        body: {
          name: String(donnees.get("name") ?? ""),
          address: String(donnees.get("address") ?? ""),
          phone: String(donnees.get("phone") ?? ""),
          email: String(donnees.get("email") ?? ""),
          legal: String(donnees.get("legal") ?? ""),
          city: String(donnees.get("city") ?? ""),
          practitioner_title: String(donnees.get("practitioner_title") ?? ""),
        },
      });
      setMessage({
        tone: "ok",
        text: "Enregistré. Vos prochains documents porteront cet en-tête.",
      });
      rechargerCabinet();
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "UNKNOWN";
      setMessage({ tone: "error", text: errorMessage(code) });
    }
  }

  return (
    <div className="page">
      <EnTetePage surTitre="Réglages" titre="Paramètres" />

      <Carte titre="Praticiens du cabinet">
        <p className="muted" style={{ marginTop: 0 }}>
          Chaque praticien garde son dictionnaire, ses préférences de rédaction et ses
          documents. Un praticien ne voit jamais les consultations d’un autre.
        </p>
        {cabinet.state === "loading" && <Squelette lignes={2} />}
        {cabinet.state === "ready" && (
          <Lignes>
            <Ligne
              href="/parametres"
              titre={`${cabinet.data.practitioner_title} ${cabinet.data.practitioner_name}`.trim()}
              detail={`${cabinet.data.name} · profil utilisé`}
              fin={<Pastille ton="valide">actif</Pastille>}
            />
          </Lignes>
        )}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 16,
            flexWrap: "wrap",
            borderTop: "1px solid var(--trait)",
            paddingTop: "var(--espace-4)",
          }}
        >
          <div>
            <strong>Créer un nouveau praticien</strong>
            <p className="muted" style={{ margin: "2px 0 0" }}>
              Le cabinet est mono-praticien pour l’instant. La création de profils viendra
              avec la gestion des accès — elle n’a pas de sens sans elle.
            </p>
          </div>
          <Bouton disabled>En attente</Bouton>
        </div>
      </Carte>

      <Carte titre="Connecteurs">
        <p className="muted" style={{ marginTop: 0 }}>
          Ce qu’Oris ira chercher ailleurs plutôt que de vous le faire ressaisir.
        </p>
        <div className="rangs-reglages">
          <div className="reglage-connecteur">
            <div>
              <strong>SmileCloud</strong>
              <p className="muted" style={{ margin: "2px 0 0" }}>
                Retrouver les photos, scans et documents du patient déjà déposés dans
                SmileCloud, et les rattacher à sa fiche sans les réimporter à la main.
              </p>
            </div>
            <span style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <Pastille ton={smilecloud ? "valide" : "attention"} point>
                {smilecloud ? "connecté" : "non connecté"}
              </Pastille>
              <Bouton disabled>En attente</Bouton>
            </span>
          </div>
          <div className="reglage-connecteur">
            <div>
              <strong>Doctolib</strong>
              <p className="muted" style={{ margin: "2px 0 0" }}>
                Reprendre les rendez-vous du jour et créer les dossiers sans ressaisie.
                Décrit dans <strong>Votre journée</strong>.
              </p>
            </div>
            <span style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <Pastille ton="attention" point>
                non connecté
              </Pastille>
              <Bouton disabled>En attente</Bouton>
            </span>
          </div>
        </div>
      </Carte>

      <div className="grille-reglages">
        <Carte titre="Praticien et cabinet">
          <p className="muted" style={{ margin: 0 }}>
            Ces informations s’impriment en tête de vos comptes rendus et de vos courriers.
          </p>
          {cabinet.state === "loading" && <Squelette lignes={4} />}
          {cabinet.state === "ready" && (
            <form onSubmit={enregistrerCabinet} style={{ display: "grid", gap: 12 }}>
              <label className="field">
                Nom du cabinet
                <Champ name="name" defaultValue={cabinet.data.name} />
              </label>
              <label className="field">
                Adresse
                <Champ name="address" defaultValue={cabinet.data.address} />
              </label>
              <div className="form-row">
                <label className="field">
                  Téléphone
                  <Champ name="phone" defaultValue={cabinet.data.phone} />
                </label>
                <label className="field">
                  Courriel
                  <Champ name="email" type="email" defaultValue={cabinet.data.email} />
                </label>
              </div>
              <div className="form-row">
                <label className="field">
                  Mention légale (RPPS, ADELI…)
                  <Champ name="legal" defaultValue={cabinet.data.legal} />
                </label>
                <label className="field">
                  Ville (pour les courriers)
                  <Champ name="city" defaultValue={cabinet.data.city} />
                </label>
              </div>
              <div className="form-row">
                <label className="field">
                  Titre du praticien
                  <Champ
                    name="practitioner_title"
                    placeholder="Dr"
                    defaultValue={cabinet.data.practitioner_title}
                  />
                </label>
                <label className="field">
                  Praticien
                  <Champ value={cabinet.data.practitioner_name} disabled readOnly />
                </label>
              </div>
              <div>
                <Bouton type="submit">Enregistrer</Bouton>
              </div>
            </form>
          )}
          {message && (
            <div
              className={`banner ${message.tone === "ok" ? "banner-info" : "banner-critical"}`}
              role="status"
            >
              {message.text}
            </div>
          )}
          <p className="muted" style={{ margin: 0 }}>
            Le logo du cabinet n’est pas encore remplaçable depuis cet écran : les documents
            portent le logo Oris.
          </p>
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

          <p className="muted" style={{ margin: 0 }}>
            Ce qui a réellement tourné sur vos consultations — pas ce qui est réglé ici.
            C’est ce qui permet de rattacher un compte rendu à la version exacte qui l’a
            produit.
          </p>
          {versions.state === "ready" && versions.data.length === 0 && (
            <EtatVide titre="Aucun traitement pour l’instant" />
          )}
          {versions.state === "ready" && versions.data.length > 0 && (
            <ul className="liste-simple">
              {versions.data.map((version) => (
                <li key={`${version.component}-${version.model_id}`}>
                  <strong>{COMPOSANT[version.component] ?? version.component}</strong> —{" "}
                  {version.provider} · {version.model_id}
                  {version.prompt_version && <> · consigne {version.prompt_version}</>}
                </li>
              ))}
            </ul>
          )}
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
