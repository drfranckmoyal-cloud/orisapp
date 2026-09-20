#!/usr/bin/env python3
"""Génère les tokens visuels web (CSS) et iOS (Swift) depuis design/tokens.json.

Usage :
  python3 scripts/generate_tokens.py          # écrit les fichiers
  python3 scripts/generate_tokens.py --check  # échoue s'ils sont périmés
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "design" / "tokens.json"
CSS_OUT = ROOT / "apps/web/src/app/tokens.css"
SWIFT_OUT = ROOT / "apps/ios/Oris/DesignSystem/Tokens.swift"
HEADER = "Généré par scripts/generate_tokens.py depuis design/tokens.json — ne pas modifier à la main."


def kebab(name: str) -> str:
    return "".join(f"-{c.lower()}" if c.isupper() else c for c in name)


def render_css(tokens: dict) -> str:
    lines = [f"/* {HEADER} */", "", ":root {"]
    for name, token in tokens["color"].items():
        lines.append(f"  --color-{kebab(name)}: {token['$value']};")
    for name, token in tokens["spacing"].items():
        lines.append(f"  --space-{name}: {token['$value']};")
    for name, token in tokens["radius"].items():
        lines.append(f"  --radius-{name}: {token['$value']};")
    for name, token in tokens.get("font", {}).items():
        lines.append(f"  --font-{kebab(name)}: {token['$value']};")
    lines += ["}", ""]
    return "\n".join(lines)


def render_swift(tokens: dict) -> str:
    lines = [f"// {HEADER}", "", "import SwiftUI", "", "public enum OrisColor {"]
    for name, token in tokens["color"].items():
        hex_value = token["$value"].lstrip("#")
        r, g, b = (int(hex_value[i : i + 2], 16) for i in (0, 2, 4))
        lines.append(
            f"    public static let {name} = Color(red: {r / 255:.4f}, green: {g / 255:.4f}, blue: {b / 255:.4f})"
        )
    lines += ["}", "", "public enum OrisSpacing {"]
    for name, token in tokens["spacing"].items():
        lines.append(f"    public static let s{name}: CGFloat = {token['$value'].removesuffix('px')}")
    lines += ["}", "", "public enum OrisRadius {"]
    for name, token in tokens["radius"].items():
        lines.append(f"    public static let {name}: CGFloat = {token['$value'].removesuffix('px')}")
    lines += ["}", ""]
    return "\n".join(lines)


def main() -> int:
    tokens = json.loads(TOKENS.read_text())
    outputs = {CSS_OUT: render_css(tokens), SWIFT_OUT: render_swift(tokens)}
    stale = []
    for path, content in outputs.items():
        if "--check" in sys.argv:
            if not path.exists() or path.read_text() != content:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            print(f"écrit {path.relative_to(ROOT)}")
    if stale:
        print("Tokens générés périmés — lancer scripts/generate_tokens.py :\n  " + "\n  ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
