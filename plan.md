# MarketForge — Project Plan

## Mission

Build an **equity market-data platform (lakehouse)** end-to-end: prove its
correctness against **synthetic ground truth**, run an honest **statistical
arbitrage research workflow** on top of it, and close the loop with
**paper / "toy money" live trading** — a portfolio that demonstrates
end-to-end data-engineering capability.

## Repository

- Location: `~/development/MarketForge`
- Environment: **WSL2 + Ubuntu 24.04**, Docker inside, VS Code (Remote-WSL /
  devcontainer). Single-node is sufficient.
- Python 3.12 via `uv`, pinned `pyproject.toml`, pytest + pre-commit + GitHub Actions.

## Guiding principles

1. **Correctness before scale.** Learn PIT / survivorship-bias / corporate
   actions on small synthetic data, then scale.
2. **Data as a product.** Every dataset has a schema, a version, lineage, and a
   quality gate.
3. **Honesty over P&L.** The real asset is the measured backtest-to-live
   gap, not the P&L.
4. **Reproducible everywhere.** Same seed → same data → same result, in CI.

## Decisions log (the "why")

| Decision | Rationale |
| --- | --- |
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
        STAT-ARB RESEARCH (screener → backtest → honest report)
                    ▼
        PAPER / LIVE TRADING (signal service → broker → P&L journal)
```

Everything from Phase 4 onward consumes the platform, which is what makes the
platform credible.

## Data

**Synthetic equity generator (Phase 0):** a deterministic, seeded generator
producing, for a configurable universe of equities:

- daily bars (OHLCV) + a reference table (name, sector, listing dates);
- **injectable events**: splits, dividends, delistings, symbol changes,
  restatements, data gaps, bad ticks, late/backfilled records;
- a **ground-truth manifest** recording every event and its date.

The generator exports to the **same Parquet schemas real data will use**, so
real sources can be dropped in later without schema churn.

**Real data (later, Phase 3/4):** equities via a free/tiered API (or crypto as a
fallback for scale). The point-in-time/survivorship-bias logic is source-agnostic.

---

## Phase 0 — Foundations

**M0.1 — Environment + repo scaffold**
- Deliverables: repo, `pyproject.toml`, devcontainer, `docker-compose.yml`,
  CI (lint/type/test), `Makefile`, README with the architecture.
- Acceptance: `make test` and `make ci` pass from a clean WSL2 checkout; `make up`
  starts Redpanda/DuckDB.

**M0.2 — Synthetic equity market-data generator**
- Deliverables: seeded generator + ground-truth manifest + injected events +
  Parquet export.
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
delisted names are present. This is the hardest, most differentiating milestone.

## Phase 3 — Tick processing + feature store

**M3.1 — Tick/LOB ingest** (synthetic tick generator first, then real data)
**M3.2 — Batch at scale** (PySpark/Dask → bars + features: VWAP, rolling vol, order-flow imbalance)
**M3.3 — Streaming** (Redpanda → realtime features)
**M3.4 — Feature store** (PIT joins, no leakage, lineage, backfill)

**Phase 3 acceptance:** a feature is recomputed for any date range *as it would
have been known then*, with a test proving no lookahead leakage, at tick scale.

---

## Phase 4 — Statistical arbitrage research system

**M4.1 — Universe + data load** (from the lakehouse/feature store — the proof)
**M4.2 — Cointegration screener** (Engle-Granger) + spread construction
**M4.3 — Backtester** (realistic costs/slippage, walk-forward CV, delisted names included)
**M4.4 — Honest results** (real edge vs survivorship-bias/overfit artifact)

**Phase 4 acceptance:** a reproducible walk-forward backtest with a report that
explicitly separates real edge from artifact.

---

## Phase 5 — Paper / live trading (toy money)

**M5.1 — Paper-trading engine + signal service** (consumes M4 signals, simulates fills)
**M5.2 — Broker integration** (paper account first — Alpaca paper / exchange sandbox)
**M5.3 — Live monitoring** (P&L tracking, risk limits, kill-switch, alerting)
**M5.4 — Journal** (the backtest-vs-live gap, quantified)

**Phase 5 acceptance:** an end-to-end loop from dataset → signal → paper order →
tracked P&L, with a written post-mortem comparing paper P&L to the backtest.

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
| 4 | A stat-arb workflow with an honestly reported backtest-to-live gap. |
| 5 | A closed loop from dataset to paper trading with a journaled gap. |

## Risks

- **Scope creep** — each phase's acceptance criteria is the definition of done; no gold-plating.
- **Overfitting to synthetic data** — mitigated by introducing real data at Phase 3/4.
- **Alpha-hunting distraction** — trading is the last layer, gated behind correctness.

## Total scope

~**7–9 months**. Phase 0–2 ≈ 3 months; Phase 3 ≈ 1.5–2; Phase 4 ≈ 1.5–2;
Phase 5 ≈ 1–2.

## Next step

Scaffold **Phase 0**: repo, devcontainer, CI, and the synthetic equity data
generator with ground-truth manifest.
