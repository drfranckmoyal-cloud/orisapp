# Design System — Oris V1

## Brand idea
**Écouter. Comprendre. Documenter.**

Oris should feel like a clinical instrument: calm, precise, premium and almost invisible during care.

## Logo/icon
Primary symbol: an open rounded contour with a subtle tooth silhouette + vertical waveform inside.
- tooth reference must remain implicit;
- no smile/tooth cartoon;
- strong silhouette at 24 px;
- app icon uses white/Cloud background with Oris Blue→Misty Teal mark;
- dark variant uses Deep Blue background and pale mark.

Concept PNGs live in `/assets`. They are visual references, not production vector masters.

## Color tokens
| Token | Hex | Use |
|---|---|---|
| deepBlue | #0F2D46 | headings, navigation, high-trust UI |
| orisBlue | #3B82F6 | primary action, listening state |
| mistyTeal | #7DD3C7 | secondary accent, learning/success nuance |
| cloud | #EAF1F6 | panels/background surfaces |
| graphite | #1F2937 | body text |
| white | #FFFFFF | main surfaces |
| warning | #B7791F | review-needed only |
| danger | #B42318 | destructive/error/recording failure |
| success | #067647 | validated state |

## Typography
- iOS: SF Pro / system.
- Web: Inter or system fallback.
- Numeric timer: tabular figures.

## Shape
- cards radius: 16 px web / native equivalent iOS;
- primary button radius: 14–16 px;
- app icon: platform-standard rounded square;
- avoid excessive pills except status badges.

## Spacing scale
4, 8, 12, 16, 24, 32, 48.

## Core screens

### Home
Primary CTA `Nouvelle consultation` above the fold. Today list + items to review. No analytics dashboard in V1.

### Active listening
Center-weighted icon, timer, waveform/voice activity, pause and stop. Transcript hidden by default. Network/mic status always visible.

### Review desktop
Two-column layout:
- left 65%: document;
- right 35%: warnings + clinical facts;
- evidence drawer opens from fact or sentence.

### Review iPhone
Segmented view: `Compte rendu | Plan | Opératoire` when available. `À vérifier` badge. Bottom action area: Corriger / Valider.

### Treatment plan
Vertical cards with step number only when sequence was explicit. Status chips use neutral semantics; do not over-color clinical choices.

### Learning
Quiet feedback: “Terme appris” or “Préférence enregistrée”; never gamified.

## Motion
- subtle pulse during listening;
- no decorative loaders for clinical processing;
- progress states explicit;
- reduce motion respected.

## Accessibility
- state not encoded by color alone;
- 44pt minimum touch target on iOS;
- keyboard navigation on web;
- dynamic type support;
- contrast AA minimum for functional text.
