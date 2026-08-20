# CLAUDE.md — gold-signal-graveyard

## Always update the build log

**Every time anything is built, changed, decided, or discovered in this repo,
append it to [BUILD_LOG.md](BUILD_LOG.md).** Not at the end of the project, not
when asked — as part of doing the work. A session that changed something and did
not touch the build log is incomplete.

That includes:

- code written or changed, and *why* it was written that way
- decisions made, and the alternatives rejected
- decisions *deferred* — record them explicitly as open, don't leave them implicit
- things discovered about the data (e.g. the corrupt bars in Entry 6)
- dependencies added, tooling changed
- anything that surprised us

### How to write an entry

Newest entry at the bottom. Assume the reader **programs fine but knows nothing
about this project and nothing about futures markets**, and was not present for
any conversation.

- **Define every domain term the first time it appears** — front month, Sharpe
  ratio, out-of-sample, basis point, contango, tz-naive, Parquet.
- **Never write "we did X" and assume X means anything.** Say what X is, what it
  does, and why it exists. Writing "we implemented `load_yahoo`" is exactly the
  failure this log was created to fix.
- **Do not explain programming fundamentals.** Miguel is a CS student — loops,
  classes, Big-O, and git are not what needs explaining. Domain and project
  context are.
- **Record reasoning, not file diffs.** Git already stores what changed. The log
  stores *why*, which git cannot recover.
- **Be honest about state.** If something is unverified, untested, or is Claude's
  draft rather than Miguel's decision, say so plainly in the entry.

Also update the **Current state at a glance** table and the **Open items** list at
the bottom of the log so they stay accurate.

## Other conventions in this repo

- **DECISIONS.md is frozen.** Parameters there are pre-registered and must not be
  changed to make a result look better. If something genuinely must change, append
  a dated amendment at the bottom rather than editing in place, and note in the
  amendment that it was made after results were seen.
- **Every strategy variant tested goes in the DECISIONS.md trial ledger**,
  including ones abandoned for looking bad. The Deflated Sharpe calculation needs
  an honest count.
- Run `uv run ruff check .` and `uv run pytest` before committing.
- Tests currently fail on purpose. Never weaken a test to make it pass.
