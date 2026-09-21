"use client";

import { useState } from "react";

import { Icone } from "@/components/Icones";
import { Bouton } from "@/components/ui";
import {
  ApiError,
  apiRequest,
  type Correspondant,
  type Envoi,
  type Rattachement,
} from "@/lib/api";
import { errorMessage, formatDateTime } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

import styles from "./consultation.module.css";

const CANAL: Record<Envoi["channel"], string> = {
  email: "par mail",
  mail: "par courrier",
  hand: "remis en main propre",
  secure_messaging: "par messagerie sécurisée",
  other: "",
};

function nomCorrespondant(fiche: Correspondant): string {
  if (fiche.kind === "organisation") return fiche.last_name;
  return [fiche.title, fiche.first_name, fiche.last_name]
    .filter(Boolean)
    .join(" ");
}

/** À qui ce document est parti. Oris n'envoie rien : il retient ce que le praticien a
 *  envoyé, pour que la liste des consultations puisse le dire. */
export function Envois({
  documentId,
  patientId,
  envois,
  onChange,
}: {
  documentId: string;
  patientId: string;
  envois: Envoi[];
  onChange: () => void;
}) {
  const [ouvert, setOuvert] = useState(false);
  const [destinataire, setDestinataire] = useState("patient");
  const [autre, setAutre] = useState("");
  const [canal, setCanal] = useState<Envoi["channel"]>("email");
  const [erreur, setErreur] = useState<string | null>(null);
  const [liens] = useApi<Rattachement[]>(
    ouvert ? `/patients/${patientId}/correspondents` : null,
  );
  const [carnet] = useApi<Correspondant[]>(ouvert ? "/correspondents" : null);

  const duPatient =
    liens.state === "ready" ? liens.data.map((l) => l.correspondent) : [];
  const autres =
    carnet.state === "ready"
      ? carnet.data.filter((c) => !duPatient.some((p) => p.id === c.id))
      : [];

  async function noter() {
    setErreur(null);
    const corps =
      destinataire === "patient"
        ? { recipient_kind: "patient", channel: canal }
        : destinataire === "autre"
          ? { recipient_kind: "other", recipient_label: autre, channel: canal }
          : {
              recipient_kind: "correspondent",
              correspondent_id: destinataire,
              channel: canal,
            };
    try {
      await apiRequest(`/documents/${documentId}/deliveries`, {
        method: "POST",
        body: corps,
      });
      setOuvert(false);
      setAutre("");
      onChange();
    } catch (caught) {
      setErreur(
        errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"),
      );
    }
  }

  async function retirer(id: string) {
    try {
      await apiRequest(`/deliveries/${id}`, { method: "DELETE" });
      onChange();
    } catch (caught) {
      setErreur(
        errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"),
      );
    }
  }

  return (
    <div className={styles.envois}>
      {envois.length === 0 && !ouvert && (
        <span className={styles.envoiRien}>Pas encore envoyé.</span>
      )}
      {envois.map((envoi) => (
        <span key={envoi.id} className={styles.envoi}>
          <Icone nom="envoi" taille={14} />
          <span>
            Envoyé à <strong>{envoi.recipient_label}</strong>{" "}
            {CANAL[envoi.channel]}
            <span className={styles.envoiDate}>
              {" "}
              · {formatDateTime(envoi.sent_at)}
            </span>
          </span>
          <button
            type="button"
            className={styles.retirer}
            title="Retirer cet envoi (noté par erreur)"
            aria-label={`Retirer l’envoi à ${envoi.recipient_label}`}
            onClick={() => void retirer(envoi.id)}
          >
            ×
          </button>
        </span>
      ))}

      {!ouvert && (
        <Bouton variante="discret" onClick={() => setOuvert(true)}>
          + Noter un envoi
        </Bouton>
      )}

      {ouvert && (
        <div className={styles.formEnvoi}>
          <label className={styles.champEnvoi}>
            Envoyé à
            <select
              className={styles.choix}
              value={destinataire}
              onChange={(event) => setDestinataire(event.target.value)}
            >
              <option value="patient">Le patient</option>
              {duPatient.length > 0 && (
                <optgroup label="Correspondants du patient">
                  {duPatient.map((c) => (
                    <option key={c.id} value={c.id}>
                      {nomCorrespondant(c)}
                    </option>
                  ))}
                </optgroup>
              )}
              {autres.length > 0 && (
                <optgroup label="Autres correspondants">
                  {autres.map((c) => (
                    <option key={c.id} value={c.id}>
                      {nomCorrespondant(c)}
                    </option>
                  ))}
                </optgroup>
              )}
              <option value="autre">Quelqu’un d’autre…</option>
            </select>
          </label>
          {destinataire === "autre" && (
            <label className={styles.champEnvoi}>
              Nom
              <input
                className={styles.choix}
                value={autre}
                maxLength={200}
                autoFocus
                placeholder="Ex. : mutuelle, laboratoire"
                onChange={(event) => setAutre(event.target.value)}
              />
            </label>
          )}
          <label className={styles.champEnvoi}>
            Comment
            <select
              className={styles.choix}
              value={canal}
              onChange={(event) =>
                setCanal(event.target.value as Envoi["channel"])
              }
            >
              <option value="email">Par mail</option>
              <option value="mail">Par courrier</option>
              <option value="hand">Remis en main propre</option>
              <option value="secure_messaging">Messagerie sécurisée</option>
            </select>
          </label>
          <div className={styles.boutonsEnvoi}>
            <Bouton
              disabled={destinataire === "autre" && !autre.trim()}
              onClick={() => void noter()}
            >
              Noter l’envoi
            </Bouton>
            <Bouton variante="secondaire" onClick={() => setOuvert(false)}>
              Annuler
            </Bouton>
          </div>
        </div>
      )}
      {erreur && <p className={styles.erreur}>{erreur}</p>}
    </div>
  );
}
