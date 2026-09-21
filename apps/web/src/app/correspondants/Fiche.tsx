"use client";

import { useState } from "react";

import { Bouton, Champ } from "@/components/ui";
import type { Correspondant } from "@/lib/api";

import styles from "./correspondants.module.css";

/** Le formulaire d'un correspondant, pour en créer un ou en modifier un.
 *
 * La nature se choisit d'abord, parce qu'elle décide du reste : une structure n'a ni
 * civilité, ni prénom, ni spécialité, et les champs correspondants disparaissent au lieu
 * de rester vides. Le serveur les efface de son côté — l'écran ne fait que le montrer.
 */

export type Brouillon = {
  kind: "practitioner" | "organisation";
  title: string;
  last_name: string;
  first_name: string;
  specialty: string;
  practice: string;
  email: string;
  phone: string;
  address: string;
  note: string;
};

export const VIDE: Brouillon = {
  kind: "practitioner",
  title: "",
  last_name: "",
  first_name: "",
  specialty: "",
  practice: "",
  email: "",
  phone: "",
  address: "",
  note: "",
};

export function brouillonDe(c: Correspondant): Brouillon {
  return {
    kind: c.kind,
    title: c.title,
    last_name: c.last_name,
    first_name: c.first_name,
    specialty: c.specialty,
    practice: c.practice,
    email: c.email,
    phone: c.phone,
    address: c.address,
    note: c.note,
  };
}

const CIVILITES = ["", "Dr", "Pr", "M.", "Mme"];

export function Fiche({
  depart,
  specialites,
  occupe,
  onValider,
  onAnnuler,
  onSupprimer,
}: {
  depart: Brouillon;
  specialites: string[];
  occupe: boolean;
  onValider: (brouillon: Brouillon) => void;
  onAnnuler: () => void;
  onSupprimer?: () => void;
}) {
  const [brouillon, setBrouillon] = useState<Brouillon>(depart);
  const personne = brouillon.kind === "practitioner";

  function poser<C extends keyof Brouillon>(champ: C, valeur: Brouillon[C]) {
    setBrouillon((actuel) => ({ ...actuel, [champ]: valeur }));
  }

  return (
    <form
      className={styles.champs}
      onSubmit={(event) => {
        event.preventDefault();
        onValider(brouillon);
      }}
    >
      <label className={`field ${styles.pleineLargeur}`}>
        Nature
        <div className={styles.natures}>
          {(
            [
              ["practitioner", "Praticien"],
              ["organisation", "Structure"],
            ] as const
          ).map(([valeur, libelle]) => (
            <button
              key={valeur}
              type="button"
              className={`${styles.nature} ${brouillon.kind === valeur ? styles.natureChoisie : ""}`}
              aria-pressed={brouillon.kind === valeur}
              onClick={() => poser("kind", valeur)}
            >
              {libelle}
            </button>
          ))}
        </div>
      </label>

      {personne && (
        <label className="field">
          Civilité
          <select
            className={styles.choix}
            value={brouillon.title}
            onChange={(event) => poser("title", event.target.value)}
          >
            {CIVILITES.map((civilite) => (
              <option key={civilite || "aucune"} value={civilite}>
                {civilite || "non renseignée"}
              </option>
            ))}
          </select>
        </label>
      )}

      <label className="field">
        {personne ? "Nom" : "Nom de la structure"}
        <Champ
          value={brouillon.last_name}
          required
          autoFocus
          onChange={(event) => poser("last_name", event.target.value)}
        />
      </label>

      {personne && (
        <label className="field">
          Prénom
          <Champ
            value={brouillon.first_name}
            onChange={(event) => poser("first_name", event.target.value)}
          />
        </label>
      )}

      {personne && (
        <label className="field">
          Spécialité
          <select
            className={styles.choix}
            value={brouillon.specialty}
            onChange={(event) => poser("specialty", event.target.value)}
          >
            <option value="">non renseignée</option>
            {specialites.map((specialite) => (
              <option key={specialite} value={specialite}>
                {specialite}
              </option>
            ))}
          </select>
        </label>
      )}

      {/* Une structure est déjà un établissement : lui demander son « cabinet » en plus
          ne veut rien dire. */}
      {personne && (
        <label className="field">
          Nom du cabinet
          <Champ
            value={brouillon.practice}
            placeholder="facultatif"
            onChange={(event) => poser("practice", event.target.value)}
          />
        </label>
      )}

      <label className="field">
        Adresse électronique
        <Champ
          type="email"
          value={brouillon.email}
          onChange={(event) => poser("email", event.target.value)}
        />
      </label>

      <label className="field">
        Téléphone
        <Champ
          type="tel"
          value={brouillon.phone}
          onChange={(event) => poser("phone", event.target.value)}
        />
      </label>

      <label className={`field ${styles.pleineLargeur}`}>
        Adresse postale
        <textarea
          className={styles.aire}
          value={brouillon.address}
          placeholder="12 rue des Lilas&#10;75011 Paris"
          onChange={(event) => poser("address", event.target.value)}
        />
      </label>

      <label className={`field ${styles.pleineLargeur}`}>
        Note
        <textarea
          className={styles.aire}
          value={brouillon.note}
          placeholder="délai, préférences d’envoi, ce qu’il faut savoir avant d’adresser…"
          onChange={(event) => poser("note", event.target.value)}
        />
      </label>

      <div className={styles.boutons}>
        <Bouton type="submit" disabled={occupe || !brouillon.last_name.trim()}>
          {occupe ? "Enregistrement…" : "Enregistrer"}
        </Bouton>
        <Bouton type="button" variante="secondaire" onClick={onAnnuler}>
          Annuler
        </Bouton>
        {onSupprimer && (
          <button type="button" className={styles.supprimer} onClick={onSupprimer}>
            Supprimer ce correspondant
          </button>
        )}
      </div>
    </form>
  );
}
