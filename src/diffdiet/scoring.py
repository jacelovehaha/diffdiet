"""The diet score: a transparent 0-100 grade for a diff.

The score starts at 100 and only ever goes down. Every deduction is a
fixed, published rate (see README.md) — no hidden weights:

============================  ======================  =====
Signal                        Deduction               Cap
============================  ======================  =====
Added lines                   1 pt per 10 added lines 30
New files                     8 pts per file          24
New dependencies              10 pts per dependency   30
Abstraction suspects          5 pts per suspect       20
Deleted files                 2 pts per file           6
============================  ======================  =====

The floor is 0. A tiny, surgical edit scores 100; a change that drags in
a framework to do a one-liner's job scores accordingly.
"""

from __future__ import annotations

from .metrics import Metrics

# (label, points) pairs, kept in deduction order for reporting.
Breakdown = list[tuple[str, int]]


def diet_score(metrics: Metrics) -> tuple[int, Breakdown]:
    """Return ``(score, breakdown)`` for *metrics*."""
    breakdown: Breakdown = []

    line_points = min(30, metrics.added_lines // 10)
    if line_points:
        breakdown.append((f"added lines x{metrics.added_lines}", line_points))

    file_points = min(24, metrics.new_files * 8)
    if file_points:
        breakdown.append((f"new files x{metrics.new_files}", file_points))

    dep_points = min(30, metrics.new_dependency_count * 10)
    if dep_points:
        breakdown.append(
            (f"new dependencies x{metrics.new_dependency_count}", dep_points)
        )

    suspect_points = min(20, metrics.abstraction_suspect_count * 5)
    if suspect_points:
        breakdown.append(
            (
                f"abstraction suspects x{metrics.abstraction_suspect_count}",
                suspect_points,
            )
        )

    deleted_points = min(6, metrics.deleted_files * 2)
    if deleted_points:
        breakdown.append(
            (f"deleted files x{metrics.deleted_files}", deleted_points)
        )

    score = max(0, 100 - sum(points for _, points in breakdown))
    return score, breakdown
