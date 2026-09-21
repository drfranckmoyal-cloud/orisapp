"use client";

import { useState } from "react";

import { Bouton } from "@/components/ui";
import {
  API_BASE_URL,
  ApiError,
  apiRequest,
  type Attachment,
  type FigureDocument,
} from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./consultation.module.css";

/** Ce qu'un PDF sait poser. Une photo HEIC de l'iPhone doit d'abord être convertie. */
const IMPRIMABLES = new Set(["image/jpeg", "image/png", "image/webp"]);

function vignette(id: string): string {
  return `${API_BASE_URL}/patients/attachments/${id}/contenu`;
}

/** « Documentation clinique » : les photos du document, légendées, sur la dernière page.
 *
 * On choisit parmi les pièces jointes du patient ; la première s'imprime en grand, les
 * suivantes deux par ligne. Oris ne regarde pas les photos : il les place.
 */
export function Documentation({
  documentId,
  patientId,
}: {
  documentId: string;
  patientId: string;
}) {
  const [figures, recharger] = useApi<FigureDocument[]>(
    `/documents/${documentId}/figures`,
  );
  const [pieces] = useApi<Attachment[]>(`/patients/${patientId}/attachments`);
  const [choix, setChoix] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [brouillons, setBrouillons] = useState<Record<string, string>>({});

  const posees = figures.state === "ready" ? figures.data : [];
  const photos =
    pieces.state === "ready"
      ? pieces.data.filter((p) => p.media_type.startsWith("image/"))
      : [];
  const disponibles = photos.filter(
    (p) => !posees.some((f) => f.attachment_id === p.id),
  );
  const nonImprimables = disponibles.filter(
    (p) => !IMPRIMABLES.has(p.media_type),
  ).length;

  async function poser(liste: { attachment_id: string; caption: string }[]) {
    setErreur(null);
    try {
      await apiRequest(`/documents/${documentId}/figures`, {
        method: "PUT",
        body: { figures: liste },
      });
      recharger();
    } catch (caught) {
      setErreur(
        errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"),
      );
    }
  }

  const actuelles = () =>
    posees.map((f) => ({
      attachment_id: f.attachment_id,
      caption: brouillons[f.attachment_id] ?? f.caption,
    }));

  function deplacer(index: number, pas: number) {
    const liste = actuelles();
    const cible = index + pas;
    if (cible < 0 || cible >= liste.length) return;
    const [deplacee] = liste.splice(index, 1);
    if (deplacee) liste.splice(cible, 0, deplacee);
    void poser(liste);
  }

  return (
    <div className={styles.documentation}>
      <div className={styles.documentationTete}>
        <strong>Documentation clinique</strong>
        <span>
          {posees.length === 0
            ? "Aucune photo : la page n’est pas imprimée."
            : `${posees.length} photo${posees.length > 1 ? "s" : ""}, sur une page à part en fin de document.`}
        </span>
      </div>

      {posees.length > 0 && (
        <ol className={styles.figures}>
          {posees.map((figure, index) => (
            <li key={figure.attachment_id} className={styles.figure}>
              {/* eslint-disable-next-line @next/next/no-img-element -- fichier servi par l'API */}
              <img src={vignette(figure.attachment_id)} alt={figure.filename} />
              <div className={styles.figureTexte}>
                <span className={styles.figureNumero}>
                  Fig. {index + 1}
                  {index === 0 && " · grand format"}
                </span>
                <input
                  className={styles.choix}
                  value={brouillons[figure.attachment_id] ?? figure.caption}
                  placeholder="Légende"
                  maxLength={300}
                  onChange={(event) =>
                    setBrouillons((b) => ({
                      ...b,
                      [figure.attachment_id]: event.target.value,
                    }))
                  }
                  onBlur={() => void poser(actuelles())}
                />
              </div>
              <div className={styles.figureOutils}>
                <button
                  type="button"
                  aria-label="Monter"
                  disabled={index === 0}
                  onClick={() => deplacer(index, -1)}
                >
                  ↑
                </button>
                <button
                  type="button"
                  aria-label="Descendre"
                  disabled={index === posees.length - 1}
                  onClick={() => deplacer(index, 1)}
                >
                  ↓
                </button>
                <button
                  type="button"
                  aria-label="Retirer du document"
                  onClick={() =>
                    void poser(
                      actuelles().filter(
                        (f) => f.attachment_id !== figure.attachment_id,
                      ),
                    )
                  }
                >
                  ×
                </button>
              </div>
            </li>
          ))}
        </ol>
      )}

      {!choix ? (
        <Bouton variante="discret" onClick={() => setChoix(true)}>
          + Ajouter des photos
        </Bouton>
      ) : (
        <div className={styles.galerie}>
          {disponibles.length === 0 && (
            <span className={styles.envoiRien}>
              Aucune autre photo dans les pièces jointes du patient.
            </span>
          )}
          {disponibles.map((piece) => {
            const imprimable = IMPRIMABLES.has(piece.media_type);
            return (
              <button
                key={piece.id}
                type="button"
                className={styles.galeriePhoto}
                disabled={!imprimable}
                title={
                  imprimable
                    ? `Ajouter ${piece.filename}`
                    : "Format HEIC : pas encore imprimable"
                }
                onClick={() =>
                  void poser([
                    ...actuelles(),
                    { attachment_id: piece.id, caption: "" },
                  ])
                }
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- fichier servi par l'API */}
                <img src={vignette(piece.id)} alt={piece.filename} />
              </button>
            );
          })}
          <div className={styles.galerieFin}>
            {nonImprimables > 0 && (
              <span className={styles.envoiRien}>
                {nonImprimables} photo{nonImprimables > 1 ? "s" : ""} HEIC
                grisée
                {nonImprimables > 1 ? "s" : ""} : pas encore imprimable
                {nonImprimables > 1 ? "s" : ""}.
              </span>
            )}
            <Bouton variante="secondaire" onClick={() => setChoix(false)}>
              Fermer
            </Bouton>
          </div>
        </div>
      )}
      {erreur && <p className={styles.erreur}>{erreur}</p>}
    </div>
  );
}
