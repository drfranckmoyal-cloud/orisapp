"use client";

import { useEffect, useState } from "react";

import { Bouton } from "@/components/ui";
import { ApiError, apiRequest } from "@/lib/api";
import { prevenirExtension } from "@/lib/extension";
import { errorMessage, formatDateTime } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./envoyerDossiers.module.css";

/** Où en est le dépôt d'un document dans un dossier (SmileCloud ou Veasy). */
interface Depot {
  etat: "absent" | "en_attente" | "depose" | "impossible";
  raison: string;
  demande_le?: string | null;
  depose_le?: string | null;
}

type EtatLien = "relie" | "trouve" | "a_confirmer" | "ambigu" | "absent" | "sans_liste";

interface LienSmileCloud {
  etat: EtatLien;
  nom: string | null;
  candidats: { case_id: string; nom: string; pour_cent: number }[];
}

interface LienVeasy {
  etat: EtatLien;
  nom: string | null;
  veasy_id: string | null;
  candidats: { veasy_id: string; nom: string; date_naissance: string; pour_cent: number }[];
}

interface Candidat {
  cle: string;
  nom: string;
  detail?: string | undefined;
  pour_cent: number;
}

/** « Envoyer sur le dossier SmileCloud / Veasy » — deux grands boutons, bien visibles, en
 * tête de la colonne de droite (Franck, 25/11/2026). Avant le premier envoi, le dossier
 * du patient se vérifie : Oris propose les plus ressemblants, le praticien confirme. Un
 * compte rendu dans le mauvais dossier est la faute à ne jamais faire. */
export function EnvoyerAuxDossiers({
  patientId,
  documentId,
  version,
  valide,
}: {
  patientId: string;
  documentId: string;
  version: number;
  /** Seul un document validé part : ce qui entre dans un dossier y reste. */
  valide: boolean;
}) {
  return (
    <section className={styles.cadre} aria-labelledby="envoyer-dossiers">
      <h2 id="envoyer-dossiers" className={styles.titreCadre}>
        Envoyer le document
      </h2>
      <CibleSmileCloud
        patientId={patientId}
        documentId={documentId}
        version={version}
        valide={valide}
      />
      <CibleVeasy
        patientId={patientId}
        documentId={documentId}
        version={version}
        valide={valide}
      />
    </section>
  );
}

function CibleSmileCloud(props: CibleProps) {
  const [lien, recharger] = useApi<LienSmileCloud>(`/patients/${props.patientId}/smilecloud`);
  const vue =
    lien.state === "ready"
      ? {
          etat: lien.data.etat,
          nom: lien.data.nom,
          candidats: lien.data.candidats.map((c) => ({
            cle: c.case_id,
            nom: c.nom,
            pour_cent: c.pour_cent,
          })),
        }
      : null;
  return (
    <Cible
      {...props}
      cible="smilecloud"
      libelle="SmileCloud"
      vue={vue}
      relier={(cle) => ({ case_id: cle })}
      rechargerLien={recharger}
    />
  );
}

function CibleVeasy(props: CibleProps) {
  const [lien, recharger] = useApi<LienVeasy>(`/patients/${props.patientId}/veasy`);
  const vue =
    lien.state === "ready"
      ? {
          etat: lien.data.etat,
          nom: lien.data.nom ?? (lien.data.veasy_id ? `dossier n° ${lien.data.veasy_id}` : null),
          candidats: lien.data.candidats.map((c) => ({
            cle: c.veasy_id,
            nom: c.nom,
            detail: c.date_naissance ? `né(e) le ${dateCourte(c.date_naissance)}` : undefined,
            pour_cent: c.pour_cent,
          })),
        }
      : null;
  return (
    <Cible
      {...props}
      cible="veasy"
      libelle="Veasy"
      vue={vue}
      relier={(cle) => ({ veasy_id: cle })}
      rechargerLien={recharger}
      saisieManuelle
    />
  );
}

interface CibleProps {
  patientId: string;
  documentId: string;
  version: number;
  valide: boolean;
}

