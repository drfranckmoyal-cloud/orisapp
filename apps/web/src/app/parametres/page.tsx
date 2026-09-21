"use client";

import Link from "next/link";
import { type ReactNode, useEffect, useState } from "react";

import { Icone } from "@/components/Icones";
import { SymboleVoix } from "@/components/Marque";
import {
  Bouton,
  Champ,
  EnTetePage,
  EtatVide,
  Pastille,
  Squelette,
  Zone,
} from "@/components/ui";
import { Dictation } from "@/lib/audio/dictation";
import {
  API_BASE_URL,
  ApiError,
  apiRequest,
  type BoiteEnvoi,
  type Cabinet,
  type ClientConfig,
  type EngineVersion,
} from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./parametres.module.css";

/** Paramètres, rangés comme ceux d'un Mac : ce qu'on règle souvent en haut, ce qu'on
 *  consulte rarement en bas. Chaque rubrique enregistre seule et le dit sur place. */

type Sante = {
  status: string;
  version: string;
  environment: string;
  providers: Record<string, string>;
};
type Preferences = {
  document_length: "standard" | "concise";
  terminology: Record<string, string>;
};
type Appareil = {
  id: string;
  nom: string;
  cree_le: string;
  dernier_usage: string | null;
  actif: boolean;
};
type AppareilCree = Appareil & { code: string };
type Retour = { ton: "ok" | "erreur"; texte: string } | null;

const RUBRIQUES: {
  groupe: string;
  items: { id: string; titre: string; icone: ReactNode }[];
}[] = [
  {
    groupe: "Vous",
    items: [
      {
        id: "profil",
        titre: "Mon profil",
        icone: <Icone nom="patients" taille={16} />,
      },
      {
        id: "redaction",
        titre: "Rédaction",
        icone: <Icone nom="documents" taille={16} />,
      },
      {
        id: "apprentissage",
        titre: "Dictionnaire et apprentissage",
        icone: <Icone nom="apprend" taille={16} />,
      },
    ],
  },
  {
    groupe: "Cabinet",
    items: [
      {
        id: "cabinet",
        titre: "Cabinet et en-tête",
        icone: <Icone nom="accueil" taille={16} />,
      },
      {
        id: "envoi",
        titre: "Envoi des documents",
        icone: <Icone nom="envoi" taille={16} />,
      },
      {
        id: "correspondants",
        titre: "Correspondants",
        icone: <Icone nom="correspondants" taille={16} />,
      },
      {
        id: "equipe",
        titre: "Praticiens",
        icone: <Icone nom="patients" taille={16} />,
      },
    ],
  },
  {
    groupe: "Consultation",
    items: [
      {
        id: "ecoute",
        titre: "Écoute et micro",
        icone: <Icone nom="micro" taille={16} />,
      },
    ],
  },
  {
    groupe: "Connexions",
    items: [
      {
        id: "appareils",
        titre: "Appareils connectés",
        icone: <IconeTelephone />,
      },
      {
        id: "connecteurs",
        titre: "Connecteurs",
        icone: <Icone nom="import" taille={16} />,
      },
    ],
  },
  {
    groupe: "Oris",
    items: [
      {
        id: "securite",
        titre: "Sécurité et données",
        icone: <IconeBouclier />,
      },
      {
        id: "apropos",
        titre: "À propos",
        icone: <Icone nom="parametres" taille={16} />,
      },
    ],
  },
];

const STANDARD = ["Omnipraticien", "ODF", "CMF"];
const MOTEURS: Record<string, string> = {
  mock: "simulateur interne",
  deepgram: "Deepgram Nova-3",
  azure_speech: "Azure AI Speech",
  anthropic: "Claude (Anthropic)",
};
const COMPOSANT: Record<string, string> = {
  speech_to_text: "Transcription",
  clinical_extraction: "Extraction clinique",
  document_generation: "Rédaction",
};

function IconeTelephone() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <rect x="6" y="2" width="12" height="20" rx="3" />
      <path d="M11 18h2" />
    </svg>
  );
}

function IconeBouclier() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z" />
    </svg>
  );
}

function messageErreur(error: unknown): string {
  return errorMessage(error instanceof ApiError ? error.code : "UNKNOWN");
}

function depuis(iso: string | null): string {
  if (!iso) return "jamais utilisé";
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  if (minutes < 2) return "à l’instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const heures = Math.round(minutes / 60);
  if (heures < 24) return `il y a ${heures} h`;
  return `le ${new Date(iso).toLocaleDateString("fr-FR")}`;
}

