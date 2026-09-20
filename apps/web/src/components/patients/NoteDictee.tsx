"use client";

import { useRef, useState } from "react";

import { Icone } from "@/components/Icones";
import { ApiError, API_BASE_URL } from "@/lib/api";
import { Dictation } from "@/lib/audio/dictation";
import { errorMessage } from "@/lib/labels";

import styles from "./note.module.css";

const NOTE_MAX = 500;

/** La note administrative, écrite ou dictée.
 *
 * Le son part dans la requête et n'est jamais conservé : il revient en texte, que
 * le praticien relit avant d'enregistrer. Rien de ce qui est dicté ici n'entre dans
 * un dossier clinique — c'est une note d'organisation, pas un compte rendu.
 */
export function NoteDictee({
  patientId,
  valeur,
  initiale,
  onChange,
  onEnregistrer,
}: {
  patientId: string;
  valeur: string;
  initiale: string;
  onChange: (texte: string) => void;
  onEnregistrer: (texte: string) => Promise<void>;
}) {
  const [dicte, setDicte] = useState(false);
  const [etat, setEtat] = useState<string | null>(null);
  const dictee = useRef<Dictation | null>(null);

  async function basculer() {
    if (dicte) {
      setDicte(false);
      setEtat("transcription…");
      try {
        const pcm = await dictee.current?.stop();
        dictee.current = null;
        if (!pcm || pcm.length === 0) {
          setEtat("rien entendu");
          return;
        }
        const reponse = await fetch(`${API_BASE_URL}/patients/${patientId}/note/dictation`, {
          method: "POST",
          headers: { "Content-Type": "audio/pcm;rate=16000;channels=1;encoding=s16le" },
          body: pcm as BodyInit,
        });
        const corps: unknown = await reponse.json().catch(() => null);
        if (!reponse.ok) {
          const code =
            typeof corps === "object" && corps !== null && "code" in corps
              ? String((corps as { code: unknown }).code)
              : "UNKNOWN";
          throw new ApiError(reponse.status, code);
        }
        const texte = String((corps as { text?: unknown })?.text ?? "").trim();
        if (!texte) {
          setEtat("rien entendu");
          return;
        }
        // On ajoute à ce qui est déjà écrit : dicter ne doit jamais effacer.
        const suite = valeur.trim() ? `${valeur.trim()} ${texte}` : texte;
        onChange(suite.slice(0, NOTE_MAX));
        setEtat("à relire, puis quittez le champ");
      } catch (error) {
        setEtat(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
      }
      return;
    }
    setEtat(null);
    try {
      dictee.current = new Dictation();
      await dictee.current.start();
      setDicte(true);
    } catch {
      dictee.current = null;
      setEtat(errorMessage("microphone_unavailable"));
    }
  }

  return (
    <span className={styles.bloc}>
      <textarea
        className={styles.champ}
        rows={1}
        maxLength={NOTE_MAX}
        placeholder="Rappel pratique — horaires, rappel à passer…"
        aria-label="Note administrative"
        value={valeur}
        onChange={(event) => onChange(event.target.value)}
        onBlur={(event) => {
          if (event.target.value.trim() === initiale.trim()) return;
          setEtat("enregistrement…");
          onEnregistrer(event.target.value).then(
            () => setEtat("enregistrée"),
            (error: unknown) =>
              setEtat(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN")),
          );
        }}
      />
      <button
        type="button"
        className={`${styles.micro} ${dicte ? styles.enCours : ""}`}
        onClick={() => void basculer()}
        aria-pressed={dicte}
        title={dicte ? "Arrêter et transcrire" : "Dicter la note"}
      >
        <Icone nom="micro" taille={15} />
        <span className="sr-only">{dicte ? "Arrêter la dictée" : "Dicter la note"}</span>
      </button>
      {etat && <span className={styles.etat}>{etat}</span>}
    </span>
  );
}
