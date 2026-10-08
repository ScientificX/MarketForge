# MarketForge — Project Plan

## Mission

Build a **real, usable tool for finding statistical-arbitrage opportunities in
less crowded markets**, and build the market-data platform it needs to be
trustworthy rather than merely plausible.

The tool is the point. The lakehouse, reconstructor, and feature store are the
**trust substrate**: they exist so that every opportunity the tool surfaces is
survivorship-bias-free, point-in-time-correct, and honestly backtested. The
project still learns the hard data-engineering problems the honest way — on
small synthetic data with provable ground truth before scaling — but the measure
of success is a usable tool, not a portfolio demo.

## The thesis: why "less crowded"

Statistical arbitrage on large-cap, liquid names is **crowded**. Many funds run
the same cointegrated pairs, so the edge is arbed away and what looks profitable
in a backtest dies live (transaction costs, slippage, capacity, adverse
selection). MarketForge targets markets where that competition is thinner:

- **Less-covered equities** — small/mid caps, cross-listings, delisted-adjacent
  and regional names with thin analyst and institutional coverage.
- **Crypto, as a complement** — 24/7, retail-dominated, many pair relationships
  (perp↔spot, cross-exchange, basket/rotation), and free tick data.

"Crowdedness" is therefore a **first-class, measurable signal**: the screener
ranks candidates by how much systematic money is already trading them (liquidity
and capacity, analyst coverage, index correlation, turnover/flow proxies) and
prefers the names everyone else ignores. Less crowded is where the edge survives
long enough to be real.

## Repository

- Location: `~/development/MarketForge`
- Environment: **WSL2 + Ubuntu 24.04**, Docker inside, VS Code (Remote-WSL /
  devcontainer). Single-node is sufficient.
- Python 3.12 via `uv`, pinned `pyproject.toml`, pytest + pre-commit + GitHub Actions.

## Guiding principles

1. **Less crowded is the edge.** Universe selection and crowdedness ranking are
   as important as the signal; a crowded pair is a dead edge.
2. **Correctness before scale.** Learn PIT / survivorship-bias / corporate
   actions on small synthetic data, then scale.
3. **Data as a product.** Every dataset has a schema, a version, lineage, and a
   quality gate.
4. **Honesty over P&L.** The real asset is the measured backtest-to-live gap and
   an honest separation of real edge from artifact, not the P&L.
5. **Reproducible everywhere.** Same seed → same data → same result, in CI.

## Decisions log (the "why")

| Decision | Rationale |
| --- | --- |
| A **usable tool**, not a portfolio demo | The output is a ranked, honest list of stat-arb opportunities in less-crowded markets. The data platform is the trust substrate that makes the list real, not the headline. |
| Target **less-crowded markets** | Large-cap pairs are crowded; their edge is arbed away. Less-covered equities + crypto are where a small, careful player still has room. |
| **Equity spine + crypto complement** | Equities force corporate actions, delistings and survivorship bias — the exact hard problems the reconstructor must prove. Crypto is added later (Phase 3/4) as a second, structurally less-crowded universe with free tick data. |
| Synthetic data first, real data later | Synthetic gives provable ground truth (inject a split/delisting/restatement and verify exact reconstruction); real data adds messy-reality scar tissue later, at the scale/research stage. |
| **Equity-style** synthetic universe | Equities force corporate actions, delistings, symbol changes and survivorship bias — the exact hard problems Phase 2 must demonstrate. Crypto would sidestep them. |
| Phase order **1 → 3 → 2** | Foundation (lakehouse) → correctness depth (reconstructor) → scale/streaming (tick + feature store). Learn correctness while data is small, then scale. |
| Linux (WSL2) | Spark/Delta/Kafka are painful on Windows-native; WSL2 gives a real Linux kernel with the lowest friction. |
| Toy-money live trading | Paper-trade for months first; the deliverable is the *engineering + honest gap*, not P&L. Only money you can afford to lose. |

## Toolchain (locked)

