# MarketForge — Agent Operating Manual

This file is the operating manual for automated coding agents working in this
repository. It states what the project is, what it is becoming, and the rules you
must follow. Read it in full before you write any code, plan any change, or open
any pull request. When this file and a human instruction disagree, ask the human
rather than guessing.

---

## 1. What this project is

MarketForge is a real, usable tool for finding statistical-arbitrage
opportunities in **less crowded** markets, built alongside the
point-in-time-correct market-data platform that makes its results trustworthy
rather than merely plausible.

The tool is the product. The lakehouse, the historical reconstructor, and the
feature store are the **trust substrate**: they exist so that every opportunity
the tool surfaces is free of survivorship bias, correct as of the point in time,
and honestly backtested.

The ordering that governs every decision here is **honesty over profit**. The
real asset is the measured gap between a backtest and live trading — not the
profit-and-loss number. Do not let a task drift toward a portfolio demo.

---

## 2. Non-negotiable rules

These rules override convenience, speed, and any habit you bring with you.

1. **Never modify the `main` branch directly.** Do each task in its own worktree
   on a new branch, and leave the main checkout on `main`, clean. `main` is
   protected: no direct commits, no direct pushes, no working-tree edits intended
   for `main`. All work — features, bug fixes, documentation, refactors — happens
   in a worktree on a branch and reaches `main` only through a reviewed pull
   request.

2. **Write plans in full words — strongly avoid abbreviations.** In any plan,
   implementation proposal, milestone description, design note, commit-message
   body, or pull-request description, spell terms out in full. Write
   "point-in-time" rather than the initials, "profit and loss" rather than the
   ampersand form, "open, high, low, close, and volume" rather than the condensed
   form, "continuous integration" rather than the two-letter form, and
   "command-line interface" rather than the three-letter form. Literal
   identifiers are exempt and must be used exactly as they are: command names
   (for example `make ci`), tool and product names (for example `ruff`, `mypy`,
   DuckDB, Parquet), and file names (for example `cli.py`, `ci.yml`). If you feel
   you must shorten a term, write it in full on first use and only then introduce
   the short form.

3. **Never break determinism or reproducibility.** The same seed must produce
   byte-identical output, everywhere, including in continuous integration. Do not
   introduce hidden state, wall-clock dependence, unordered iteration that
   changes output, or non-seeded randomness.

4. **Treat the data schemas as a stable contract.** The PyArrow schemas in
   `src/marketforge/schemas.py` are the shared contract between the synthetic
   generator and the future real-data ingestion layer. Do not rename, retype, or
   reorder fields casually. Any schema change is a breaking change and must be
   deliberate, documented, and carried through every consumer and test.

5. **Respect the trading guardrail.** This project paper-trades first, for
   months, with toy money the owner can afford to lose. Do not build, promise, or
   imply real-money trading, portfolio performance, or profit claims. The
   deliverable is the engineering and the honest backtest-to-live gap.

6. **Ship to the acceptance criteria.** Every milestone in `plan.md` has
   acceptance criteria. Those are the definition of done. Do not gold-plate, and
   do not declare work finished until the criteria actually pass.

7. **Always open a pull request for finished work.** When a change is complete,
   push its branch and open a pull request into `main` so it can be reviewed and
   merged. Never leave finished work as an unpushed branch, and never merge to
   `main` yourself.

---

## 3. Before you start any task

1. **Read the map.** `plan.md` is the phased plan and definition of done;
   `README.md` is the current status and quickstart; the files in `docs/thoughts/`
   record the reasoning behind each decision. Read the relevant ones before you
   act. Do not re-litigate a settled decision without new evidence; if you believe
   one must change, say so explicitly and record the reasoning.

2. **Check the phase.** The repository is in Phase 0 (foundations). Later phases —
   the lakehouse, the reconstructor, tick processing and the feature store, the
   statistical-arbitrage screener, and paper trading — are planned but not built.
   Do not build ahead of the current phase unless the task explicitly asks for it.

3. **Create a worktree first.** See the worktree rules below. Every task gets its
   own worktree on a new branch; never work in the main checkout.

4. **Plan before code, in full words.** Write a short plan stating what will
   change and how you will verify it, using no abbreviations. For anything larger
   than a trivial fix, share the plan and wait for approval before implementing.

---

