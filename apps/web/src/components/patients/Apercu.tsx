"use client";

import { useEffect } from "react";

import { Bouton } from "@/components/ui";
import type { Attachment } from "@/lib/api";

import styles from "./apercu.module.css";
import { VisionneuseStl } from "./VisionneuseStl";

/** Formats qu'un navigateur sait afficher lui-même, sans aide. */
const IMAGES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);

function estStl(piece: Attachment): boolean {
  return piece.filename.toLowerCase().endsWith(".stl");
}

/** Aperçu d'une pièce jointe, à la manière d'un coup d'œil rapide.
 *
 * Un clic ne doit jamais déclencher un téléchargement sans prévenir : on montre
 * d'abord, on télécharge si on le demande. Quand un format n'est pas affichable,
 * on le dit franchement plutôt que de lancer le fichier dans le vide.
 */
export function Apercu({
  piece,
  url,
  onFermer,
}: {
  piece: Attachment;
  url: string;
  onFermer: () => void;
}) {
  useEffect(() => {
    const surTouche = (evenement: KeyboardEvent) => {
      if (evenement.key === "Escape") onFermer();
    };
    document.addEventListener("keydown", surTouche);
    return () => document.removeEventListener("keydown", surTouche);
  }, [onFermer]);

  return (
    <div
      className={styles.voile}
      role="dialog"
      aria-modal="true"
      aria-label={`Aperçu de ${piece.filename}`}
      onClick={onFermer}
    >
      <div className={styles.fenetre} onClick={(evenement) => evenement.stopPropagation()}>
        <header className={styles.entete}>
          <span className={styles.nom}>{piece.filename}</span>
          <button type="button" className={styles.fermer} onClick={onFermer} aria-label="Fermer">
            ✕
          </button>
        </header>

        <div className={styles.corps}>
          {IMAGES.has(piece.media_type) ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={url} alt={piece.filename} className={styles.image} />
          ) : piece.media_type === "application/pdf" ? (
            <iframe src={url} title={piece.filename} className={styles.cadre} />
          ) : estStl(piece) ? (
            <VisionneuseStl url={url} />
          ) : (
            <p className={styles.indisponible}>
              Ce format ne s’affiche pas ici — ouvrez-le avec le logiciel de votre
              ordinateur.
              {piece.media_type === "image/heic" || piece.media_type === "image/heif"
                ? " Les photos HEIC de l’iPhone ne sont lisibles que par Safari."
                : ""}
            </p>
          )}
        </div>

        <footer className={styles.pied}>
          <Bouton variante="secondaire" onClick={() => window.open(url, "_blank", "noopener")}>
            Ouvrir dans un onglet
          </Bouton>
          <a className={styles.telecharger} href={url} download={piece.filename}>
            Télécharger
          </a>
        </footer>
      </div>
    </div>
  );
}
