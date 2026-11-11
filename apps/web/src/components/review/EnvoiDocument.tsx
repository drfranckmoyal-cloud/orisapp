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
/** Ce qu'Oris sait du dépôt du document dans le dossier SmileCloud du patient. */
interface DepotSmileCloud {
  etat: "absent" | "en_attente" | "depose" | "impossible";
  raison: string;
}

export function EnvoiDocument({
  documentId,
  version,
  onEnvoye,
  onEditer,
  smilecloudRelie = false,
  valide = false,
}: {
  documentId: string;
  version: number;
  onEnvoye: () => void;
  onEditer: () => void;
  /** Le patient est relié à son dossier SmileCloud. */
  smilecloudRelie?: boolean;
  /** Seul un document validé part dans SmileCloud : ce qui y entre y reste. */
  valide?: boolean;
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
  // Le dossier SmileCloud du patient est un destinataire comme les autres (Franck,
  // 11/11/2026 : « pouvoir envoyer le CR sur le dossier SmileCloud, assez facilement »).
  const [depot, rechargerDepot] = useApi<DepotSmileCloud>(
    `/documents/${documentId}/smilecloud?v=${version}`,
  );
  const [versSmileCloud, setVersSmileCloud] = useState<boolean | null>(null);
  const [retourSmileCloud, setRetourSmileCloud] = useState<string | null>(null);

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
  const etatDepot = depot.state === "ready" ? depot.data.etat : "absent";
  const smilecloudPossible = smilecloudRelie && valide;
  const smilecloud =
    smilecloudPossible && (versSmileCloud ?? etatDepot === "absent");
  const total = nombre + (smilecloud ? 1 : 0);

  async function deposerDansSmileCloud(): Promise<string> {
    try {
      const fait = await apiRequest<DepotSmileCloud>(`/documents/${documentId}/smilecloud`, {
        method: "POST",
      });
      return fait.etat === "depose"
        ? "Déjà rangé dans le dossier SmileCloud."
        : "Demandé au dossier SmileCloud : l’extension Chrome le dépose à son prochain passage.";
    } catch (caught) {
      const code = caught instanceof ApiError ? caught.code : "UNKNOWN";
      return `SmileCloud : ${errorMessage(code)}`;
    } finally {
      rechargerDepot();
    }
  }

  async function envoyer() {
    setErreur(null);
    setResultats(null);
    setRetourSmileCloud(null);
    setEnvoi("en_cours");
    if (smilecloud) setRetourSmileCloud(await deposerDansSmileCloud());
    if (nombre === 0) {
      setEnvoi("repos");
      onEnvoye();
      return;
    }
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
        <label className={`${styles.destinataire} ${styles.destinataireSmileCloud}`}>
          <input
            type="checkbox"
            checked={smilecloud}
            disabled={!smilecloudPossible}
            onChange={(event) => setVersSmileCloud(event.target.checked)}
          />
          <span>
            <strong>Dossier SmileCloud du patient</strong>
            <span className={styles.adresse}>
              {!smilecloudRelie
                ? "patient pas encore relié à son dossier SmileCloud (fiche patient)"
                : !valide
                  ? "après validation : ce qui entre dans SmileCloud y reste"
                  : etatDepot === "depose"
                    ? "déjà rangé — cochez pour l’y ranger à nouveau"
                    : etatDepot === "en_attente"
                      ? "demandé, en attente de l’extension Chrome"
                      : "le PDF y est rangé avec la documentation"}
            </span>
          </span>
        </label>
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
          disabled={
            total === 0 || (nombre > 0 && !donnees.configure) || envoi === "en_cours"
          }
          onClick={() => void envoyer()}
        >
          {envoi === "en_cours"
            ? "Envoi…"
            : `Envoyer${total > 0 ? ` à ${total} destinataire${total > 1 ? "s" : ""}` : ""}`}
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
      {retourSmileCloud && <p className={styles.envoiNote}>{retourSmileCloud}</p>}
      {erreur && <p className={styles.erreur}>{erreur}</p>}
    </section>
  );
}
