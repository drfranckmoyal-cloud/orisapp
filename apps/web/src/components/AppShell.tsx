"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import styles from "./AppShell.module.css";

const NAVIGATION = [
  { href: "/", label: "Accueil" },
  { href: "/patients", label: "Patients" },
  { href: "/consultations", label: "Consultations" },
] as const;

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className={styles.shell}>
      <nav className={styles.sidebar} aria-label="Navigation principale">
        <p className={styles.wordmark}>Oris</p>
        <ul className={styles.nav}>
          {NAVIGATION.map(({ href, label }) => (
            <li key={href}>
              <Link
                href={href}
                className={styles.navItem}
                aria-current={isActive(pathname, href) ? "page" : undefined}
              >
                {label}
              </Link>
            </li>
          ))}
          {["Modèles", "Paramètres"].map((label) => (
            <li key={label}>
              <span className={styles.navItem} aria-disabled="true">
                {label}
              </span>
            </li>
          ))}
        </ul>
        <p className={styles.demo}>Données fictives uniquement</p>
      </nav>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
