---
name: diffdiet
description: Keep code changes minimal. Use before and while editing code to enforce a smallest-diff discipline — prefer editing existing files over creating new ones, avoid single-use abstractions and new dependencies, delete dead code, and pick the approach that touches the fewest lines.
---

# Diffdiet: the smallest change that works

## When to apply

Apply this skill to any task that modifies code: bug fixes, features,
refactors, and generated scaffolding alike.

## Doctrine

1. **Edit before you create.** Look for the file or function that
   already owns this behaviour and change it there. A new module is
   justified only when no existing home fits.

2. **Solve it fully, then stop.** The target diff is the smallest one
   after which the problem is *gone* — not merely smaller. Resist the
   extra option, the extra layer, the extra file "for later".

3. **Abstractions must be earned twice.** If a helper would have a
   single call site, keep the logic inline at that site. Extract only
   when repetition is real and visible.

4. **Spend the project's existing toolbox first.** Standard library,
   then dependencies already in the manifest, then — reluctantly — a
   new dependency. State explicitly why any new dependency is worth its
   upkeep.

5. **Dead code is deleted, never commented out.** "Kept just in case"
   blocks are removed. History systems are the safety net.

6. **Match the local style.** Mirror each file's conventions for
   naming, layout and error handling. A diff should read as if the
   file's original author wrote it.

7. **Break ties by footprint.** Between two correct approaches, the
   one with fewer changed lines and fewer touched files wins.

## Self-review before finishing

- Lines changed: could a reviewer believe each one was necessary?
- Anything created that is used exactly once? Inline it.
- Any dependency added for a standard-library job? Remove it.
- Any commented-out code left behind? Delete it.
