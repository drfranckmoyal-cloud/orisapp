"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";

import {
  ApiError,
  apiRequest,
  type Consignes,
  type LectureAssistant,
  type PropositionRelecture,
  type ResultatAssistant,
  sendVoiceAssistant,
} from "@/lib/api";
import { Dictation } from "@/lib/audio/dictation";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./assistant.module.css";

/** Corriger avec Claude : on dit ce qui ne va pas, Oris dit ce qu'il a compris, on confirme.
 *
 * Franck, le 10/11/2026 : « j'aimerais pouvoir proposer des corrections dans une boîte de
 * dialogue IA ». La case d'avant ne connaissait qu'une liste de tournures. Ici la demande
 * est libre, et Claude dit d'abord de quoi il s'agit — la rédaction, le dossier clinique,
 * la civilité — sans rien changer. Rien ne part sans un clic du praticien.
 */

type Echange =
  | { id: number; qui: "moi"; texte: string }
  | { id: number; qui: "oris"; sorte: "attente"; texte: string }
  | { id: number; qui: "oris"; sorte: "erreur"; texte: string }
  | { id: number; qui: "oris"; sorte: "fait"; texte: string }
  | { id: number; qui: "oris"; sorte: "lecture"; lecture: LectureAssistant }
  | { id: number; qui: "oris"; sorte: "relecture"; propositions: PropositionRelecture[] };

export type AssistantHandle = {
  /** Lance la relecture du document ouvert (bouton de la barre du document). */
  relire: () => void;
};

const NATURE: Record<string, string> = {
  dossier: "Dossier clinique",
  redaction: "Rédaction",
  civilite: "Fiche patient",
  incompris: "À préciser",
};

function codeDe(caught: unknown): string {
  return caught instanceof ApiError ? caught.code : "UNKNOWN";
}

export const AssistantCorrection = forwardRef<
  AssistantHandle,
  {
    encounterId: string;
    /** Le document qu'on regarde : c'est lui qu'une consigne réécrit. */
    documentId: string | null;
    /** Compte rendu ou courrier : les seuls que Claude rédige, donc relit. */
    relisible: boolean;
    /** Oris n'accepte une correction que sur une consultation traitée, hors mode ombre. */
    actif: boolean;
    civilite: string;
    onChange: () => void;
  }
