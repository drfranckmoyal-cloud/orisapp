"use client";

import { Bouton } from "@/components/ui";
import type { Correspondant } from "@/lib/api";

import styles from "./correspondants.module.css";

/** La fiche d'un correspondant, telle qu'on la lit.
 *
 * Ouvrir une fiche, c'est la consulter — pas la modifier. On y vient pour retrouver un
 * numéro ou vérifier une adresse ; tomber d'emblée sur un formulaire donne l'impression
 * qu'on risque d'abîmer quelque chose. Le bouton qui rend modifiable reste discret.
 */

function Ligne({ cle, valeur }: { cle: string; valeur: string }) {
  return (
    <div className={styles.ligneDetail}>
      <span className={styles.cle}>{cle}</span>
      <span className={styles.valeur}>
        {valeur ? valeur : <span className={styles.manque}>non renseigné</span>}
      </span>
    </div>
  );
}

export function Detail({
  correspondant,
  onModifier,
}: {
  correspondant: Correspondant;
  onModifier: () => void;
}) {
  const personne = correspondant.kind === "practitioner";

  return (
    <div className={styles.detail}>
      <div className={styles.cadreDetail}>
        <Ligne cle="Nature" valeur={personne ? "Praticien" : "Structure"} />
        {personne && <Ligne cle="Civilité" valeur={correspondant.title} />}
        <Ligne
          cle={personne ? "Nom" : "Nom de la structure"}
          valeur={
            personne
              ? `${correspondant.first_name} ${correspondant.last_name}`.trim()
              : correspondant.last_name
          }
        />
        {personne && <Ligne cle="Spécialité" valeur={correspondant.specialty} />}
        {personne && <Ligne cle="Cabinet" valeur={correspondant.practice} />}
        <Ligne cle="Adresse électronique" valeur={correspondant.email} />
        {/* Le second contact ne se montre que s'il existe : une ligne « non renseigné »
            de plus ferait croire qu'il manque quelque chose. */}
        {correspondant.secondary_email && (
          <Ligne cle="Autre adresse" valeur={correspondant.secondary_email} />
        )}
        <Ligne cle="Téléphone" valeur={correspondant.phone} />
        {correspondant.secondary_phone && (
          <Ligne cle="Autre téléphone" valeur={correspondant.secondary_phone} />
        )}
        <Ligne cle="Adresse postale" valeur={correspondant.address} />
        <Ligne cle="Note" valeur={correspondant.note} />
      </div>

      <div className={styles.piedDetail}>
        <Bouton variante="secondaire" onClick={onModifier}>
          Modifier
        </Bouton>
      </div>
    </div>
  );
}
