import type { Encounter } from "@/lib/api";

export type TypeVisite = Encounter["visit_kind"];

/** Les rubriques des modèles de compte rendu du Dr Moyal, dans leur ordre
 *  (docs/MODELES_CR.md, décisions du 21/09/2026). Une rubrique sans contenu disparaît
 *  du document : la liste dit ce qui est attendu, pas ce qui est obligatoire. */
export const RUBRIQUES: Record<
  TypeVisite,
  { titre: string; detail?: string }[]
> = {
  consultation: [
    { titre: "Motif de la consultation" },
    { titre: "Examen clinique", detail: "radios, examens complémentaires" },
    { titre: "Diagnostic / analyse" },
    { titre: "Proposition thérapeutique" },
    { titre: "Informations données au patient" },
    { titre: "Actes réalisés" },
    { titre: "Suite de la prise en charge" },
    {
      titre: "Points d’attention / coordination",
      detail: "antécédents, traitements, allergies",
    },
  ],
  procedure: [
    { titre: "Indication" },
    { titre: "Situation pré-opératoire" },
    { titre: "Intervention réalisée" },
    {
      titre: "Protocole / éléments techniques",
      detail: "anesthésie, isolation, matériaux",
    },
    { titre: "Résultat immédiat" },
    { titre: "Suites et consignes" },
    { titre: "Coordination / prochaine étape" },
  ],
};

export const TYPE_VISITE: Record<TypeVisite, string> = {
  consultation: "Consultation",
  procedure: "Acte",
};
