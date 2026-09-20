"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { Icone, type NomIcone } from "@/components/Icones";
import { Symbole } from "@/components/Marque";
import type { Cabinet } from "@/lib/api";
import { useApi } from "@/lib/useApi";

import styles from "./AppShell.module.css";

const NAVIGATION: { href: string; label: string; icone: NomIcone }[] = [
  { href: "/", label: "Accueil", icone: "accueil" },
  { href: "/journee", label: "Votre journée", icone: "journee" },
  { href: "/patients", label: "Patients", icone: "patients" },
  { href: "/correspondants", label: "Correspondants", icone: "correspondants" },
  { href: "/consultations", label: "Consultations", icone: "consultations" },
  { href: "/documents", label: "Documents", icone: "documents" },
  { href: "/apprentissage", label: "Oris apprend", icone: "apprend" },
  { href: "/parametres", label: "Paramètres", icone: "parametres" },
];

function estActif(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

/** Deux lettres pour le jeton : « Dr Franck Moyal » donne FM. */
function initiales(nom: string): string {
  const mots = nom.replace(/^Dr\.?\s+/i, "").split(/\s+/).filter(Boolean);
  return mots.slice(0, 2).map((mot) => mot[0]?.toUpperCase() ?? "").join("") || "—";
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [cabinet] = useApi<Cabinet>("/me/cabinet");
  const [ouvert, setOuvert] = useState(false);

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

        <ul className={styles.nav}>
          {NAVIGATION.map(({ href, label, icone }) => (
            <li key={href}>
              <Link
                href={href}
                className={styles.item}
                aria-current={estActif(pathname, href) ? "page" : undefined}
              >
                <Icone nom={icone} />
                {label}
              </Link>
            </li>
          ))}
        </ul>

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
