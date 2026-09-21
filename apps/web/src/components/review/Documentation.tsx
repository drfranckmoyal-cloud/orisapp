"use client";

import { type DragEvent, useRef, useState } from "react";

import { Icone } from "@/components/Icones";
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

import { RetoucheImage } from "./RetoucheImage";
import styles from "./consultation.module.css";

/** Photos qu'Oris sait imprimer ; un HEIC d'iPhone est converti en JPEG au passage. */
const IMPRIMABLES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/heic",
  "image/heif",
]);

/** L'aperçu converti par le serveur : un HEIC s'affiche dans tous les navigateurs. */
function vignette(id: string): string {
  return `${API_BASE_URL}/patients/attachments/${id}/apercu`;
}

type Format = "large" | "demi";
type Figure = { attachment_id: string; caption: string; format?: Format };

/** Ce qui est en cours de correction : une photo déposée, ou une pièce déjà rangée. */
type Retouche = {
  source: string;
  nom: string;
  fichier?: File;
  pieceId?: string;
  legende?: string | undefined;
  remplace?: string | undefined; // la figure dont la photo est remplacée par sa version corrigée
};

/** « Documentation clinique » : les photos du document, légendées, sur la dernière page.
 *
 * Deux sens : une photo déposée ici rejoint les pièces jointes du patient (rattachée à
 * la consultation) ; une pièce jointe déjà rangée peut être choisie ici. Toute photo
 * passe par une correction possible — recadrer, retourner — avant d'être posée.
 */
