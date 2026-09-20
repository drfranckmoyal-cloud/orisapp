"use client";

import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

import styles from "./ui.module.css";

type Ton = "neutre" | "accent" | "valide" | "attention" | "alerte";

const TON_PASTILLE: Record<Ton, string> = {
  neutre: "",
  accent: styles.pastilleAccent ?? "",
  valide: styles.pastilleValide ?? "",
  attention: styles.pastilleAttention ?? "",
  alerte: styles.pastilleAlerte ?? "",
};

/** Bouton. Trois intentions seulement : principale, secondaire, discrète. */
export function Bouton({
  variante = "principal",
  grand = false,
  className = "",
  ...props
}: ComponentProps<"button"> & { variante?: "principal" | "secondaire" | "discret"; grand?: boolean }) {
  const classes = [styles.bouton, styles[variante], grand ? styles.grand : "", className];
  return <button {...props} className={classes.filter(Boolean).join(" ")} />;
}

/** Lien qui se comporte comme un bouton (navigation, pas action). */
export function LienBouton({
  variante = "principal",
  grand = false,
  className = "",
  ...props
}: ComponentProps<typeof Link> & { variante?: "principal" | "secondaire" | "discret"; grand?: boolean }) {
  const classes = [styles.bouton, styles[variante], grand ? styles.grand : "", className];
  return <Link {...props} className={classes.filter(Boolean).join(" ")} />;
}

export function Carte({
  titre,
  action,
  serree = false,
  children,
  ...props
}: ComponentProps<"section"> & { titre?: ReactNode; action?: ReactNode; serree?: boolean }) {
  return (
    <section {...props} className={`${styles.carte} ${serree ? styles.carteSerree : ""}`}>
      {(titre || action) && (
        <header className={styles.enTeteCarte}>
          {titre && <h2 className={styles.titreCarte}>{titre}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function EnTetePage({
  surTitre,
  titre,
  action,
}: {
  surTitre?: string;
  titre: ReactNode;
  action?: ReactNode;
}) {
  return (
    <header className={styles.enTetePage}>
      <div>
        {surTitre && <p className={styles.surTitre}>{surTitre}</p>}
        <h1 className={styles.titrePage}>{titre}</h1>
      </div>
      {action}
    </header>
  );
}

/** Pastille d'état. Jamais la couleur seule : toujours accompagnée d'un mot. */
export function Pastille({
  ton = "neutre",
  point = false,
  children,
}: {
  ton?: Ton;
  point?: boolean;
  children: ReactNode;
}) {
  return (
    <span className={`${styles.pastille} ${TON_PASTILLE[ton]}`}>
      {point && <span className={styles.point} aria-hidden="true" />}
      {children}
    </span>
  );
}

/** État vide : dire ce qui manque et quoi faire, jamais un écran blanc. */
export function EtatVide({ titre, children }: { titre: string; children?: ReactNode }) {
  return (
    <div className={styles.vide}>
      <span className={styles.videTitre}>{titre}</span>
      {children}
    </div>
  );
}

export function Squelette({ lignes = 3 }: { lignes?: number }) {
  return (
    <div style={{ display: "grid", gap: 12 }} aria-hidden="true">
      {Array.from({ length: lignes }).map((_, index) => (
        <div
          key={index}
          className={styles.squelette}
          style={{ width: `${100 - index * 12}%` }}
        />
      ))}
    </div>
  );
}

export function Lignes({ children }: { children: ReactNode }) {
  return <div className={styles.lignes}>{children}</div>;
}

export function Ligne({
  href,
  titre,
  detail,
  fin,
}: {
  href: string;
  titre: ReactNode;
  detail?: ReactNode;
  fin?: ReactNode;
}) {
  return (
    <Link href={href} className={styles.ligne}>
      <span>
        <span className={styles.ligneTitre}>{titre}</span>
        {detail && (
          <>
            <br />
            <span className={styles.ligneDetail}>{detail}</span>
          </>
        )}
      </span>
      {fin}
    </Link>
  );
}

export function Champ(props: ComponentProps<"input">) {
  return <input {...props} className={`${styles.champ} ${props.className ?? ""}`} />;
}

/** Onglets. Un seul groupe visible à la fois, jamais de contenu caché sans onglet. */
export function Onglets<T extends string>({
  valeur,
  onChange,
  options,
}: {
  valeur: T;
  onChange: (valeur: T) => void;
  options: { valeur: T; libelle: ReactNode }[];
}) {
  return (
    <div className={styles.onglets} role="tablist">
      {options.map((option) => (
        <button
          key={option.valeur}
          type="button"
          role="tab"
          aria-selected={option.valeur === valeur}
          className={styles.onglet}
          onClick={() => onChange(option.valeur)}
        >
          {option.libelle}
        </button>
      ))}
    </div>
  );
}

export type EtapeEtat = "attente" | "encours" | "faite";

/** Étapes d'un traitement. Une étape n'est cochée que si elle est réellement faite. */
export function Etapes({ etapes }: { etapes: { libelle: string; etat: EtapeEtat }[] }) {
  return (
    <ul className={styles.etapes}>
      {etapes.map(({ libelle, etat }) => (
        <li
          key={libelle}
          className={[
            styles.etape,
            etat === "faite" ? styles.etapeFaite : "",
            etat === "encours" ? styles.etapeEnCours : "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          <span className={styles.etapeMarque} aria-hidden="true">
            {etat === "faite" ? "✓" : ""}
          </span>
          {libelle}
          {etat === "encours" && <span className="sr-only">en cours</span>}
        </li>
      ))}
    </ul>
  );
}

export function Barre({ children }: { children: ReactNode }) {
  return <div className={styles.barre}>{children}</div>;
}

export function Pousse() {
  return <span className={styles.pousse} />;
}

/** Zone de texte. `compacte` pour une note de quelques lignes, pas un document. */
export function Zone({
  compacte = false,
  ...props
}: ComponentProps<"textarea"> & { compacte?: boolean }) {
  const classes = [styles.zone, compacte ? styles.zoneCompacte : "", props.className ?? ""];
  return <textarea {...props} className={classes.filter(Boolean).join(" ")} />;
}
