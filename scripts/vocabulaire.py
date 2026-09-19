"""Écrit `docs/VOCABULAIRE.md` depuis l'ontologie : la liste que le praticien complète.

    services/api/.venv/bin/python scripts/vocabulaire.py          # écrit le fichier
    services/api/.venv/bin/python scripts/vocabulaire.py --check  # vérifie qu'il est à jour
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))

from oris_api.ontology.labels import THEMES, ValueMode  # noqa: E402

TARGET = ROOT / "docs/VOCABULAIRE.md"

MODE_HELP: dict[ValueMode, str] = {
    "hide": "le libellé suffit",
    "show": "ce qui a été dit est repris (nom de produit, mots du patient)",
    "value_only": "c'est la valeur dite qui est écrite",
    "statement": "« libellé : valeur » (hémostase : obtenue)",
}

HEADER = """# Vocabulaire d'Oris — à compléter

**Ce qu'est cette liste.** Oris n'écrit que ce qu'il sait nommer. Un élément absent de
cette liste n'est jamais deviné : le compte rendu affiche « à rédiger : élément non
reconnu », et rien n'est inventé. Compléter cette liste, c'est élargir ce qu'Oris sait
rédiger — jamais ce qu'il sait inventer.

**Comment la compléter.** Ajoutez vos termes à la fin du thème qui convient, dans le
tableau « À ajouter » : le mot tel que vous le diriez, et rien d'autre. Je m'occupe du
code et de la formulation. Un terme peut apparaître dans plusieurs thèmes si vous
l'employez dans plusieurs sens — dites-le simplement.

**Trois questions utiles pour chaque terme** :
1. Comment le dites-vous à voix haute pendant la consultation ?
2. Comment voulez-vous le lire dans le compte rendu ?
3. Y a-t-il une précision à conserver (une valeur, un grade, un nom de produit) ?

*Ce fichier est produit depuis le code (`services/api/src/oris_api/ontology/labels.py`)
par `scripts/vocabulaire.py`. Écrivez vos ajouts dans les tableaux « À ajouter » : je les
reporte ensuite dans le code, et cette liste est régénérée.*

**Hors périmètre V1** (décisions figées) : l'implantologie et l'endodontie ne sont pas
traitées par Oris. Les quelques termes présents servent à *reconnaître* le mot quand il
est prononcé, pas à rédiger l'acte.

"""

FOOTER_TEMPLATE = """
---

## Ce qui manque encore, à votre avis

Notez ici tout ce qui ne rentre dans aucun thème, ou les thèmes entiers qui manquent.

| Terme | Ce que ça veut dire | Où ça irait |
|---|---|---|
|  |  |  |
"""


def anchor(theme: str) -> str:
    """Ancre GitHub : minuscules, ponctuation retirée, espaces en tirets."""
    kept = [ch for ch in theme.lower() if ch.isalnum() or ch in " -_"]
    return re.sub(r"-+", "-", "".join(kept).strip().replace(" ", "-"))


def render() -> str:
    parts = [HEADER]
    total = sum(len(group) for group in THEMES.values())
    parts.append(f"**{total} termes** connus aujourd'hui, en {len(THEMES)} thèmes.\n\n")
    parts.append("## Sommaire\n\n")
    for theme, group in THEMES.items():
        parts.append(f"- [{theme}](#{anchor(theme)}) — {len(group)} termes\n")
    parts.append("\n---\n")
    for theme, group in THEMES.items():
        parts.append(f"\n## {theme}\n\n")
        parts.append("| Terme écrit dans le compte rendu | Précision conservée |\n|---|---|\n")
        for label in sorted(group.values(), key=lambda item: item.label.lower()):
            parts.append(f"| {label.label} | {MODE_HELP[label.value_mode]} |\n")
        parts.append("\n**À ajouter dans ce thème**\n\n")
        parts.append("| Terme (comme vous le dites) | Remarque |\n|---|---|\n|  |  |\n")
    parts.append(FOOTER_TEMPLATE)
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="échoue si le fichier a dérivé")
    args = parser.parse_args()
    content = render()
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        # Les ajouts du praticien vivent dans les tableaux « À ajouter » : seuls les
        # termes connus doivent correspondre.
        if known_terms(current) != known_terms(content):
            print("docs/VOCABULAIRE.md a dérivé : relancez scripts/vocabulaire.py", file=sys.stderr)
            return 1
        return 0
    TARGET.write_text(content, encoding="utf-8")
    print(f"{TARGET.relative_to(ROOT)} écrit ({sum(len(g) for g in THEMES.values())} termes)")
    return 0


def known_terms(markdown: str) -> list[str]:
    """Termes listés comme connus, section « À ajouter » exclue."""
    terms: list[str] = []
    collecting = False
    for line in markdown.splitlines():
        if line.startswith("| Terme écrit dans le compte rendu"):
            collecting = True
            continue
        if line.startswith("**À ajouter") or line.startswith("## "):
            collecting = False
        if collecting and line.startswith("|") and not line.startswith("|---"):
            terms.append(line.split("|")[1].strip())
    return terms


if __name__ == "__main__":
    raise SystemExit(main())
