"use client";

import { useEffect, useRef, useState } from "react";

import { lireStl, type Maillage } from "@/lib/stl";

import styles from "./apercu.module.css";

const SOMMET = `
attribute vec3 position;
attribute vec3 normale;
uniform mat4 modeleVue;
uniform mat4 projection;
varying vec3 vNormale;
void main() {
  vNormale = mat3(modeleVue) * normale;
  gl_Position = projection * modeleVue * vec4(position, 1.0);
}`;

const FRAGMENT = `
precision mediump float;
varying vec3 vNormale;
void main() {
  vec3 n = normalize(vNormale);
  // Sur fond clair, c'est le modelé qui doit porter le relief : une lumière de face,
  // une rasante, et un assombrissement sur les bords pour détacher la silhouette.
  float face = max(dot(n, normalize(vec3(0.35, 0.55, 1.0))), 0.0);
  float rase = max(dot(n, normalize(vec3(-0.7, -0.2, 0.3))), 0.0);
  float bord = 1.0 - pow(1.0 - abs(n.z), 2.2);
  vec3 teinte = vec3(0.78, 0.75, 0.70) * (0.34 + 0.52 * face + 0.20 * rase) * (0.62 + 0.38 * bord);
  gl_FragColor = vec4(teinte, 1.0);
}`;

function compiler(
  gl: WebGLRenderingContext,
  type: number,
  source: string,
): WebGLShader {
  const shader = gl.createShader(type);
  if (!shader) throw new Error("SHADER");
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    throw new Error(gl.getShaderInfoLog(shader) ?? "SHADER");
  }
  return shader;
}

/** Matrice de projection en perspective. */
function projection(aspect: number): Float32Array {
  const f = 1 / Math.tan(Math.PI / 8);
  const proche = 0.1;
  const loin = 100;
  return new Float32Array([
    f / aspect,
    0,
    0,
    0,
    0,
    f,
    0,
    0,
    0,
    0,
    (loin + proche) / (proche - loin),
    -1,
    0,
    0,
    (2 * loin * proche) / (proche - loin),
    0,
  ]);
}

/** Modèle-vue : on centre l'objet, on le tourne, on recule la caméra. */
function modeleVue(
  centre: [number, number, number],
  echelle: number,
  pivotX: number,
  pivotY: number,
  distance: number,
): Float32Array {
  const cx = Math.cos(pivotX);
  const sx = Math.sin(pivotX);
  const cy = Math.cos(pivotY);
  const sy = Math.sin(pivotY);
  // Rotation Y puis X, mise à l'échelle, translation du centre, recul caméra.
  const r = [
    cy * echelle,
    sy * sx * echelle,
    -sy * cx * echelle,
    0,
    cx * echelle,
    sx * echelle,
    sy * echelle,
    -cy * sx * echelle,
    cy * cx * echelle,
  ];
  const t = [
    -(r[0]! * centre[0] + r[3]! * centre[1] + r[6]! * centre[2]),
    -(r[1]! * centre[0] + r[4]! * centre[1] + r[7]! * centre[2]),
    -(r[2]! * centre[0] + r[5]! * centre[1] + r[8]! * centre[2]) - distance,
  ];
  return new Float32Array([
    r[0]!,
    r[1]!,
    r[2]!,
    0,
    r[3]!,
    r[4]!,
    r[5]!,
    0,
    r[6]!,
    r[7]!,
    r[8]!,
    0,
    t[0]!,
    t[1]!,
    t[2]!,
    1,
  ]);
}

/** Aperçu d'une empreinte numérique. Glisser pour tourner, molette pour approcher.
 *
 * Écrit à la main plutôt qu'avec une bibliothèque 3D : un STL n'est qu'une liste de
 * triangles, et six cents kilo-octets de dépendance pour l'afficher seraient de trop.
 */
