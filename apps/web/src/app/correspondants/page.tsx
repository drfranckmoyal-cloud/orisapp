"use client";

import { useMemo, useState } from "react";

import { Bouton, Carte, Champ, EnTetePage, EtatVide, Pastille, Squelette } from "@/components/ui";
import { Icone } from "@/components/Icones";
import { ApiError, apiRequest, type Correspondant } from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import { Fiche, VIDE, brouillonDe, type Brouillon } from "./Fiche";
import styles from "./correspondants.module.css";

/** Carnet d'adresses : les confrères et les structures à qui l'on adresse un patient.
 *
 * Ce ne sont pas des utilisateurs d'Oris — personne ne s'y connecte. Ce sont des fiches
 * d'adresse, dont la raison d'être est le courrier d'adressage : d'où l'adresse postale,
 * qui pèse ici autant que le nom.
 */

/** `null` = toutes ; `""` = seulement celles dont la spécialité n'est pas renseignée. */
type Filtre = string | null;

function initiales(c: Correspondant): string {
  const nom = c.last_name.trim();
  if (c.kind === "organisation") return nom.slice(0, 2).toLocaleUpperCase("fr-FR");
  return `${c.first_name.trim()[0] ?? ""}${nom[0] ?? ""}`.toLocaleUpperCase("fr-FR");
}

function nomComplet(c: Correspondant): string {
  if (c.kind === "organisation") return c.last_name;
  const civilite = c.title ? `${c.title} ` : "";
  return `${civilite}${c.first_name} ${c.last_name.toLocaleUpperCase("fr-FR")}`.replace("  ", " ");
}

