"use client";

import { useState } from "react";

import {
  ApiError,
  apiRequest,
  type GlossaryTerm,
  type LearningSuggestion,
  type Preferences,
} from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

/** « Oris apprend de vous » (spec §124) : ce qui a été retenu, et comment le défaire. */
export default function LearningPage() {
  const [preferences, reloadPreferences] = useApi<Preferences>("/me/preferences");
  const [glossary, reloadGlossary] = useApi<GlossaryTerm[]>("/glossary");
  const [suggestions, reloadSuggestions] = useApi<LearningSuggestion[]>(
    "/me/learning/suggestions",
  );
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [term, setTerm] = useState("");
  const [aliases, setAliases] = useState("");

  function reloadAll() {
    reloadPreferences();
    reloadGlossary();
    reloadSuggestions();
  }

  async function act(run: () => Promise<unknown>, success: string) {
    setMessage(null);
    try {
      await run();
      setMessage({ tone: "ok", text: success });
      reloadAll();
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "UNKNOWN";
      setMessage({ tone: "error", text: errorMessage(code) });
    }
  }

  function acceptSuggestion(suggestion: LearningSuggestion) {
    if (suggestion.kind === "preference") {
      void act(
        () =>
          apiRequest("/me/preferences", {
            method: "PATCH",
            body: { [String(suggestion.payload.field)]: suggestion.payload.value },
          }),
        "Préférence enregistrée. Vous pouvez la défaire à tout moment.",
      );
      return;
    }
    void act(
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

  const current = preferences.state === "ready" ? preferences.data : null;
  const terminology = Object.entries(current?.terminology ?? {});

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="subtitle">Personnalisation</p>
          <h1>Oris apprend de vous</h1>
        </div>
      </header>

      <p className="muted">
        Ce qu’Oris retient change la façon d’écrire et d’entendre, jamais le contenu
        clinique. Tout se défait ici.
      </p>

      {message && (
        <div
          className={`banner ${message.tone === "ok" ? "banner-info" : "banner-critical"}`}
          role="status"
        >
          {message.text}
        </div>
      )}

      <section className="card" aria-labelledby="suggestions-heading">
        <h2 id="suggestions-heading">Ce qu’Oris a remarqué</h2>
        {suggestions.state === "ready" && suggestions.data.length === 0 && (
          <p className="muted">
            Rien pour l’instant. Oris ne propose une règle qu’après plusieurs corrections
            allant dans le même sens.
          </p>
        )}
        {suggestions.state === "ready" &&
          suggestions.data.map((suggestion) => (
            <div key={suggestion.key} className="banner banner-review">
              {suggestion.message}
              <div>
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => acceptSuggestion(suggestion)}
                >
                  Adopter
                </button>
              </div>
            </div>
          ))}
      </section>

      <section className="card" aria-labelledby="preferences-heading">
        <h2 id="preferences-heading">Préférences de rédaction</h2>
        <label className="field" style={{ maxWidth: 360 }}>
          Longueur du compte rendu
          <select
            className="input"
            value={current?.document_length ?? "standard"}
            onChange={(event) =>
              void act(
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

        <h3>Vos mots</h3>
        {terminology.length === 0 && (
          <p className="muted">
            Aucun mot préféré. Oris utilise son vocabulaire par défaut.
          </p>
        )}
        <ul>
          {terminology.map(([concept, word]) => (
            <li key={concept}>
              {concept} → <strong>{word}</strong>{" "}
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  const next = { ...(current?.terminology ?? {}) };
                  delete next[concept];
                  void act(
                    () =>
                      apiRequest("/me/preferences", {
                        method: "PATCH",
                        body: { terminology: next },
                      }),
                    "Mot retiré.",
                  );
                }}
              >
                retirer
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="card" aria-labelledby="glossary-heading">
        <h2 id="glossary-heading">Votre dictionnaire</h2>
        <p className="muted">
          Marques, produits et termes que vous employez : Oris les entend mieux et les
          écrit correctement.
        </p>
        <form
          className="form-row"
          onSubmit={(event) => {
            event.preventDefault();
            if (!term.trim()) return;
            void act(
              () =>
                apiRequest("/glossary", {
                  method: "POST",
                  body: {
                    canonical: term.trim(),
                    aliases: aliases
                      .split(",")
                      .map((alias) => alias.trim())
                      .filter(Boolean),
                    category: "material",
                  },
                }),
              "Terme ajouté.",
            ).then(() => {
              setTerm("");
              setAliases("");
            });
          }}
        >
          <label className="field">
            Terme exact
            <input
              className="input"
              value={term}
              placeholder="G-ænial A’CHORD"
              onChange={(event) => setTerm(event.target.value)}
            />
          </label>
          <label className="field">
            Ce qu’on entend parfois (séparé par des virgules)
            <input
              className="input"
              value={aliases}
              placeholder="genial accord, genial a chord"
              onChange={(event) => setAliases(event.target.value)}
            />
          </label>
          <button type="submit" className="button button-primary">
            Ajouter
          </button>
        </form>

        {glossary.state === "ready" && glossary.data.length === 0 && (
          <p className="muted">Votre dictionnaire est vide.</p>
        )}
        {glossary.state === "ready" && glossary.data.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>Terme</th>
                <th>Variantes entendues</th>
                <th>État</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {glossary.data.map((entry) => (
                <tr key={entry.id}>
                  <td>{entry.canonical}</td>
                  <td className="muted">{entry.aliases.join(", ") || "—"}</td>
                  <td>
                    <span className={`chip ${entry.status === "active" ? "chip-success" : ""}`}>
                      {entry.status === "active" ? "actif" : "désactivé"}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="link-button"
                      onClick={() =>
                        void act(
                          () =>
                            apiRequest(`/glossary/${entry.id}`, {
                              method: "PATCH",
                              body: {
                                status: entry.status === "active" ? "disabled" : "active",
                              },
                            }),
                          entry.status === "active" ? "Terme désactivé." : "Terme réactivé.",
                        )
                      }
                    >
                      {entry.status === "active" ? "désactiver" : "réactiver"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
