"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, apiRequest } from "./api";

export type Loadable<T> =
  | { state: "loading" }
  | { state: "error"; code: string }
  | { state: "ready"; data: T };

/** Charge une ressource de l'API ; `reload` la relit après une action. */
export function useApi<T>(path: string | null): [Loadable<T>, () => void] {
  const [result, setResult] = useState<Loadable<T>>({ state: "loading" });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (path === null) return;
    let active = true;
    apiRequest<T>(path)
      .then((data) => active && setResult({ state: "ready", data }))
      .catch((error: unknown) => {
        if (active) {
          setResult({ state: "error", code: error instanceof ApiError ? error.code : "UNKNOWN" });
        }
      });
    return () => {
      active = false;
    };
  }, [path, tick]);

  const reload = useCallback(() => setTick((value) => value + 1), []);
  return [result, reload];
}
