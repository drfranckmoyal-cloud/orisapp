import { Icone } from "@/components/Icones";
import type { DocumentView } from "@/lib/api";
import { DOCUMENT_TYPE } from "@/lib/labels";

import styles from "./typeDocument.module.css";

const TEINTE: Record<DocumentView["document_type"], string | undefined> = {
  consultation_note: styles.compteRendu,
  treatment_plan_text: styles.plan,
  operative_note: styles.operatoire,
  patient_summary: styles.resume,
  referral_letter: styles.courrier,
};

/** Le type d'un document, dans sa teinte : on reconnaît un plan de traitement sans lire.
 *
 * Un document validé porte une coche : c'est la seule chose qu'on veut savoir de son
 * état en parcourant une liste.
 */
export function TypeDocument({
  type,
  valide = false,
  taille = "normal",
}: {
  type: DocumentView["document_type"];
  valide?: boolean;
  taille?: "normal" | "petit" | "leger";
}) {
  return (
    <span
      className={`${styles.type} ${TEINTE[type] ?? ""} ${taille === "petit" ? styles.petit : ""} ${taille === "leger" ? styles.leger : ""}`}
      title={valide ? `${DOCUMENT_TYPE[type]} — validé` : DOCUMENT_TYPE[type]}
    >
      {valide && <Icone nom="valide" taille={12} aria-hidden="true" />}
      {DOCUMENT_TYPE[type]}
    </span>
  );
}