## 4. Worktrees, branches, and commits

The default is **one worktree per task**, so parallel agents never collide in a
shared working directory. The main checkout stays on `main`, clean, at all times.

- Start every task from an up-to-date `main`:

      git fetch origin
      git worktree add ../MarketForge-<task-slug> -b <branch-name> origin/main

- The worktree lives in a sibling directory (`../MarketForge-<task-slug>`); the
  slug is short and kebab-case, and the branch name follows the same convention
  with a type prefix, for example `feature/`, `fix/`, `docs/`, `chore/`, or
  `refactor/`.
- Do all work inside that worktree directory. Never share a worktree between two
  tasks or two agents.
- A new worktree starts without the `.venv` or `data/` directories (they are
  git-ignored and are not copied), so run `uv sync` — and `make up` if the task
  needs Redpanda — inside the worktree before running anything.
- Never commit to `main`. Never push directly to `main`. `main` changes only by
  merging a reviewed pull request.
- When the work is done and committed, push the branch and open a pull request
  into `main`; the pull request is the only path into `main`.
- Write commit messages with a concise imperative subject line, for example
  "Add the statistical-arbitrage screener". When a body is needed to explain a
  plan or rationale, write it in full words with no abbreviations.
- Keep commits small and single-purpose: one logical change per commit.
- After the pull request is merged and the worktree is clean, remove it:

      git worktree remove ../MarketForge-<task-slug>

  If the directory was deleted by hand, run `git worktree prune` to clear the
  stale record.

---

## 5. Repository layout

| Path | Purpose |
| --- | --- |
| `plan.md` | The phased plan, milestones, and acceptance criteria. |
| `README.md` | Project status, architecture, and quickstart. |
| `agents.md` | This operating manual for coding agents. |
| `docs/thoughts/` | The decision log — the "why" behind each choice. |
| `src/marketforge/` | The Python package (source layout). |
| `src/marketforge/cli.py` | The command-line interface (Typer). |
| `src/marketforge/config.py` | Frozen configuration dataclasses. |
| `src/marketforge/schemas.py` | The production data schemas (stable contract). |
| `src/marketforge/calendar.py` | The trading calendar. |
| `src/marketforge/rng.py` | Seeded random-number generation. |
| `src/marketforge/verify.py` | Manifest verification. |
| `src/marketforge/synthetic/` | The Phase 0 generator: `bars`, `events`, `export`, `generate`, `manifest`, `universe`. |
| `tests/` | The pytest suite; one test module per source module. |
| `.github/workflows/ci.yml` | Continuous integration. |
| `Makefile` | Development targets. |
| `pyproject.toml` | Project metadata, dependencies, and tool configuration. |
| `uv.lock` | Pinned dependency resolution. |

---

## 6. Environment and toolchain

- **Python 3.12**, managed with `uv`. Do not change the Python version casually;
  the lock file and continuous integration pin it.
- **Target platform** is Linux — Windows Subsystem for Linux 2 (Ubuntu 24.04) or
  the devcontainer. Docker is available for Redpanda.
- **Dataframes:** Polars (primary) and Pandas.
- **Columnar and warehouse:** PyArrow and DuckDB (embedded, in-process — do not
  run DuckDB as a long-lived container; see `docker-compose.yml` for why).
- **Lakehouse:** Parquet and Delta Lake.
- **Streaming:** Redpanda (a Kafka-compatible broker).
- **Orchestration:** Dagster.
- **Versioning and lineage:** DVC (Data Version Control) plus git, with Delta
  time-travel.
- **Validation:** pandera plus custom anomaly checks.
- **Lint and format:** ruff. **Type checking:** mypy. **Tests:** pytest.
  Pre-commit hooks are configured.

---

## 7. Commands

The Makefile wraps the common development loop. Run these from the project root.

| Command | What it does |
| --- | --- |
| `make sync` | Install the pinned environment (Python 3.12 and dependencies). |
| `make test` | Run the test suite. |
| `make lint` | Run ruff checks and the format check. |
| `make type` | Run mypy over `src` and `tests`. |
| `make fmt` | Auto-format and auto-fix. |
| `make ci` | The full gate: lint, format check, type check, and tests. |
| `make up` / `make down` | Start / stop the local services (Redpanda). |
| `make gen` | Generate synthetic data (default seed 42). |
| `make verify` | Verify a dataset against its ground-truth manifest. |
| `make schema` | Print the production schemas. |
| `make duckdb` | Open an interactive SQL shell over the generated data. |
| `make clean` | Remove generated data and caches. |

