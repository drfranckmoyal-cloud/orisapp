/** Schéma dentaire des deux arcades, vues d'en haut — la même géométrie que le PDF
 *  (services/api/src/oris_api/documents/odontogramme.py). Unités : millimètres,
 *  axe vertical vers le bas. */

const HAUT: Record<number, [number, number]> = {
  1: [8.5, 7.0],
  2: [6.6, 6.2],
  3: [7.6, 8.0],
  4: [7.0, 9.0],
  5: [6.6, 9.0],
  6: [10.2, 11.0],
  7: [9.2, 10.6],
  8: [8.6, 10.0],
};
const BAS: Record<number, [number, number]> = {
  1: [5.4, 6.0],
  2: [5.9, 6.4],
  3: [6.9, 7.6],
  4: [7.0, 7.8],
  5: [7.1, 8.2],
  6: [11.0, 10.4],
  7: [10.4, 10.0],
  8: [10.0, 9.6],
};

export type DentPlacee = {
  numero: string;
  x: number;
  y: number;
  angle: number;
  largeur: number;
  epaisseur: number;
  dehors: [number, number];
  rang: number;
};

export function ordre(arcade: "haut" | "bas"): string[] {
  const [droite, gauche] = arcade === "haut" ? ["1", "2"] : ["4", "3"];
  return [
    ...[8, 7, 6, 5, 4, 3, 2, 1].map((i) => `${droite}${i}`),
    ...[1, 2, 3, 4, 5, 6, 7, 8].map((i) => `${gauche}${i}`),
  ];
}

export function placer(
  arcade: "haut" | "bas",
  cx: number,
  cy: number,
  a: number,
  b: number,
): DentPlacee[] {
  const tailles = arcade === "haut" ? HAUT : BAS;
  const signe = arcade === "haut" ? -1 : 1;
  const debut = Math.PI - 0.02;
  const fin = 0.02;
  const pas = 400;
  const points: [number, number][] = [];
  for (let i = 0; i <= pas; i += 1) {
    const t = debut + ((fin - debut) * i) / pas;
    points.push([cx + a * Math.cos(t), cy + signe * b * Math.sin(t)]);
  }
  const cumul = [0];
  for (let i = 1; i < points.length; i += 1) {
    const [x0, y0] = points[i - 1]!;
    const [x1, y1] = points[i]!;
    cumul.push(cumul[i - 1]! + Math.hypot(x1 - x0, y1 - y0));
  }
  const longueur = cumul[cumul.length - 1]!;
  const numeros = ordre(arcade);
  const largeurs = numeros.map((n) => tailles[Number(n[1])]![0]);
  const jeu = 0.9;
  const echelle =
    longueur / (largeurs.reduce((s, l) => s + l, 0) + jeu * largeurs.length);

  let parcouru = 0;
  return numeros.map((numero, k) => {
    const largeur = largeurs[k]!;
    const milieu = (parcouru + (largeur + jeu) / 2) * echelle;
    parcouru += largeur + jeu;
    let i = cumul.findIndex((c) => c >= milieu);
    i = Math.min(Math.max(i, 1), pas);
    const [x0, y0] = points[i - 1]!;
    const [x, y] = points[i]!;
    const rang = Number(numero[1]);
    const norme = Math.hypot(x - cx, y - cy) || 1;
    return {
      numero,
      x,
      y,
      angle: (Math.atan2(y - y0, x - x0) * 180) / Math.PI,
      largeur: tailles[rang]![0] * echelle,
      epaisseur: tailles[rang]![1] * echelle,
      dehors: [(x - cx) / norme, (y - cy) / norme],
      rang,
    };
  });
}
