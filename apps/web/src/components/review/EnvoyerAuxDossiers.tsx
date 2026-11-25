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
  /** Quand l'extension a pris le PDF : le dépôt est en route. */
  pris_le?: string | null;
  depose_le?: string | null;
}

type EtatLien =
  "relie" | "trouve" | "a_confirmer" | "ambigu" | "absent" | "sans_liste";

interface LienSmileCloud {
  etat: EtatLien;
  nom: string | null;
  candidats: { case_id: string; nom: string; pour_cent: number }[];
}

interface LienVeasy {
  /** Le dernier contrôle de l'extension (rattachement automatique, 26/11/2026). */
  controle?: { statut: string; le: string } | null;
  etat: EtatLien;
  nom: string | null;
  veasy_id: string | null;
  candidats: {
    veasy_id: string;
    nom: string;
    date_naissance: string;
    pour_cent: number;
  }[];
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
  const [lien, recharger] = useApi<LienSmileCloud>(
    `/patients/${props.patientId}/smilecloud`,
  );
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
  const [lien, recharger] = useApi<LienVeasy>(
    `/patients/${props.patientId}/veasy`,
  );
  const vue =
    lien.state === "ready"
      ? {
          etat: lien.data.etat,
          nom:
            lien.data.nom ??
            (lien.data.veasy_id ? `dossier n° ${lien.data.veasy_id}` : null),
          candidats: lien.data.candidats.map((c) => ({
            cle: c.veasy_id,
            nom: c.nom,
            detail: c.date_naissance
              ? `né(e) le ${dateCourte(c.date_naissance)}`
              : undefined,
            pour_cent: c.pour_cent,
          })),
        }
      : null;
  const relie = lien.state === "ready" && lien.data.etat === "relie";
  // Pas encore relié : l'extension le cherche tout de suite (même pont que le dépôt).
  useEffect(() => {
    if (lien.state === "ready" && lien.data.etat !== "relie")
      prevenirExtension("veasy", "oris:relier");
  }, [lien]);
  const controle = lien.state === "ready" ? lien.data.controle : null;
  return (
    <Cible
      {...props}
      cible="veasy"
      libelle="Veasy"
      vue={vue}
      relier={(cle) => ({ veasy_id: cle })}
      rechargerLien={recharger}
      saisieManuelle
      note={noteControle(controle ?? null, relie)}
    />
  );
}

