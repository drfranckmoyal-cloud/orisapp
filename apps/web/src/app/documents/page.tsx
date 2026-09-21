import { redirect } from "next/navigation";

/** L'ancienne page « Documents » est devenue « Envois » (22/09/2026). */
export default function DocumentsPage() {
  redirect("/envois");
}
