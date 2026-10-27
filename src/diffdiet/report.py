"""Render metrics, score and gate results as text, Markdown or JSON."""

from __future__ import annotations

import json

from .metrics import Metrics
from .scoring import Breakdown

_METRIC_ROWS = [
    ("added_lines", "Added lines"),
    ("deleted_lines", "Deleted lines"),
    ("net_lines", "Net lines"),
    ("files_touched", "Files touched"),
    ("new_files", "New files"),
    ("deleted_files", "Deleted files"),
    ("new_dependency_count", "New dependencies"),
    ("abstraction_suspect_count", "Abstraction suspects"),
    ("churn_ratio", "Churn ratio (lines/file)"),
]


def _metric_value(metrics: Metrics, key: str):
    return getattr(metrics, key)


def render_json(
    metrics: Metrics,
    score: int,
    breakdown: Breakdown,
    violations: list[str] | None = None,
) -> str:
    payload: dict = {
        "score": score,
        "metrics": metrics.to_dict(),
        "breakdown": [
            {"signal": label, "points": points} for label, points in breakdown
        ],
    }
    if violations is not None:
        payload["gate"] = {
            "passed": not violations,
            "violations": list(violations),
        }
    return json.dumps(payload, indent=2)


def render_text(
    metrics: Metrics,
    score: int,
    breakdown: Breakdown,
    violations: list[str] | None = None,
) -> str:
    lines = [f"Diet score: {score}/100"]
    if breakdown:
        lines.append("Deductions:")
        for label, points in breakdown:
            lines.append(f"  -{points:<3} {label}")
    else:
        lines.append("Deductions: none")
    lines.append("")
    lines.append("Metrics:")
    for key, label in _METRIC_ROWS:
        lines.append(f"  {label + ':':28} {_metric_value(metrics, key)}")
    if metrics.new_dependencies:
        lines.append(
            "  New dependency names:      " + ", ".join(metrics.new_dependencies)
        )
    if metrics.abstraction_suspects:
        lines.append(
            "  Abstraction suspects:      "
            + ", ".join(metrics.abstraction_suspects)
        )
    if violations is not None:
        lines.append("")
        if violations:
            lines.append("Gate: FAILED")
            for violation in violations:
                lines.append(f"  ! {violation}")
        else:
            lines.append("Gate: PASSED")
    return "\n".join(lines)


def render_markdown(
    metrics: Metrics,
    score: int,
    breakdown: Breakdown,
    violations: list[str] | None = None,
) -> str:
    lines = [f"## Diet score: {score}/100", ""]
    if breakdown:
        lines.append("### Deductions")
        lines.append("")
        lines.append("| Signal | Points |")
        lines.append("| --- | ---: |")
        for label, points in breakdown:
            lines.append(f"| {label} | -{points} |")
        lines.append("")
    lines.append("### Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | ---: |")
    for key, label in _METRIC_ROWS:
        lines.append(f"| {label} | {_metric_value(metrics, key)} |")
    lines.append("")
    if metrics.new_dependencies:
        lines.append(
            "New dependencies: " + ", ".join(metrics.new_dependencies) + "\n"
        )
    if metrics.abstraction_suspects:
        lines.append(
            "Abstraction suspects: "
            + ", ".join(metrics.abstraction_suspects)
            + "\n"
        )
    if violations is not None:
        if violations:
            lines.append("### Gate: FAILED")
            lines.append("")
            for violation in violations:
                lines.append(f"- {violation}")
        else:
            lines.append("### Gate: PASSED")
        lines.append("")
    return "\n".join(lines)


_RENDERERS = {
    "text": render_text,
    "md": render_markdown,
    "json": render_json,
}


def render(
    fmt: str,
    metrics: Metrics,
    score: int,
    breakdown: Breakdown,
    violations: list[str] | None = None,
) -> str:
    return _RENDERERS[fmt](metrics, score, breakdown, violations)