/** Ce que l'extension a trouvé en cherchant seule le dossier Veasy du patient. */
function noteControle(
  controle: { statut: string; le: string } | null,
  relie: boolean,
): { texte: string; ton?: "alerte" } | null {
  if (!controle) return null;
  const le = controle.le ? ` le ${formatDateTime(controle.le)}` : "";
  if (relie && (controle.statut === "relie" || controle.statut === "verifie"))
    return {
      texte: `Relié et vérifié par l’extension${le} (nom, prénom, date de naissance).`,
    };
  switch (controle.statut) {
    case "aucun":
      return {
        texte:
          "L’extension n’a trouvé aucun dossier Veasy à ce nom et cette date de naissance.",
      };
    case "plusieurs":
      return {
        texte:
          "Plusieurs dossiers Veasy correspondent : choisissez le bon, ou saisissez son numéro.",
      };
    case "sans_naissance":
      return {
        texte:
          "Ajoutez la date de naissance dans la fiche patient : Oris pourra le relier tout seul.",
      };
    case "lien_douteux":
      return {
        texte:
          "Le lien précédent visait la fiche Veasy d’un autre patient : il a été retiré.",
        ton: "alerte",
      };
    default:
      return null;
  }
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
  note = null,
}: CibleProps & {
  cible: "smilecloud" | "veasy";
  libelle: string;
  vue: { etat: EtatLien; nom: string | null; candidats: Candidat[] } | null;
  relier: (cle: string | null) => Record<string, string | null>;
  rechargerLien: () => void;
  saisieManuelle?: boolean;
  note?: { texte: string; ton?: "alerte" } | null;
}) {
  const [depot, rechargerDepot] = useApi<Depot>(
    `/documents/${documentId}/${cible}?v=${version}`,
  );
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

  async function agir(
    chemin: string,
    methode: "POST" | "PUT",
    corps?: unknown,
  ) {
    setOccupe(true);
    setErreur(null);
    try {
      await apiRequest(chemin, { method: methode, body: corps });
    } catch (caught) {
      setErreur(
        errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"),
      );
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
          {relie
            ? `vérifié : ${vue?.nom ?? "dossier relié"}`
            : "à vérifier avant le premier envoi"}
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

      {note && (
        <p className={styles.etat} data-ton={note.ton}>
          {note.texte}
        </p>
      )}

      {vue && !relie && (
        <div className={styles.verif}>
          {vue.etat === "sans_liste" && (
            <span>
              La liste des dossiers {libelle} n’est pas encore arrivée :
              l’extension Chrome la livrera.
            </span>
          )}
          {vue.etat === "absent" && (
            <span>Aucun dossier {libelle} ne ressemble à ce nom.</span>
          )}
          {(vue.etat === "trouve" ||
            vue.etat === "a_confirmer" ||
            vue.etat === "ambigu") && (
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
                <strong>{c.nom}</strong>{" "}
                <small>
                  {c.detail ?? ""} · {c.pour_cent} %
                </small>
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
                if (numero.trim())
                  void agir(lienPatient, "PUT", relier(numero.trim()));
              }}
            >
              <input
                inputMode="numeric"
                placeholder={`ou n° de la fiche ${libelle} (dans son adresse)`}
                aria-label={`Numéro du dossier ${libelle}`}
                value={numero}
                onChange={(event) => setNumero(event.target.value)}
              />
              <Bouton
                variante="secondaire"
                type="submit"
                disabled={occupe || !numero.trim()}
              >
                Relier
              </Bouton>
            </form>
          )}
          {saisieManuelle && (
            <small>
              Le numéro de la fiche se lit dans l’adresse de la page Veasy du
              patient : …/Consultation/<strong>13005043</strong>. Ce n’est pas
              le numéro entre parenthèses à côté de son nom.
            </small>
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
        {occupe || enCours
          ? "Dépôt en cours…"
          : `Envoyer sur le dossier ${libelle}`}
      </button>

      {!valide || !relie ? (
        <p className={styles.etat}>
          {!valide
            ? "Validez d’abord le document : ce qui entre dans le dossier y reste."
            : `Vérifiez d’abord le dossier ${libelle} ci-dessus.`}
        </p>
      ) : (
        <BarreEtat depot={etatDepot} libelle={libelle} />
      )}
      {erreur && (
        <p className={styles.etat} data-ton="alerte">
          {erreur}
        </p>
      )}
    </div>
  );
}

/** L'envoi en trois étapes, et son issue écrite en toutes lettres (Franck, 25/11/2026 :
 * « on n'est pas sûr, en regardant, si l'envoi et le dépôt sont validés ou non »).
 * Demandé → pris par l'extension (le PDF est parti du serveur) → déposé dans le dossier,
 * vérifié par l'extension. Un échec le dit en rouge, avec sa raison. */
function BarreEtat({
  depot,
  libelle,
}: {
  depot: Depot | null;
  libelle: string;
}) {
  if (!depot || depot.etat === "absent") {
    return <p className={styles.etat}>Pas encore envoyé dans {libelle}.</p>;
  }
  const etapes = [
    { nom: "Demandé", quand: depot.demande_le, fait: true },
    {
      nom: "Pris par l’extension",
      quand: depot.pris_le,
      fait: Boolean(depot.pris_le) || depot.etat !== "en_attente",
    },
    {
      nom: `Déposé dans ${libelle}`,
      quand: depot.depose_le,
      fait: depot.etat === "depose",
    },
  ];
  const echec = depot.etat === "impossible";
  return (
    <div className={styles.barreEtat}>
      <ol className={styles.etapes} aria-label={`Envoi dans ${libelle}`}>
        {etapes.map((etape, rang) => {
          const etat = etape.fait
            ? "fait"
            : echec && rang === 2
              ? "echec"
              : "attente";
          return (
            <li key={etape.nom} className={styles.etape} data-etat={etat}>
              <span className={styles.pastilleEtape} aria-hidden="true">
                {etat === "fait" ? "✓" : etat === "echec" ? "✕" : rang + 1}
              </span>
              <span>{etape.nom}</span>
            </li>
          );
        })}
      </ol>
      {depot.etat === "depose" && (
        <p className={styles.issue} data-ton="ok">
          ✓ Déposé dans le dossier {libelle}
          {depot.depose_le ? ` le ${formatDateTime(depot.depose_le)}` : ""} —
          vérifié par l’extension.
        </p>
      )}
      {echec && (
        <p className={styles.issue} data-ton="alerte">
          ✕ Pas déposé : {depot.raison || "raison inconnue"}. Rien n’est entré
          dans le dossier.
        </p>
      )}
      {depot.etat === "en_attente" && (
        <p className={styles.issue} data-ton="attente">
          {depot.raison
            ? `En attente : ${depot.raison}. Oris réessaie tout seul.`
            : depot.pris_le
              ? `Dépôt en cours dans ${libelle}…`
              : "En attente de l’extension Chrome (Mac allumé, Chrome ouvert)…"}
        </p>
      )}
    </div>
  );
}

function dateCourte(iso: string): string {
  const [a, m, j] = iso.split("-");
  return a && m && j ? `${j}/${m}/${a}` : iso;
}
