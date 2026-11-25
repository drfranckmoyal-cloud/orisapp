/** Prévenir l'extension Chrome (Dental Lens) qu'un dépôt l'attend.
 *
 * Le serveur ne peut pas réveiller l'extension : c'est elle qui vient demander, à
 * intervalles. Quand le praticien clique depuis le site ouvert dans le même Chrome, la page
 * la prévient directement et le dépôt part dans la seconde (Franck, 25/11/2026 : « pourquoi
 * pas immédiatement au clic ? »). Un simple message à la fenêtre, que le script de
 * l'extension sur ce site relaie : aucun identifiant, aucune donnée de patient — seulement
 * « va voir la file ». Sans extension sur ce navigateur, le message se perd sans bruit et
 * le passage régulier prend le relais.
 */
export type CibleDepot = "smilecloud" | "veasy";

export function prevenirExtension(
  cible: CibleDepot,
  type: "oris:depot" | "oris:relier" = "oris:depot",
): void {
  if (typeof window === "undefined") return;
  // « oris:relier » (26/11/2026) : un patient pas encore relié à Veasy est ouvert ; que
  // l'extension cherche son dossier tout de suite. Toujours sans aucune donnée.
  window.postMessage(
    type === "oris:relier"
      ? { source: "oris", type }
      : { source: "oris", type, cible },
    window.location.origin,
  );
}
