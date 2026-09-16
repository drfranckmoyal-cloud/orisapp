"use client";

import { useEffect, useState } from "react";

import { fetchHealth, type ApiHealth } from "@/lib/api";

import styles from "./ApiStatus.module.css";

type Status = { state: "checking" } | ApiHealth;

export function ApiStatus({ load = fetchHealth }: { load?: () => Promise<ApiHealth> }) {
  const [status, setStatus] = useState<Status>({ state: "checking" });

  useEffect(() => {
    let active = true;
    load().then((result) => {
      if (active) setStatus(result);
    });
    return () => {
      active = false;
    };
  }, [load]);

  // L'état est toujours écrit en toutes lettres, jamais porté par la seule couleur.
  if (status.state === "checking") {
    return (
      <p className={styles.status} role="status">
        <span className={styles.dot} data-state="checking" aria-hidden="true" />
        Vérification du serveur…
      </p>
    );
  }

  if (status.state === "unreachable") {
    return (
      <p className={styles.status} role="status">
        <span className={styles.dot} data-state="unreachable" aria-hidden="true" />
        Serveur Oris injoignable
      </p>
    );
  }

  const { health } = status;
  const allMock = Object.values(health.providers).every((name) => name === "mock");
  return (
    <div role="status">
      <p className={styles.status}>
        <span className={styles.dot} data-state="reachable" aria-hidden="true" />
        Serveur Oris connecté · version {health.version}
      </p>
      {allMock && (
        <p className={styles.detail}>Mode démonstration : aucun moteur d’IA réel n’est branché.</p>
      )}
    </div>
  );
}
