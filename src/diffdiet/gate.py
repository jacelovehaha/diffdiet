"""The budget gate.

A budget is a small JSON object, by default read from ``.diffdiet.json``
in the current directory (or from an explicit ``--config`` path)::

    {
      "max_added_lines": 300,
      "max_new_files": 3,
      "max_new_deps": 0,
      "min_score": 60
    }

Any key may be omitted; missing keys fall back to the defaults below.
``diffdiet check`` exits 1 when the diff breaks any budget line.
"""

from __future__ import annotations

import json
import os

from .metrics import Metrics

DEFAULT_BUDGET: dict[str, int] = {
    "max_added_lines": 300,
    "max_new_files": 3,
    "max_new_deps": 0,
    "min_score": 60,
}

DEFAULT_CONFIG_NAME = ".diffdiet.json"


def load_config(path: str | None = None) -> dict[str, int]:
    """Load a budget config, merged over :data:`DEFAULT_BUDGET`.

    With *path* given, that file must exist. Without it, ``.diffdiet.json``
    in the current directory is used if present; otherwise the defaults.
    """
    config = dict(DEFAULT_BUDGET)
    chosen = path
    if chosen is None and os.path.exists(DEFAULT_CONFIG_NAME):
        chosen = DEFAULT_CONFIG_NAME
    if chosen is not None:
        with open(chosen, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"{chosen}: config must be a JSON object")
        for key in DEFAULT_BUDGET:
            if key in data:
                config[key] = int(data[key])
    return config


def check_gate(
    metrics: Metrics, score: int, config: dict[str, int]
) -> list[str]:
    """Return the list of budget violations (empty means the gate passes)."""
    violations: list[str] = []
    if metrics.added_lines > config["max_added_lines"]:
        violations.append(
            f"added lines {metrics.added_lines} exceeds budget "
            f"{config['max_added_lines']}"
        )
    if metrics.new_files > config["max_new_files"]:
        violations.append(
            f"new files {metrics.new_files} exceeds budget "
            f"{config['max_new_files']}"
        )
    if metrics.new_dependency_count > config["max_new_deps"]:
        names = ", ".join(metrics.new_dependencies)
        violations.append(
            f"new dependencies {metrics.new_dependency_count} exceeds budget "
            f"{config['max_new_deps']} ({names})"
        )
    if score < config["min_score"]:
        violations.append(
            f"diet score {score} below minimum {config['min_score']}"
        )
    return violations
