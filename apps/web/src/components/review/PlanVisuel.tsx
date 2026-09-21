"use client";

import type { EtapePlan, PlanVue } from "@/lib/api";
import { type DentPlacee, placer } from "@/lib/odontogramme";
import { useApi } from "@/lib/useApi";

import styles from "./plan.module.css";

const LARGEUR = 170;
const A = LARGEUR * 0.25;
const B = A * 0.62;
const HAUT_CY = B + 13;
const BAS_CY = HAUT_CY + 7;
const HAUTEUR = BAS_CY + B + 12;
/** Cadrage serré sur les arcades : à l'écran, la marge du PDF n'a pas lieu d'être. */
const X0 = LARGEUR / 2 - A - 16;
const LARGEUR_VUE = 2 * A + 32;

const trait = (index: number) => `var(--etape-${index % 6})`;
const fond = (index: number) => `var(--etape-${index % 6}-douce)`;

function Dent({
  dent,
  couleurs,
  absente,
}: {
  dent: DentPlacee;
  couleurs: number[];
  absente: boolean;
}) {
  const derniere = couleurs.at(-1);
  const w = dent.largeur;
  const d = dent.epaisseur;
  const rayon = Math.min(w, d) * (dent.rang <= 3 ? 0.48 : 0.36);
  const portee = Math.max(w, d) / 2 + 3.2;
  const [ox, oy] = dent.dehors;
  return (
    <g>
      <g transform={`translate(${dent.x} ${dent.y}) rotate(${dent.angle})`}>
        <rect
          x={-w / 2}
          y={-d / 2}
          width={w}
          height={d}
          rx={rayon}
          fill={
            derniere === undefined
              ? absente
                ? "none"
                : "var(--surface)"
              : fond(derniere)
          }
          stroke={
            derniere === undefined ? "var(--trait-fort)" : trait(derniere)
          }
          strokeWidth={derniere === undefined ? 0.3 : 0.5}
          strokeDasharray={absente ? "0.9 0.7" : undefined}
        />
        {!absente && dent.rang >= 4 && (
          <g
            stroke={derniere === undefined ? "var(--trait)" : trait(derniere)}
            strokeWidth={0.2}
          >
            <line x1={-w * 0.28} y1={0} x2={w * 0.28} y2={0} />
            {dent.rang >= 6 && (
              <line x1={0} y1={-d * 0.25} x2={0} y2={d * 0.25} />
            )}
          </g>
        )}
      </g>
      <text
        x={dent.x + ox * portee}
        y={dent.y + oy * portee + 0.9}
        className={styles.numero}
        textAnchor="middle"
      >
        {dent.numero}
      </text>
      {couleurs.map((index, rang) => {
        const distance = portee + 3.3 + rang * 2.9;
        return (
          <circle
            key={`${index}-${rang}`}
            cx={dent.x + ox * distance}
            cy={dent.y + oy * distance}
            r={1.15}
            fill={trait(index)}
          />
        );
      })}
    </g>
  );
}

/** Les deux arcades en vue occlusale, teintées par étape. */
export function Odontogramme({ vue }: { vue: PlanVue }) {
  const etapesDe = new Map<string, number[]>();
  for (const etape of vue.etapes) {
    for (const dent of etape.dents)
      etapesDe.set(dent, [...(etapesDe.get(dent) ?? []), etape.couleur]);
  }
  const absentes = new Set(vue.dents_absentes);
  const dents = [
    ...placer("haut", LARGEUR / 2, HAUT_CY, A, B),
    ...placer("bas", LARGEUR / 2, BAS_CY, A, B),
  ];
  return (
    <figure className={styles.schema}>
      <svg
        viewBox={`${X0} -5 ${LARGEUR_VUE} ${HAUTEUR + 5}`}
        role="img"
        aria-label="Schéma dentaire"
      >
        <text x={X0 + 1} y={0} className={styles.arcade}>
          Maxillaire
        </text>
        <text x={X0 + 1} y={HAUTEUR - 1} className={styles.arcade}>
          Mandibule
        </text>
        {dents.map((dent) => (
          <Dent
            key={dent.numero}
            dent={dent}
            couleurs={etapesDe.get(dent.numero) ?? []}
            absente={absentes.has(dent.numero)}
          />
        ))}
      </svg>
      <figcaption>
        {vue.dents_absentes.length > 0 && "En pointillé : dents absentes. "}
        Pastilles : étapes qui concernent la dent.
      </figcaption>
    </figure>
  );
}

function titre(etape: EtapePlan) {
  return etape.rang ? `Étape ${etape.rang} — ${etape.titre}` : etape.titre;
}

/** Le plan comme il s'imprime : schéma, étapes, chronologie, écarté. */
export function PlanVisuel({
  encounterId,
  version,
}: {
  encounterId: string;
  version: number;
}) {
  const [vue] = useApi<PlanVue>(
    `/encounters/${encounterId}/plan-vue?v=${version}`,
  );
  if (vue.state !== "ready") return null;
  const plan = vue.data;
  if (plan.etapes.length === 0 && plan.ecartes.length === 0) return null;
  const frise = plan.etapes.length > 1 && plan.etapes.some((e) => e.delai);

  return (
    <div className={styles.plan}>
      <Odontogramme vue={plan} />

      <ol className={styles.etapes}>
        {plan.etapes.map((etape) => (
          <li
            key={`${etape.couleur}-${etape.titre}`}
            className={styles.etape}
            style={{ borderLeftColor: trait(etape.couleur) }}
          >
            <h4 style={{ color: trait(etape.couleur) }}>{titre(etape)}</h4>
            <p className={styles.meta}>
              {[etape.delai, etape.statut].filter(Boolean).join(" · ")}
            </p>
            {etape.dents.length > 0 && <p>Dents : {etape.dents.join(", ")}</p>}
            {etape.details.map((detail) => (
              <p key={detail}>{detail}</p>
            ))}
          </li>
        ))}
      </ol>

      {frise && (
        <section>
          <h4 className={styles.sousTitre}>Chronologie</h4>
          <ol className={styles.frise}>
            {plan.etapes.map((etape) => (
              <li key={`${etape.couleur}-frise`}>
                <span className={styles.delai}>{etape.delai ?? " "}</span>
                <span
                  className={styles.point}
                  style={{ background: trait(etape.couleur) }}
                />
                {etape.rang && (
                  <strong style={{ color: trait(etape.couleur) }}>
                    Étape {etape.rang}
                  </strong>
                )}
                <span className={styles.friseTitre}>{etape.titre}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {plan.ecartes.length > 0 && (
        <section>
          <h4 className={styles.sousTitre}>Écarté</h4>
          {plan.ecartes.map((etape) => (
            <p key={etape.titre} className={styles.ecarte}>
              <strong>
                {etape.titre}
                {etape.dents.length > 0 && ` (${etape.dents.join(", ")})`}
              </strong>{" "}
              — {etape.statut}. {etape.details.join(" ")}
            </p>
          ))}
        </section>
      )}
    </div>
  );
}
