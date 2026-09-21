"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { TypeDocument } from "@/components/documents/TypeDocument";
import { Icone } from "@/components/Icones";
import { EnvoiDocument } from "@/components/review/EnvoiDocument";
import {
  Champ,
  EnTetePage,
  EtatVide,
  Onglets,
  Squelette,
} from "@/components/ui";
import type { Encounter } from "@/lib/api";
import { errorMessage, nomPatient } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./envois.module.css";

type Volet = "a_envoyer" | "envoyes" | "a_valider";
type Ligne = {
  id: string;
  type: Encounter["documents"][number]["document_type"];
  statut: string;
  envoyeA: string[];
  patient: string;
  consultation: string;
  quand: Date;
};

const VALIDES = new Set(["validated", "exported"]);

function date(d: Date): string {
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

/** Envois : ce qui attend de partir, ce qui est parti, ce qui attend d'être validé.
 *  Une page pour agir — pas une liste de documents de plus (choix de Franck, 22/09/2026). */
export default function EnvoisPage() {
  const router = useRouter();
  const [encounters, recharger] = useApi<Encounter[]>("/encounters");
  const [volet, setVolet] = useState<Volet>("a_envoyer");
  const [ouvert, setOuvert] = useState<string | null>(null);
  const [recherche, setRecherche] = useState("");
  const [parti, setParti] = useState<string | null>(null);

  const lignes = useMemo<Ligne[]>(() => {
    const toutes = encounters.state === "ready" ? encounters.data : [];
    return toutes
      .flatMap((e) =>
        e.documents
          .filter((d) => d.status !== "superseded")
          .map((d) => ({
            id: d.id,
            type: d.document_type,
            statut: d.status,
            envoyeA: d.sent_to ?? [],
            patient: nomPatient(e.patient),
            consultation: e.id,
            quand: new Date(e.started_at ?? e.created_at),
          })),
      )
      .filter((l) =>
        recherche.trim()
          ? l.patient.toLowerCase().includes(recherche.trim().toLowerCase())
          : true,
      )
      .sort((a, b) => b.quand.getTime() - a.quand.getTime());
  }, [encounters, recherche]);

  const aEnvoyer = lignes.filter(
    (l) => VALIDES.has(l.statut) && l.envoyeA.length === 0,
  );
  const envoyes = lignes.filter((l) => l.envoyeA.length > 0);
  const aValider = lignes.filter((l) => !VALIDES.has(l.statut));
  const visibles =
    volet === "a_envoyer" ? aEnvoyer : volet === "envoyes" ? envoyes : aValider;

  return (
    <div className="page">
      <EnTetePage surTitre="Courrier" titre="Envois" />

      <div className={styles.compteurs}>
        {(
          [
            [
              "a_envoyer",
              "À envoyer",
              aEnvoyer.length,
              "orange",
              "validés, jamais partis",
            ],
            [
              "envoyes",
              "Envoyés",
              envoyes.length,
              "vert",
              "partis par courriel",
            ],
            [
              "a_valider",
              "À valider",
              aValider.length,
              "ardoise",
              "pas encore validés",
            ],
          ] as const
        ).map(([cle, titre, n, teinte, detail]) => (
          <button
            key={cle}
            type="button"
            className={styles.compteur}
            data-teinte={teinte}
            aria-pressed={volet === cle}
            onClick={() => setVolet(cle)}
          >
            <span className={styles.compteurChiffre}>{n}</span>
            <span className={styles.compteurTitre}>{titre}</span>
            <span className={styles.compteurDetail}>{detail}</span>
          </button>
        ))}
      </div>

      <div className={styles.barre}>
        <Onglets
          valeur={volet}
          onChange={setVolet}
          options={[
            { valeur: "a_envoyer", libelle: `À envoyer (${aEnvoyer.length})` },
            { valeur: "envoyes", libelle: `Envoyés (${envoyes.length})` },
            { valeur: "a_valider", libelle: `À valider (${aValider.length})` },
          ]}
        />
        <Champ
          type="search"
          value={recherche}
          placeholder="Rechercher un patient…"
          aria-label="Rechercher un patient"
          style={{ width: 260 }}
          onChange={(event) => setRecherche(event.target.value)}
        />
      </div>

      {parti && (
        <p className={styles.parti} role="status">
          <Icone nom="valide" taille={16} /> {parti}
        </p>
      )}

      <section className={styles.liste}>
        {encounters.state === "loading" && <Squelette lignes={5} />}
        {encounters.state === "error" && (
          <EtatVide titre={errorMessage(encounters.code)} />
        )}
        {encounters.state === "ready" && visibles.length === 0 && (
          <EtatVide
            titre={
              volet === "a_envoyer"
                ? "Rien à envoyer"
                : volet === "envoyes"
                  ? "Aucun envoi pour l’instant"
                  : "Rien à valider"
            }
          >
            {volet === "a_envoyer"
              ? "Tout document validé est déjà parti. Bravo."
              : volet === "envoyes"
                ? "Les documents envoyés depuis Oris apparaissent ici, avec leurs destinataires."
                : "Les brouillons d’Oris apparaissent ici tant qu’ils ne sont pas validés."}
          </EtatVide>
        )}
        {visibles.map((l) => (
          <article
            key={l.id}
            className={styles.ligne}
            data-ouvert={ouvert === l.id || undefined}
          >
            <div className={styles.ligneHaut}>
              <span className={styles.quand}>{date(l.quand)}</span>
              <TypeDocument type={l.type} valide={VALIDES.has(l.statut)} />
              <Link
                href={`/consultations/${l.consultation}`}
                className={styles.patient}
              >
                {l.patient}
              </Link>
              <span className={styles.fin}>
                {volet === "envoyes" && (
                  <span className={styles.destinataires}>
                    <Icone nom="envoi" taille={14} /> {l.envoyeA.join(", ")}
                  </span>
                )}
                {volet === "a_valider" ? (
                  <Link
                    href={`/consultations/${l.consultation}`}
                    className={styles.action}
                  >
                    Relire et valider →
                  </Link>
                ) : (
                  <button
                    type="button"
                    className={
                      volet === "a_envoyer" ? styles.actionForte : styles.action
                    }
                    aria-expanded={ouvert === l.id}
                    onClick={() => setOuvert(ouvert === l.id ? null : l.id)}
                  >
                    {ouvert === l.id
                      ? "Fermer"
                      : volet === "a_envoyer"
                        ? "Envoyer"
                        : "Renvoyer"}
                  </button>
                )}
              </span>
            </div>
            {ouvert === l.id && (
              <div className={styles.envoi}>
                <EnvoiDocument
                  documentId={l.id}
                  version={0}
                  onEnvoye={() => {
                    setOuvert(null);
                    setParti(`Envoyé : ${l.patient}.`);
                    recharger();
                  }}
                  onEditer={() => {
                    router.push(`/consultations/${l.consultation}`);
                  }}
                />
              </div>
            )}
          </article>
        ))}
      </section>
    </div>
  );
}
