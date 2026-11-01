# diffdiet

**A minimal-diff guard for AI coding agents.**

Coding agents are enthusiastic. Given a one-line bug, an agent will
happily return a new module, a helper framework, two abstractions and a
fresh dependency. The fix works — and the codebase pays for it forever.

diffdiet pushes back in two ways:

1. **A rules pack** (`rules/`) that teaches the agent the discipline up
   front: edit before creating, no single-use abstractions, no new
   dependency for a standard-library job, delete dead code instead of
   commenting it out.
2. **A measuring tool** (the `diffdiet` CLI) that parses a unified diff,
   computes how heavy the change is, grades it with a transparent
   0–100 **diet score**, and enforces a **budget gate** in CI.

Zero third-party dependencies. Python ≥ 3.10.

## Install

```bash
pip install .
# or run without installing:
PYTHONPATH=src python -m diffdiet --help
```

## Quick start

```bash
# Score the current uncommitted change
git diff | diffdiet check

# Check a saved diff against the budget
diffdiet check --diff change.diff

# Check a commit range
diffdiet check --git main..HEAD

# Just the score (always exits 0 — handy for dashboards)
diffdiet score --diff change.diff --format json
```

Output for a change that went on a binge (see `examples/bloated.diff`):

```
Diet score: 57/100
Deductions:
  -5   added lines x57
  -8   new files x1
  -10  new dependencies x1
  -20  abstraction suspects x4
...
Gate: FAILED
  ! new dependencies 1 exceeds budget 0 (fancylib)
  ! diet score 57 below minimum 60
```

The same feature as a small edit (`examples/lean.diff`) scores 100/100
and passes the gate. Try both:

```bash
diffdiet check --diff examples/lean.diff     # exit 0
diffdiet check --diff examples/bloated.diff  # exit 1
```

## What gets measured

| Metric | Meaning |
| --- | --- |
| Added / deleted / net lines | Raw size of the change |
| Files touched | Blast radius |
| New files / deleted files | Structural churn |
| New dependencies | Packages added to `pyproject.toml`, `requirements.txt` or `package.json` dependency blocks |
| Abstraction suspects | Functions/classes defined in the diff whose name occurs **only once** in the whole diff — defined, never used. The classic single-use abstraction. |
| Churn ratio | (added + deleted) / files touched |

## The diet score

The score starts at 100 and only goes down, at fixed published rates:

| Signal | Deduction | Cap |
| --- | --- | --- |
| Added lines | 1 pt per 10 added lines | 30 |
| New files | 8 pts each | 24 |
| New dependencies | 10 pts each | 30 |
| Abstraction suspects | 5 pts each | 20 |
| Deleted files | 2 pts each | 6 |

Floor: 0. No hidden weights — you can recompute any score by hand from
the metrics table.

## The budget gate

`diffdiet check` reads `.diffdiet.json` in the current directory (or a
file given with `--config`):

```json
{
  "max_added_lines": 300,
  "max_new_files": 3,
  "max_new_deps": 0,
  "min_score": 60
}
```

All keys are optional; omitted keys use the defaults above. The command
exits **1** when any budget line is broken, **0** otherwise — drop it
into CI and let the build argue with the agent.

In CI (example):

```yaml
- run: git diff origin/main...HEAD > change.diff
- run: diffdiet check --diff change.diff
```

## The rules pack

Three wordings of the same doctrine — use whichever your agent reads:

| File | For |
| --- | --- |
| `rules/AGENTS.md` | Generic agents that read `AGENTS.md` |
| `rules/CLAUDE.md` | Claude-style project instructions |
| `rules/SKILL.md` | Agent-skill format (front matter + instructions) |

Copy the file into your repository (renaming as your tool expects) and
the agent starts its work already on the diet.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

## Commercial note

The core is open source (MIT). Planned paid extras: hosted trend
dashboards (score history per repo/agent), organisation-wide budget
policies, and per-agent leaderboards for teams running several coding
agents.

## License

MIT — see `LICENSE`.
