"""Rapport de banc d'essai en français, lisible par un non-développeur."""

from __future__ import annotations

from oris_api.benchmark.dataset import Dataset
from oris_api.benchmark.runner import WEIGHTS, ProviderReport

LABELS = {
    "tooth_number_accuracy": "Numéros de dent exacts",
    "hallucinated_teeth": "Numéros de dent inventés ou faux",
    "critical_term_recall": "Termes dentaires / marques retrouvés",
    "negation_preservation": "Négations conservées",
    "speaker_accuracy": "Locuteurs bien séparés",
    "single_voice_rate": "Enregistrements rendus d'une seule voix (aucune séparation)",
    "role_accuracy": "Rôles praticien / patient bien attribués",
    "wer": "Taux d'erreur de mots (WER)",
    "reliability": "Requêtes réussies",
    "finalization_latency_p50_s": "Délai de transcription finale, médian (s)",
    "finalization_latency_p95_s": "Délai de transcription finale, 95e centile (s)",
    "finalization_rtf_p95": "Délai / durée audio, 95e centile",
    "interim_latency_p50_ms": "Délai du texte en direct, médian (ms)",
    "interim_latency_p95_ms": "Délai du texte en direct, 95e centile (ms)",
    "final_latency_p50_ms": "Délai du texte définitif en direct, médian (ms)",
    "final_latency_p95_ms": "Délai du texte définitif en direct, 95e centile (ms)",
    "stream_reconnections": "Reconnexions en direct",
    "stream_failures": "Échecs du direct",
    "glossary_gain_term_recall": "Gain du glossaire sur les termes",
    "glossary_gain_tooth_accuracy": "Gain du glossaire sur les dents",
    "glossary_gain_wer": "Gain du glossaire sur le WER",
    "cost_usd_per_30_min": "Coût pour 30 min (USD)",
    "weighted_score": "Score pondéré",
    "weighted_score_coverage": "Part de la pondération mesurée",
}
PERCENT = {
    "tooth_number_accuracy", "critical_term_recall", "negation_preservation", "speaker_accuracy",
    "role_accuracy", "wer", "reliability", "single_voice_rate", "glossary_gain_term_recall",
    "glossary_gain_tooth_accuracy",
    "glossary_gain_wer", "weighted_score", "weighted_score_coverage",
}  # fmt: skip
GATES = {"passed": "validée", "failed": "refusée", "not_reviewed": "non évaluée"}


def fmt(key: str, value: float | None) -> str:
    if value is None:
        return "non mesuré"
    if key in PERCENT:
        return f"{value * 100:.1f} %"
    return f"{value:.2f}" if isinstance(value, float) and not value.is_integer() else f"{value:.0f}"


def render_markdown(reports: list[ProviderReport], dataset: Dataset) -> str:
    lines = [
        f"# Banc d'essai transcription — {dataset.name} v{dataset.version}",
        "",
        f"{len(dataset.items)} enregistrement(s), langue {dataset.locale}.",
    ]
    if dataset.synthetic_only:
        lines += [
            "",
            "> **Données synthétiques (voix de synthèse macOS).** Ce banc valide la chaîne de "
            "mesure et donne une première tendance ; il **ne suffit pas** pour choisir un "
            "fournisseur : il faut des consultations simulées par des professionnels, en cabinet.",
        ]
    keys = [k for k in LABELS if any(r.summary.get(k) is not None for r in reports)]
    header = "| Mesure | " + " | ".join(f"{r.key} ({r.version})" for r in reports) + " |"
    lines += ["", "## Résultats", "", header, "|---|" + "---|" * len(reports)]
    for key in keys:
        lines.append(
            f"| {LABELS[key]} | " + " | ".join(fmt(key, r.summary.get(key)) for r in reports) + " |"
        )
    lines += ["", "## Conformité (préalable, pas un bonus)", ""]
    for report in reports:
        lines.append(
            f"- {report.key} : conformité HDS / contrat **{GATES.get(report.compliance_gate, report.compliance_gate)}**."
        )
    lines += ["", "## Erreurs critiques", ""]
    for report in reports:
        regressions = report.critical_regressions
        lines.append(
            f"- {report.key} : {len(regressions)} — " + (", ".join(regressions[:20]) or "aucune")
        )
    lines += [
        "",
        "## Méthode",
        "",
        "- Mêmes fichiers audio pour chaque fournisseur ; textes normalisés (minuscules, ponctuation "
        "retirée, numéros de dent en chiffres) avant comparaison.",
        "- Numéros de dent et négations : comptés justes seulement s'ils sont alignés au même endroit "
        "que dans la référence.",
        "- Locuteurs : meilleure correspondance entre étiquettes du fournisseur et locuteurs réels, "
        "au temps de parole.",
        "- Score pondéré : "
        + ", ".join(f"{k} {int(w * 100)} %" for k, w in WEIGHTS.items())
        + ". Une mesure absente (tarif non renseigné, direct non testé) est retirée de la "
        "pondération ; la part mesurée est indiquée.",
        "- Latence : direct = 1 − p95/3 s ; sinon 1 − (délai/durée audio). Coût : 1 − coût/10 USD.",
        "",
        "Aucun fournisseur n'est choisi par ce rapport (décision D020).",
    ]
    return "\n".join(lines) + "\n"
