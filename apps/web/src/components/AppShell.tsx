"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import styles from "./AppShell.module.css";

const NAVIGATION = [
  { href: "/", label: "Accueil", icone: "M4 10.5 12 4l8 6.5V20H4z" },
  { href: "/patients", label: "Patients", icone: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-8 8a8 8 0 0 1 16 0" },
  { href: "/consultations", label: "Consultations", icone: "M6 3h12v18l-6-4-6 4z" },
  { href: "/apprentissage", label: "Oris apprend", icone: "M12 4 3 9l9 5 9-5zM6 12v5l6 3 6-3v-5" },
] as const;

const PALETTES = [
  { valeur: "bleu", couleur: "#3B82F6", nom: "Bleu" },
  { valeur: "sauge", couleur: "#2F6F67", nom: "Sauge" },
] as const;

function estActif(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  // La palette est posée sur <html> avant l'affichage (voir layout) : on la lit là,
  // sans effet de bord ni clignotement.
  const [palette, setPalette] = useState<string>(() =>
    typeof document === "undefined"
      ? "bleu"
      : (document.documentElement.dataset.palette ?? "bleu"),
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-palette", palette);
  }, [palette]);

  function choisir(valeur: string) {
    setPalette(valeur);
    window.localStorage.setItem("oris-palette", valeur);
  }

  return (
    <div className={styles.shell}>
      <nav className={styles.menu} aria-label="Navigation principale">
        <Link href="/" className={styles.marque}>
          <span className={styles.nom}>Oris</span>
        </Link>

        <ul className={styles.nav}>
          {NAVIGATION.map(({ href, label, icone }) => (
            <li key={href}>
              <Link
                href={href}
                className={styles.item}
                aria-current={estActif(pathname, href) ? "page" : undefined}
              >
                <svg className={styles.icone} viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d={icone} stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                </svg>
                {label}
              </Link>
            </li>
          ))}
        </ul>

        <div className={styles.bas}>
          <div className={styles.palettes} role="group" aria-label="Palette de couleurs">
            {PALETTES.map(({ valeur, couleur, nom }) => (
              <button
                key={valeur}
                type="button"
                className={styles.palette}
                style={{ background: couleur }}
                aria-pressed={palette === valeur}
                aria-label={`Palette ${nom}`}
                title={`Palette ${nom}`}
                onClick={() => choisir(valeur)}
              />
            ))}
            <span>palette</span>
          </div>
          <div className={styles.praticien}>
            <span className={styles.praticienNom}>Dr Franck Moyal</span>
            <span className={styles.mention}>Données fictives uniquement</span>
          </div>
        </div>
      </nav>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
