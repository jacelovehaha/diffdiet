"""Diff metrics: how heavy is a change?

Beyond raw line counts, diffdiet looks for the two classic ways an agent
change gets heavy:

* **new dependencies** — packages added to ``pyproject.toml``,
  ``requirements.txt`` or ``package.json`` dependency blocks;
* **abstraction suspects** — functions/classes the diff *defines* but
  never references again anywhere in the same diff. A name that occurs
  exactly once (its own definition) is very likely a single-use
  abstraction that could have been inlined or never written.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from .parser import FileDiff


@dataclass
class Metrics:
    added_lines: int = 0
    deleted_lines: int = 0
    net_lines: int = 0
    files_touched: int = 0
    new_files: int = 0
    deleted_files: int = 0
    new_dependencies: list[str] = field(default_factory=list)
    abstraction_suspects: list[str] = field(default_factory=list)
    # (added + deleted) / files_touched — average churn per touched file.
    churn_ratio: float = 0.0

    @property
    def new_dependency_count(self) -> int:
        return len(self.new_dependencies)

    @property
    def abstraction_suspect_count(self) -> int:
        return len(self.abstraction_suspects)

    def to_dict(self) -> dict:
        return {
            "added_lines": self.added_lines,
            "deleted_lines": self.deleted_lines,
            "net_lines": self.net_lines,
            "files_touched": self.files_touched,
            "new_files": self.new_files,
            "deleted_files": self.deleted_files,
            "new_dependencies": list(self.new_dependencies),
            "new_dependency_count": self.new_dependency_count,
            "abstraction_suspects": list(self.abstraction_suspects),
            "abstraction_suspect_count": self.abstraction_suspect_count,
            "churn_ratio": self.churn_ratio,
        }


# ---------------------------------------------------------------------------
# New-dependency detection
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_PEP621_ARRAY_RE = re.compile(r"^[\w.\-]*dependencies[\w.\-]*\s*=\s*\[")
_ANY_ARRAY_RE = re.compile(r"^[\w.\-]+\s*=\s*\[")
_QUOTED_RE = re.compile(r"""^["']([^"']+)["']\s*,?$""")
_TABLE_KV_RE = re.compile(r"^([A-Za-z0-9_.\-]+)\s*=")
_PKG_BLOCK_RE = re.compile(r'^"(?:dev|peer|optional)?[Dd]ependencies"\s*:\s*\{')
_PKG_ENTRY_RE = re.compile(r'^\s*"([^"]+)"\s*:\s*"')
_SPEC_SPLIT_RE = re.compile(r"[<>=!~;\[\s]")


def _dep_name(spec: str) -> str:
    """Reduce a version spec like ``requests>=2`` to just the name."""
    return _SPEC_SPLIT_RE.split(spec.strip(), maxsplit=1)[0]


def _pyproject_deps(filediff: FileDiff) -> list[str]:
    """Dependencies added in a pyproject.toml diff.

    Handles both the PEP 621 array form::

        dependencies = [
            "requests>=2",
        ]

    (including arrays inside ``[project.optional-dependencies]``) and
    table form used by tools such as Poetry::

        [tool.poetry.dependencies]
        requests = "^2"
    """
    deps: list[str] = []
    section = ""
    in_array = False
    for kind, content in filediff.sequenced_lines():
        if kind == "-":
            continue
        stripped = content.strip()
        m = _SECTION_RE.match(content)
        if m:
            section = m.group(1)
            in_array = False
            continue
        if _PEP621_ARRAY_RE.match(stripped) or (
            section.split(".")[-1] == "optional-dependencies"
            and _ANY_ARRAY_RE.match(stripped)
        ):
            in_array = True
            continue
        if in_array:
            if stripped.startswith("]"):
                in_array = False
                continue
            if kind == "+":
                qm = _QUOTED_RE.match(stripped)
                if qm:
                    deps.append(_dep_name(qm.group(1)))
            continue
        if section.split(".")[-1] == "dependencies" and kind == "+":
            km = _TABLE_KV_RE.match(stripped)
            if km:
                deps.append(km.group(1))
    return deps


def _requirements_deps(filediff: FileDiff) -> list[str]:
    """Dependencies added in a requirements.txt diff."""
    deps: list[str] = []
    for line in filediff.added_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        name = _dep_name(stripped)
        if name:
            deps.append(name)
    return deps


def _package_json_deps(filediff: FileDiff) -> list[str]:
    """Dependencies added inside package.json dependency blocks."""
    deps: list[str] = []
    in_block = False
    for kind, content in filediff.sequenced_lines():
        if kind == "-":
            continue
        stripped = content.strip()
        if _PKG_BLOCK_RE.match(stripped):
            in_block = True
            continue
        if in_block and stripped in ("}", "},"):
            in_block = False
            continue
        if in_block and kind == "+":
            m = _PKG_ENTRY_RE.match(content)
            if m:
                deps.append(m.group(1))
    return deps


def detect_new_dependencies(files: list[FileDiff]) -> list[str]:
    """All newly introduced dependency names, in order of appearance."""
    deps: list[str] = []
    for filediff in files:
        base = os.path.basename(filediff.path)
        if base == "pyproject.toml":
            deps.extend(_pyproject_deps(filediff))
        elif base.endswith("requirements.txt"):
            deps.extend(_requirements_deps(filediff))
        elif base == "package.json":
            deps.extend(_package_json_deps(filediff))
    return deps


# ---------------------------------------------------------------------------
# Abstraction suspects
# ---------------------------------------------------------------------------

_DEFINITION_PATTERNS = [
    re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)"),            # Python def
    re.compile(r"^\s*class\s+([A-Za-z_]\w*)"),                         # Python / JS class
    re.compile(r"^\s*(?:export\s+)?function\s+([A-Za-z_]\w*)"),      # JS function
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_]\w*)\s*=>"),  # JS arrow
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*function\b"),  # JS function expr
]


def detect_abstraction_suspects(
    files: list[FileDiff], diff_text: str
) -> list[str]:
    """Names defined by added lines that occur only once in the diff.

    The single occurrence is the definition itself — nothing in the
    change ever calls, instantiates or references the new abstraction.
    """
    defined: list[str] = []
    for filediff in files:
        for line in filediff.added_lines:
            for pattern in _DEFINITION_PATTERNS:
                m = pattern.match(line)
                if m and m.group(1) not in defined:
                    defined.append(m.group(1))
                    break
    suspects: list[str] = []
    for name in defined:
        occurrences = len(re.findall(r"\b" + re.escape(name) + r"\b", diff_text))
        if occurrences <= 1:
            suspects.append(name)
    return suspects


# ---------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------


def compute_metrics(files: list[FileDiff], diff_text: str = "") -> Metrics:
    """Aggregate all metrics for a parsed diff."""
    added = sum(len(f.added_lines) for f in files)
    deleted = sum(len(f.deleted_lines) for f in files)
    metrics = Metrics(
        added_lines=added,
        deleted_lines=deleted,
        net_lines=added - deleted,
        files_touched=len(files),
        new_files=sum(1 for f in files if f.is_new),
        deleted_files=sum(1 for f in files if f.is_deleted),
        new_dependencies=detect_new_dependencies(files),
        abstraction_suspects=detect_abstraction_suspects(files, diff_text),
    )
    metrics.churn_ratio = round(
        (added + deleted) / max(1, metrics.files_touched), 2
    )
    return metrics
