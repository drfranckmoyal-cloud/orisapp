import Link from "next/link";

import type { Encounter } from "@/lib/api";
import { DOCUMENT_STATUS, DOCUMENT_TYPE, ENCOUNTER_STATUS, formatDateTime } from "@/lib/labels";

export function EncounterTable({ encounters }: { encounters: Encounter[] }) {
  if (encounters.length === 0) {
    return <p className="muted">Aucune consultation.</p>;
  }
  return (
    <table className="table">
      <thead>
        <tr>
          <th scope="col">Patient</th>
          <th scope="col">Date</th>
          <th scope="col">État</th>
          <th scope="col">Documents</th>
        </tr>
      </thead>
      <tbody>
        {encounters.map((encounter) => (
          <tr key={encounter.id}>
            <td>
              <Link href={`/consultations/${encounter.id}`}>
                {encounter.patient.first_name} {encounter.patient.last_name}
              </Link>
            </td>
            <td>{formatDateTime(encounter.started_at ?? encounter.created_at)}</td>
            <td>
              <span className="chip">{ENCOUNTER_STATUS[encounter.status]}</span>{" "}
              {encounter.critical_warning_count > 0 && (
                <span className="chip chip-critical">Alerte critique</span>
              )}
            </td>
            <td>
              {encounter.documents.map((doc) => (
                <div key={doc.id}>
                  {DOCUMENT_TYPE[doc.document_type]} : {DOCUMENT_STATUS[doc.status]}
                </div>
              ))}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
