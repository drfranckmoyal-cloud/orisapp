"use client";

import { useState } from "react";

import {
  Bouton,
  Carte,
  Champ,
  EnTetePage,
  EtatVide,
  Pastille,
  Squelette,
} from "@/components/ui";
import {
  ApiError,
  apiRequest,
  type FrequentCorrection,
  type GlossaryTerm,
  type LearningExport,
  type LearningSuggestion,
  type Preferences,
} from "@/lib/api";
import { LEARNING_EVENT, changeEnFrancais, errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";
import { useConcepts } from "@/lib/useConcepts";

function LigneTerme({
  entree,
  basculer,
}: {
  entree: GlossaryTerm;
  basculer: (entree: GlossaryTerm) => void;
}) {
  return (
    <div className="ligne-mot">
      <span>
        <strong>{entree.canonical}</strong>
        {entree.aliases.length > 0 && (
          <span className="muted"> — entendu : {entree.aliases.join(", ")}</span>
        )}
      </span>
      <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <Pastille ton={entree.status === "active" ? "valide" : "neutre"}>
          {entree.status === "active" ? "actif" : "désactivé"}
        </Pastille>
        <Bouton variante="discret" onClick={() => basculer(entree)}>
          {entree.status === "active" ? "désactiver" : "réactiver"}
        </Bouton>
      </span>
    </div>
  );
}

/** « Oris apprend de vous » (S13, §124) : ce qui a été retenu, et comment le défaire. */
export default function ApprentissagePage() {
  const [preferences, rechargerPreferences] = useApi<Preferences>("/me/preferences");
  const [glossaire, rechargerGlossaire] = useApi<GlossaryTerm[]>("/glossary");
  const [suggestions, rechargerSuggestions] = useApi<LearningSuggestion[]>(
    "/me/learning/suggestions",
  );
  const [corrections, rechargerCorrections] = useApi<FrequentCorrection[]>(
    "/me/learning/corrections",
  );
  const motDe = useConcepts();
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [terme, setTerme] = useState("");
  const [variantes, setVariantes] = useState("");
  const [categorie, setCategorie] = useState("material");

  function toutRecharger() {
    rechargerPreferences();
    rechargerGlossaire();
    rechargerSuggestions();
    rechargerCorrections();
  }

  async function agir(action: () => Promise<unknown>, succes: string) {
    setMessage(null);
    try {
      await action();
      setMessage({ tone: "ok", text: succes });
      toutRecharger();
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "UNKNOWN";
      setMessage({ tone: "error", text: errorMessage(code) });
    }
  }

  function basculer(entree: GlossaryTerm) {
    void agir(
      () =>
        apiRequest(`/glossary/${entree.id}`, {
          method: "PATCH",
          body: { status: entree.status === "active" ? "disabled" : "active" },
        }),
      entree.status === "active" ? "Terme désactivé." : "Terme réactivé.",
    );
  }

  function adopter(suggestion: LearningSuggestion) {
    if (suggestion.kind === "preference") {
      void agir(
        () =>
          apiRequest("/me/preferences", {
            method: "PATCH",
            body: { [String(suggestion.payload.field)]: suggestion.payload.value },
          }),
        "Préférence enregistrée. Vous pouvez la défaire à tout moment.",
      );
      return;
    }
    void agir(
      () =>
        apiRequest("/glossary", {
          method: "POST",
          body: {
            canonical: suggestion.payload.canonical,
            aliases: (suggestion.payload.aliases ?? "").split("|").filter(Boolean),
            category: "material",
          },
        }),
      "Terme ajouté à votre dictionnaire.",
    );
  }

  const actuelles = preferences.state === "ready" ? preferences.data : null;
  const mots = Object.entries(actuelles?.terminology ?? {});
  const propositions = suggestions.state === "ready" ? suggestions.data : [];
  const termes = glossaire.state === "ready" ? glossaire.data : [];
  const materiaux = termes.filter((entree) => entree.category === "material");
  const autresTermes = termes.filter((entree) => entree.category !== "material");
  const frequentes = corrections.state === "ready" ? corrections.data : [];

  // « Oris a appris : ✓ … » (§124) — la lecture en clair de ce qui est actif.
  const regles: string[] = [
    ...(actuelles?.document_length === "concise"
      ? ["Vos comptes rendus sont rédigés courts."]
      : []),
    ...mots.map(([concept, mot]) => `Vous dites « ${mot} » plutôt que « ${motDe(concept)} ».`),
    ...materiaux
      .filter((entree) => entree.status === "active")
      .map((entree) => `« ${entree.canonical} » est un matériau qu'Oris reconnaît.`),
  ];

  async function exporter() {
    try {
      const donnees = await apiRequest<LearningExport>("/me/learning/export");
      const fichier = new Blob([JSON.stringify(donnees, null, 2)], {
        type: "application/json",
      });
      const lien = document.createElement("a");
      lien.href = URL.createObjectURL(fichier);
      lien.download = `oris-preferences-${donnees.exported_at.slice(0, 10)}.json`;
      lien.click();
      URL.revokeObjectURL(lien.href);
      setMessage({ tone: "ok", text: "Vos préférences ont été enregistrées sur l’ordinateur." });
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "UNKNOWN";
      setMessage({ tone: "error", text: errorMessage(code) });
    }
  }

  return (
    <div className="page">
      <EnTetePage surTitre="Personnalisation" titre="Oris apprend de vous" />

      <p className="muted" style={{ margin: 0, maxWidth: 720 }}>
        Ce qu’Oris retient change sa façon d’entendre et d’écrire — <strong>jamais</strong> le
        contenu clinique. Rien ne s’installe sans votre accord, et tout se défait ici.
      </p>

      {message && (
        <div
          className={`banner ${message.tone === "ok" ? "banner-info" : "banner-critical"}`}
          role="status"
        >
          {message.text}
        </div>
      )}

      <Carte
        titre="Ce qu’Oris a remarqué"
        action={propositions.length > 0 ? <Pastille ton="attention">{propositions.length}</Pastille> : null}
      >
        {suggestions.state === "loading" && <Squelette lignes={2} />}
        {suggestions.state === "ready" && propositions.length === 0 && (
          <EtatVide titre="Rien pour l’instant">
            Oris ne propose une règle qu’après plusieurs corrections allant dans le même
            sens.
          </EtatVide>
        )}
        {propositions.map((suggestion) => (
          <div key={suggestion.key} className="proposition">
            <span>{suggestion.message}</span>
            <Bouton onClick={() => adopter(suggestion)}>Adopter</Bouton>
          </div>
        ))}
      </Carte>

      <Carte
        titre="Oris a appris"
        action={
          <Bouton variante="discret" onClick={() => void exporter()}>
            Exporter
          </Bouton>
        }
      >
        {regles.length === 0 ? (
          <EtatVide titre="Rien encore">
            Oris écrit pour l’instant comme il le fait par défaut. Ce que vous corrigez
            souvent finira ici.
          </EtatVide>
        ) : (
          <ul className="liste-simple liste-cochee">
            {regles.map((regle) => (
              <li key={regle}>
                <span aria-hidden="true" style={{ color: "var(--valide)" }}>
                  ✓{" "}
                </span>
                {regle}
              </li>
            ))}
          </ul>
        )}
      </Carte>

      <div className="grille-reglages">
        <Carte titre="Vos préférences de rédaction">
          <label className="field">
            Longueur du compte rendu
            <select
              className="input"
              value={actuelles?.document_length ?? "standard"}
              onChange={(event) =>
                void agir(
                  () =>
                    apiRequest("/me/preferences", {
                      method: "PATCH",
                      body: { document_length: event.target.value },
                    }),
                  "Préférence enregistrée.",
                )
              }
            >
              <option value="standard">Standard</option>
              <option value="concise">Concis — sans les répétitions de titre</option>
            </select>
          </label>
          {actuelles?.document_length !== "standard" && (
            <Bouton
              variante="discret"
              onClick={() =>
                void agir(
                  () =>
                    apiRequest("/me/preferences/reset", {
                      method: "POST",
                      body: { field: "document_length" },
                    }),
                  "Longueur revenue au réglage d’Oris.",
                )
              }
            >
              revenir au réglage d’Oris
            </Bouton>
          )}

          <div>
            <p style={{ margin: "0 0 8px", fontWeight: 500 }}>Vos mots</p>
            {mots.length === 0 && (
              <EtatVide titre="Aucun mot préféré">
                Dites « appelle ça une avulsion » pendant une correction, ou ajoutez-le ici
                plus tard.
              </EtatVide>
            )}
            {mots.map(([concept, mot]) => (
              <div key={concept} className="ligne-mot">
                <span>
                  {motDe(concept)} → <strong>{mot}</strong>
                </span>
                <Bouton
                  variante="discret"
                  onClick={() => {
                    const suite = { ...(actuelles?.terminology ?? {}) };
                    delete suite[concept];
                    void agir(
                      () =>
                        apiRequest("/me/preferences", {
                          method: "PATCH",
                          body: { terminology: suite },
                        }),
                      "Mot retiré.",
                    );
                  }}
                >
                  retirer
                </Bouton>
              </div>
            ))}
          </div>

          {(actuelles?.document_length !== "standard" || mots.length > 0) && (
            <Bouton
              variante="discret"
              onClick={() =>
                void agir(
                  () => apiRequest("/me/preferences/reset", { method: "POST", body: {} }),
                  "Toutes vos préférences sont revenues aux réglages d’Oris. Votre dictionnaire est intact.",
                )
              }
            >
              tout remettre aux réglages d’Oris
            </Bouton>
          )}
        </Carte>

        <Carte titre="Votre dictionnaire">
          <p className="muted" style={{ margin: 0 }}>
            Marques, produits et termes que vous employez : Oris les entend mieux et les
            écrit correctement.
          </p>
          <form
            className="form-row"
            onSubmit={(event) => {
              event.preventDefault();
              if (!terme.trim()) return;
              void agir(
                () =>
                  apiRequest("/glossary", {
                    method: "POST",
                    body: {
                      canonical: terme.trim(),
                      aliases: variantes
                        .split(",")
                        .map((variante) => variante.trim())
                        .filter(Boolean),
                      category: categorie,
                    },
                  }),
                "Terme ajouté.",
              ).then(() => {
                setTerme("");
                setVariantes("");
              });
            }}
          >
            <label className="field">
              Terme exact
              <Champ
                value={terme}
                placeholder="G-ænial A’CHORD"
                onChange={(event) => setTerme(event.target.value)}
              />
            </label>
            <label className="field">
              Ce qu’on entend parfois
              <Champ
                value={variantes}
                placeholder="genial accord, genial a chord"
                onChange={(event) => setVariantes(event.target.value)}
              />
            </label>
            <label className="field">
              Nature
              <select
                className="input"
                value={categorie}
                onChange={(event) => setCategorie(event.target.value)}
              >
                <option value="material">Matériau ou marque</option>
                <option value="other">Autre terme</option>
              </select>
            </label>
            <Bouton type="submit" variante="secondaire">
              Ajouter
            </Bouton>
          </form>

          {glossaire.state === "loading" && <Squelette lignes={3} />}
          {glossaire.state === "ready" && termes.length === 0 && (
            <EtatVide titre="Dictionnaire vide">
              Ajoutez vos marques : ce sont elles que la machine entend le plus mal.
            </EtatVide>
          )}

          {materiaux.length > 0 && (
            <div>
              <p style={{ margin: "0 0 8px", fontWeight: 500 }}>Matériaux reconnus</p>
              {materiaux.map((entree) => (
                <LigneTerme key={entree.id} entree={entree} basculer={basculer} />
              ))}
            </div>
          )}
          {autresTermes.length > 0 && (
            <div>
              <p style={{ margin: "0 0 8px", fontWeight: 500 }}>Termes appris</p>
              {autresTermes.map((entree) => (
                <LigneTerme key={entree.id} entree={entree} basculer={basculer} />
              ))}
            </div>
          )}
        </Carte>
      </div>

      <Carte titre="Ce que vous corrigez le plus souvent">
        <p className="muted" style={{ marginTop: 0 }}>
          Ce qu’Oris fait rater. Rien n’en est déduit automatiquement : c’est à vous de
          décider si une règle mérite d’être posée.
        </p>
        {corrections.state === "loading" && <Squelette lignes={3} />}
        {corrections.state === "ready" && frequentes.length === 0 && (
          <EtatVide titre="Aucune correction enregistrée">
            Chaque correction que vous faites sur un compte rendu se retrouvera ici.
          </EtatVide>
        )}
        {frequentes.slice(0, 8).map((item) => (
          <div key={`${item.event_type}-${item.detail}`} className="ligne-mot">
            <span>
              {LEARNING_EVENT[item.event_type] ?? item.event_type}
              {item.detail && (
                <span className="muted"> — {changeEnFrancais(item.detail)}</span>
              )}
            </span>
            <Pastille>
              {item.occurrences === 1 ? "1 fois" : `${item.occurrences} fois`}
            </Pastille>
          </div>
        ))}
      </Carte>
    </div>
  );
}