export function Documentation({
  documentId,
  patientId,
  encounterId,
}: {
  documentId: string;
  patientId: string;
  encounterId: string;
}) {
  const [figures, recharger] = useApi<FigureDocument[]>(
    `/documents/${documentId}/figures`,
  );
  const [pieces, rechargerPieces] = useApi<Attachment[]>(
    `/patients/${patientId}/attachments`,
  );
  const [galerie, setGalerie] = useState(false);
  const [retouche, setRetouche] = useState<Retouche | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [travail, setTravail] = useState(false);
  // La photo dont on confirme la suppression (déposée par erreur).
  const [aSupprimer, setASupprimer] = useState<string | null>(null);
  const [survol, setSurvol] = useState(false);
  const [brouillons, setBrouillons] = useState<Record<string, string>>({});
  const champ = useRef<HTMLInputElement>(null);

  const posees = figures.state === "ready" ? figures.data : [];
  const photos =
    pieces.state === "ready"
      ? pieces.data.filter((p) => p.media_type.startsWith("image/"))
      : [];
  const disponibles = photos.filter(
    (p) => !posees.some((f) => f.attachment_id === p.id),
  );

  const actuelles = (): Figure[] =>
    posees.map((f) => ({
      attachment_id: f.attachment_id,
      caption: brouillons[f.attachment_id] ?? f.caption,
      format: f.format,
    }));

  function changerFormat(id: string, format: Format) {
    void poser(
      actuelles().map((f) => (f.attachment_id === id ? { ...f, format } : f)),
    );
  }

  async function poser(liste: Figure[]) {
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

  /** Range une image dans les pièces jointes du patient, rattachée à la consultation. */
  async function ranger(image: Blob, nom: string): Promise<string> {
    const corps = new FormData();
    corps.append("files", image, nom);
    corps.append("encounter_id", encounterId);
    const reponse = await fetch(
      `${API_BASE_URL}/patients/${patientId}/attachments`,
      {
        method: "POST",
        body: corps,
      },
    );
    const donnees: unknown = await reponse.json().catch(() => null);
    if (!reponse.ok || !Array.isArray(donnees) || donnees.length === 0) {
      const code =
        typeof donnees === "object" && donnees !== null && "code" in donnees
          ? String((donnees as { code: unknown }).code)
          : "UNKNOWN";
      throw new ApiError(reponse.status, code);
    }
    return String((donnees[0] as { id: string }).id);
  }

  function ouvrirFichier(fichier: File) {
    if (!fichier.type.startsWith("image/")) {
      setErreur(
        "Seules les photos se posent ici ; les autres fichiers vont dans les pièces jointes.",
      );
      return;
    }
    setRetouche({
      source: URL.createObjectURL(fichier),
      nom: fichier.name,
      fichier,
    });
  }

  async function ouvrirPiece(
    piece: { id: string; filename: string },
    remplace?: string,
  ) {
    setErreur(null);
    try {
      // Par un blob local : une image venue d'une autre adresse ne se redessine pas.
      const reponse = await fetch(vignette(piece.id));
      const image = await reponse.blob();
      setRetouche({
        source: URL.createObjectURL(image),
        nom: piece.filename,
        pieceId: piece.id,
        remplace,
        legende: remplace
          ? (brouillons[remplace] ??
            posees.find((f) => f.attachment_id === remplace)?.caption)
          : undefined,
      });
    } catch {
      setErreur(errorMessage("NETWORK_UNREACHABLE"));
    }
  }

  async function terminer(image: Blob | null, legende: string) {
    const en_cours = retouche;
    setRetouche(null);
    if (!en_cours) return;
    URL.revokeObjectURL(en_cours.source);
    setTravail(true);
    setErreur(null);
    try {
      let id = en_cours.pieceId;
      if (image) {
        const base = en_cours.nom.replace(/\.[^.]+$/, "");
        id = await ranger(image, `${base}-corrigee.jpg`);
      } else if (en_cours.fichier) {
        id = await ranger(en_cours.fichier, en_cours.fichier.name);
      }
      if (!id) return;
      const liste = actuelles();
      if (en_cours.remplace) {
        const nouvelle = liste.map((f) =>
          f.attachment_id === en_cours.remplace
            ? { attachment_id: id, caption: legende || f.caption }
            : f,
        );
        await poser(nouvelle);
      } else if (!liste.some((f) => f.attachment_id === id)) {
        await poser([...liste, { attachment_id: id, caption: legende }]);
      }
      rechargerPieces();
      setGalerie(false);
    } catch (caught) {
      setErreur(
        errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"),
      );
    } finally {
      setTravail(false);
    }
  }

  /** Retire la photo du document, puis la supprime des pièces jointes du patient. */
  async function supprimer(id: string) {
    setASupprimer(null);
    setErreur(null);
    try {
      await poser(actuelles().filter((f) => f.attachment_id !== id));
      const reponse = await fetch(
        `${API_BASE_URL}/patients/attachments/${id}`,
        {
          method: "DELETE",
        },
      );
      if (!reponse.ok)
        throw new ApiError(reponse.status, `HTTP_${reponse.status}`);
      rechargerPieces();
    } catch (caught) {
      setErreur(
        errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"),
      );
    }
  }

  function deplacer(index: number, pas: number) {
    const liste = actuelles();
    const cible = index + pas;
    if (cible < 0 || cible >= liste.length) return;
    const [deplacee] = liste.splice(index, 1);
    if (deplacee) liste.splice(cible, 0, deplacee);
    void poser(liste);
  }

  function deposer(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    setSurvol(false);
    const fichier = event.dataTransfer.files[0];
    if (fichier) ouvrirFichier(fichier);
  }

  return (
    <section
      className={styles.documentation}
      data-survol={survol}
      aria-label="Documentation clinique"
      onDragOver={(event) => {
        event.preventDefault();
        setSurvol(true);
      }}
      onDragLeave={() => setSurvol(false)}
      onDrop={deposer}
    >
      <header className={styles.documentationTete}>
        <h3>Documentation clinique</h3>
        <span>
          {posees.length === 0
            ? "Aucune photo : la page n’est pas imprimée."
            : `${posees.length} photo${posees.length > 1 ? "s" : ""} · page à part, en fin de document.`}
        </span>
      </header>

      {posees.length > 0 && (
        <ol className={styles.figures}>
          {posees.map((figure, index) => (
            <li
              key={figure.attachment_id}
              className={styles.figure}
              data-format={figure.format}
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- fichier servi par l'API */}
              <img src={vignette(figure.attachment_id)} alt={figure.filename} />
              <div className={styles.figureTexte}>
                <span className={styles.figureNumero}>Fig. {index + 1}</span>
                {/* La taille à l'impression : c'est le praticien qui choisit. */}
                <div
                  className={styles.format}
                  role="group"
                  aria-label="Taille à l'impression"
                >
                  {(["large", "demi"] as const).map((format) => (
                    <button
                      key={format}
                      type="button"
                      aria-pressed={figure.format === format}
                      onClick={() =>
                        changerFormat(figure.attachment_id, format)
                      }
                    >
                      {format === "large" ? "Pleine largeur" : "Moitié"}
                    </button>
                  ))}
                </div>
                <input
                  className={styles.choix}
                  value={brouillons[figure.attachment_id] ?? figure.caption}
                  placeholder="Légende sous la photo"
                  aria-label={`Légende de la figure ${index + 1}`}
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
                  className={styles.corriger}
                  onClick={() =>
                    void ouvrirPiece(
                      { id: figure.attachment_id, filename: figure.filename },
                      figure.attachment_id,
                    )
                  }
                >
                  Corriger
                </button>
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
                  title="Retirer du document (la photo reste dans les pièces jointes)"
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
                <button
                  type="button"
                  className={styles.supprimerPhoto}
                  title="Supprimer la photo (déposée par erreur)"
                  aria-label="Supprimer la photo"
                  onClick={() => setASupprimer(figure.attachment_id)}
                >
                  <Icone nom="corbeille" taille={14} />
                </button>
              </div>
              {aSupprimer === figure.attachment_id && (
                <div className={styles.confirmerSuppression} role="alertdialog">
                  <span>
                    Supprimer définitivement cette photo ? Elle disparaît aussi
                    des pièces jointes du patient.
                  </span>
                  <div>
                    <button
                      type="button"
                      className={styles.supprimerFort}
                      onClick={() => void supprimer(figure.attachment_id)}
                    >
                      Supprimer
                    </button>
                    <button type="button" onClick={() => setASupprimer(null)}>
                      Annuler
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}

      <div className={styles.depot}>
        <Bouton disabled={travail} onClick={() => champ.current?.click()}>
          {travail ? "Enregistrement…" : "+ Déposer une photo"}
        </Bouton>
        <Bouton variante="secondaire" onClick={() => setGalerie((v) => !v)}>
          Choisir dans les pièces jointes
        </Bouton>
        <span>ou glissez une photo dans ce cadre</span>
        <input
          ref={champ}
          type="file"
          accept="image/*"
          hidden
          onChange={(event) => {
            const fichier = event.target.files?.[0];
            if (fichier) ouvrirFichier(fichier);
            event.target.value = "";
          }}
        />
      </div>

      {galerie && (
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
                    : "Format non imprimable"
                }
                onClick={() => void ouvrirPiece(piece)}
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- fichier servi par l'API */}
                <img src={vignette(piece.id)} alt={piece.filename} />
              </button>
            );
          })}
        </div>
      )}

      {erreur && <p className={styles.erreur}>{erreur}</p>}

      {retouche && (
        <RetoucheImage
          source={retouche.source}
          nom={retouche.nom}
          legendeInitiale={retouche.legende ?? ""}
          onValider={(image, legende) => void terminer(image, legende)}
          onAnnuler={() => {
            URL.revokeObjectURL(retouche.source);
            setRetouche(null);
          }}
        />
      )}
    </section>
  );
}
