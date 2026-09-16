import { ApiStatus } from "@/components/ApiStatus";

import styles from "./page.module.css";

const NAVIGATION = ["Accueil", "Patients", "Consultations", "Modèles", "Paramètres"] as const;

export default function HomePage() {
  return (
    <div className={styles.shell}>
      <nav className={styles.sidebar} aria-label="Navigation principale">
        <p className={styles.wordmark}>Oris</p>
        <ul className={styles.nav}>
          {NAVIGATION.map((label) => (
            <li key={label}>
              {label === "Accueil" ? (
                <span className={styles.navItem} aria-current="page">
                  {label}
                </span>
              ) : (
                <span className={styles.navItem} aria-disabled="true">
                  {label}
                </span>
              )}
            </li>
          ))}
        </ul>
      </nav>

      <main className={styles.main}>
        <header>
          <p className={styles.tagline}>Écouter. Comprendre. Documenter.</p>
          <h1 className={styles.title}>Bonjour</h1>
        </header>

        <section className={styles.actions}>
          <button type="button" className={styles.primary} disabled>
            Nouvelle consultation
          </button>
          <p className={styles.hint}>La consultation arrive à l’étape suivante du développement.</p>
        </section>

        <section className={styles.card} aria-labelledby="server-heading">
          <h2 id="server-heading" className={styles.cardTitle}>
            État du service
          </h2>
          <ApiStatus />
        </section>
      </main>
    </div>
  );
}
