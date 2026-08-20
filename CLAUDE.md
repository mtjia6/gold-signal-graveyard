# CLAUDE.md: gold-signal-graveyard

## Always update the build log

**Every time anything is built, changed, decided, or discovered in this repo,
append it to [BUILD_LOG.md](BUILD_LOG.md).** Not at the end of the project, not
when asked: as part of doing the work. A session that changed something and did
not touch the build log is incomplete.

That includes:

- code written or changed, and *why* it was written that way
- decisions made, and the alternatives rejected
- decisions *deferred*: record them explicitly as open, don't leave them implicit
- things discovered about the data (e.g. the corrupt bars in Entry 6)
- dependencies added, tooling changed
- anything that surprised us

### How to write an entry

Newest entry at the bottom. Assume the reader **programs fine but knows nothing
about this project and nothing about futures markets**, and was not present for
any conversation.

- **Define every domain term the first time it appears**: front month, Sharpe
  ratio, out-of-sample, basis point, contango, tz-naive, Parquet.
- **Never write "we did X" and assume X means anything.** Say what X is, what it
  does, and why it exists. Writing "we implemented `load_yahoo`" is exactly the
  failure this log was created to fix.
- **Do not explain programming fundamentals.** Miguel is a CS student: loops,
  classes, Big-O, and git are not what needs explaining. Domain and project
  context are.
- **Record reasoning, not file diffs.** Git already stores what changed. The log
  stores *why*, which git cannot recover.
- **Be honest about state.** If something is unverified, untested, or is Claude's
  draft rather than Miguel's decision, say so plainly in the entry.

Also update the **Current state at a glance** table and the **Open items** list at
the bottom of the log so they stay accurate.

## Explain every calculation where it is introduced

Whenever a new calculation is implemented, explain it **inside the build log entry that
builds it**: woven into the reasoning, not collected in a separate reference section.
A formula quarantined in an appendix loses the thing that makes it comprehensible: why
it is computed that way, and what it is for.

Each calculation needs, in the flow of the entry:

- the actual code, as a `python` block
- what each step does, and its units
- **a worked example with real numbers from this project's data**: show the arithmetic
- the frozen parameters it depends on
- any correctness subtlety: an execution lag, a `.shift()`, a unit conversion
- where a step is cosmetic rather than load-bearing, say so

**Check the arithmetic in every worked example before writing it.** A wrong worked
example in a teaching document is worse than none: one was shipped in Entry 10 that
used the same day's position instead of the previous day's, which is the exact bug the
surrounding text was explaining.

One exception: **do not write out the Deflated Sharpe Ratio formulas.** That derivation
is deliberately left to Miguel (Entry 3); cite the paper instead.

## Also keep the concept notes

[CONCEPTS.md](CONCEPTS.md) collects the *ideas* behind the project in plain language.
It is a reference, not a diary: `BUILD_LOG.md` records what was done on a given day,
`CONCEPTS.md` records what a thing *is*, independent of when it came up.

**When a concept gets explained in conversation and Miguel confirms it landed, write
it into CONCEPTS.md.** Use the explanation that actually worked, not a tidied-up
version: if a concrete numeric example is what made it click, the numbers go in.

### Register

Write at the level of a university course, not a simplified explainer. Miguel is a CS
student: he has the mathematical background, he lacks the domain vocabulary. So build
from the ground up, but **use the correct technical terms and define them properly**
rather than avoiding them. The names are how he finds the literature later.

Concretely: say "volatility is the standard deviation of returns", not "how much it
bounces around". Say "heteroskedasticity", "ex ante", "autocorrelation", "notional
exposure", "measurable with respect to the information set" and define each on first
use. Order the material so every definition uses only terms already introduced.

**No em dashes anywhere.** Use a colon where a clause explains the one before it, a
comma where it qualifies, a full stop where it is a separate thought, or parentheses
for a genuine aside. Applies to prose, documentation, commit messages, and chat.

Be comprehensive. Do not omit a concept because it seems peripheral; if the code
computes it or the report mentions it, it needs a definition somewhere in CONCEPTS.md.

Guidelines:

- **Assume no finance background whatsoever.** Define every domain term on first use,
  including ones that feel too basic to bother with: long, short, position, return,
  exposure. Miguel's questions ("so vol_target is just the lot size?", "why are we
  estimating the future?") are the register to write at.
- **Always include worked examples with real numbers** pulled from this project's own
  data, not invented ones. Show the arithmetic: `0.10 / 0.457 = 0.22`. A concrete day
  from the actual price history beats any amount of prose.
- Prefer a small table of measured values over paragraphs.
- Say what the concept is *for*, which decision it affects: not just what it means.
- Be honest about limits in the same breath. Vol targeting reduced the March 2020 loss
  but did not prevent it; say so rather than letting the example oversell.
- Do not explain programming fundamentals. Domain concepts only.

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
