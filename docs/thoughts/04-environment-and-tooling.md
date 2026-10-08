# 04 — Environment & tooling

## Environment decision

- **WSL2 + Ubuntu 24.04**, Docker inside, VS Code (Remote-WSL / devcontainer).
- Single-node is sufficient (PySpark local mode, Delta local, one Redpanda broker).
- A cheap cloud VM is a later option for long-running backfills/jobs.

**Rationale:** PySpark/Delta/Kafka are the
pain points on Windows-native. WSL2 gives a real Linux kernel + shell with the
lowest friction on a Windows host.

## Toolchain, with the "why"

| Tool | Why |
| --- | --- |
| uv (Python 3.12) | fast, reproducible, modern; pin in `pyproject.toml` |
| Polars (primary) + Pandas | Polars = modern vectorized default; Pandas for quick exploration |
| PyArrow + DuckDB | columnar + single-process SQL engine for the serving layer |
| Parquet + Delta Lake | versioning, time-travel, point-in-time |
| PySpark (local) / Dask | tick-scale batch (Phase 3) |
| Redpanda | Kafka-compatible, single binary, less ops than Kafka+Zookeeper |
| Dagster | Python-native orchestration, first-class backfill/idempotency |
| DVC + git, Delta time-travel | lineage + reproducibility |
| pandera + anomaly checks | quality gates (Phase 1) |
| pytest, pre-commit, GitHub Actions | tests + CI |
| Paper broker (Alpaca paper / exchange sandbox) | toy trading (Phase 5) |
| Free/tiered data APIs (equities + crypto) | real data in Phase 3/4; crypto perp↔spot / cross-exchange feeds |

## Discipline

Exploration in Jupyter; production as modules + tests + a CLI. "I built a data
platform" reads differently from "I analysed data."

## Less-crowded data sources

The tool's edge is the universe, not just the model. Equity sources cover the
thinly-covered names (small/mid caps, cross-listings, delisted history); crypto
sources (perp↔spot, cross-exchange) are 24/7 and retail-dominated, so the pairs
are less picked over. Crowdedness proxies (capacity/liquidity, analyst coverage,
index correlation, turnover) are computed in Phase 4, not fetched — so the tool
stays source-agnostic.
