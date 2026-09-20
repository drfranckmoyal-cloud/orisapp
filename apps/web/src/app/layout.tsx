import type { Metadata } from "next";
import { Fraunces, Manrope } from "next/font/google";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";

import "./globals.css";

// L'interface parle en Manrope : nette, ouverte, lisible debout à un mètre.
const manrope = Manrope({
  subsets: ["latin"],
  display: "swap",
  variable: "--police-interface",
});

// La marque parle d'une autre voix. Fraunces ne sert qu'au nom « Oris ».
const fraunces = Fraunces({
  subsets: ["latin"],
  display: "swap",
  weight: ["600"],
  variable: "--police-nom",
});

export const metadata: Metadata = {
  title: "Oris",
  description: "Rien que ce qui a été dit.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr" className={`${manrope.variable} ${fraunces.variable}`}>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