>(function AssistantCorrection(
  { encounterId, documentId, relisible, actif, civilite, onChange },
  ref,
) {
  const [fil, setFil] = useState<Echange[]>([]);
  const [saisie, setSaisie] = useState("");
  const [occupe, setOccupe] = useState(false);
  const [dictee, setDictee] = useState(false);
  const [coches, setCoches] = useState<Record<number, Set<number>>>({});
  const [voirConsignes, setVoirConsignes] = useState(false);
  const [consignes, rechargerConsignes] = useApi<Consignes>(
    `/encounters/${encounterId}/consignes`,
  );
  const compteur = useRef(0);
  const micro = useRef<Dictation | null>(null);
  const bas = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bas.current?.scrollIntoView?.({ block: "nearest" });
  }, [fil]);

  function ajouter(echange: Omit<Echange, "id"> & Record<string, unknown>): number {
    compteur.current += 1;
    const id = compteur.current;
    setFil((courant) => [...courant, { ...echange, id } as Echange]);
    return id;
  }

  function remplacer(id: number, echange: Omit<Echange, "id"> & Record<string, unknown>) {
    setFil((courant) =>
      courant.map((e) => (e.id === id ? ({ ...echange, id } as Echange) : e)),
    );
  }

  async function demander(texte: string) {
    const demande = texte.trim();
    if (!demande || occupe) return;
    setSaisie("");
    ajouter({ qui: "moi", texte: demande });
    const attente = ajouter({ qui: "oris", sorte: "attente", texte: "Je lis votre demande…" });
    setOccupe(true);
    try {
      const lecture = await apiRequest<LectureAssistant>(
        `/encounters/${encounterId}/assistant`,
        { method: "POST", body: { demande } },
      );
      remplacer(attente, { qui: "oris", sorte: "lecture", lecture });
    } catch (caught) {
      remplacer(attente, { qui: "oris", sorte: "erreur", texte: errorMessage(codeDe(caught)) });
    } finally {
      setOccupe(false);
    }
  }

  async function commencerDictee() {
    const enregistreur = new Dictation();
    try {
      await enregistreur.start(() => setDictee(false));
      micro.current = enregistreur;
      setDictee(true);
    } catch {
      ajouter({ qui: "oris", sorte: "erreur", texte: errorMessage("MICROPHONE_UNAVAILABLE") });
    }
  }

  async function finirDictee() {
    const enregistreur = micro.current;
    micro.current = null;
    setDictee(false);
    if (!enregistreur) return;
    const pcm = enregistreur.stop();
    if (pcm.length === 0) {
      ajouter({ qui: "oris", sorte: "erreur", texte: "Rien n’a été entendu." });
      return;
    }
    const attente = ajouter({ qui: "oris", sorte: "attente", texte: "J’écoute votre demande…" });
    setOccupe(true);
    try {
      const lecture = await sendVoiceAssistant(encounterId, pcm);
      // Ce qui a été entendu s'affiche comme une demande écrite : on voit ce qu'Oris a lu.
      setFil((courant) => {
        const sans = courant.filter((e) => e.id !== attente);
        compteur.current += 2;
        return [
          ...sans,
          ...(lecture.demande
            ? [{ id: compteur.current - 1, qui: "moi", texte: lecture.demande } as Echange]
            : []),
          { id: compteur.current, qui: "oris", sorte: "lecture", lecture } as Echange,
        ];
      });
    } catch (caught) {
      remplacer(attente, { qui: "oris", sorte: "erreur", texte: errorMessage(codeDe(caught)) });
    } finally {
      setOccupe(false);
    }
  }

  async function appliquer(id: number, corps: Record<string, unknown>) {
    setOccupe(true);
    remplacer(id, { qui: "oris", sorte: "attente", texte: "J’applique…" });
    try {
      const resultat = await apiRequest<ResultatAssistant>(
        `/encounters/${encounterId}/assistant/appliquer`,
        { method: "POST", body: { ...corps, ...(documentId ? { document_id: documentId } : {}) } },
      );
      remplacer(id, { qui: "oris", sorte: "fait", texte: resultat.message });
      rechargerConsignes();
      onChange();
    } catch (caught) {
      remplacer(id, { qui: "oris", sorte: "erreur", texte: errorMessage(codeDe(caught)) });
    } finally {
      setOccupe(false);
    }
  }

  function appliquerLecture(id: number, lecture: LectureAssistant, retenir = false) {
    if (lecture.nature === "dossier") {
      return appliquer(id, {
        nature: "dossier",
        operations: lecture.operations,
        expected_object_version: lecture.object_version,
      });
    }
    if (lecture.nature === "civilite") {
      return appliquer(id, { nature: "civilite", civilite: lecture.civilite });
    }
    return appliquer(id, { nature: "redaction", consignes: [lecture.consigne], retenir });
  }

  async function relire() {
    if (!documentId || occupe) return;
    ajouter({ qui: "moi", texte: "Relis ce document et propose des améliorations." });
    const attente = ajouter({ qui: "oris", sorte: "attente", texte: "Je relis le document…" });
    setOccupe(true);
    try {
      const { propositions } = await apiRequest<{ propositions: PropositionRelecture[] }>(
        `/documents/${documentId}/relecture`,
        { method: "POST" },
      );
      if (propositions.length === 0) {
        remplacer(attente, {
          qui: "oris",
          sorte: "fait",
          texte: "Je n’ai rien à proposer : le document se lit bien tel qu’il est.",
        });
      } else {
        remplacer(attente, { qui: "oris", sorte: "relecture", propositions });
        // Tout est coché au départ : décocher est plus rapide que cocher.
        setCoches((c) => ({ ...c, [attente]: new Set(propositions.map((_, i) => i)) }));
      }
    } catch (caught) {
      remplacer(attente, { qui: "oris", sorte: "erreur", texte: errorMessage(codeDe(caught)) });
    } finally {
      setOccupe(false);
    }
  }

  useImperativeHandle(ref, () => ({ relire: () => void relire() }));

  async function retirerConsigne(portee: "consultation" | "praticien", consigne: string) {
    if (consignes.state !== "ready") return;
    try {
      if (portee === "consultation") {
        await apiRequest(`/encounters/${encounterId}/consignes`, {
          method: "PUT",
          body: { consultation: consignes.data.consultation.filter((c) => c !== consigne) },
        });
      } else {
        await apiRequest("/me/preferences", {
          method: "PATCH",
          body: { consignes: consignes.data.praticien.filter((c) => c !== consigne) },
        });
      }
      rechargerConsignes();
    } catch (caught) {
      ajouter({ qui: "oris", sorte: "erreur", texte: errorMessage(codeDe(caught)) });
    }
  }

  const retenues = consignes.state === "ready" ? consignes.data.praticien : [];
  const dIci = consignes.state === "ready" ? consignes.data.consultation : [];
  const suggestions = [
    "Plus court",
    civilite === "madame" ? "C’est un homme" : "C’est une femme",
    "Moins de répétitions",
    "Phrases plus simples",
  ];

  return (
    <section className={styles.assistant} aria-label="Corriger avec Claude">
      <header className={styles.tete}>
        <h2 className={styles.titre}>
          <span className={styles.pastille} aria-hidden="true">
            ✦
          </span>
          Corriger avec Claude
        </h2>
        <p className={styles.sous}>
          Dites ce qui ne va pas, comme à un assistant. Rien ne change sans votre accord.
        </p>
      </header>

      {fil.length > 0 && (
        <div className={styles.fil} aria-live="polite">
          {fil.map((echange) => {
            if (echange.qui === "moi") {
              return (
                <div key={echange.id} className={`${styles.bulle} ${styles.moi}`}>
                  {echange.texte}
                </div>
              );
            }
            if (echange.sorte === "attente" || echange.sorte === "fait" || echange.sorte === "erreur") {
              return (
                <div
                  key={echange.id}
                  className={`${styles.bulle} ${styles.oris}`}
                  data-sorte={echange.sorte}
                  role={echange.sorte === "erreur" ? "alert" : "status"}
                >
                  {echange.sorte === "fait" && <strong>✓ </strong>}
                  {echange.texte}
                </div>
              );
            }
            if (echange.sorte === "relecture") {
              const choisies = coches[echange.id] ?? new Set<number>();
              const retenuesIci = echange.propositions
                .filter((_, i) => choisies.has(i))
                .map((p) => p.consigne);
              return (
                <div key={echange.id} className={`${styles.bulle} ${styles.oris}`}>
                  <strong>Relecture</strong> — {echange.propositions.length} amélioration
                  {echange.propositions.length > 1 ? "s" : ""} possible
                  {echange.propositions.length > 1 ? "s" : ""}, aucune ne touche aux faits :
                  <ul className={styles.propositions}>
                    {echange.propositions.map((proposition, i) => (
                      <li key={i}>
                        <label>
                          <input
                            type="checkbox"
                            checked={choisies.has(i)}
                            onChange={() =>
                              setCoches((c) => {
                                const suite = new Set(c[echange.id] ?? []);
                                if (suite.has(i)) suite.delete(i);
                                else suite.add(i);
                                return { ...c, [echange.id]: suite };
                              })
                            }
                          />
                          <span>
                            <b>{proposition.titre}</b>
                            {proposition.detail}
                          </span>
                        </label>
                      </li>
                    ))}
                  </ul>
                  <div className={styles.choix}>
                    <button
                      type="button"
                      className={styles.principal}
                      disabled={occupe || retenuesIci.length === 0}
                      onClick={() =>
                        void appliquer(echange.id, {
                          nature: "redaction",
                          consignes: retenuesIci,
                          retenir: false,
                        })
                      }
                    >
                      Appliquer{retenuesIci.length > 0 ? ` (${retenuesIci.length})` : ""}
                    </button>
                    <button
                      type="button"
                      className={styles.secondaire}
                      disabled={occupe || retenuesIci.length === 0}
                      title="Ces consignes vaudront aussi pour vos prochains documents"
                      onClick={() =>
                        void appliquer(echange.id, {
                          nature: "redaction",
                          consignes: retenuesIci,
                          retenir: true,
                        })
                      }
                    >
                      Appliquer et retenir
                    </button>
                    <button
                      type="button"
                      className={styles.discret}
                      disabled={occupe}
                      onClick={() =>
                        remplacer(echange.id, {
                          qui: "oris",
                          sorte: "fait",
                          texte: "Propositions écartées : le document n’a pas changé.",
                        })
                      }
                    >
                      Écarter
                    </button>
                  </div>
                </div>
              );
            }
            const { lecture } = echange;
            return (
              <div key={echange.id} className={`${styles.bulle} ${styles.oris}`}>
                <span className={styles.nature} data-nature={lecture.nature}>
                  {NATURE[lecture.nature]}
                </span>
                <div>{lecture.resume}</div>
                {lecture.nature === "redaction" && (
                  <div className={styles.apercu}>Consigne : {lecture.consigne}</div>
                )}
                {lecture.nature !== "incompris" && (
                  <>
                    <div className={styles.choix}>
                      <button
                        type="button"
                        className={styles.principal}
                        disabled={occupe}
                        onClick={() => void appliquerLecture(echange.id, lecture)}
                      >
                        {lecture.nature === "dossier"
                          ? "Corriger le dossier"
                          : lecture.nature === "civilite"
                            ? "Enregistrer dans la fiche"
                            : "Appliquer ici"}
                      </button>
                      {lecture.nature === "redaction" && (
                        <button
                          type="button"
                          className={styles.secondaire}
                          disabled={occupe}
                          title="Cette consigne vaudra aussi pour vos prochains documents"
                          onClick={() => void appliquerLecture(echange.id, lecture, true)}
                        >
                          Appliquer et retenir
                        </button>
                      )}
                      <button
                        type="button"
                        className={styles.discret}
                        disabled={occupe}
                        onClick={() =>
                          remplacer(echange.id, {
                            qui: "oris",
                            sorte: "fait",
                            texte: "Annulé : rien n’a changé.",
                          })
                        }
                      >
                        Annuler
                      </button>
                    </div>
                    <p className={styles.garde}>
                      {lecture.nature === "dossier"
                        ? "Le dossier est corrigé d’abord, puis les documents sont réécrits."
                        : lecture.nature === "redaction"
                          ? "Les garde-fous restent : négations, incertitudes et refus sont vérifiés."
                          : "Tous les documents de ce patient s’accorderont."}
                    </p>
                  </>
                )}
              </div>
            );
          })}
          <div ref={bas} />
        </div>
      )}

      <div className={styles.saisie}>
        <div className={styles.champ} data-dictee={dictee}>
          <input
            value={saisie}
            disabled={!actif || occupe || dictee}
            aria-label="Votre demande de correction"
            placeholder={
              dictee
                ? "Je vous écoute… cliquez le micro pour finir"
                : "« c’est trop long », « la 26 c’est la 27 »…"
            }
            onChange={(event) => setSaisie(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void demander(saisie);
            }}
          />
          <button
            type="button"
            className={styles.micro}
            data-actif={dictee}
            disabled={!actif || occupe}
            title={dictee ? "Arrêter la dictée" : "Dicter la demande"}
            aria-label={dictee ? "Arrêter la dictée" : "Dicter la demande"}
            onClick={() => (dictee ? void finirDictee() : void commencerDictee())}
          >
            <svg viewBox="0 0 20 20" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
              <rect x="7.4" y="2.6" width="5.2" height="9" rx="2.6" />
              <path d="M4.6 9.6a5.4 5.4 0 0 0 10.8 0M10 15v2.6" />
            </svg>
          </button>
          <button
            type="button"
            className={styles.envoi}
            disabled={!actif || occupe || !saisie.trim()}
            title="Envoyer la demande"
            aria-label="Envoyer la demande"
            onClick={() => void demander(saisie)}
          >
            ↑
          </button>
        </div>

        {actif ? (
          <div className={styles.suggestions}>
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                disabled={occupe}
                onClick={() => void demander(suggestion)}
              >
                {suggestion}
              </button>
            ))}
            {relisible && (
              <button type="button" disabled={occupe || !documentId} onClick={() => void relire()}>
                ✦ Relire tout le document
              </button>
            )}
          </div>
        ) : (
          <p className={styles.garde}>
            Les corrections s’ouvrent quand la consultation est traitée.
          </p>
        )}

        {retenues.length + dIci.length > 0 && (
          <div className={styles.consignes}>
            <button type="button" onClick={() => setVoirConsignes((v) => !v)}>
              {retenues.length > 0 &&
                `${retenues.length} consigne${retenues.length > 1 ? "s" : ""} retenue${retenues.length > 1 ? "s" : ""}`}
              {retenues.length > 0 && dIci.length > 0 && " · "}
              {dIci.length > 0 && `${dIci.length} pour cette consultation`}
              <span>{voirConsignes ? "Masquer" : "Voir"}</span>
            </button>
            {voirConsignes && (
              <ul>
                {retenues.map((consigne) => (
                  <li key={`p-${consigne}`}>
                    <span>
                      {consigne} <em>toujours</em>
                    </span>
                    <button
                      type="button"
                      title="Ne plus appliquer cette consigne"
                      aria-label={`Retirer la consigne ${consigne}`}
                      onClick={() => void retirerConsigne("praticien", consigne)}
                    >
                      ×
                    </button>
                  </li>
                ))}
                {dIci
                  .filter((consigne) => !retenues.includes(consigne))
                  .map((consigne) => (
                    <li key={`c-${consigne}`}>
                      <span>
                        {consigne} <em>cette consultation</em>
                      </span>
                      <button
                        type="button"
                        title="Retirer cette consigne"
                        aria-label={`Retirer la consigne ${consigne}`}
                        onClick={() => void retirerConsigne("consultation", consigne)}
                      >
                        ×
                      </button>
                    </li>
                  ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </section>
  );
});
