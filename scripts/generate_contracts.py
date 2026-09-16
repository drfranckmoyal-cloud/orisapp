#!/usr/bin/env python3
"""Génère les types Python, TypeScript et Swift depuis schemas/*.schema.json.

Les JSON Schemas sont la seule définition des objets cliniques (CLAUDE.md,
spec §99). Ce script en dérive des types pour chaque client ; les fichiers
produits sont commités et ne s'éditent jamais à la main.

Usage :
  python3 scripts/generate_contracts.py          # écrit les fichiers
  python3 scripts/generate_contracts.py --check  # échoue s'ils sont périmés

Bibliothèque standard uniquement : doit tourner partout, y compris en CI.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schemas"
SCHEMA_FILES = (
    "transcript_segment.schema.json",
    "clinical_fact.schema.json",
    "treatment_plan.schema.json",
    "procedure.schema.json",
    "clinical_encounter.schema.json",
    "document.schema.json",
    "learning_event.schema.json",
    "practitioner_learning_profile.schema.json",
    "evaluation_run.schema.json",
)
OUTPUTS = {
    "python": ROOT / "services/api/src/oris_api/contracts/generated.py",
    "typescript": ROOT / "apps/web/src/contracts/generated.ts",
    "swift": ROOT / "apps/ios/Oris/Contracts/Generated.swift",
}
# Noms des objets définis en ligne dans les schémas (propriété -> type).
INLINE_OBJECT_NAMES = {
    ("ClinicalEncounter", "warnings"): "EncounterWarning",
    ("TreatmentPlan", "items"): "TreatmentPlanItem",
    ("PractitionerLearningProfile", "speech_aliases"): "SpeechAlias",
}
HEADER = "Généré par scripts/generate_contracts.py depuis schemas/ — ne pas modifier à la main."


# --- Représentation intermédiaire -------------------------------------------


@dataclass(frozen=True)
class Prim:
    name: str  # string | integer | number | boolean


@dataclass(frozen=True)
class AnyValue:
    pass


@dataclass(frozen=True)
class Ref:
    name: str


@dataclass(frozen=True)
class ArrayOf:
    item: TypeIR


@dataclass(frozen=True)
class MapOf:
    value: TypeIR


@dataclass(frozen=True)
class Nullable:
    inner: TypeIR


TypeIR = Prim | AnyValue | Ref | ArrayOf | MapOf | Nullable


@dataclass
class Constraints:
    pattern: str | None = None
    min_length: int | None = None
    minimum: float | None = None
    maximum: float | None = None


@dataclass
class Field:
    name: str
    type: TypeIR
    required: bool
    constraints: Constraints = field(default_factory=Constraints)
    item_constraints: Constraints = field(default_factory=Constraints)


@dataclass
class ObjectDef:
    name: str
    fields: list[Field]


@dataclass
class EnumDef:
    name: str
    values: list[str]


@dataclass
class Registry:
    objects: dict[str, ObjectDef] = field(default_factory=dict)
    enums: dict[str, EnumDef] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)  # dépendances d'abord


def pascal(snake: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in snake.split("_"))


def camel(snake: str) -> str:
    p = pascal(snake)
    return p[:1].lower() + p[1:]


def ref_title(ref: str) -> str:
    return json.loads((SCHEMA_DIR / ref).read_text())["title"]


def constraints_of(schema: dict) -> Constraints:
    return Constraints(
        pattern=schema.get("pattern"),
        min_length=schema.get("minLength"),
        minimum=schema.get("minimum"),
        maximum=schema.get("maximum"),
    )


def resolve(schema: dict, owner: str, prop: str, reg: Registry) -> TypeIR:
    if "$ref" in schema:
        return Ref(ref_title(schema["$ref"]))
    if "anyOf" in schema:
        options = [o for o in schema["anyOf"] if o.get("type") != "null"]
        if len(options) != 1 or len(schema["anyOf"]) != 2:
            raise ValueError(f"anyOf non géré : {owner}.{prop}")
        return Nullable(resolve(options[0], owner, prop, reg))
    kind = schema.get("type")
    if kind is None:
        return AnyValue()
    if isinstance(kind, list):
        others = [k for k in kind if k != "null"]
        if len(others) != 1:
            raise ValueError(f"type multiple non géré : {owner}.{prop}")
        return Nullable(resolve({**schema, "type": others[0]}, owner, prop, reg))
    if "enum" in schema:
        name = owner + pascal(prop)
        reg.enums[name] = EnumDef(name, list(schema["enum"]))
        return Ref(name)
    if kind == "array":
        return ArrayOf(resolve(schema.get("items", {}), owner, prop, reg))
    if kind == "object":
        if "properties" in schema:
            name = INLINE_OBJECT_NAMES.get((owner, prop))
            if name is None:
                raise ValueError(f"objet en ligne sans nom : {owner}.{prop}")
            build_object(name, schema, reg)
            return Ref(name)
        extra = schema.get("additionalProperties")
        return MapOf(resolve(extra, owner, prop, reg) if isinstance(extra, dict) else AnyValue())
    return Prim(kind)


def build_object(name: str, schema: dict, reg: Registry) -> None:
    if name in reg.objects:
        return
    required = set(schema.get("required", []))
    fields = []
    for prop, prop_schema in schema["properties"].items():
        items = prop_schema.get("items", {}) if prop_schema.get("type") == "array" else {}
        fields.append(
            Field(
                name=prop,
                type=resolve(prop_schema, name, prop, reg),
                required=prop in required,
                constraints=constraints_of(prop_schema),
                item_constraints=constraints_of(items),
            )
        )
    reg.objects[name] = ObjectDef(name, fields)
    reg.order.append(name)


def load_registry() -> Registry:
    reg = Registry()
    for filename in SCHEMA_FILES:
        schema = json.loads((SCHEMA_DIR / filename).read_text())
        build_object(schema["title"], schema, reg)
    return reg


# --- Python (Pydantic v2) ----------------------------------------------------


def py_constraints(c: Constraints) -> str:
    args = []
    if c.min_length is not None:
        args.append(f"min_length={c.min_length}")
    if c.pattern is not None:
        args.append(f'pattern=r"{c.pattern}"')
    if c.minimum is not None:
        args.append(f"ge={c.minimum}")
    if c.maximum is not None:
        args.append(f"le={c.maximum}")
    return ", ".join(args)


def py_type(t: TypeIR, c: Constraints | None = None, item_c: Constraints | None = None) -> str:
    match t:
        case Prim(name):
            base = {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}[name]
            args = py_constraints(c) if c else ""
            return f"Annotated[{base}, Field({args})]" if args else base
        case AnyValue():
            return "Any"
        case Ref(name):
            return name
        case ArrayOf(item):
            return f"list[{py_type(item, item_c)}]"
        case MapOf(value):
            return f"dict[str, {py_type(value)}]"
        case Nullable(inner):
            return f"{py_type(inner, c)} | None"
    raise TypeError(t)


def render_python(reg: Registry) -> str:
    out = [
        f'"""{HEADER}"""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Annotated, Any, Literal",
        "",
        "from pydantic import BaseModel, ConfigDict, Field",
        "",
    ]
    for enum in reg.enums.values():
        values = ", ".join(f'"{v}"' for v in enum.values)
        out.append(f"{enum.name} = Literal[{values}]")
    for name in reg.order:
        obj = reg.objects[name]
        out += ["", "", f"class {name}(BaseModel):", '    model_config = ConfigDict(extra="forbid")', ""]
        for f in obj.fields:
            annotation = py_type(f.type, f.constraints, f.item_constraints)
            if f.required:
                out.append(f"    {f.name}: {annotation}")
            else:
                optional = annotation if annotation.endswith("| None") else f"{annotation} | None"
                out.append(f"    {f.name}: {optional} = None")
    out.append("")
    return "\n".join(out)


# --- TypeScript ----------------------------------------------------------------


def ts_type(t: TypeIR) -> str:
    match t:
        case Prim(name):
            return {"string": "string", "integer": "number", "number": "number", "boolean": "boolean"}[name]
        case AnyValue():
            return "unknown"
        case Ref(name):
            return name
        case ArrayOf(item):
            inner = ts_type(item)
            return f"({inner})[]" if "|" in inner else f"{inner}[]"
        case MapOf(value):
            return f"Record<string, {ts_type(value)}>"
        case Nullable(inner):
            return f"{ts_type(inner)} | null"
    raise TypeError(t)


def constant_name(pascal_name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", pascal_name).upper() + "_VALUES"


def render_typescript(reg: Registry) -> str:
    out = [f"// {HEADER}", ""]
    for enum in reg.enums.values():
        const = constant_name(enum.name)
        out.append(f"export const {const} = [")
        out += [f'  "{v}",' for v in enum.values]
        out.append("] as const;")
        out.append(f"export type {enum.name} = (typeof {const})[number];")
        out.append("")
    for name in reg.order:
        out.append(f"export interface {name} {{")
        for f in reg.objects[name].fields:
            out.append(f"  {f.name}{'' if f.required else '?'}: {ts_type(f.type)};")
        out.append("}")
        out.append("")
    return "\n".join(out)


# --- Swift ---------------------------------------------------------------------

SWIFT_RESERVED = {
    "any", "as", "associatedtype", "break", "case", "catch", "class", "continue",
    "default", "defer", "deinit", "do", "else", "enum", "extension", "fallthrough",
    "false", "for", "func", "guard", "if", "import", "in", "init", "inout",
    "internal", "is", "let", "nil", "operator", "private", "protocol", "public",
    "repeat", "return", "self", "Self", "some", "static", "struct", "subscript",
    "super", "switch", "throw", "throws", "true", "try", "typealias", "var",
    "where", "while",
}  # fmt: skip

SWIFT_JSON_VALUE = """\
/// Valeur JSON arbitraire (propriétés sans type fixe dans les schémas).
public enum JSONValue: Codable, Equatable, Sendable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else {
            self = .object(try container.decode([String: JSONValue].self))
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value): try container.encode(value)
        case .number(let value): try container.encode(value)
        case .bool(let value): try container.encode(value)
        case .object(let value): try container.encode(value)
        case .array(let value): try container.encode(value)
        case .null: try container.encodeNil()
        }
    }
}
"""


def swift_ident(name: str) -> str:
    return f"`{name}`" if name in SWIFT_RESERVED else name


def swift_type(t: TypeIR) -> str:
    match t:
        case Prim(name):
            return {"string": "String", "integer": "Int", "number": "Double", "boolean": "Bool"}[name]
        case AnyValue():
            return "JSONValue"
        case Ref(name):
            return name
        case ArrayOf(item):
            return f"[{swift_type(item)}]"
        case MapOf(value):
            return f"[String: {swift_type(value)}]"
        case Nullable(inner):
            return f"{swift_type(inner)}?"
    raise TypeError(t)


def render_swift(reg: Registry) -> str:
    out = [f"// {HEADER}", "", "import Foundation", "", SWIFT_JSON_VALUE]
    for enum in reg.enums.values():
        out.append(f"public enum {enum.name}: String, Codable, CaseIterable, Sendable {{")
        out += [f'    case {swift_ident(camel(v.lower()))} = "{v}"' for v in enum.values]
        out += ["}", ""]
    for name in reg.order:
        fields = reg.objects[name].fields
        props = []
        for f in fields:
            t = swift_type(f.type)
            if not f.required and not t.endswith("?"):
                t += "?"
            props.append((swift_ident(camel(f.name)), camel(f.name), t, f))
        out.append(f"public struct {name}: Codable, Equatable, Sendable {{")
        out += [f"    public var {ident}: {t}" for ident, _, t, _ in props]
        out.append("")
        params = ", ".join(f"{bare}: {t}{' = nil' if t.endswith('?') else ''}" for _, bare, t, _ in props)
        out.append(f"    public init({params}) {{")
        out += [f"        self.{bare} = {swift_ident(bare)}" for _, bare, _, _ in props]
        out += ["    }", "", "    enum CodingKeys: String, CodingKey {"]
        out += [f'        case {ident} = "{f.name}"' for ident, _, _, f in props]
        out += ["    }", "", "    public init(from decoder: Decoder) throws {"]
        out.append("        let c = try decoder.container(keyedBy: CodingKeys.self)")
        for ident, bare, t, f in props:
            if f.required:
                # Requis : la clé doit exister, même si sa valeur est `null`.
                out.append(f"        {bare} = try c.decode({t}.self, forKey: .{ident})")
            else:
                out.append(f"        {bare} = try c.decodeIfPresent({t[:-1]}.self, forKey: .{ident})")
        out += ["    }", "", "    public func encode(to encoder: Encoder) throws {"]
        out.append("        var c = encoder.container(keyedBy: CodingKeys.self)")
        for ident, bare, _, f in props:
            # Un champ requis mais nullable doit apparaître avec `null`.
            method = "encode" if f.required else "encodeIfPresent"
            out.append(f"        try c.{method}({bare}, forKey: .{ident})")
        out += ["    }", "}", ""]
    return "\n".join(out)


# --- Point d'entrée --------------------------------------------------------------


def main() -> int:
    reg = load_registry()
    rendered = {
        "python": render_python(reg),
        "typescript": render_typescript(reg),
        "swift": render_swift(reg),
    }
    check = "--check" in sys.argv
    stale = []
    for lang, path in OUTPUTS.items():
        content = rendered[lang]
        if check:
            if not path.exists() or path.read_text() != content:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            print(f"écrit {path.relative_to(ROOT)}")
    if stale:
        print("Contrats générés périmés — lancer scripts/generate_contracts.py :")
        print("\n".join(f"  {s}" for s in stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
