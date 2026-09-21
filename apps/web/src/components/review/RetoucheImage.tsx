"use client";

import { type PointerEvent, useEffect, useRef, useState } from "react";

import { Bouton } from "@/components/ui";

import styles from "./retouche.module.css";

type Cadre = { x: number; y: number; w: number; h: number };
const TOUT: Cadre = { x: 0, y: 0, w: 1, h: 1 };

/** Corriger une photo avant de la mettre au document : recadrer, retourner.
 *
 * Les photos intrabuccales sont prises au miroir : il faut souvent les retourner
 * (gauche-droite, haut-bas) et couper les bords. L'original n'est jamais modifié : la
 * version corrigée devient une nouvelle pièce jointe.
 */
export function RetoucheImage({
  source,
  nom,
  onValider,
  onAnnuler,
  legendeInitiale = "",
}: {
  source: string;
  nom: string;
  /** `null` : rien n'a été changé, l'image d'origine convient. */
  onValider: (image: Blob | null, legende: string) => void;
  legendeInitiale?: string;
  onAnnuler: () => void;
}) {
  const image = useRef<HTMLImageElement>(null);
  const zone = useRef<HTMLDivElement>(null);
  const [miroirH, setMiroirH] = useState(false);
  const [miroirV, setMiroirV] = useState(false);
  const [cadre, setCadre] = useState<Cadre>(TOUT);
  const [depart, setDepart] = useState<{ x: number; y: number } | null>(null);
  const [travail, setTravail] = useState(false);
  const [legende, setLegende] = useState(legendeInitiale);

  useEffect(() => {
    const echap = (event: KeyboardEvent) =>
      event.key === "Escape" && onAnnuler();
    window.addEventListener("keydown", echap);
    return () => window.removeEventListener("keydown", echap);
  }, [onAnnuler]);

  function position(event: PointerEvent<HTMLDivElement>) {
    const boite = zone.current!.getBoundingClientRect();
    return {
      x: Math.min(Math.max((event.clientX - boite.left) / boite.width, 0), 1),
      y: Math.min(Math.max((event.clientY - boite.top) / boite.height, 0), 1),
    };
  }

  function commencer(event: PointerEvent<HTMLDivElement>) {
    event.currentTarget.setPointerCapture(event.pointerId);
    const p = position(event);
    setDepart(p);
    setCadre({ x: p.x, y: p.y, w: 0, h: 0 });
  }

  function tirer(event: PointerEvent<HTMLDivElement>) {
    if (!depart) return;
    const p = position(event);
    setCadre({
      x: Math.min(depart.x, p.x),
      y: Math.min(depart.y, p.y),
      w: Math.abs(p.x - depart.x),
      h: Math.abs(p.y - depart.y),
    });
  }

  function finir() {
    setDepart(null);
    // Un simple clic, sans tracer : on garde toute l'image.
    setCadre((c) => (c.w < 0.03 || c.h < 0.03 ? TOUT : c));
  }

  const change = miroirH || miroirV || cadre.w < 0.999 || cadre.h < 0.999;

  function valider() {
    const img = image.current;
    if (!img) return;
    if (!change) {
      onValider(null, legende);
      return;
    }
    setTravail(true);
    // L'image entière, retournée comme à l'écran, puis la zone choisie découpée.
    const plein = window.document.createElement("canvas");
    plein.width = img.naturalWidth;
    plein.height = img.naturalHeight;
    const pc = plein.getContext("2d")!;
    pc.translate(miroirH ? plein.width : 0, miroirV ? plein.height : 0);
    pc.scale(miroirH ? -1 : 1, miroirV ? -1 : 1);
    pc.drawImage(img, 0, 0);
    const coupe = window.document.createElement("canvas");
    coupe.width = Math.max(1, Math.round(cadre.w * plein.width));
    coupe.height = Math.max(1, Math.round(cadre.h * plein.height));
    coupe
      .getContext("2d")!
      .drawImage(
        plein,
        Math.round(cadre.x * plein.width),
        Math.round(cadre.y * plein.height),
        coupe.width,
        coupe.height,
        0,
        0,
        coupe.width,
        coupe.height,
      );
    coupe.toBlob((blob) => onValider(blob, legende), "image/jpeg", 0.92);
  }

  return (
    <div
      className={styles.voile}
      role="dialog"
      aria-modal="true"
      aria-label="Corriger la photo"
    >
      <div className={styles.panneau}>
        <header className={styles.tete}>
          <strong>Corriger la photo</strong>
          <span>{nom}</span>
        </header>
        <p className={styles.aide}>
          Tracez un cadre sur la photo pour la recadrer. Un clic sans tracer
          garde toute l’image.
        </p>
        <div className={styles.scene}>
          <div
            ref={zone}
            className={styles.zone}
            onPointerDown={commencer}
            onPointerMove={tirer}
            onPointerUp={finir}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- image locale à corriger */}
            <img
              ref={image}
              src={source}
              alt=""
              draggable={false}
              style={{
                transform: `scale(${miroirH ? -1 : 1}, ${miroirV ? -1 : 1})`,
              }}
            />
            <div
              className={styles.cadre}
              style={{
                left: `${cadre.x * 100}%`,
                top: `${cadre.y * 100}%`,
                width: `${cadre.w * 100}%`,
                height: `${cadre.h * 100}%`,
              }}
            />
          </div>
        </div>
        <div className={styles.outils}>
          <Bouton
            variante="secondaire"
            aria-pressed={miroirH}
            onClick={() => setMiroirH((v) => !v)}
          >
            ⇆ Miroir gauche-droite
          </Bouton>
          <Bouton
            variante="secondaire"
            aria-pressed={miroirV}
            onClick={() => setMiroirV((v) => !v)}
          >
            ⇅ Miroir haut-bas
          </Bouton>
          <Bouton
            variante="discret"
            onClick={() => {
              setMiroirH(false);
              setMiroirV(false);
              setCadre(TOUT);
            }}
          >
            Tout annuler
          </Bouton>
        </div>
        <label className={styles.legende}>
          Légende (imprimée sous la photo)
          <input
            value={legende}
            maxLength={300}
            placeholder="Ex. : vue occlusale maxillaire avant traitement"
            onChange={(event) => setLegende(event.target.value)}
          />
        </label>
        <footer className={styles.pied}>
          <Bouton variante="secondaire" onClick={onAnnuler}>
            Annuler
          </Bouton>
          <Bouton disabled={travail} onClick={valider}>
            {change ? "Enregistrer la photo corrigée" : "Utiliser telle quelle"}
          </Bouton>
        </footer>
      </div>
    </div>
  );
}
