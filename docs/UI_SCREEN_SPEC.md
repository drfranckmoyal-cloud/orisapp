# UI Screen Specification — Oris V1

Reference visual direction: `docs/DESIGN_SYSTEM.md` + `/assets` concept boards.

## Global navigation

### iPhone
Bottom navigation V1:
- Accueil
- Patients
- Consultations
- Paramètres

During recording/review, use modal/full-screen task flow; bottom navigation may be hidden to prevent accidental context switching.

### Desktop
Left sidebar, 220–248 px:
- Accueil
- Patients
- Consultations
- Modèles (read-only/config minimal V1)
- Paramètres

Main content max-width 1440 px. Avoid dashboard density.

---

## S01 — Home iPhone

### Purpose
Start a consultation in one action and surface drafts needing review.

### Hierarchy
1. Wordmark/logo small.
2. Greeting + practitioner name.
3. Primary full-width CTA `Nouvelle consultation`.
4. `À valider` list if non-empty.
5. `Aujourd’hui` encounter list.

### Components
- `PrimaryActionButton`
- `EncounterRow`
- `ReviewBadge`
- `EmptyState`

### States
- normal;
- no encounters;
- offline (new consultation disabled unless local capture strategy explicitly supported);
- pending processing.

---

## S02 — Patient selection

### iPhone
Search field pinned top, recent patients below, `+ Nouveau patient` secondary action.

### Desktop
Search centered in content header; results in simple table/list.

### Rule
Do not build a comprehensive patient chart. V1 only selects identity/context for encounters.

---

## S03 — Pre-consultation

### Content
- Patient identity card.
- Microphone status.
- Network status.
- Information-patient workflow status configurable.
- Primary CTA `Commencer l’écoute`.

### Acceptance
No more than one screen between patient selection and recording.

---

## S04 — Active Listening iPhone

### Layout
- Top: patient name + small connection indicator.
- Center: Oris symbol/listening animation, 120–160 pt visual area.
- Timer with tabular figures.
- Small voice-activity waveform.
- Bottom: `Pause` and `Terminer`.
- Optional collapsed `Voir transcription` link.

### Visual behavior
- Oris Blue pulse while active.
- Paused = neutral Cloud/Graphite, explicit text `En pause`.
- Reconnecting = warning icon + `Reconnexion…`.
- Audio gap = persistent critical banner until review.

### Never
- hide microphone state;
- use only color for recording state;
- flood screen with transcript.

---

## S05 — Active Listening Desktop

Centered task card, max width ~760 px.
Right optional drawer for transcript, closed by default.
Do not display unrelated patient history in V1.

---

## S06 — Processing

### Copy
`Oris prépare le dossier…`

Show deterministic stages only if real:
- Finalisation de la transcription
- Structuration clinique
- Préparation des documents

Do not fake percentages.
If processing exceeds normal threshold, allow leaving screen and show pending state on Home.

---

## S07 — Review iPhone

### Header
Patient + encounter date + `À vérifier N` badge.

### Segmented control
- `Compte rendu`
- `Plan`
- `Opératoire` only when generated

### Main document
Readable editable text; supported facts may show a subtle evidence indicator on tap/long press.

### Bottom action area
- secondary `Corriger`
- primary `Valider`

### Warning access
Persistent button/badge opens bottom sheet.

---

## S08 — Review Desktop

### Grid
- 65% left: document editor.
- 35% right: review rail.

Review rail tabs:
- À vérifier
- Données cliniques
- Historique

Evidence panel may slide over right rail.

### Sentence provenance interaction
Selecting/tapping evidence-supported sentence shows:
- fact(s);
- speaker;
- transcript excerpt;
- timestamp;
- confidence category.

Do not expose raw numeric confidence as a medical probability.

---

## S09 — Treatment Plan

### Card fields
- teeth/site;
- problem;
- action;
- status;
- sequence only if explicit;
- uncertainty note when applicable.

### Status labels FR
- Discuté
- Proposé
- Accepté
- Refusé
- Différé
- Planifié
- Réalisé

### Editing
Changing a clinical status edits the canonical plan object and makes projected text stale until regenerated.

---

## S10 — Operative Note

Header identifies procedure type.
Sections rendered only when evidence exists.
Missing configured-important information appears in a separate `À vérifier` rail, never as placeholder text in the final note.

---

## S11 — Voice correction

Bottom sheet/modal:
- microphone state;
- live command transcript;
- interpreted patch preview for high-impact changes.

Example:
`Remplacer la dent 26 par 27 dans 2 faits cliniques ?`

Actions:
- Annuler
- Appliquer

Low-impact style commands may apply directly with undo.

---

## S12 — Evidence / provenance drawer

Display:
- semantic fact;
- source role;
- timestamp;
- source excerpt;
- status: rapporté/observé/proposé/réalisé;
- certainty label.

Never claim audio exists after purge; use retained transcript evidence after audio lifecycle ends.

---

## S13 — Learning feedback

Non-intrusive toast/sheet:
- `Terme appris : G-ænial A’CHORD`
- `Préférence enregistrée : “avulsion”`

Settings page can list/revert learned preferences.
No points, streaks or gamification.

---

## Responsive component mapping

| Concept | SwiftUI | Web |
|---|---|---|
| Primary CTA | Button + custom style | button component |
| Review cards | VStack/LazyVStack | CSS grid/card |
| Segments | Picker segmented | Tabs |
| Warning sheet | .sheet | Dialog/Drawer |
| Evidence panel | .sheet/navigationDestination | side drawer |
| Timer | Text monospacedDigit | tabular-nums |
| Listening pulse | Canvas/SymbolEffect restrained | CSS/SVG restrained |

---

## Design QA checklist per screen

- Is the primary action obvious in <2 seconds?
- Is clinical state clear without relying on color?
- Are there any invented dashboard metrics?
- Is PHI accidentally sent to analytics?
- Can the user recover from network/audio failure?
- Does editing clinical content update canonical data, not only rendered text?
- Are loading states honest about actual system state?