function Cible({
  patientId,
  documentId,
  version,
  valide,
  cible,
  libelle,
  vue,
  relier,
  rechargerLien,
  saisieManuelle = false,
}: CibleProps & {
  cible: "smilecloud" | "veasy";
  libelle: string;
  vue: { etat: EtatLien; nom: string | null; candidats: Candidat[] } | null;
  relier: (cle: string | null) => Record<string, string | null>;
  rechargerLien: () => void;
  saisieManuelle?: boolean;
}) {
  const [depot, rechargerDepot] = useApi<Depot>(`/documents/${documentId}/${cible}?v=${version}`);
  const [occupe, setOccupe] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [numero, setNumero] = useState("");

  const relie = vue?.etat === "relie";
  const etatDepot = depot.state === "ready" ? depot.data : null;
  const enCours = etatDepot?.etat === "en_attente";

  // Tant que le dépôt est en cours, l'écran le suit : il passe de lui-même à « Déposé »
  // (ou dit pourquoi non) sans qu'on ait à recharger la page.
  useEffect(() => {
    if (!enCours) return;
    const minuterie = window.setInterval(rechargerDepot, 3000);
    return () => window.clearInterval(minuterie);
  }, [enCours, rechargerDepot]);

  async function agir(chemin: string, methode: "POST" | "PUT", corps?: unknown) {
    setOccupe(true);
    setErreur(null);
    try {
      await apiRequest(chemin, { method: methode, body: corps });
    } catch (caught) {
      setErreur(errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"));
    } finally {
      setOccupe(false);
      rechargerLien();
      rechargerDepot();
    }
  }

  const lienPatient = `/patients/${patientId}/${cible}`;
  const pret = relie && valide && !occupe;

  return (
    <div className={styles.cible}>
      <div className={styles.entete}>
        <span
          className={`${styles.logo} ${cible === "smilecloud" ? styles.logoSc : styles.logoVeasy}`}
          aria-hidden="true"
        >
          {cible === "smilecloud" ? "SC" : "VE"}
        </span>
        <span className={styles.nomDossier}>
          <strong>Dossier {libelle}</strong>
          {relie ? `vérifié : ${vue?.nom ?? "dossier relié"}` : "à vérifier avant le premier envoi"}
        </span>
        {relie && (
          <button
            type="button"
            className={styles.lien}
            onClick={() => void agir(lienPatient, "PUT", relier(null))}
          >
            changer
          </button>
        )}
      </div>

      {vue && !relie && (
        <div className={styles.verif}>
          {vue.etat === "sans_liste" && (
            <span>
              La liste des dossiers {libelle} n’est pas encore arrivée : l’extension Chrome la
              livrera.
            </span>
          )}
          {vue.etat === "absent" && <span>Aucun dossier {libelle} ne ressemble à ce nom.</span>}
          {(vue.etat === "trouve" || vue.etat === "a_confirmer" || vue.etat === "ambigu") && (
            <span>
              {vue.etat === "trouve"
                ? "Un dossier porte ce nom. Confirmez que c’est bien ce patient :"
                : vue.etat === "ambigu"
                  ? "Plusieurs dossiers portent ce nom : choisissez le bon."
                  : "Des dossiers ressemblent à ce nom, sans certitude : à vous de trancher."}
            </span>
          )}
          {vue.candidats.map((c) => (
            <div key={c.cle} className={styles.candidat}>
              <span>
                <strong>{c.nom}</strong> <small>{c.detail ?? ""} · {c.pour_cent} %</small>
              </span>
              <Bouton
                variante="secondaire"
                disabled={occupe}
                onClick={() => void agir(lienPatient, "PUT", relier(c.cle))}
              >
                C’est ce patient
              </Bouton>
            </div>
          ))}
          {saisieManuelle && (
            <form
              className={styles.saisie}
              onSubmit={(event) => {
                event.preventDefault();
                if (numero.trim()) void agir(lienPatient, "PUT", relier(numero.trim()));
              }}
            >
              <input
                inputMode="numeric"
                placeholder={`ou n° de dossier ${libelle}`}
                aria-label={`Numéro du dossier ${libelle}`}
                value={numero}
                onChange={(event) => setNumero(event.target.value)}
              />
              <Bouton variante="secondaire" type="submit" disabled={occupe || !numero.trim()}>
                Relier
              </Bouton>
            </form>
          )}
        </div>
      )}

      <button
        type="button"
        className={`${styles.grand} ${cible === "smilecloud" ? styles.grandSc : styles.grandVeasy}`}
        disabled={!pret}
        onClick={() =>
          void agir(`/documents/${documentId}/${cible}`, "POST").then(() =>
            prevenirExtension(cible),
          )
        }
      >
        {occupe || enCours ? "Dépôt en cours…" : `Envoyer sur le dossier ${libelle}`}
      </button>

      <p className={styles.etat} data-ton={tonDe(etatDepot)}>
        {!valide
          ? "Validez d’abord le document : ce qui entre dans le dossier y reste."
          : !relie
            ? `Vérifiez d’abord le dossier ${libelle} ci-dessus.`
            : texteDe(etatDepot, libelle)}
      </p>
      {erreur && (
        <p className={styles.etat} data-ton="alerte">
          {erreur}
        </p>
      )}
    </div>
  );
}

function texteDe(depot: Depot | null, libelle: string): string {
  if (!depot || depot.etat === "absent") return "Pas encore envoyé.";
  if (depot.etat === "en_attente")
    return depot.raison
      ? `Dépôt en cours — pas encore fait : ${depot.raison}`
      : `Dépôt en cours dans ${libelle}…`;
  if (depot.etat === "impossible") return `Pas déposé : ${depot.raison}`;
  return `Déposé dans ${libelle}${depot.depose_le ? ` le ${formatDateTime(depot.depose_le)}` : ""}.`;
}

function tonDe(depot: Depot | null): "ok" | "alerte" | undefined {
  if (depot?.etat === "depose") return "ok";
  if (depot?.etat === "impossible") return "alerte";
  return undefined;
}

function dateCourte(iso: string): string {
  const [a, m, j] = iso.split("-");
  return a && m && j ? `${j}/${m}/${a}` : iso;
}
