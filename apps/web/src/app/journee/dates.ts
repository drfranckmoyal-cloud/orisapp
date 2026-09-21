/** Petites manipulations de dates pour la colonne de gauche.
 *
 * Tout passe par des chaînes « AAAA-MM-JJ » et l'heure locale. Jamais `toISOString`,
 * qui répond à l'heure de Greenwich : après minuit, il renvoie la veille.
 */

export function aujourdhuiISO(): string {
  return enISO(new Date());
}

export function enISO(date: Date): string {
  const mois = String(date.getMonth() + 1).padStart(2, "0");
  const jour = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${mois}-${jour}`;
}

/** Midi, pas minuit : à midi aucun changement d'heure ne fait basculer le jour. */
export function depuisISO(iso: string): Date {
  return new Date(`${iso}T12:00:00`);
}

export function jourDecale(iso: string, pas: number): string {
  const date = depuisISO(iso);
  date.setDate(date.getDate() + pas);
  return enISO(date);
}

/** Le lundi de la semaine où tombe ce jour-là. */
export function lundiDe(iso: string): string {
  const date = depuisISO(iso);
  const depuisLundi = (date.getDay() + 6) % 7;
  return jourDecale(iso, -depuisLundi);
}

export function enFrancais(iso: string, options: Intl.DateTimeFormatOptions): string {
  return depuisISO(iso).toLocaleDateString("fr-FR", options);
}

/** « Aujourd'hui » et « Demain » valent mieux que « mardi » : c'est ce qu'on cherche. */
export function nomDuJour(iso: string): string {
  const today = aujourdhuiISO();
  if (iso === today) return "Aujourd’hui";
  if (iso === jourDecale(today, 1)) return "Demain";
  if (iso === jourDecale(today, -1)) return "Hier";
  return enFrancais(iso, { weekday: "long" });
}

/** « 21 – 27 sept. », ou « 28 sept. – 4 oct. » quand la semaine change de mois. */
export function libelleSemaine(debut: string, jours: number): string {
  const fin = jourDecale(debut, jours - 1);
  const memeMois = debut.slice(0, 7) === fin.slice(0, 7);
  const court: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
  const premier = memeMois ? enFrancais(debut, { day: "numeric" }) : enFrancais(debut, court);
  return `${premier} – ${enFrancais(fin, court)}`;
}

export function estWeekend(iso: string): boolean {
  const jour = depuisISO(iso).getDay();
  return jour === 0 || jour === 6;
}