Run `make ci` before you consider any change complete. For anything the Makefile
does not wrap, use `uv run <command>`.

---

## 8. Code conventions

- Python 3.12. Every module begins with `from __future__ import annotations`.
- Type annotations everywhere; mypy must pass with `check_untyped_defs` and
  `warn_unused_ignores`. Do not add a `# type: ignore` you cannot justify.
- ruff is the formatter and linter. Line length is 100. The enabled lint rules
  are `E`, `F`, `I`, `UP`, `B`, and `SIM`. Run `make fmt` and `make lint` before
  committing.
- Every module and public function has a concise docstring in the imperative
  mood. Configuration is expressed as frozen dataclasses (`config.py`).
- Keep modules small and single-purpose, mirroring the existing layout under
  `synthetic/` (bars, events, export, generate, manifest, universe).
- Prefer the standard library and the locked dependencies. Do not add a
  dependency without a stated reason, and always update `uv.lock`.

---

## 9. Data contracts and determinism

- The production schemas in `src/marketforge/schemas.py` are the shared contract
  between the generator and future real-data ingestion. Keep them stable.
- The generator exports to the same schemas real data will use, so real sources
  can be dropped in later without schema churn.
- Determinism is a data property, not an implementation detail: the same seed
  produces byte-identical reference, bars, and manifest files, including the JSON
  manifest.
- The manifest is ground truth. Every injected event — split, dividend,
  delisting, symbol change, restatement, data gap, bad tick, and late or
  backfilled record — is recorded so later phases can prove reconstruction
  against a known answer.

---

## 10. Testing

- pytest, with shared fixtures in `tests/conftest.py` (for example
  `small_config`, a small fast universe).
- One test module per source module, named `test_<module>.py`.
- Test determinism explicitly, as `tests/test_determinism.py` does: byte-identical
  output across runs and directories.
- Tests must be fast and deterministic. No network, no wall clock, no reliance on
  ordering that is not guaranteed.
- Add or update tests for every behavior change. A change that ships without a
  test does not meet the bar.

---

## 11. Phases and roadmap context

| Phase | What it builds | Status |
| --- | --- | --- |
| 0 | Foundations: a reproducible, seeded, testable synthetic data generator with ground truth. | Current |
| 1 | The market-data lakehouse: versioned, point-in-time-correct storage with quality gates and orchestration. | Planned |
| 2 | The historical reconstructor: survivorship-bias-free universes and corporate-actions handling, proven against ground truth. | Planned |
| 3 | Tick processing and the feature store: tick-scale features with no lookahead, plus the crypto universe. | Planned |
| 4 | The statistical-arbitrage screener: the usable tool that ranks less-crowded candidates and backtests honestly. | Planned |
| 5 | Paper trading: the closed loop from opportunity list to signal to paper order to tracked profit and loss, with a journaled gap. | Planned |

Each phase's acceptance criteria in `plan.md` are its definition of done. Do not
build a later phase's machinery before its phase unless the task says so.

---

## 12. Guardrails and honesty

- **Paper trade first**, for months, with toy money. The real asset is the
  engineering and the honest backtest-to-live gap, not profit and loss.
- **Correctness before scale.** Learn point-in-time, survivorship-bias, and
  corporate-actions handling on small synthetic data before scaling up.
- **Data as a product.** Every dataset has a schema, a version, lineage, and a
  quality gate.
- **Reproducible everywhere.** Same seed, same data, same result, in continuous
  integration.
- **Report uncertainty honestly.** For example, the crowdedness ranking is a
  proxy, not a census; say so rather than overstating precision.

---

## 13. Definition of done

A change is finished only when all of the following hold:

- It lives in its own worktree on a branch, not on `main`.
- Its branch is pushed and a pull request into `main` is open for it.
- It is covered by tests, and the full gate (`make ci`) passes.
- Any plan or design text it introduces is written in full words with no
  abbreviations.
- It respects the data-schema contract and the determinism guarantees.
- It meets the acceptance criteria of the milestone it belongs to, and
  `README.md` or `plan.md` is updated if the change alters project state.