/** Une rubrique : un titre avec son icône, une phrase qui dit à quoi elle sert. */
function Rubrique({
  id,
  icone,
  titre,
  resume,
  children,
}: {
  id: string;
  icone: ReactNode;
  titre: string;
  resume: string;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      className={styles.rubrique}
      aria-labelledby={`${id}-titre`}
    >
      <header className={styles.enTete}>
        <span className={styles.tuile}>{icone}</span>
        <div>
          <h2 id={`${id}-titre`} className={styles.titre}>
            {titre}
          </h2>
          <p className={styles.resume}>{resume}</p>
        </div>
      </header>
      <div className={styles.corps}>{children}</div>
    </section>
  );
}

function RetourLigne({ retour }: { retour: Retour }) {
  if (!retour) return null;
  return (
    <p
      className={`${styles.retour} ${retour.ton === "ok" ? styles.retourOk : styles.retourErreur}`}
      role="status"
    >
      {retour.texte}
    </p>
  );
}

function Fait({ libelle, children }: { libelle: string; children: ReactNode }) {
  return (
    <div className={styles.fait}>
      <dt>{libelle}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export default function ParametresPage() {
  const [cabinet, rechargerCabinet] = useApi<Cabinet>("/me/cabinet");
  const [actif, setActif] = useState("profil");

  // La rubrique visible s'allume dans le sommaire.
  useEffect(() => {
    const observateur = new IntersectionObserver(
      (entrees) => {
        const visible = entrees
          .filter((e) => e.isIntersecting)
          .sort(
            (a, b) => a.boundingClientRect.top - b.boundingClientRect.top,
          )[0];
        if (visible) setActif(visible.target.id);
      },
      { rootMargin: "-20% 0px -65% 0px" },
    );
    for (const groupe of RUBRIQUES)
      for (const item of groupe.items) {
        const element = document.getElementById(item.id);
        if (element) observateur.observe(element);
      }
    return () => observateur.disconnect();
  }, [cabinet.state]);

  return (
    <div className="page">
      <EnTetePage surTitre="Réglages" titre="Paramètres" />
      <div className={styles.mise}>
        <nav className={styles.sommaire} aria-label="Rubriques des paramètres">
          {RUBRIQUES.map((groupe) => (
            <div key={groupe.groupe} className={styles.groupe}>
              <p className={styles.groupeTitre}>{groupe.groupe}</p>
              {groupe.items.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className={`${styles.lien} ${actif === item.id ? styles.lienActif : ""}`}
                  aria-current={actif === item.id ? "true" : undefined}
                >
                  <span className={styles.lienIcone}>{item.icone}</span>
                  {item.titre}
                </a>
              ))}
            </div>
          ))}
        </nav>

        <div className={styles.rubriques}>
          {cabinet.state === "loading" && <Squelette lignes={6} />}
          {cabinet.state === "error" && (
            <EtatVide titre={errorMessage(cabinet.code)} />
          )}
          {cabinet.state === "ready" && (
            <>
              <Profil cabinet={cabinet.data} recharger={rechargerCabinet} />
              <Redaction />
              <Apprentissage />
              <CabinetEtEnTete
                cabinet={cabinet.data}
                recharger={rechargerCabinet}
              />
              <Envoi cabinet={cabinet.data} recharger={rechargerCabinet} />
            </>
          )}
          <Specialites />
          {cabinet.state === "ready" && <Equipe cabinet={cabinet.data} />}
          <Ecoute />
          <Appareils />
          <Connecteurs />
          <Securite />
          <APropos />
        </div>
      </div>
    </div>
  );
}

/** Les champs du cabinet partent tous ensemble ; chaque rubrique n'en modifie qu'une partie. */
function corpsCabinet(cabinet: Cabinet, changes: Partial<Cabinet>) {
  const tout = { ...cabinet, ...changes };
  return {
    name: tout.name,
    address: tout.address,
    phone: tout.phone,
    email: tout.email,
    legal: tout.legal,
    city: tout.city,
    practitioner_title: tout.practitioner_title,
    qualifications: tout.qualifications,
    sending_email: tout.sending_email,
  };
}

function useEnregistrer(cabinet: Cabinet, recharger: () => void) {
  const [retour, setRetour] = useState<Retour>(null);
  const [enCours, setEnCours] = useState(false);
  async function enregistrer(changes: Partial<Cabinet>, texte: string) {
    setRetour(null);
    setEnCours(true);
    try {
      await apiRequest("/me/cabinet", {
        method: "PATCH",
        body: corpsCabinet(cabinet, changes),
      });
      setRetour({ ton: "ok", texte });
      recharger();
    } catch (error) {
      setRetour({ ton: "erreur", texte: messageErreur(error) });
    } finally {
      setEnCours(false);
    }
  }
  return { retour, enCours, enregistrer };
}

