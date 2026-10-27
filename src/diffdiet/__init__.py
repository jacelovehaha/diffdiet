"""diffdiet — a minimal-diff guard for AI coding agents.

Parses unified diffs, measures how heavy a change is, scores it on a
transparent 0-100 "diet score", and enforces a configurable budget gate
suitable for CI.
"""

from .gate import DEFAULT_BUDGET, check_gate, load_config
from .metrics import Metrics, compute_metrics
from .parser import FileDiff, Hunk, parse_diff
from .scoring import diet_score

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_BUDGET",
    "FileDiff",
    "Hunk",
    "Metrics",
    "check_gate",
    "compute_metrics",
    "diet_score",
    "load_config",
    "parse_diff",
    "__version__",
]
