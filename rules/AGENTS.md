# Working agreement: change less

These rules apply to every edit made in this repository. They exist
because the cheapest code to review, test and delete is the code that was
never written — and because a small, precise change is almost always
safer than a large, clever one.

## The rules

1. **Repair before you build.** If a file, function or pattern already
   exists that does most of the job, extend or fix it. A new file is the
   last resort, not the first instinct.

2. **Ship the smallest diff that completely solves the problem.** "Completely"
   matters — a partial fix that leaves the bug half-alive is not small,
   it is unfinished. But once the problem is solved, stop. Do not
   gold-plate.

3. **One call site does not earn an abstraction.** A helper, class or
   layer used exactly once is indirection without payoff. Inline it.
   Earn the abstraction on the second or third real use, when the shape
   of the repetition is actually known.

4. **Exhaust what is already here before importing anything.** The
   standard library first, then the dependencies the project already
   carries, then — and only then — a new dependency. Every new package
   is a lifetime maintenance contract signed on the user's behalf.

5. **Delete dead code; do not embalm it.** Commented-out blocks are not
   documentation, they are litter. Version control remembers everything
   that was removed. Trust it.

6. **Write in the file's own accent.** Match the naming, formatting,
   error handling and idioms already present in the file you are
   touching, even where you would personally choose differently.
   Consistency inside a file beats your preference across files.

7. **When two designs tie, count the cost.** Pick the one that touches
   fewer lines and fewer files. The diff is the unit of risk: smaller
   diff, smaller blast radius.

## The pre-flight check

Before presenting a change, ask:

- Could this be a five-line edit instead of a fifty-line one?
- Did I create anything that is used only once?
- Did I add a dependency for something the standard library does?
- Is there dead or commented-out code I should have removed?

If any answer is yes, slim the diff down before it leaves your hands.