function Profil({
  cabinet,
  recharger,
}: {
  cabinet: Cabinet;
  recharger: () => void;
}) {
  const { retour, enCours, enregistrer } = useEnregistrer(cabinet, recharger);
  const initiales = cabinet.practitioner_name
    .split(" ")
    .map((mot) => mot[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return (
    <Rubrique
      id="profil"
      icone={<Icone nom="patients" taille={18} />}
      titre="Mon profil"
      resume="Votre nom, vos titres et votre numéro RPPS, tels qu’ils s’impriment sous votre signature."
    >
      <div className={styles.identite}>
        <span className={styles.vignette}>{initiales}</span>
        <div>
          <strong className={styles.nom}>
            {cabinet.practitioner_title} {cabinet.practitioner_name}
          </strong>
          <span className={styles.sousNom}>
            {cabinet.name} · profil utilisé
          </span>
        </div>
      </div>
      <form
        className={styles.formulaire}
        onSubmit={(event) => {
          event.preventDefault();
          const d = new FormData(event.currentTarget);
          void enregistrer(
            {
              practitioner_title: String(d.get("titre") ?? ""),
              qualifications: String(d.get("qualifications") ?? ""),
              legal: String(d.get("legal") ?? ""),
            },
            "Profil enregistré : vos prochains documents porteront ces titres.",
          );
        }}
      >
        <div className={styles.deux}>
          <label className="field">
            Civilité
            <select
              name="titre"
              defaultValue={cabinet.practitioner_title}
              className={styles.choix}
            >
              {["Dr", "Pr", "M.", "Mme", ""].map((t) => (
                <option key={t} value={t}>
                  {t || "—"}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Nom
            <Champ value={cabinet.practitioner_name} disabled readOnly />
          </label>
        </div>
        <label className="field">
          Titres, une ligne chacun
          <Zone
            compacte
            name="qualifications"
            rows={3}
            defaultValue={cabinet.qualifications}
            placeholder={"Chirurgien-dentiste\nExercice exclusif…"}
          />
        </label>
        <label className="field">
          RPPS et mention légale
          <Champ
            name="legal"
            defaultValue={cabinet.legal}
            placeholder="RPPS : 10000000000"
          />
        </label>
        <div className={styles.actions}>
          <Bouton type="submit" disabled={enCours}>
            {enCours ? "Enregistrement…" : "Enregistrer"}
          </Bouton>
          <RetourLigne retour={retour} />
        </div>
      </form>
    </Rubrique>
  );
}

function Redaction() {
  const [preferences, recharger] = useApi<Preferences>("/me/preferences");
  const [retour, setRetour] = useState<Retour>(null);

  async function longueur(valeur: Preferences["document_length"]) {
    setRetour(null);
    try {
      await apiRequest("/me/preferences", {
        method: "PATCH",
        body: { document_length: valeur },
      });
      setRetour({
        ton: "ok",
        texte: "Enregistré : s’applique aux prochains documents.",
      });
      recharger();
    } catch (error) {
      setRetour({ ton: "erreur", texte: messageErreur(error) });
    }
  }

  async function reinitialiser() {
    setRetour(null);
    try {
      await apiRequest("/me/preferences/reset", {
        method: "POST",
        body: { field: "terminology" },
      });
      setRetour({
        ton: "ok",
        texte: "Mots préférés effacés : Oris reprend ses mots.",
      });
      recharger();
    } catch (error) {
      setRetour({ ton: "erreur", texte: messageErreur(error) });
    }
  }

  const mots =
    preferences.state === "ready"
      ? Object.keys(preferences.data.terminology).length
      : 0;
  const actuelle =
    preferences.state === "ready" ? preferences.data.document_length : null;
  return (
    <Rubrique
      id="redaction"
      icone={<Icone nom="documents" taille={18} />}
      titre="Rédaction"
      resume="La forme de vos comptes rendus. Le fond, lui, vient toujours de ce qui a été dit."
    >
      <div className={styles.ligneReglage}>
        <div>
          <strong>Longueur des comptes rendus</strong>
          <p className={styles.aide}>
            Standard : phrases rédigées. Concise : l’essentiel, plus court.
          </p>
        </div>
        <div
          className={styles.segments}
          role="radiogroup"
          aria-label="Longueur des comptes rendus"
        >
          {(["standard", "concise"] as const).map((valeur) => (
            <button
              key={valeur}
              type="button"
              role="radio"
              aria-checked={actuelle === valeur}
              className={`${styles.segment} ${actuelle === valeur ? styles.segmentActif : ""}`}
              onClick={() => void longueur(valeur)}
            >
              {valeur === "standard" ? "Standard" : "Concise"}
            </button>
          ))}
        </div>
      </div>
      <div className={styles.ligneReglage}>
        <div>
          <strong>Mots préférés</strong>
          <p className={styles.aide}>
            {mots === 0
              ? "Aucun : Oris emploie ses propres mots."
              : `${mots} mot${mots > 1 ? "s" : ""} remplacé${mots > 1 ? "s" : ""} par les vôtres (« avulsion » plutôt qu’« extraction »…).`}
          </p>
        </div>
        <span className={styles.boutons}>
          <Link href="/apprentissage" className={styles.lienDiscret}>
            Dictionnaire et suggestions
          </Link>
          {mots > 0 && (
            <Bouton variante="discret" onClick={() => void reinitialiser()}>
              Effacer
            </Bouton>
          )}
        </span>
      </div>
      <RetourLigne retour={retour} />
    </Rubrique>
  );
}

/** Ce qu'Oris retient de vos corrections : dictionnaire, suggestions, corrections
 *  fréquentes. L'ancien onglet « Oris apprend », rangé ici (22/09/2026). */
function Apprentissage() {
  const [glossaire] = useApi<unknown[]>("/glossary");
  const [suggestions] = useApi<unknown[]>("/me/learning/suggestions");
  const [corrections] = useApi<unknown[]>("/me/learning/corrections");
  const n = (x: { state: string; data?: unknown[] }) =>
    x.state === "ready" && Array.isArray(x.data) ? x.data.length : 0;
  const mots = n(glossaire as { state: string; data?: unknown[] });
  const idees = n(suggestions as { state: string; data?: unknown[] });
  const corrige = n(corrections as { state: string; data?: unknown[] });
  return (
    <Rubrique
      id="apprentissage"
      icone={<Icone nom="apprend" taille={18} />}
      titre="Dictionnaire et apprentissage"
      resume="Ce qu’Oris retient de vos corrections pour mieux vous entendre et mieux écrire — sans jamais ajouter un fait."
    >
      <div className={styles.compteursApprentissage}>
        <span>
          <strong>{mots}</strong> mot{mots > 1 ? "s" : ""} dans votre
          dictionnaire
        </span>
        <span data-alerte={idees > 0 || undefined}>
          <strong>{idees}</strong> suggestion{idees > 1 ? "s" : ""} d’Oris
        </span>
        <span>
          <strong>{corrige}</strong> correction{corrige > 1 ? "s" : ""} retenue
          {corrige > 1 ? "s" : ""}
        </span>
      </div>
      <div className={styles.actions}>
        <Link href="/apprentissage" className={styles.lienBouton}>
          Ouvrir le dictionnaire et les suggestions
        </Link>
      </div>
    </Rubrique>
  );
}

function CabinetEtEnTete({
  cabinet,
  recharger,
}: {
  cabinet: Cabinet;
  recharger: () => void;
}) {
  const { retour, enCours, enregistrer } = useEnregistrer(cabinet, recharger);
  const titres = cabinet.qualifications.split("\n").filter(Boolean);
  return (
    <Rubrique
      id="cabinet"
      icone={<Icone nom="accueil" taille={18} />}
      titre="Cabinet et en-tête des documents"
      resume="Ce qui s’imprime en haut de chaque compte rendu et de chaque courrier."
    >
      {/* L'en-tête tel qu'il sortira : texte à gauche, logo à droite, comme sur le PDF. */}
      <div className={styles.apercu} aria-label="Aperçu de l’en-tête">
        <div>
          <p className={styles.apercuNom}>
            {cabinet.practitioner_title} {cabinet.practitioner_name}
          </p>
          {titres.map((t) => (
            <p key={t} className={styles.apercuLigne}>
              {t}
            </p>
          ))}
          <p className={styles.apercuPetit}>{cabinet.legal}</p>
          <p className={styles.apercuPetit}>
            {[cabinet.name, cabinet.address].filter(Boolean).join(" · ")}
          </p>
          <p className={styles.apercuPetit}>
            {[cabinet.email, cabinet.phone].filter(Boolean).join(" · ")}
          </p>
        </div>
        <span className={styles.apercuLogo}>logo</span>
      </div>
      <form
        className={styles.formulaire}
        onSubmit={(event) => {
          event.preventDefault();
          const d = new FormData(event.currentTarget);
          void enregistrer(
            {
              name: String(d.get("name") ?? ""),
              address: String(d.get("address") ?? ""),
              city: String(d.get("city") ?? ""),
              phone: String(d.get("phone") ?? ""),
              email: String(d.get("email") ?? ""),
            },
            "Cabinet enregistré : l’en-tête des prochains documents est à jour.",
          );
        }}
      >
        <div className={styles.deux}>
          <label className="field">
            Nom du cabinet
            <Champ name="name" defaultValue={cabinet.name} />
          </label>
          <label className="field">
            Ville (date des courriers)
            <Champ name="city" defaultValue={cabinet.city} />
          </label>
        </div>
        <label className="field">
          Adresse
          <Champ name="address" defaultValue={cabinet.address} />
        </label>
        <div className={styles.deux}>
          <label className="field">
            Téléphone
            <Champ name="phone" defaultValue={cabinet.phone} />
          </label>
          <label className="field">
            Courriel du cabinet
            <Champ name="email" type="email" defaultValue={cabinet.email} />
          </label>
        </div>
        <div className={styles.actions}>
          <Bouton type="submit" disabled={enCours}>
            {enCours ? "Enregistrement…" : "Enregistrer"}
          </Bouton>
          <RetourLigne retour={retour} />
        </div>
      </form>
      <p className={styles.aide}>
        Le logo se change pour l’instant dans le fichier de réglages du cabinet
        : demandez-le à Claude.
      </p>
    </Rubrique>
  );
}

function Envoi({
  cabinet,
  recharger,
}: {
  cabinet: Cabinet;
  recharger: () => void;
}) {
  const [boite, rechargerBoite] = useApi<BoiteEnvoi>("/me/boite-envoi");
  const { retour, enCours, enregistrer } = useEnregistrer(cabinet, () => {
    recharger();
    rechargerBoite();
  });
  return (
    <Rubrique
      id="envoi"
      icone={<Icone nom="envoi" taille={18} />}
      titre="Envoi des documents"
      resume="La boîte d’où partent vos comptes rendus et vos courriers."
    >
      {boite.state === "ready" && (
        <div className={styles.etat}>
          <Pastille ton={boite.data.configure ? "valide" : "attention"} point>
            {boite.data.configure ? "boîte branchée" : "boîte non branchée"}
          </Pastille>
          <span className={styles.aide}>
            {boite.data.configure
              ? `${boite.data.adresse} · ${boite.data.serveur}`
              : boite.data.raison === "SENDING_EMAIL_MISSING"
                ? "Renseignez l’adresse d’envoi ci-dessous."
                : "Il manque le mot de passe d’application de la messagerie, dans le fichier de réglages privé d’Oris."}
          </span>
        </div>
      )}
      <form
        className={styles.formulaire}
        onSubmit={(event) => {
          event.preventDefault();
          const d = new FormData(event.currentTarget);
          void enregistrer(
            { sending_email: String(d.get("sending_email") ?? "") },
            "Adresse d’envoi enregistrée.",
          );
        }}
      >
        <label className="field">
          Adresse d’envoi
          <Champ
            name="sending_email"
            type="email"
            defaultValue={cabinet.sending_email}
            placeholder="prenom.nom@exemple.fr"
          />
        </label>
        <div className={styles.actions}>
          <Bouton type="submit" disabled={enCours}>
            {enCours ? "Enregistrement…" : "Enregistrer"}
          </Bouton>
          <RetourLigne retour={retour} />
        </div>
      </form>
    </Rubrique>
  );
}

function Specialites() {
  const [specialites, recharger] = useApi<string[]>(
    "/correspondents/specialties",
  );
  const [retour, setRetour] = useState<Retour>(null);

  async function ajouter(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const label = String(new FormData(form).get("label") ?? "").trim();
    if (!label) return;
    try {
      await apiRequest("/correspondents/specialties", {
        method: "POST",
        body: { label },
      });
      form.reset();
      recharger();
      setRetour({ ton: "ok", texte: `« ${label} » ajoutée.` });
    } catch (error) {
      setRetour({ ton: "erreur", texte: messageErreur(error) });
    }
  }

  async function retirer(label: string) {
    try {
      await apiRequest(
        `/correspondents/specialties/${encodeURIComponent(label)}`,
        { method: "DELETE" },
      );
      recharger();
      setRetour({ ton: "ok", texte: `« ${label} » retirée.` });
    } catch (error) {
      setRetour({ ton: "erreur", texte: messageErreur(error) });
    }
  }

  return (
    <Rubrique
      id="correspondants"
      icone={<Icone nom="correspondants" taille={18} />}
      titre="Correspondants"
      resume="Les spécialités proposées dans le carnet ; chacune a sa couleur. Retirer une spécialité ne touche pas les fiches qui la portent."
    >
      {specialites.state === "loading" && <Squelette lignes={1} />}
      {specialites.state === "ready" && (
        <div className="rangee-pastilles">
          {specialites.data.map((s) => (
            <span key={s} className="jeton-specialite">
              {s}
              {!STANDARD.includes(s) && (
                <button
                  type="button"
                  aria-label={`Retirer ${s}`}
                  title={`Retirer ${s}`}
                  onClick={() => void retirer(s)}
                >
                  ×
                </button>
              )}
            </span>
          ))}
        </div>
      )}
      <form className={styles.enLigne} onSubmit={ajouter}>
        <Champ
          name="label"
          placeholder="Nouvelle spécialité : Parodontie, Implantologie…"
          required
          aria-label="Nouvelle spécialité"
        />
        <Bouton type="submit" variante="secondaire">
          Ajouter
        </Bouton>
      </form>
      <RetourLigne retour={retour} />
      <Link href="/correspondants" className={styles.lienDiscret}>
        Ouvrir le carnet de correspondants →
      </Link>
    </Rubrique>
  );
}

function Equipe({ cabinet }: { cabinet: Cabinet }) {
  return (
    <Rubrique
      id="equipe"
      icone={<Icone nom="patients" taille={18} />}
      titre="Praticiens du cabinet"
      resume="Chaque praticien garde son dictionnaire, ses préférences et ses consultations ; aucun ne voit celles d’un autre."
    >
      <div className={styles.ligneReglage}>
        <div className={styles.identite}>
          <span className={styles.vignettePetite}>
            {cabinet.practitioner_name
              .split(" ")
              .map((m) => m[0] ?? "")
              .join("")
              .slice(0, 2)}
          </span>
          <div>
            <strong>
              {cabinet.practitioner_title} {cabinet.practitioner_name}
            </strong>
            <span className={styles.sousNom}>vous</span>
          </div>
        </div>
        <Pastille ton="valide">actif</Pastille>
      </div>
      <div className={styles.ligneReglage}>
        <div>
          <strong>Inviter un praticien ou une assistante</strong>
          <p className={styles.aide}>
            Viendra avec les comptes et la connexion (feuille de route, étape
            1).
          </p>
        </div>
        <Bouton disabled variante="secondaire">
          Bientôt
        </Bouton>
      </div>
    </Rubrique>
  );
}

/** « Tester le micro » : six secondes, Oris dit ce qu'il a compris. Rien n'est gardé. */
function EssaiMicro() {
  const [etat, setEtat] = useState<"pret" | "ecoute" | "analyse">("pret");
  const [reste, setReste] = useState(6);
  const [niveau, setNiveau] = useState(0);
  const [resultat, setResultat] = useState<{
    texte: string;
    muet: boolean;
    crete: number;
  } | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  async function lancer() {
    setResultat(null);
    setErreur(null);
    const dictee = new Dictation();
    try {
      await dictee.start(undefined, setNiveau);
    } catch {
      setErreur(
        "Le micro n’a pas pu démarrer : autorisez-le dans le navigateur.",
      );
      return;
    }
    setEtat("ecoute");
    const debut = Date.now();
    await new Promise<void>((fin) => {
      const minuterie = window.setInterval(() => {
        const ecoule = (Date.now() - debut) / 1000;
        setReste(Math.max(0, Math.ceil(6 - ecoule)));
        if (ecoule >= 6) {
          window.clearInterval(minuterie);
          fin();
        }
      }, 120);
    });
    const pcm = dictee.stop();
    setNiveau(0);
    setEtat("analyse");
    try {
      const reponse = await fetch(`${API_BASE_URL}/diagnostic/micro`, {
        method: "POST",
        headers: {
          "Content-Type": "audio/pcm;rate=16000;channels=1;encoding=s16le",
          "X-Entree": "navigateur",
        },
        body: pcm as unknown as BodyInit,
      });
      if (!reponse.ok) throw new Error(String(reponse.status));
      setResultat(await reponse.json());
    } catch {
      setErreur("Le serveur Oris n’a pas pu analyser l’essai.");
    } finally {
      setEtat("pret");
    }
  }

  return (
    <div className={styles.essai}>
      <span className={styles.essaiSymbole}>
        <SymboleVoix niveau={etat === "ecoute" ? niveau : 0.35} taille={40} />
      </span>
      <div className={styles.essaiTexte}>
        <strong>Tester le micro</strong>
        {etat === "ecoute" && (
          <span className={styles.aide}>Parlez… {reste} s</span>
        )}
        {etat === "analyse" && (
          <span className={styles.aide}>Oris écoute l’enregistrement…</span>
        )}
        {etat === "pret" && !resultat && !erreur && (
          <span className={styles.aide}>
            Dites une phrase pendant 6 secondes : Oris affiche ce qu’il a
            compris. Rien n’est gardé.
          </span>
        )}
        {resultat && (
          <span className={resultat.texte ? styles.essaiOk : styles.essaiKo}>
            {resultat.muet
              ? "Aucun son capté : le micro n’a rien enregistré."
              : resultat.texte
                ? `Oris vous entend : « ${resultat.texte} »`
                : "Du son a été capté, mais aucune parole reconnue."}
          </span>
        )}
        {erreur && <span className={styles.essaiKo}>{erreur}</span>}
      </div>
      <Bouton
        variante="secondaire"
        disabled={etat !== "pret"}
        onClick={() => void lancer()}
      >
        {etat === "pret" ? "Lancer l’essai" : "Écoute…"}
      </Bouton>
    </div>
  );
}

function Ecoute() {
  const [config] = useApi<ClientConfig>("/config/client");
  return (
    <Rubrique
      id="ecoute"
      icone={<Icone nom="micro" taille={18} />}
      titre="Écoute et micro"
      resume="Comment Oris écoute une consultation, et un essai pour vérifier qu’il vous entend."
    >
      <EssaiMicro />
      <dl className={styles.faits}>
        <Fait libelle="Durée maximale d’une écoute">
          {config.state === "ready"
            ? `${config.data.max_session_minutes} minutes`
            : "—"}
        </Fait>
        <Fait libelle="Information du patient">
          {config.state === "ready" &&
          config.data.patient_information_mode === "confirm"
            ? "confirmée avant chaque écoute"
            : "non demandée"}
        </Fait>
        <Fait libelle="Son enregistré">
          supprimé dès que la transcription a abouti
        </Fait>
      </dl>
    </Rubrique>
  );
}

function Appareils() {
  const [appareils, recharger] = useApi<Appareil[]>("/me/appareils");
  const [nouveau, setNouveau] = useState<AppareilCree | null>(null);
  const [retour, setRetour] = useState<Retour>(null);
  const [copie, setCopie] = useState(false);

  async function autoriser(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const nom = String(new FormData(form).get("nom") ?? "").trim();
    if (!nom) return;
    setRetour(null);
    try {
      setNouveau(
        await apiRequest<AppareilCree>("/me/appareils", {
          method: "POST",
          body: { nom },
        }),
      );
      setCopie(false);
      form.reset();
      recharger();
    } catch (error) {
      setRetour({ ton: "erreur", texte: messageErreur(error) });
    }
  }

  async function deconnecter(appareil: Appareil) {
    if (
      !window.confirm(
        `Déconnecter « ${appareil.nom} » ? Il ne pourra plus rien lire tant qu’un nouveau code ne lui est pas donné.`,
      )
    )
      return;
    try {
      await apiRequest(`/me/appareils/${appareil.id}`, { method: "DELETE" });
      setRetour({ ton: "ok", texte: `« ${appareil.nom} » est déconnecté.` });
      recharger();
    } catch (error) {
      setRetour({ ton: "erreur", texte: messageErreur(error) });
    }
  }

  const actifs =
    appareils.state === "ready" ? appareils.data.filter((a) => a.actif) : [];
  const anciens =
    appareils.state === "ready" ? appareils.data.filter((a) => !a.actif) : [];
  return (
    <Rubrique
      id="appareils"
      icone={<IconeTelephone />}
      titre="Appareils connectés"
      resume="Les appareils qui ont accès à vos dossiers, comme votre iPhone. Un appareil perdu se déconnecte ici, d’un geste."
    >
      {appareils.state === "loading" && <Squelette lignes={2} />}
      {appareils.state === "ready" && actifs.length === 0 && (
        <p className={styles.aide}>
          Aucun appareil connecté en dehors de ce Mac.
        </p>
      )}
      {actifs.map((a) => (
        <div key={a.id} className={styles.ligneReglage}>
          <div className={styles.identite}>
            <span className={styles.tuilePetite}>
              <IconeTelephone />
            </span>
            <div>
              <strong>{a.nom}</strong>
              <span className={styles.sousNom}>
                utilisé {depuis(a.dernier_usage)} · autorisé le{" "}
                {new Date(a.cree_le).toLocaleDateString("fr-FR")}
              </span>
            </div>
          </div>
          <Bouton variante="discret" onClick={() => void deconnecter(a)}>
            Déconnecter
          </Bouton>
        </div>
      ))}
      {nouveau && (
        <div className={styles.code} role="status">
          <strong>
            Code d’accès de « {nouveau.nom} » — affiché une seule fois
          </strong>
          <code>{nouveau.code}</code>
          <span className={styles.boutons}>
            <Bouton
              variante="secondaire"
              onClick={() => {
                void navigator.clipboard
                  ?.writeText(nouveau.code)
                  .then(() => setCopie(true));
              }}
            >
              {copie ? "Copié" : "Copier"}
            </Bouton>
            <Bouton variante="discret" onClick={() => setNouveau(null)}>
              J’ai terminé
            </Bouton>
          </span>
          <span className={styles.aide}>
            Collez-le dans l’app Oris de l’appareil (Paramètres › Jeton
            d’accès), puis touchez « J’ai terminé ».
          </span>
        </div>
      )}
      <form className={styles.enLigne} onSubmit={autoriser}>
        <Champ
          name="nom"
          placeholder="Nom de l’appareil : iPad du cabinet…"
          required
          aria-label="Nom du nouvel appareil"
        />
        <Bouton type="submit" variante="secondaire">
          Autoriser un appareil
        </Bouton>
      </form>
      <RetourLigne retour={retour} />
      {anciens.length > 0 && (
        <p className={styles.aide}>
          {anciens.length} ancien{anciens.length > 1 ? "s" : ""} appareil
          {anciens.length > 1 ? "s" : ""} déconnecté
          {anciens.length > 1 ? "s" : ""}.
        </p>
      )}
    </Rubrique>
  );
}

function Connecteurs() {
  const [config] = useApi<ClientConfig>("/config/client");
  const smilecloud =
    config.state === "ready" && config.data.smilecloud_connected;
  const connecteurs = [
    {
      nom: "SmileCloud",
      detail:
        "Photos, scans et documents du patient déjà déposés dans SmileCloud, rattachés à sa fiche sans réimport.",
      connecte: smilecloud,
    },
    {
      nom: "Doctolib",
      detail:
        "Les rendez-vous du jour, lus par l’extension de Dental Lens. Voir « Votre journée ».",
      connecte: false,
    },
  ];
  return (
    <Rubrique
      id="connecteurs"
      icone={<Icone nom="import" taille={18} />}
      titre="Connecteurs"
      resume="Ce qu’Oris va chercher ailleurs plutôt que de vous le faire ressaisir."
    >
      {connecteurs.map((c) => (
        <div key={c.nom} className={styles.ligneReglage}>
          <div>
            <strong>{c.nom}</strong>
            <p className={styles.aide}>{c.detail}</p>
          </div>
          <Pastille ton={c.connecte ? "valide" : "attention"} point>
            {c.connecte ? "connecté" : "non connecté"}
          </Pastille>
        </div>
      ))}
    </Rubrique>
  );
}

function Securite() {
  return (
    <Rubrique
      id="securite"
      icone={<IconeBouclier />}
      titre="Sécurité et données"
      resume="Où en est la protection des dossiers, et ce que vous pouvez emporter."
    >
      <dl className={styles.faits}>
        <Fait libelle="Accès depuis un autre appareil">
          <Pastille ton="valide">code d’accès personnel</Pastille>
        </Fait>
        <Fait libelle="Verrouillage de l’iPhone">Face ID à l’ouverture</Fait>
        <Fait libelle="Deuxième facteur de connexion">
          <Pastille ton="attention">à venir</Pastille> avec l’hébergeur agréé
        </Fait>
        <Fait libelle="Hébergement agréé santé (HDS)">
          <Pastille ton="alerte">pas encore</Pastille> aucun patient réel hors
          de ce Mac
        </Fait>
        <Fait libelle="Journal">
          chaque action est tracée, sans contenu clinique
        </Fait>
      </dl>
      <div className={styles.ligneReglage}>
        <div>
          <strong>Exporter ce qu’Oris a appris de vous</strong>
          <p className={styles.aide}>
            Dictionnaire, préférences et corrections, dans un fichier.
          </p>
        </div>
        <a
          className={styles.lienDiscret}
          href={`${API_BASE_URL}/me/learning/export`}
          download
        >
          Télécharger
        </a>
      </div>
    </Rubrique>
  );
}

function APropos() {
  const [sante] = useApi<Sante>("/health");
  const [versions] = useApi<EngineVersion[]>("/system/versions");
  const moteurs = sante.state === "ready" ? sante.data.providers : {};
  return (
    <Rubrique
      id="apropos"
      icone={<Icone nom="parametres" taille={18} />}
      titre="À propos"
      resume="La version d’Oris et les moteurs qui travaillent pour vous."
    >
      <dl className={styles.faits}>
        <Fait libelle="Oris">
          {sante.state === "ready" ? `version ${sante.data.version}` : "—"}
        </Fait>
        <Fait libelle="Serveur">
          {sante.state === "ready" ? (
            <Pastille ton="valide" point>
              en marche
            </Pastille>
          ) : (
            <Pastille ton="alerte" point>
              injoignable
            </Pastille>
          )}
        </Fait>
        <Fait libelle="Transcription">
          {MOTEURS[moteurs.speech_to_text ?? ""] ??
            moteurs.speech_to_text ??
            "—"}
        </Fait>
        <Fait libelle="Extraction clinique">
          {MOTEURS[moteurs.clinical_extraction ?? ""] ??
            moteurs.clinical_extraction ??
            "—"}
        </Fait>
        <Fait libelle="Rédaction">
          {MOTEURS[moteurs.document_generation ?? ""] ??
            moteurs.document_generation ??
            "—"}
          , contrôlée par Oris
        </Fait>
      </dl>
      {versions.state === "ready" && versions.data.length > 0 && (
        <details className={styles.details}>
          <summary>Versions réellement utilisées sur vos consultations</summary>
          <ul className="liste-simple">
            {versions.data.map((v) => (
              <li key={`${v.component}-${v.model_id}`}>
                <strong>{COMPOSANT[v.component] ?? v.component}</strong> —{" "}
                {v.provider} · {v.model_id}
                {v.prompt_version && <> · consigne {v.prompt_version}</>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </Rubrique>
  );
}
