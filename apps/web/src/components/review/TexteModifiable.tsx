"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";

import { ApiError, apiRequest, type Claim, type DocumentView } from "@/lib/api";
import { errorMessage } from "@/lib/labels";

import { DocumentBody } from "./DocumentView";
import styles from "./relecture.module.css";

export type EtatTexte = "repos" | "saisie" | "enregistrement" | "enregistre" | "erreur";

/** Le texte du document, modifiable à même la page.
 *
 * Franck, le 10/11/2026 : « la page s'ouvre directement modifiable ». Plus de bouton
 * « Éditer » ni de bandeau : on clique dans le texte, on écrit, c'est enregistré tout
 * seul. Tant qu'on n'a rien tapé, rien ne change — le texte rédigé par Claude garde ses
 * phrases rattachées au dossier. À la première frappe, il devient celui du praticien
 * (§48) : Oris ne le vérifie plus contre le dossier, et le dit.
 */
export function TexteModifiable({
  document,
  modifiable,
  selected,
  onSelect,
  onEtat,
  onEnregistre,
}: {
  document: DocumentView;
  /** Faux pour un document validé ou en mode ombre : on lit, on n'écrit pas. */
  modifiable: boolean;
  selected: Claim | null;
  onSelect: (claim: Claim) => void;
  onEtat: (etat: EtatTexte, message?: string) => void;
  /** Le texte a changé et l'édition est finie : la page recharge le document. */
  onEnregistre: () => void;
}) {
  const [edition, setEdition] = useState<{ texte: string; curseur: number } | null>(null);
  const zone = useRef<HTMLTextAreaElement | null>(null);
  const minuterie = useRef<number | null>(null);
  // Ce que le serveur a : sert à ne rien envoyer quand rien n'a bougé.
  const enregistre = useRef(document.content);
  const courant = useRef(document.content);
  const aChange = useRef(false);
  const enVol = useRef<Promise<void> | null>(null);

  async function envoyer(): Promise<void> {
    const texte = courant.current.trim();
    if (!texte || texte === enregistre.current.trim()) return;
    onEtat("enregistrement");
    try {
      await apiRequest(`/documents/${document.id}/text`, {
        method: "POST",
        body: { content: texte },
      });
      enregistre.current = texte;
      aChange.current = true;
      onEtat("enregistre");
    } catch (caught) {
      const code = caught instanceof ApiError ? caught.code : "UNKNOWN";
      // Le serveur a déjà ce texte : ce n'est pas une erreur.
      if (code === "NO_CHANGE") {
        enregistre.current = texte;
        onEtat("enregistre");
      } else {
        onEtat("erreur", errorMessage(code));
      }
    }
  }

  function enregistrerBientot() {
    if (minuterie.current !== null) window.clearTimeout(minuterie.current);
    minuterie.current = window.setTimeout(() => {
      minuterie.current = null;
      enVol.current = envoyer();
    }, 900);
  }

  async function finir() {
    if (minuterie.current !== null) {
      window.clearTimeout(minuterie.current);
      minuterie.current = null;
    }
    await enVol.current;
    await envoyer();
    setEdition(null);
    if (aChange.current) {
      aChange.current = false;
      onEnregistre();
    } else {
      onEtat("repos");
    }
  }

  // La zone épouse son texte : pas d'ascenseur dans la feuille.
  useLayoutEffect(() => {
    const element = zone.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${element.scrollHeight}px`;
  }, [edition?.texte]);

  // À l'ouverture, le curseur va là où l'on a cliqué.
  const ouverte = edition !== null;
  useEffect(() => {
    const element = zone.current;
    if (!ouverte || !element) return;
    element.focus({ preventScroll: true });
    const position = Math.min(edition?.curseur ?? 0, element.value.length);
    element.setSelectionRange(position, position);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- à l'ouverture seulement
  }, [ouverte]);

  // Changer de document ou quitter la page n'emporte pas ce qui vient d'être tapé.
  useEffect(
    () => () => {
      if (minuterie.current !== null) window.clearTimeout(minuterie.current);
      void envoyer();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps -- au démontage seulement
    [],
  );

  if (edition === null) {
    return (
      <div className={styles.texte}>
        <DocumentBody
          document={document}
          selected={selected}
          onSelect={onSelect}
          onEdit={
            modifiable
              ? (position) => {
                  courant.current = document.content;
                  enregistre.current = document.content;
                  setEdition({ texte: document.content, curseur: position });
                  onEtat("saisie");
                }
              : undefined
          }
        />
      </div>
    );
  }

  return (
    <div className={styles.texte}>
      {document.claims.length > 0 && (
        <p className={styles.noteEdition}>
          Vous écrivez à la main : dès la première modification, ce texte devient le vôtre,
          et Oris ne le vérifie plus contre le dossier clinique. Pour corriger une donnée
          clinique, passez plutôt par « Corriger avec Claude ».
        </p>
      )}
      <textarea
        ref={zone}
        className={styles.zoneTexte}
        value={edition.texte}
        aria-label="Texte du document"
        spellCheck
        onChange={(event) => {
          courant.current = event.target.value;
          setEdition({ texte: event.target.value, curseur: edition.curseur });
          onEtat("saisie");
          enregistrerBientot();
        }}
        onBlur={() => void finir()}
        onKeyDown={(event) => {
          if (event.key === "Escape") event.currentTarget.blur();
        }}
      />
    </div>
  );
}
