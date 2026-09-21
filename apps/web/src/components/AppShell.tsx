"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { Icone, type NomIcone } from "@/components/Icones";
import { Symbole } from "@/components/Marque";
import { apiRequest, type Cabinet } from "@/lib/api";
import { useApi } from "@/lib/useApi";

import styles from "./AppShell.module.css";

type Entree = { href: string; label: string; icone: NomIcone; teinte: string };

/** Trois groupes, du plus fréquent au plus rare. Chaque rubrique a sa teinte : on la
 *  retrouve d'un coup d'œil, comme dans les Réglages du Mac. */
const GROUPES: { titre: string; entrees: Entree[] }[] = [
  {
    titre: "Au fauteuil",
    entrees: [
      { href: "/", label: "Accueil", icone: "accueil", teinte: "vert" },
      { href: "/journee", label: "Votre journée", icone: "journee", teinte: "ocre" },
      { href: "/patients", label: "Patients", icone: "patients", teinte: "bleu" },
      { href: "/consultations", label: "Consultations", icone: "consultations", teinte: "lagune" },
    ],
  },
  {
    titre: "Dossiers",
    entrees: [
      { href: "/correspondants", label: "Correspondants", icone: "correspondants", teinte: "prune" },
      { href: "/documents", label: "Documents", icone: "documents", teinte: "terre" },
    ],
  },
  {
    titre: "Oris",
    entrees: [
      { href: "/apprentissage", label: "Oris apprend", icone: "apprend", teinte: "indigo" },
      { href: "/parametres", label: "Paramètres", icone: "parametres", teinte: "ardoise" },
    ],
  },
];

