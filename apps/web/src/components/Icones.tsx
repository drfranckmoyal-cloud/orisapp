import type { ComponentProps } from "react";

/** Pictogrammes de la navigation, dessinés dans la famille géométrique du logo.
 *
 * Ils remplacent les puces : une liste à puces n'est pas une navigation.
 */
const TRACES = {
  accueil: <path d="M3 9.5 10 3.5l7 6M4.8 11v5.5h10.4V11" />,
  patients: (
    <>
      <circle cx="10" cy="7" r="3.2" />
      <path d="M4 16.6c.9-2.7 3.2-4.1 6-4.1s5.1 1.4 6 4.1" />
    </>
  ),
  correspondants: (
    <>
      <path d="M2.6 5.2h14.8v9.6H2.6z" />
      <path d="M2.6 5.6 10 10.8l7.4-5.2" />
    </>
  ),
  consultations: <path d="M4 8v4M7.3 5.4v9.2M10.6 7v6M14 4.6v10.8M17.3 8.4v3.2" />,
  documents: <path d="M5 3.2h6.4L15.4 7v9.8H5zM11.2 3.4V7.2h3.9M7.6 11h5M7.6 13.7h3.4" />,
  apprend: <path d="M10 3.2 11.7 7.9 16.4 9.6 11.7 11.3 10 16 8.3 11.3 3.6 9.6 8.3 7.9z" />,
  parametres: (
    <>
      <path d="M3.6 6.2h12.8M3.6 13.8h12.8" />
      <circle cx="12.4" cy="6.2" r="2.1" />
      <circle cx="7.6" cy="13.8" r="2.1" />
    </>
  ),
  chevron: <path d="M4 10.5 8 6.5l4 4" />,
  micro: (
    <>
      <path d="M10 2.6a2.3 2.3 0 0 1 2.3 2.3v4.4a2.3 2.3 0 0 1-4.6 0V4.9A2.3 2.3 0 0 1 10 2.6z" />
      <path d="M5.2 9a4.8 4.8 0 0 0 9.6 0M10 13.8v3.4" />
    </>
  ),
  retour: <path d="M16 10H4.6M9 4.8 4 10l5 5.2" />,
  journee: (
    <>
      <path d="M3.2 5.4h13.6v11.4H3.2zM3.2 8.8h13.6" />
      <path d="M6.6 3.2v3M13.4 3.2v3" />
    </>
  ),
} as const;

export type NomIcone = keyof typeof TRACES;

export function Icone({
  nom,
  taille = 20,
  ...props
}: { nom: NomIcone; taille?: number } & ComponentProps<"svg">) {
  return (
    <svg
      {...props}
      viewBox="0 0 20 20"
      width={taille}
      height={taille}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {TRACES[nom]}
    </svg>
  );
}