| Concern | Choice |
| --- | --- |
| Dataframes | Polars (primary) + Pandas |
| Columnar / warehouse | PyArrow + DuckDB |
| Lakehouse | Parquet + Delta Lake (delta-spark) |
| Scale | PySpark (local) / Dask |
| Streaming | Redpanda (Kafka-compatible) |
| Orchestration | Dagster |
| Versioning / lineage | DVC + git, Delta time-travel |
| Validation | pandera + custom anomaly checks |
| Trading (toy) | Paper account first (Alpaca paper / exchange sandbox) |

## Architecture

```
        UNIVERSE SELECTION
   (less-covered equities + crypto,
        crowdedness ranking)
                │
                ▼
  Synthetic Generator (equity) ─┐
  Real sources (later) ──────────┤
                                 ▼
                        INGEST (normalizers)
                                 ▼
                  LAKEHOUSE (Parquet + Delta, versioned, PIT)
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
   RECONSTRUCTOR           FEATURE STORE           SERVING (DuckDB/SQL)
   (corp actions,          (tick-derived,          (catalog + query CLI)
    survivor-free)          PIT joins)
         │                       │
         └───────────┬───────────┘
                     ▼
         STAT-ARB SCREENER (the tool)
   (universe + crowdedness → cointegration → walk-forward backtest → honest report)
                     ▼
         PAPER / LIVE TRADING (signal service → broker → P&L journal)
```

The screener is the product; everything above it exists to make its output
trustworthy.

## Data

**Synthetic equity generator (Phase 0):** a deterministic, seeded generator
producing, for a configurable universe of equities:

- daily bars (OHLCV) + a reference table (name, sector, listing dates);
- a **crowdedness axis**: the universe spans liquid mega-caps (crowded) down to
  thinly-covered small/mid caps (less crowded), so the tool can be tested on the
  very distinction it exploits;
- **injectable events**: splits, dividends, delistings, symbol changes,
  restatements, data gaps, bad ticks, late/backfilled records;
- a **ground-truth manifest** recording every event and its date.

The generator exports to the **same Parquet schemas real data will use**, so
real sources can be dropped in later without schema churn.

**Crypto universe (Phase 3/4):** a second, structurally less-crowded universe —
perp↔spot, cross-exchange and basket relationships — from free/tiered APIs with
tick data. Its purpose is to widen the opportunity set, not to replace the
equity spine.

**Real data (later, Phase 3/4):** equities via a free/tiered API. The
point-in-time/survivorship-bias logic is source-agnostic.

---

## Phase 0 — Foundations

**M0.1 — Environment + repo scaffold**
- Deliverables: repo, `pyproject.toml`, devcontainer, `docker-compose.yml`,
  CI (lint/type/test), `Makefile`, README with the architecture.
- Acceptance: `make test` and `make ci` pass from a clean WSL2 checkout; `make up`
  starts Redpanda/DuckDB.

**M0.2 — Synthetic equity market-data generator**
- Deliverables: seeded generator + ground-truth manifest + injected events +
  Parquet export, with a **crowdedness axis** (mega-cap → thin small/mid-cap).
- Acceptance: same seed → byte-identical output; every injected event is
  verifiable against the manifest; output uses the production schemas.

---

## Phase 1 — Market-data lakehouse

**M1.1 — Ingestion + schema contracts + dataset registry**
- Unified schemas (bars, ticks, quotes, reference, events); a registry
  (`name → schema, partitioning, PIT, lineage`).

**M1.2 — Storage layer**
- Parquet + Delta, partitioned (symbol/date), versioned, time-travel.

**M1.3 — Quality gates**
- pandera validation + anomaly detection (spikes, stale, gaps, cross-source
  reconciliation). Bad data is blocked, not just logged.

**M1.4 — Orchestration**
- Dagster pipelines: idempotent, backfillable, retries.

**M1.5 — Serving**
- DuckDB-backed catalog + SQL/query API + CLI.

**Phase 1 acceptance:** a researcher gets any clean, versioned, PIT dataset via
one API call, with a failed-quality record provably blocked.

---

## Phase 2 — Historical reconstructor

**M2.1 — Corporate-actions engine** (splits, dividends → adjustment factors)
**M2.2 — Survivorship-bias-free universes** (delisted names included; PIT membership)
**M2.3 — Point-in-time prices** (as-of-correct; restatements where applicable)
**M2.4 — Backfill + reconciliation** (re-run on source correction; diff vs synthetic ground truth)

