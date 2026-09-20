"use client";

import { useRef, useState } from "react";

import { Icone } from "@/components/Icones";
import { Bouton, EtatVide, Pastille, Squelette } from "@/components/ui";
import { API_BASE_URL, ApiError, type Attachment, type ClientConfig } from "@/lib/api";
import { errorMessage, formatDateTime } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./pieces.module.css";

const NATURE: Record<string, string> = {
  photo: "Photo",
  radio: "Radio",
  empreinte: "Empreinte",
  document: "Document",
};

function poids(octets: number): string {
  if (octets < 1024) return `${octets} o`;
  if (octets < 1024 * 1024) return `${Math.round(octets / 1024)} ko`;
  return `${(octets / (1024 * 1024)).toFixed(1).replace(".", ",")} Mo`;
}

/** Pièces jointes du patient : photos, radios, empreintes, documents (§55).
 *
 * On les importe en les déposant ou par le bouton. Oris ne les lit pas — elles
 * accompagnent le compte rendu, elles ne le nourrissent pas. C'est le praticien
 * qui s'y réfère, en écrivant.
 */
export function PiecesJointes({
  patientId,
  encounterId,
  compact = false,
}: {
  patientId: string;
  /** Rattache les pièces importées à cette consultation (écran de révision). */
  encounterId?: string;
  /** Version resserrée, pour le rail de révision. */
  compact?: boolean;
}) {
  const [pieces, recharger] = useApi<Attachment[]>(`/patients/${patientId}/attachments`);
  const [config] = useApi<ClientConfig>("/config/client");
  const [survol, setSurvol] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const champ = useRef<HTMLInputElement | null>(null);

  const liste = pieces.state === "ready" ? pieces.data : [];
  const formats = config.state === "ready" ? config.data.attachment_formats : [];
  const maxOctets = config.state === "ready" ? config.data.attachment_max_bytes : 0;

  async function importer(fichiers: FileList | null) {
    if (!fichiers || fichiers.length === 0) return;
    setEnvoi(true);
    setMessage(null);
    const corps = new FormData();
    for (const fichier of Array.from(fichiers)) corps.append("files", fichier);
    if (encounterId) corps.append("encounter_id", encounterId);
    try {
      const reponse = await fetch(`${API_BASE_URL}/patients/${patientId}/attachments`, {
        method: "POST",
        body: corps,
      });
      const donnees: unknown = await reponse.json().catch(() => null);
      if (!reponse.ok) {
        const code =
          typeof donnees === "object" && donnees !== null && "code" in donnees
            ? String((donnees as { code: unknown }).code)
            : "UNKNOWN";
        throw new ApiError(reponse.status, code);
      }
      const rangees = Array.isArray(donnees) ? donnees.length : 0;
      setMessage(rangees === 1 ? "1 fichier importé." : `${rangees} fichiers importés.`);
      recharger();
    } catch (error) {
      setMessage(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setEnvoi(false);
      if (champ.current) champ.current.value = "";
    }
  }

  async function retirer(piece: Attachment) {
    setMessage(null);
    try {
      const reponse = await fetch(`${API_BASE_URL}/patients/attachments/${piece.id}`, {
        method: "DELETE",
      });
      if (!reponse.ok) throw new ApiError(reponse.status, "UNKNOWN");
      recharger();
    } catch (error) {
      setMessage(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
  }

  return (
    <div className={`${styles.bloc} ${compact ? styles.compact : ""}`}>
      <div
        className={`${styles.depot} ${survol ? styles.survol : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setSurvol(true);
        }}
        onDragLeave={() => setSurvol(false)}
        onDrop={(event) => {
          event.preventDefault();
          setSurvol(false);
          void importer(event.dataTransfer.files);
        }}
      >
        <Icone nom="import" taille={compact ? 18 : 24} className={styles.fleche} />
        <p className={styles.invite}>
          {compact ? (
            <strong>Déposez une photo, une radio, une empreinte</strong>
          ) : (
            <>
              <strong>Déposez vos fichiers ici</strong> — photos, radios, empreintes,
              documents.
            </>
          )}
        </p>
        <Bouton variante="secondaire" disabled={envoi} onClick={() => champ.current?.click()}>
          {envoi ? "Importation…" : "Choisir des fichiers"}
        </Bouton>
        <input
          ref={champ}
          type="file"
          multiple
          hidden
          accept={formats.join(",")}
          onChange={(event) => void importer(event.target.files)}
        />
        {!compact && (
          <p className={styles.formats}>
            {formats.length > 0 && (
              <>
                {formats.map((f) => f.replace(".", "").toUpperCase()).join(" · ")}
                {maxOctets > 0 && ` — ${Math.round(maxOctets / (1024 * 1024))} Mo par fichier`}
              </>
            )}
          </p>
        )}
      </div>

      {message && (
        <p className="muted" role="status" style={{ margin: 0 }}>
          {message}
        </p>
      )}

      {pieces.state === "loading" && <Squelette lignes={2} />}
      {pieces.state === "ready" && liste.length === 0 && !compact && (
        <EtatVide titre="Aucune pièce jointe">
          Les fichiers importés ici accompagnent le dossier. Vous vous y référez en
          rédigeant ; Oris ne les interprète pas.
        </EtatVide>
      )}

      {liste.length > 0 && (
        <ul className={styles.liste}>
          {liste.map((piece) => (
            <li key={piece.id} className={styles.piece}>
              <a
                className={styles.lien}
                href={`${API_BASE_URL}/patients/attachments/${piece.id}/contenu`}
                target="_blank"
                rel="noreferrer"
              >
                {piece.kind === "photo" ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    className={styles.vignette}
                    src={`${API_BASE_URL}/patients/attachments/${piece.id}/contenu`}
                    alt=""
                  />
                ) : (
                  <span className={styles.vignetteVide}>
                    {piece.filename.split(".").pop()?.toUpperCase()}
                  </span>
                )}
                <span className={styles.texte}>
                  <span className={styles.nom}>{piece.filename}</span>
                  <span className={styles.detail}>
                    {poids(piece.byte_size)} · {formatDateTime(piece.created_at)}
                  </span>
                </span>
              </a>
              <span className={styles.fin}>
                {!compact && <Pastille>{NATURE[piece.kind] ?? piece.kind}</Pastille>}
                <button
                  type="button"
                  className={styles.retirer}
                  onClick={() => void retirer(piece)}
                  title="Retirer cette pièce"
                >
                  retirer
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