export default function CorrespondantsPage() {
  const [filtre, setFiltre] = useState<Filtre>(null);
  const [recherche, setRecherche] = useState("");
  const parametres = new URLSearchParams();
  if (recherche.trim()) parametres.set("q", recherche.trim());
  if (filtre !== null) parametres.set("specialty", filtre);
  const requete = parametres.toString();

  const [carnet, recharger] = useApi<Correspondant[]>(
    `/correspondents${requete ? `?${requete}` : ""}`,
  );
  const [specialites, rechargerSpecialites] = useApi<string[]>("/correspondents/specialties");

  const [nouveau, setNouveau] = useState(false);
  const [ouvert, setOuvert] = useState<string | null>(null);
  const [occupe, setOccupe] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const liste = useMemo(() => (carnet.state === "ready" ? carnet.data : []), [carnet]);
  const choix = useMemo(
    () => (specialites.state === "ready" ? specialites.data : []),
    [specialites],
  );

  async function enregistrer(brouillon: Brouillon, id: string | null) {
    setOccupe(true);
    setMessage(null);
    try {
      await apiRequest(id ? `/correspondents/${id}` : "/correspondents", {
        method: id ? "PATCH" : "POST",
        body: brouillon,
      });
      setNouveau(false);
      setOuvert(null);
      setMessage(id ? "Correspondant modifié." : "Correspondant ajouté.");
      recharger();
      rechargerSpecialites();
    } catch (error) {
      setMessage(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setOccupe(false);
    }
  }

  async function supprimer(id: string) {
    setOccupe(true);
    setMessage(null);
    try {
      await apiRequest(`/correspondents/${id}`, { method: "DELETE" });
      setOuvert(null);
      setMessage("Correspondant supprimé.");
      recharger();
    } catch (error) {
      setMessage(errorMessage(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setOccupe(false);
    }
  }

  return (
    <div className="page">
      <EnTetePage
        surTitre="Carnet d’adresses"
        titre="Correspondants"
        action={
          <Bouton
            variante="secondaire"
            onClick={() => {
              setOuvert(null);
              setNouveau((ouvert) => !ouvert);
            }}
          >
            {nouveau ? "Annuler" : "Nouveau correspondant"}
          </Bouton>
        }
      />

      {message && (
        <div className="banner banner-info" role="status">
          {message}
        </div>
      )}

      {nouveau && (
        <Carte titre="Nouveau correspondant">
          <Fiche
            depart={VIDE}
            specialites={choix}
            occupe={occupe}
            onValider={(brouillon) => void enregistrer(brouillon, null)}
            onAnnuler={() => setNouveau(false)}
          />
        </Carte>
      )}

      <Carte
        titre={`${liste.length} correspondant${liste.length > 1 ? "s" : ""}`}
        action={
          <Champ
            type="search"
            value={recherche}
            placeholder="Rechercher un nom, un cabinet…"
            aria-label="Rechercher un correspondant"
            style={{ width: 260 }}
            onChange={(event) => setRecherche(event.target.value)}
          />
        }
      >
        {/* Filtrer par spécialité, « non renseignée » comprise : c'est ce filtre-là qui
            sert à retrouver les fiches restées à moitié remplies. */}
        <div className={styles.filtres}>
          <Bouton
            variante={filtre === null ? "principal" : "secondaire"}
            onClick={() => setFiltre(null)}
          >
            Toutes
          </Bouton>
          {choix.map((specialite) => (
            <Bouton
              key={specialite}
              variante={filtre === specialite ? "principal" : "secondaire"}
              onClick={() => setFiltre(specialite)}
            >
              {specialite}
            </Bouton>
          ))}
          <Bouton
            variante={filtre === "" ? "principal" : "secondaire"}
            onClick={() => setFiltre("")}
          >
            Non renseignée
          </Bouton>
        </div>

        {carnet.state === "loading" && <Squelette lignes={4} />}
        {carnet.state === "error" && <EtatVide titre={errorMessage(carnet.code)} />}

        {carnet.state === "ready" && liste.length === 0 && (
          <EtatVide titre={recherche || filtre !== null ? "Aucun correspondant" : "Carnet vide"}>
            {recherche || filtre !== null
              ? "Aucun correspondant ne répond à cette recherche."
              : "Ajoutez le premier confrère ou la première structure à qui vous adressez des patients."}
          </EtatVide>
        )}

        {liste.length > 0 && (
          <div className={styles.liste}>
            {liste.map((c) => (
              <div key={c.id}>
                <button
                  type="button"
                  className={`${styles.fiche} ${ouvert === c.id ? styles.ficheOuverte : ""}`}
                  aria-expanded={ouvert === c.id}
                  onClick={() => {
                    setNouveau(false);
                    setOuvert((actuel) => (actuel === c.id ? null : c.id));
                  }}
                >
                  <span
                    className={`${styles.jeton} ${
                      c.kind === "organisation" ? styles.jetonStructure : ""
                    }`}
                    aria-hidden="true"
                  >
                    {initiales(c)}
                  </span>

                  <span className={styles.qui}>
                    <span className={styles.nom}>{nomComplet(c)}</span>
                    <span className={styles.dessous}>
                      {c.kind === "organisation"
                        ? "structure"
                        : c.specialty || <span className={styles.manque}>spécialité non renseignée</span>}
                      {c.practice && ` · ${c.practice}`}
                    </span>
                  </span>

                  <span className={styles.joindre}>
                    <span className={styles.dessous}>
                      {c.email || <span className={styles.manque}>pas de courriel</span>}
                    </span>
                    <span className={styles.dessous}>
                      {c.phone || <span className={styles.manque}>pas de téléphone</span>}
                    </span>
                  </span>

                  {/* L'adresse postale est ce dont la lettre a besoin : son absence se
                      signale, sa présence ne dit rien de particulier. */}
                  <span className={styles.marques}>
                    {!c.address && (
                      <Pastille ton="attention" point>
                        sans adresse
                      </Pastille>
                    )}
                  </span>

                  <span className={styles.chevron} aria-hidden="true">
                    <Icone nom="suivant" taille={16} />
                  </span>
                </button>

                {ouvert === c.id && (
                  <Carte titre={`Modifier — ${nomComplet(c)}`}>
                    <Fiche
                      depart={brouillonDe(c)}
                      specialites={choix}
                      occupe={occupe}
                      onValider={(brouillon) => void enregistrer(brouillon, c.id)}
                      onAnnuler={() => setOuvert(null)}
                      onSupprimer={() => void supprimer(c.id)}
                    />
                  </Carte>
                )}
              </div>
            ))}
          </div>
        )}
      </Carte>
    </div>
  );
}