export function VisionneuseStl({ url }: { url: string }) {
  const toile = useRef<HTMLCanvasElement | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [maillage, setMaillage] = useState<Maillage | null>(null);

  useEffect(() => {
    let vivant = true;
    (async () => {
      try {
        const reponse = await fetch(url);
        if (!reponse.ok) throw new Error("TELECHARGEMENT");
        const lu = lireStl(await reponse.arrayBuffer());
        if (vivant) setMaillage(lu);
      } catch {
        if (vivant)
          setErreur("Ce fichier n’a pas pu être lu comme une empreinte STL.");
      }
    })();
    return () => {
      vivant = false;
    };
  }, [url]);

  useEffect(() => {
    const canvas = toile.current;
    const forme = maillage;
    if (!canvas || !forme) return;

    // Tout le montage se fait à la trame suivante : régler un état pendant le corps
    // d'un effet déclenche un rendu en cascade, et React s'en plaint à juste titre.
    let nettoyer: (() => void) | undefined;
    const montage = requestAnimationFrame(() => {
      nettoyer = monter(canvas, forme);
    });
    return () => {
      cancelAnimationFrame(montage);
      nettoyer?.();
    };

    function monter(canvas: HTMLCanvasElement, forme: Maillage): (() => void) | undefined {
      const gl = canvas.getContext("webgl", { antialias: true });
      if (!gl) {
        setErreur("L’affichage 3D n’est pas disponible dans ce navigateur.");
        return;
      }

      const programme = gl.createProgram();
      if (!programme) return;
      try {
        gl.attachShader(programme, compiler(gl, gl.VERTEX_SHADER, SOMMET));
        gl.attachShader(programme, compiler(gl, gl.FRAGMENT_SHADER, FRAGMENT));
        gl.linkProgram(programme);
        gl.useProgram(programme);
      } catch {
        setErreur("L’affichage 3D n’a pas pu démarrer.");
        return;
      }

      function tampon(donnees: Float32Array, nom: string) {
        const buf = gl!.createBuffer();
        gl!.bindBuffer(gl!.ARRAY_BUFFER, buf);
        gl!.bufferData(gl!.ARRAY_BUFFER, donnees, gl!.STATIC_DRAW);
        const place = gl!.getAttribLocation(programme!, nom);
        gl!.enableVertexAttribArray(place);
        gl!.vertexAttribPointer(place, 3, gl!.FLOAT, false, 0, 0);
      }
      tampon(forme.positions, "position");
      tampon(forme.normales, "normale");

      const uModeleVue = gl.getUniformLocation(programme, "modeleVue");
      const uProjection = gl.getUniformLocation(programme, "projection");
      gl.enable(gl.DEPTH_TEST);
      // Fond blanc à peine grisé : l'empreinte se lit comme un plâtre sur un plan de travail.
    gl.clearColor(0.962, 0.956, 0.945, 1);

      // L'objet est ramené à une taille d'une unité : la caméra ne bouge plus.
      const echelle = 1 / forme.rayon;
      let pivotX = -0.5;
      let pivotY = 0.6;
      let distance = 3.2;
      let animation = 0;

      function dessiner() {
        const largeur = canvas!.clientWidth;
        const hauteur = canvas!.clientHeight;
        const densite = Math.min(window.devicePixelRatio || 1, 2);
        if (
          canvas!.width !== largeur * densite ||
          canvas!.height !== hauteur * densite
        ) {
          canvas!.width = largeur * densite;
          canvas!.height = hauteur * densite;
        }
        gl!.viewport(0, 0, canvas!.width, canvas!.height);
        gl!.clear(gl!.COLOR_BUFFER_BIT | gl!.DEPTH_BUFFER_BIT);
        gl!.uniformMatrix4fv(
          uProjection,
          false,
          projection(largeur / hauteur || 1),
        );
        gl!.uniformMatrix4fv(
          uModeleVue,
          false,
          modeleVue(forme.centre, echelle, pivotX, pivotY, distance),
        );
        gl!.drawArrays(gl!.TRIANGLES, 0, forme.triangles * 3);
      }

      function redessiner() {
        cancelAnimationFrame(animation);
        animation = requestAnimationFrame(dessiner);
      }
      redessiner();

      let saisi = false;
      let dernierX = 0;
      let dernierY = 0;
      function debut(evenement: PointerEvent) {
        saisi = true;
        dernierX = evenement.clientX;
        dernierY = evenement.clientY;
        canvas!.setPointerCapture(evenement.pointerId);
      }
      function bouge(evenement: PointerEvent) {
        if (!saisi) return;
        pivotY += (evenement.clientX - dernierX) * 0.01;
        pivotX += (evenement.clientY - dernierY) * 0.01;
        pivotX = Math.max(-1.5, Math.min(1.5, pivotX));
        dernierX = evenement.clientX;
        dernierY = evenement.clientY;
        redessiner();
      }
      function fin() {
        saisi = false;
      }
      function molette(evenement: WheelEvent) {
        evenement.preventDefault();
        distance = Math.max(
          1.4,
          Math.min(9, distance + evenement.deltaY * 0.004),
        );
        redessiner();
      }
      canvas.addEventListener("pointerdown", debut);
      canvas.addEventListener("pointermove", bouge);
      canvas.addEventListener("pointerup", fin);
      canvas.addEventListener("wheel", molette, { passive: false });
      const surTaille = () => redessiner();
      window.addEventListener("resize", surTaille);

      return () => {
        cancelAnimationFrame(animation);
        canvas.removeEventListener("pointerdown", debut);
        canvas.removeEventListener("pointermove", bouge);
        canvas.removeEventListener("pointerup", fin);
        canvas.removeEventListener("wheel", molette);
        window.removeEventListener("resize", surTaille);
      };
    }
  }, [maillage]);

  if (erreur) return <p className={styles.indisponible}>{erreur}</p>;
  if (!maillage)
    return <p className={styles.indisponible}>Lecture de l’empreinte…</p>;

  return (
    <div className={styles.scene}>
      <canvas ref={toile} className={styles.toile} />
      <p className={styles.aide}>
        Glissez pour tourner, molette pour approcher ·{" "}
        {maillage.triangles.toLocaleString("fr-FR")} triangles
      </p>
    </div>
  );
}