**Phase 2 acceptance:** for a corpus with known injected splits/delistings/
restatements, the reconstructed dataset matches ground truth **exactly** and the
delisted names are present. This is the hardest, most differentiating milestone —
without it, every "opportunity" the tool finds is suspect.

---

## Phase 3 — Tick processing + feature store

**M3.1 — Tick/LOB ingest** (synthetic tick generator first, then real data)
**M3.2 — Batch at scale** (PySpark/Dask → bars + features: VWAP, rolling vol, order-flow imbalance)
**M3.3 — Streaming** (Redpanda → realtime features)
**M3.4 — Feature store** (PIT joins, no leakage, lineage, backfill)

**Phase 3 acceptance:** a feature is recomputed for any date range *as it would
have been known then*, with a test proving no lookahead leakage, at tick scale.
This phase also onboards the **crypto universe** (perp↔spot, cross-exchange).

---

## Phase 4 — Statistical-arbitrage screener (the point)

**M4.1 — Universe selection + crowdedness ranking**
- Less-covered equities + crypto; rank candidates by capacity/liquidity, analyst
  coverage, index correlation, and turnover/flow proxies. Less crowded first.

**M4.2 — Cointegration screener** (Engle-Granger) + spread construction
**M4.3 — Backtester** (realistic costs/slippage, walk-forward CV, delisted names included)
**M4.4 — Honest results** (real edge vs survivorship-bias/overfit artifact, per-candidate crowdedness flag)

**Phase 4 acceptance:** a reproducible walk-forward backtest over a less-crowded
universe, with a report that explicitly separates real edge from artifact and
flags each candidate's crowdedness. This is the moment the project becomes a
usable tool.

---

## Phase 5 — Paper / live trading (toy money)

**M5.1 — Paper-trading engine + signal service** (consumes M4's ranked list, simulates fills)
**M5.2 — Broker integration** (paper account first — Alpaca paper / exchange sandbox)
**M5.3 — Live monitoring** (P&L tracking, risk limits, kill-switch, alerting)
**M5.4 — Journal** (the backtest-vs-live gap, quantified)

**Phase 5 acceptance:** an end-to-end loop from opportunity list → signal → paper
order → tracked P&L, with a written post-mortem comparing paper P&L to the backtest.

## Trading guardrail

> Paper trade first, for months. Only ever run **toy money you can afford to
> lose**. The real asset is the **engineering + honest backtest-to-live
> gap** — not the P&L. A project that says "I built the pipeline, backtested
> with survivorship-bias correction, paper-traded for 3 months, and here's where
> my backtest was wrong" beats one that says "I made 8%."

## Phase outcomes

| Phase | What it demonstrates |
| --- | --- |
| 0 | Reproducible, seeded, testable data. |
| 1 | A versioned, PIT-correct lakehouse with quality gates and orchestration. |
| 2 | Survivorship bias and corporate actions handled end-to-end — with proof. |
| 3 | Tick data processed in PySpark with PIT features and no leakage. |
| 4 | The usable tool: a less-crowded universe screened, ranked, and honestly backtested. |
| 5 | A closed loop from opportunity list to paper trading with a journaled gap. |

## Risks

- **Scope creep** — each phase's acceptance criteria is the definition of done; no gold-plating.
- **Overfitting to synthetic data** — mitigated by introducing real data at Phase 3/4.
- **Crowdedness is hard to measure** — the ranking is a proxy (coverage, capacity, correlation, turnover), not a census; report its uncertainty honestly.
- **Alpha-hunting distraction** — the edge is the honest gap, not the P&L.

## Total scope

~**7–9 months**. Phase 0–2 ≈ 3 months; Phase 3 ≈ 1.5–2; Phase 4 ≈ 1.5–2;
Phase 5 ≈ 1–2.

## Next step

Phase 1 (ingestion + schema contracts + dataset registry), and extend the
Phase 0 synthetic universe with the **crowdedness axis** so Phase 4 can be tested
on the very distinction the tool exploits.
