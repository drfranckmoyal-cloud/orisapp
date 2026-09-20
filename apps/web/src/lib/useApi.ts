"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, apiRequest } from "./api";

export type Loadable<T> =
  | { state: "loading" }
  | { state: "error"; code: string }
  | { state: "ready"; data: T };

/** Charge une ressource de l'API ; `reload` la relit après une action.
 *
 * Le résultat retient **de quelle ressource** il vient. Tant que la réponse en main
 * ne concerne pas celle qu'on demande, l'écran attend : sans cela, changer de jour
 * d'agenda afficherait les rendez-vous de la veille sous la date du lendemain.
 * Un simple rechargement, lui, garde les données à l'écran — la liste ne clignote pas.
 */
export function useApi<T>(path: string | null): [Loadable<T>, () => void] {
  const [recu, setRecu] = useState<{ path: string | null; result: Loadable<T> }>({
    path,
    result: { state: "loading" },
  });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (path === null) return;
    let active = true;
    apiRequest<T>(path)
      .then((data) => active && setRecu({ path, result: { state: "ready", data } }))
      .catch((error: unknown) => {
        if (active) {
          setRecu({
            path,
            result: { state: "error", code: error instanceof ApiError ? error.code : "UNKNOWN" },
          });
        }
      });
    return () => {
      active = false;
    };
  }, [path, tick]);

  const reload = useCallback(() => setTick((value) => value + 1), []);
  const result: Loadable<T> = recu.path === path ? recu.result : { state: "loading" };
  return [result, reload];
}
