import type { Metadata } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";

import "./globals.css";

// La police de la marque, réellement chargée et auto-hébergée (planche d'identité).
const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--police",
});

export const metadata: Metadata = {
  title: "Oris",
  description: "Écouter. Comprendre. Documenter.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr" data-palette="bleu" className={inter.variable}>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
