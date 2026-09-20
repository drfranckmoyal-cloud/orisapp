"use client";

import Link from "next/link";

import { Carte, EnTetePage, EtatVide, Ligne, Lignes, Pastille, Squelette } from "@/components/ui";
import type { Encounter } from "@/lib/api";
import { ENCOUNTER_STATUS, errorMessage, formatDateTime } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

const PRATICIEN = "Docteur Moyal";

function salutation(heure: number): string {
  if (heure < 13) return "Bonjour";
  if (heure < 18) return "Bon après-midi";
  return "Bonsoir";
}

function jourDe(encounter: Encounter): string {
  return (encounter.started_at ?? encounter.created_at).slice(0, 10);
}

function estAujourdhui(encounter: Encounter): boolean {
  return jourDe(encounter) === new Date().toISOString().slice(0, 10);
}

function heureDe(encounter: Encounter): string {
  const quand = new Date(encounter.started_at ?? encounter.created_at);
  return quand.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

function nomDe(encounter: Encounter): string {
  return `${encounter.patient.first_name} ${encounter.patient.last_name}`.trim();
}

function documentsDe(encounter: Encounter): string {
  const total = encounter.documents.length;
  if (total === 0) return "aucun document";
  return total === 1 ? "1 document" : `${total} documents`;
}

/** Accueil : ce qui se passe aujourd'hui, ce qui attend, et une seule action. */
export default function HomePage() {
  const [encounters] = useApi<Encounter[]>("/encounters");
  const toutes = encounters.state === "ready" ? encounters.data : [];

  const aValider = toutes.filter((e) => e.status === "review");
  const aujourdhui = toutes.filter(estAujourdhui);
  const terminees = toutes.filter((e) => ["validated", "exported", "archived"].includes(e.status));
  const enEchec = toutes.filter((e) =>
    ["transcription_failed", "generation_failed", "audio_error", "upload_interrupted"].includes(
      e.status,
    ),
  );

  return (
    <div className="page">
      <EnTetePage
        surTitre={new Date().toLocaleDateString("fr-FR", {
          weekday: "long",
          day: "numeric",
          month: "long",
        })}
        titre={`${salutation(new Date().getHours())} ${PRATICIEN}`}
        action={
          <Link href="/consultations/nouvelle" className="cta">
            <span aria-hidden="true">●</span> Démarrer une consultation
          </Link>
        }
      />

      <div className="grille-accueil">
        <Carte
          titre="À relire"
          action={aValider.length > 0 ? <Pastille ton="attention">{aValider.length}</Pastille> : null}
        >
          {encounters.state === "loading" && <Squelette lignes={3} />}
          {encounters.state === "error" && <EtatVide titre={errorMessage(encounters.code)} />}
          {encounters.state === "ready" && aValider.length === 0 && (
            <EtatVide titre="Rien à relire">
              Les comptes rendus apparaissent ici dès qu’une consultation est traitée.
            </EtatVide>
          )}
          {aValider.length > 0 && (
            <Lignes>
              {aValider.slice(0, 6).map((encounter) => (
                <Ligne
                  key={encounter.id}
                  href={`/consultations/${encounter.id}`}
                  titre={nomDe(encounter)}
                  detail={`${formatDateTime(encounter.started_at ?? encounter.created_at)} · ${documentsDe(encounter)}`}
                  fin={<Pastille ton="attention">à relire</Pastille>}
                />
              ))}
            </Lignes>
          )}
        </Carte>

        <Carte titre="Aujourd’hui">
          {encounters.state === "loading" && <Squelette lignes={2} />}
          {encounters.state === "ready" && aujourdhui.length === 0 && (
            <EtatVide titre="Aucune consultation aujourd’hui">
              Démarrez-en une : Oris écoute et prépare le compte rendu.
            </EtatVide>
          )}
          {aujourdhui.length > 0 && (
            <Lignes>
              {aujourdhui.slice(0, 6).map((encounter) => (
                <Ligne
                  key={encounter.id}
                  href={`/consultations/${encounter.id}`}
                  titre={nomDe(encounter)}
                  detail={<time>{heureDe(encounter)}</time>}
                  fin={
                    <Pastille
                      ton={
                        encounter.status === "review"
                          ? "attention"
                          : encounter.status === "validated" || encounter.status === "exported"
                            ? "valide"
                            : "neutre"
                      }
                    >
                      {ENCOUNTER_STATUS[encounter.status]}
                    </Pastille>
                  }
                />
              ))}
            </Lignes>
          )}
        </Carte>

        <Carte titre="Terminées">
          {encounters.state === "ready" && terminees.length === 0 && (
            <EtatVide titre="Aucune consultation validée">
              Une consultation validée reste consultable et exportable.
            </EtatVide>
          )}
          {terminees.length > 0 && (
            <Lignes>
              {terminees.slice(0, 5).map((encounter) => (
                <Ligne
                  key={encounter.id}
                  href={`/consultations/${encounter.id}`}
                  titre={nomDe(encounter)}
                  detail={formatDateTime(encounter.started_at ?? encounter.created_at)}
                  fin={<Pastille ton="valide">{ENCOUNTER_STATUS[encounter.status]}</Pastille>}
                />
              ))}
            </Lignes>
          )}
        </Carte>

        {enEchec.length > 0 && (
          <Carte titre="À reprendre">
            <Lignes>
              {enEchec.slice(0, 5).map((encounter) => (
                <Ligne
                  key={encounter.id}
                  href={`/consultations/${encounter.id}`}
                  titre={nomDe(encounter)}
                  detail={formatDateTime(encounter.started_at ?? encounter.created_at)}
                  fin={<Pastille ton="alerte">{ENCOUNTER_STATUS[encounter.status]}</Pastille>}
                />
              ))}
            </Lignes>
          </Carte>
        )}
      </div>
    </div>
  );
}
