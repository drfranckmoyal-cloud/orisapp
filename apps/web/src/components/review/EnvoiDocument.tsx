"use client";

import { useState } from "react";

import { Bouton } from "@/components/ui";
import {
  ApiError,
  apiRequest,
  type EnvoiPrepare,
  fetchDocumentExport,
  type ResultatEnvoi,
} from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./consultation.module.css";

const RAISON: Record<string, string> = {
  SENDING_EMAIL_MISSING:
    "Aucune adresse d’envoi sur votre profil : renseignez-la dans Paramètres › Praticien et cabinet.",
  SMTP_NOT_CONFIGURED:
    "La boîte d’envoi n’est pas encore branchée : le mot de passe d’application de votre messagerie reste à ajouter (voir Paramètres).",
};

/** Envoyer ce document par courriel, l'imprimer, ou revenir au texte.
 *
 * Les destinataires viennent de la fiche du patient ; le correspondant principal est
 * coché d'office. Chaque destinataire reçoit son propre message, le PDF joint.
 */
export function EnvoiDocument({
  documentId,
  version,
  onEnvoye,
  onEditer,
}: {
  documentId: string;
  version: number;
  onEnvoye: () => void;
  onEditer: () => void;
}) {
  const [prepare] = useApi<EnvoiPrepare>(
    `/documents/${documentId}/envoi?v=${version}`,
  );
  const [coches, setCoches] = useState<Record<string, boolean> | null>(null);
  // Une adresse par champ ; « + » en ajoute un.
  const [autres, setAutres] = useState<string[]>([""]);
  const [objet, setObjet] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState<"repos" | "en_cours">("repos");
  const [resultats, setResultats] = useState<ResultatEnvoi[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  if (prepare.state !== "ready") return null;
  const donnees = prepare.data;
  const etat =
    coches ??
    Object.fromEntries(donnees.candidats.map((c) => [c.cle, c.coche]));
  const choisis = donnees.candidats
    .filter((c) => etat[c.cle])
    .map((c) => c.cle);
  const libres = autres.map((a) => a.trim()).filter(Boolean);
  const nombre = choisis.length + libres.length;

  async function envoyer() {
    setErreur(null);
    setResultats(null);
    setEnvoi("en_cours");
    try {
      const retour = await apiRequest<ResultatEnvoi[]>(
        `/documents/${documentId}/envoi`,
        {
          method: "POST",
          body: {
            destinataires: choisis,
            adresses: libres,
            objet: objet ?? donnees.objet,
            message: message ?? donnees.message,
          },
        },
      );
      setResultats(retour);
      setAutres([""]);
      onEnvoye();
    } catch (caught) {
      setErreur(
        errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"),
      );
    } finally {
      setEnvoi("repos");
    }
  }

  async function imprimer() {
    setErreur(null);
    try {
      const { blob } = await fetchDocumentExport(documentId, "pdf");
      const url = URL.createObjectURL(blob);
      // Le PDF s'ouvre dans un onglet, avec son bouton d'impression : le navigateur
      // n'imprime pas de façon fiable un PDF glissé dans la page.
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (caught) {
      setErreur(
        errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"),
      );
    }
  }

  return (
    <section className={styles.envoiMail} aria-label="Envoyer le document">
      <div className={styles.envoiTete}>
        <strong>Envoyer ce document</strong>
        <span>
          {donnees.expediteur
            ? `depuis ${donnees.expediteur}`
            : "aucune adresse d’envoi"}{" "}
          · pièce jointe : {donnees.nom_fichier}
        </span>
      </div>

      {!donnees.configure && donnees.raison && (
        <p className={styles.envoiAlerte}>
          {RAISON[donnees.raison] ?? donnees.raison}
        </p>
      )}
      {donnees.brouillon && (
        <p className={styles.envoiNote}>
          Document non validé : le PDF porte la mention « brouillon ».
        </p>
      )}

      <fieldset className={styles.destinataires}>
        <legend>Destinataires</legend>
        {donnees.candidats.length === 0 && (
          <p className={styles.envoiNote}>
            Ni le patient ni ses correspondants n’ont d’adresse : saisissez-en
            une ci-dessous.
          </p>
        )}
        {donnees.candidats.map((candidat) => (
          <label key={candidat.cle} className={styles.destinataire}>
            <input
              type="checkbox"
              checked={Boolean(etat[candidat.cle])}
              onChange={(event) =>
                setCoches({ ...etat, [candidat.cle]: event.target.checked })
              }
            />
            <span>
              <strong>{candidat.libelle}</strong>
              {candidat.detail && (
                <span className={styles.envoiNote}> · {candidat.detail}</span>
              )}
              <span className={styles.adresse}>{candidat.email}</span>
            </span>
          </label>
        ))}
        <div className={styles.autresAdresses}>
          {autres.map((adresse, rang) => (
            <div key={rang} className={styles.autreAdresse}>
              <input
                className={styles.choix}
                type="email"
                value={adresse}
                placeholder="Autre adresse"
                aria-label={`Autre adresse ${rang + 1}`}
                onChange={(event) =>
                  setAutres(
                    autres.map((a, i) => (i === rang ? event.target.value : a)),
                  )
                }
              />
              {autres.length > 1 && (
                <button
                  type="button"
                  className={styles.retirer}
                  aria-label="Retirer cette adresse"
                  onClick={() => setAutres(autres.filter((_, i) => i !== rang))}
                >
                  ×
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            className={styles.ajouterAdresse}
            onClick={() => setAutres([...autres, ""])}
          >
            + Ajouter une adresse
          </button>
        </div>
      </fieldset>

      <label className={styles.champEnvoi}>
        Objet
        <input
          className={styles.choix}
          value={objet ?? donnees.objet}
          onChange={(event) => setObjet(event.target.value)}
        />
      </label>
      <label className={styles.champEnvoi}>
        Message
        <textarea
          className={styles.choix}
          rows={8}
          value={message ?? donnees.message}
          onChange={(event) => setMessage(event.target.value)}
        />
      </label>

      <div className={styles.boutonsEnvoi}>
        <Bouton
          disabled={!donnees.configure || nombre === 0 || envoi === "en_cours"}
          onClick={() => void envoyer()}
        >
          {envoi === "en_cours"
            ? "Envoi…"
            : `Envoyer${nombre > 0 ? ` à ${nombre} destinataire${nombre > 1 ? "s" : ""}` : ""}`}
        </Bouton>
        <Bouton variante="secondaire" onClick={() => void imprimer()}>
          Imprimer
        </Bouton>
        <Bouton variante="discret" onClick={onEditer}>
          Modifier le texte
        </Bouton>
      </div>

      {resultats && (
        <ul className={styles.resultats}>
          {resultats.map((r) => (
            <li key={r.destinataire} data-ok={r.envoye}>
              {r.envoye ? "Envoyé à " : "Échec pour "}
              {r.destinataire}
              {r.code && ` — ${errorMessage(r.code)}`}
            </li>
          ))}
        </ul>
      )}
      {erreur && <p className={styles.erreur}>{erreur}</p>}
    </section>
  );
}
