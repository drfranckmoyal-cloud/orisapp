"""Habillage des documents : identité du cabinet et couleurs de la marque.

L'identité vient d'un fichier de configuration, pas du code : le praticien la
remplit une fois. Tout y est facultatif — un champ vide ne laisse pas de ligne vide
sur la page, il disparaît.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.colors import Color, HexColor

CONFIG_PATH = Path(__file__).resolve().parents[3] / "config/cabinet.json"

# docs/DESIGN_SYSTEM.md — la marque, pas une décoration improvisée.
DEEP_BLUE = HexColor("#0F2D46")
ORIS_BLUE = HexColor("#3B82F6")
GRAPHITE = HexColor("#1F2937")
MUTED = HexColor("#6B7A8C")
RULE = HexColor("#C9D6E0")


@dataclass(frozen=True)
class Cabinet:
    """Ce qui identifie le cabinet sur un document imprimé."""

    name: str = "Cabinet"
    address: str = ""
    phone: str = ""
    email: str = ""
    legal: str = ""  # RPPS, ADELI, SIRET… ce que le praticien veut y voir
    city: str = ""
    practitioner_title: str = ""
    logo_path: str = ""
    logo: Path | None = field(default=None, compare=False)

    @classmethod
    def from_identity(cls, identity: dict[str, str], nom: str, path: Path = CONFIG_PATH) -> Cabinet:
        """Identité saisie par le praticien ; le fichier de configuration sert de repli."""
        base = cls.load(path)
        connus = {
            "name": identity.get("name") or nom or base.name,
            "address": identity.get("address", base.address),
            "phone": identity.get("phone", base.phone),
            "email": identity.get("email", base.email),
            "legal": identity.get("legal", base.legal),
            "city": identity.get("city", base.city),
            "practitioner_title": identity.get("practitioner_title", base.practitioner_title),
            "logo_path": base.logo_path,
        }
        return cls(**connus, logo=base.logo)

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> Cabinet:
        """Lit la configuration ; en son absence, un en-tête sobre sans logo."""
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        known = {
            f: raw.get(f, "")
            for f in (
                "name",
                "address",
                "phone",
                "email",
                "legal",
                "city",
                "practitioner_title",
                "logo_path",
            )
        }
        known["name"] = known["name"] or "Cabinet"
        logo = (path.parent / known["logo_path"]).resolve() if known["logo_path"] else None
        return cls(**known, logo=logo if logo and logo.is_file() else None)

    def contact_lines(self) -> list[str]:
        """Les lignes de contact effectivement renseignées."""
        return [line for line in (self.address, self.phone, self.email, self.legal) if line]


COLORS = {
    "title": DEEP_BLUE,
    "heading": DEEP_BLUE,
    "body": GRAPHITE,
    "muted": MUTED,
    "rule": RULE,
    "accent": ORIS_BLUE,
}


def color(name: str) -> Color:
    return COLORS[name]
