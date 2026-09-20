/** Lecture d'un fichier STL — binaire ou ASCII.
 *
 * Le STL est le format des empreintes numériques : une liste de triangles, sans
 * couleur ni texture. Rien d'autre à en tirer, et c'est tant mieux — on peut le
 * lire en quelques lignes plutôt que d'embarquer une bibliothèque de 600 ko.
 */

export type Maillage = {
  /** 3 sommets × 3 coordonnées par triangle. */
  positions: Float32Array;
  /** Une normale par sommet, pour l'éclairage. */
  normales: Float32Array;
  triangles: number;
  /** Centre et rayon de la boîte englobante, pour cadrer la vue. */
  centre: [number, number, number];
  rayon: number;
};

/** Un STL binaire annonce son nombre de triangles : la taille doit correspondre. */
function estBinaire(donnees: ArrayBuffer): boolean {
  if (donnees.byteLength < 84) return false;
  const vue = new DataView(donnees);
  const triangles = vue.getUint32(80, true);
  if (84 + triangles * 50 === donnees.byteLength) return true;
  // Sinon on regarde l'en-tête : un ASCII commence par « solid ».
  const debut = new TextDecoder().decode(new Uint8Array(donnees, 0, 5)).toLowerCase();
  return debut !== "solid";
}

function lireBinaire(donnees: ArrayBuffer): { positions: Float32Array; normales: Float32Array } {
  const vue = new DataView(donnees);
  const triangles = vue.getUint32(80, true);
  const positions = new Float32Array(triangles * 9);
  const normales = new Float32Array(triangles * 9);
  let curseur = 84;
  for (let t = 0; t < triangles; t += 1) {
    const nx = vue.getFloat32(curseur, true);
    const ny = vue.getFloat32(curseur + 4, true);
    const nz = vue.getFloat32(curseur + 8, true);
    curseur += 12;
    for (let s = 0; s < 3; s += 1) {
      const i = t * 9 + s * 3;
      positions[i] = vue.getFloat32(curseur, true);
      positions[i + 1] = vue.getFloat32(curseur + 4, true);
      positions[i + 2] = vue.getFloat32(curseur + 8, true);
      normales[i] = nx;
      normales[i + 1] = ny;
      normales[i + 2] = nz;
      curseur += 12;
    }
    curseur += 2; // attribut, toujours ignoré
  }
  return { positions, normales };
}

function lireAscii(donnees: ArrayBuffer): { positions: Float32Array; normales: Float32Array } {
  const texte = new TextDecoder().decode(donnees);
  const sommets: number[] = [];
  const normales: number[] = [];
  let normale: [number, number, number] = [0, 0, 1];
  for (const ligne of texte.split("\n")) {
    const mots = ligne.trim().split(/\s+/);
    if (mots[0] === "facet" && mots[1] === "normal") {
      normale = [Number(mots[2]), Number(mots[3]), Number(mots[4])];
    } else if (mots[0] === "vertex") {
      sommets.push(Number(mots[1]), Number(mots[2]), Number(mots[3]));
      normales.push(...normale);
    }
  }
  return { positions: new Float32Array(sommets), normales: new Float32Array(normales) };
}

/** Une normale nulle (certains exportateurs les omettent) se recalcule. */
function completerNormales(positions: Float32Array, normales: Float32Array): void {
  for (let i = 0; i < positions.length; i += 9) {
    if (normales[i] !== 0 || normales[i + 1] !== 0 || normales[i + 2] !== 0) continue;
    const ax = positions[i + 3]! - positions[i]!;
    const ay = positions[i + 4]! - positions[i + 1]!;
    const az = positions[i + 5]! - positions[i + 2]!;
    const bx = positions[i + 6]! - positions[i]!;
    const by = positions[i + 7]! - positions[i + 1]!;
    const bz = positions[i + 8]! - positions[i + 2]!;
    let nx = ay * bz - az * by;
    let ny = az * bx - ax * bz;
    let nz = ax * by - ay * bx;
    const longueur = Math.hypot(nx, ny, nz) || 1;
    nx /= longueur;
    ny /= longueur;
    nz /= longueur;
    for (let s = 0; s < 3; s += 1) {
      normales[i + s * 3] = nx;
      normales[i + s * 3 + 1] = ny;
      normales[i + s * 3 + 2] = nz;
    }
  }
}

export function lireStl(donnees: ArrayBuffer): Maillage {
  const { positions, normales } = estBinaire(donnees) ? lireBinaire(donnees) : lireAscii(donnees);
  if (positions.length === 0) throw new Error("STL_VIDE");
  completerNormales(positions, normales);

  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;
  for (let i = 0; i < positions.length; i += 3) {
    minX = Math.min(minX, positions[i]!);
    maxX = Math.max(maxX, positions[i]!);
    minY = Math.min(minY, positions[i + 1]!);
    maxY = Math.max(maxY, positions[i + 1]!);
    minZ = Math.min(minZ, positions[i + 2]!);
    maxZ = Math.max(maxZ, positions[i + 2]!);
  }
  const centre: [number, number, number] = [
    (minX + maxX) / 2,
    (minY + maxY) / 2,
    (minZ + maxZ) / 2,
  ];
  const rayon = Math.max(maxX - minX, maxY - minY, maxZ - minZ) / 2 || 1;
  return { positions, normales, triangles: positions.length / 9, centre, rayon };
}
