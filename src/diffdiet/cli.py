"""diffdiet command-line interface.

Usage::

    diffdiet check [--diff FILE | --git [REV_RANGE]] [--config FILE]
                   [--format text|md|json]
    diffdiet score [same input options] [--format text|md|json]

Diff input, in priority order:

1. ``--diff FILE`` — read the diff from a file (``-`` means stdin);
2. ``--git [REV_RANGE]`` — run ``git diff`` (default range: ``HEAD``);
3. stdin — when input is piped and neither flag is given.

``check`` applies the budget gate and exits 1 when the diff is over
budget. ``score`` prints the score only and always exits 0.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from .gate import check_gate, load_config
from .metrics import compute_metrics
from .parser import parse_diff
from .report import render
from .scoring import diet_score


def _add_input_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--diff",
        metavar="FILE",
        help="read the diff from FILE ('-' reads stdin)",
    )
    parser.add_argument(
        "--git",
        nargs="?",
        const="HEAD",
        default=None,
        metavar="REV_RANGE",
        help="take the diff from `git diff [REV_RANGE]` (default: HEAD)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "md", "json"],
        default="text",
        help="output format (default: text)",
    )


def _read_diff_text(args: argparse.Namespace) -> str:
    if args.diff is not None:
        if args.diff == "-":
            return sys.stdin.read()
        with open(args.diff, encoding="utf-8") as fh:
            return fh.read()
    if args.git is not None:
        result = subprocess.run(
            ["git", "diff", args.git],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git diff failed: {result.stderr.strip()}")
        return result.stdout
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="diffdiet",
        description="A minimal-diff guard for AI coding agents: score a "
        "diff and gate it against a size budget.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser(
        "check", help="score a diff and enforce the budget gate"
    )
    _add_input_args(check)
    check.add_argument(
        "--config",
        metavar="FILE",
        help="budget config JSON (default: .diffdiet.json if present)",
    )

    score = subparsers.add_parser(
        "score", help="print the diet score only (always exits 0)"
    )
    _add_input_args(score)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        diff_text = _read_diff_text(args)
    except (OSError, RuntimeError) as exc:
        print(f"diffdiet: {exc}", file=sys.stderr)
        return 2

    files = parse_diff(diff_text)
    metrics = compute_metrics(files, diff_text)
    score, breakdown = diet_score(metrics)

    if args.command == "score":
        if args.format == "json":
            print('{"score": ' + str(score) + "}")
        elif args.format == "md":
            print(f"## Diet score: {score}/100")
        else:
            print(f"Diet score: {score}/100")
        return 0

    # command == "check"
    try:
        config = load_config(args.config)
    except (OSError, ValueError) as exc:
        print(f"diffdiet: cannot load config: {exc}", file=sys.stderr)
        return 2
    violations = check_gate(metrics, score, config)
    print(render(args.format, metrics, score, breakdown, violations))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