function estActif(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

/** Deux lettres pour le jeton : « Dr Franck Moyal » donne FM. */
function initiales(nom: string): string {
  const mots = nom.replace(/^Dr\.?\s+/i, "").split(/\s+/).filter(Boolean);
  return mots.slice(0, 2).map((mot) => mot[0]?.toUpperCase() ?? "").join("") || "—";
}

type Voyant = {
  etat: string;
  ton: "actif" | "alerte" | "travail" | "neutre";
  detail: string;
  ouvrir: "doctolib" | "smilecloud" | null;
};
type Connecteurs = { doctolib: Voyant; smilecloud: Voyant; peut_ouvrir: boolean };

/** Doctolib et SmileCloud en deux voyants, comme dans Dental Lens : un point de couleur,
 *  l'état en toutes lettres, et « reconnecter » seulement quand un geste le règle. */
function VoyantsConnecteurs() {
  const [connecteurs, recharger] = useApi<Connecteurs>("/connecteurs");
  const [envoi, setEnvoi] = useState<string | null>(null);

  // L'état bouge sans nous (Chrome fermé, session expirée) : on relit toutes les 30 s.
  useEffect(() => {
    const minuterie = window.setInterval(recharger, 30_000);
    return () => window.clearInterval(minuterie);
  }, [recharger]);

  if (connecteurs.state !== "ready") return null;
  const lignes: [string, Voyant][] = [
    ["Doctolib", connecteurs.data.doctolib],
    ["SmileCloud", connecteurs.data.smilecloud],
  ];
  return (
    <div className={styles.voyants} aria-label="État des connecteurs">
      <p className={styles.voyantsTitre}>État</p>
      {lignes.map(([nom, v]) => (
        <div key={nom} className={styles.voyant} data-ton={v.ton} title={v.detail}>
          <span className={styles.point} aria-hidden="true" />
          <span className={styles.voyantNom}>{nom}</span>
          <span className={styles.voyantEtat}>{v.etat}</span>
          {v.ouvrir && connecteurs.data.peut_ouvrir && v.ton !== "actif" && (
            <button
              type="button"
              className={styles.reconnecter}
              disabled={envoi === v.ouvrir}
              onClick={async () => {
                setEnvoi(v.ouvrir);
                try {
                  await apiRequest("/connecteurs/ouvrir", { method: "POST", body: { site: v.ouvrir } });
                } catch {
                  /* Dental Lens ne répond pas : le voyant le dira à la relecture. */
                }
                window.setTimeout(() => {
                  setEnvoi(null);
                  recharger();
                }, 3000);
              }}
            >
              {envoi === v.ouvrir ? "…" : v.ton === "alerte" ? "reconnecter" : "ouvrir"}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [cabinet] = useApi<Cabinet>("/me/cabinet");
  const [ouvert, setOuvert] = useState(false);
  // Le nombre de comptes rendus à relire, en pastille sur « Consultations ».
  const [aRelireListe] = useApi<unknown[]>("/encounters?status=review");
  const aRelire = aRelireListe.state === "ready" ? aRelireListe.data.length : 0;

  const nom = cabinet.state === "ready" ? cabinet.data.practitioner_name : "";
  const titre = cabinet.state === "ready" ? cabinet.data.practitioner_title : "";
  const praticien = `${titre} ${nom}`.trim();
  const lieu = cabinet.state === "ready" ? cabinet.data.name : "";

  // Le menu de profil se referme dès qu'on clique ailleurs.
  useEffect(() => {
    if (!ouvert) return;
    const fermer = () => setOuvert(false);
    document.addEventListener("click", fermer);
    return () => document.removeEventListener("click", fermer);
  }, [ouvert]);

  return (
    <div className={styles.shell}>
      <nav className={styles.menu} aria-label="Navigation principale">
        <div className={styles.enTeteMarque}>
          <Link href="/" className={styles.marque}>
            <Symbole taille={36} />
            <span className={styles.nom}>Oris</span>
            <span className={styles.retour} aria-hidden="true">
              accueil
            </span>
            <span className="sr-only">Revenir à l’accueil</span>
          </Link>
          <span className={styles.slogan}>Vous soignez. Oris documente.</span>
        </div>

        <div className={styles.groupes}>
          {GROUPES.map((groupe) => (
            <div key={groupe.titre} className={styles.groupe}>
              <p className={styles.groupeTitre}>{groupe.titre}</p>
              <ul className={styles.nav}>
                {groupe.entrees.map(({ href, label, icone, teinte }) => (
                  <li key={href}>
                    <Link
                      href={href}
                      className={styles.item}
                      aria-current={estActif(pathname, href) ? "page" : undefined}
                    >
                      <span className={styles.tuile} data-teinte={teinte}>
                        <Icone nom={icone} taille={16} />
                      </span>
                      <span className={styles.libelle}>{label}</span>
                      {href === "/consultations" && aRelire > 0 && (
                        <span className={styles.compteur} title={`${aRelire} à relire`}>
                          {aRelire}
                        </span>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <VoyantsConnecteurs />

        <div className={styles.profil}>
          {ouvert && (
            <ul className={styles.liste} onClick={(event) => event.stopPropagation()}>
              <li>
                <button type="button" className={styles.entree}>
                  <span className={styles.jeton}>{initiales(praticien)}</span>
                  {praticien || "Praticien"}
                </button>
              </li>
              <li>
                <hr className={styles.separateur} />
              </li>
              <li>
                {/* La création d'un praticien attend son tour : l'écran le dit. */}
                <button type="button" className={styles.entree} disabled>
                  <span className={styles.jeton}>+</span>
                  <span>
                    Nouveau praticien
                    <span className={styles.aVenir}>à venir</span>
                  </span>
                </button>
              </li>
            </ul>
          )}
          <button
            type="button"
            className={styles.profilBouton}
            aria-expanded={ouvert}
            onClick={(event) => {
              event.stopPropagation();
              setOuvert((etat) => !etat);
            }}
          >
            <span className={styles.jeton}>{praticien ? initiales(praticien) : "—"}</span>
            <span>
              <span className={styles.praticienNom}>{praticien || " "}</span>
              <span className={styles.mention}>{lieu || "Données fictives"}</span>
            </span>
            <Icone nom="chevron" taille={16} className={styles.chevron} />
          </button>
        </div>
      </nav>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
