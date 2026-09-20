"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import type { Cabinet } from "@/lib/api";
import { useApi } from "@/lib/useApi";

import styles from "./AppShell.module.css";

const NAVIGATION = [
  { href: "/", label: "Accueil", icone: "M4 10.5 12 4l8 6.5V20H4z" },
  { href: "/patients", label: "Patients", icone: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-8 8a8 8 0 0 1 16 0" },
  { href: "/consultations", label: "Consultations", icone: "M6 3h12v18l-6-4-6 4z" },
  { href: "/documents", label: "Documents", icone: "M7 3h7l4 4v14H7zM14 3v5h5" },
  { href: "/apprentissage", label: "Oris apprend", icone: "M12 4 3 9l9 5 9-5zM6 12v5l6 3 6-3v-5" },
  { href: "/parametres", label: "Paramètres", icone: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM4 12h2m12 0h2M12 4v2m0 12v2" },
] as const;

function estActif(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [cabinet] = useApi<Cabinet>("/me/cabinet");
  const praticien =
    cabinet.state === "ready"
      ? `${cabinet.data.practitioner_title} ${cabinet.data.practitioner_name}`.trim()
      : "";

  return (
    <div className={styles.shell}>
      <nav className={styles.menu} aria-label="Navigation principale">
        <Link href="/" className={styles.marque} aria-label="Oris — accueil">
          <Image
            src="/oris-symbole-blanc.png"
            alt=""
            width={368}
            height={365}
            className={styles.symbole}
            priority
          />
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
          <div className={styles.praticien}>
            <span className={styles.praticienNom}>{praticien || "\u00a0"}</span>
            <span className={styles.mention}>Données fictives uniquement</span>
          </div>
        </div>
      </nav>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
