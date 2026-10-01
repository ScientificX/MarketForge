# MarketForge

An **equity market-data platform (lakehouse)**, built end-to-end to demonstrate
data-engineering capability: a deterministic synthetic-data generator
with ground truth, a versioned + point-in-time lakehouse, a historical
reconstructor, a feature store, a statistical-arbitrage research workflow, and
paper / "toy money" live trading.

See [`plan.md`](plan.md) for the full plan and [`docs/thoughts/`](docs/thoughts/)
for the reasoning behind it.

## Architecture

```mermaid
flowchart TD
    A[Synthetic Generator (equity)] --> I[INGEST normalizers]
    R[Real sources (later)] --> I
    I --> L[LAKEHOUSE<br/>Parquet + Delta, versioned, PIT]
    L --> RC[RECONSTRUCTOR<br/>corp actions, survivor-free]
    L --> FS[FEATURE STORE<br/>tick-derived, PIT joins]
    L --> SV[SERVING<br/>DuckDB / SQL]
    RC --> SA[STAT-ARB RESEARCH]
    FS --> SA
    SA --> PT[PAPER / LIVE TRADING]
```

## Phase 0 (this scaffold)

- **M0.1** — repo, `pyproject.toml`, devcontainer, `docker-compose.yml`
  (Redpanda + DuckDB), CI (ruff + mypy + pytest), `Makefile`, README.
- **M0.2** — a seeded, byte-deterministic synthetic equity data generator with a
  ground-truth manifest and production Parquet schemas.

## Quickstart

```bash
# 1. Install Python 3.12 + dependencies (uv)
uv sync

# 2. Start local services (Redpanda broker + DuckDB shell)
make up

# 3. Generate synthetic data (deterministic: same seed -> identical bytes)
make gen

# 4. Verify the generated data against its ground-truth manifest
make verify

# 5. Run the full CI gate (lint + format + type + tests)
make ci
```

## Data model

| Dataset | Contents |
| --- | --- |
| `reference.parquet` | symbol, name, sector, listing date, currency, exchange |
| `bars.parquet` | daily OHLCV (raw, as-traded) + nullable `as_of` delivery time |
| `manifest.parquet` / `manifest.json` | ground-truth log of every injected event |

The generator injects and records these events: splits, dividends, delistings,
symbol changes, restatements, data gaps, bad ticks, and late/backfilled records —
so later phases have provable ground truth to reconstruct against.

## Environment

- **WSL2 + Ubuntu 24.04** (or the devcontainer), Docker inside.
- Python 3.12 via `uv`; single node is sufficient.
