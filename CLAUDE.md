# airRoaster — working conventions

## Commit automatically after significant work

**Commit without being asked, as soon as a unit of work is complete and
verified.** Do not wait to be told, and do not batch several unrelated units
into one commit.

"Significant" means a coherent, finished change — a firmware feature that
compiles under `./verify.sh`, a tool that runs, an analysis whose conclusion
landed in the state docs, a documentation restructure. It does not mean every
file write: work in progress, a half-migrated refactor, or an edit you are
about to revise stays uncommitted.

Rules that still apply:

- **Never push automatically.** Pushing is outward-facing; ask first.
- **Never commit onto `main` automatically.** Roasting work happens on a
  feature branch (`feature/…` off `main`); if the branch is `main`, branch
  first or ask.
- **Never `git add -A`.** Stage the paths you actually changed, so an
  unrelated experiment sitting in the working tree does not ride along.
  (`secrets.h`, `build/` and `.DS_Store` are already gitignored.)
- If `verify.sh` fails or a check does not pass, say so and leave the work
  uncommitted rather than committing something known-broken.
- Follow the existing message style: a lowercase `area:` prefix
  (`firmware:`, `artisan:`, `tools:`, `plan:`, `docs:`), then a body that
  explains *why* and records anything the change corrected.

## State documents

Read [state-current.md](state-current.md) first — it carries the active effort
and the version/branch truth. [state-plan.md](state-plan.md) is work not yet
done and the specifications in force; [state-history.md](state-history.md) is
the cascade PID investigation record (chronological, later sections supersede
earlier); [state-archive.md](state-archive.md) is completed work and the
F-numbered review findings. Keep all four in sync as part of the same commit as
the change they describe.
