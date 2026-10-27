"""Unified diff parsing.

Parses the output of ``git diff`` (and compatible unified diffs) into a
small object model: a list of :class:`FileDiff`, each holding its hunks.
Only the structure diffdiet needs is modelled — file paths, new/deleted
file markers, hunk headers, and the raw prefixed lines of each hunk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_DIFF_GIT_RE = re.compile(r"^diff --git a/(.*?) b/(.*)$")


@dataclass
class Hunk:
    """One ``@@ ... @@`` section of a file diff."""

    old_start: int = 0
    old_count: int = 0
    new_start: int = 0
    new_count: int = 0
    # Raw lines, each still carrying its one-character prefix:
    # '+' added, '-' deleted, ' ' context.
    lines: list[str] = field(default_factory=list)

    @property
    def added(self) -> list[str]:
        """Content of added lines, prefix stripped."""
        return [ln[1:] for ln in self.lines if ln.startswith("+")]

    @property
    def deleted(self) -> list[str]:
        """Content of deleted lines, prefix stripped."""
        return [ln[1:] for ln in self.lines if ln.startswith("-")]

    @property
    def context(self) -> list[str]:
        """Content of context lines, prefix stripped."""
        return [ln[1:] for ln in self.lines if ln.startswith(" ")]


@dataclass
class FileDiff:
    """All hunks belonging to one file in a diff."""

    old_path: str | None = None
    new_path: str | None = None
    is_new: bool = False
    is_deleted: bool = False
    is_binary: bool = False
    hunks: list[Hunk] = field(default_factory=list)

    @property
    def path(self) -> str:
        """Best display path: the new path if present, else the old one."""
        return self.new_path or self.old_path or ""

    @property
    def added_lines(self) -> list[str]:
        out: list[str] = []
        for hunk in self.hunks:
            out.extend(hunk.added)
        return out

    @property
    def deleted_lines(self) -> list[str]:
        out: list[str] = []
        for hunk in self.hunks:
            out.extend(hunk.deleted)
        return out

    def sequenced_lines(self) -> list[tuple[str, str]]:
        """``(prefix, content)`` pairs for every hunk line, in order.

        Useful for stateful scanners (e.g. dependency-block detection)
        that need context lines interleaved with added/deleted ones.
        """
        out: list[tuple[str, str]] = []
        for hunk in self.hunks:
            for ln in hunk.lines:
                if ln and ln[0] in "+- ":
                    out.append((ln[0], ln[1:]))
        return out


def _strip_prefix(path: str, prefix: str) -> str | None:
    path = path.strip()
    if path == "/dev/null":
        return None
    if path.startswith(prefix):
        return path[len(prefix):]
    return path


def parse_diff(text: str) -> list[FileDiff]:
    """Parse unified-diff *text* into a list of :class:`FileDiff`."""
    files: list[FileDiff] = []
    current: FileDiff | None = None
    hunk: Hunk | None = None

    for raw in text.splitlines():
        if raw.startswith("diff --git "):
            current = FileDiff()
            files.append(current)
            hunk = None
            m = _DIFF_GIT_RE.match(raw)
            if m:
                current.old_path = m.group(1)
                current.new_path = m.group(2)
            continue

        if current is None:
            # Tolerate diffs without the "diff --git" preamble.
            if raw.startswith("--- "):
                current = FileDiff()
                files.append(current)
                hunk = None
            else:
                continue

        if raw.startswith("new file mode"):
            current.is_new = True
            continue
        if raw.startswith("deleted file mode"):
            current.is_deleted = True
            continue
        if raw.startswith("Binary files"):
            current.is_binary = True
            continue
        if raw.startswith("--- "):
            current.old_path = _strip_prefix(raw[4:], "a/")
            continue
        if raw.startswith("+++ "):
            current.new_path = _strip_prefix(raw[4:], "b/")
            continue

        m = _HUNK_RE.match(raw)
        if m:
            hunk = Hunk(
                old_start=int(m.group(1)),
                old_count=int(m.group(2) or 1),
                new_start=int(m.group(3)),
                new_count=int(m.group(4) or 1),
            )
            current.hunks.append(hunk)
            continue

        if hunk is not None:
            if raw.startswith("\\"):
                # "\ No newline at end of file" — metadata, not content.
                continue
            if raw == "":
                # A bare empty line inside a hunk is an empty context line.
                hunk.lines.append(" ")
            elif raw[0] in "+- ":
                hunk.lines.append(raw)

    return files
