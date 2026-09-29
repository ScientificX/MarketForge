# 01 — Skills & competencies

## Skills to demonstrate

A data-engineering portfolio should show:

- building **algorithms, processes and datasets** that turn raw data into revenue
- **optimising quant code and algorithms**, analysing data, and developing **modelling features**
- writing, testing, and deploying Python code that **defines data orchestration**
- using **data-manipulation libraries** (Pandas, Polars, PySpark)
- working in a **Linux** environment
- working closely with researchers to accelerate their work

## What the project rewards (5 competencies)

1. **Vectorized data manipulation** (Pandas → Polars → PySpark, by scale)
2. **Algorithm design & optimization** (profile, cache, vectorize)
3. **Data orchestration** (scheduled, repeatable, versioned pipelines)
4. **Modelling features for research** (raw data → signals)
5. **Engineering in a quant shop** (Linux, tests, reproducible envs)

## The honest caveat (recorded because it drove the whole pivot)

The existing Scala `risk-traceability-compiler` project builds *pricing/risk*
skills but not the *data* skills above — wrong language, no data manipulation,
no orchestration, no scale. Continuing its Stages 4–9 would not build the
data-engineering profile. Hence: a **new Python project**.

## What "advanced + months" means

Systems, not scripts: multiple subsystems, real data at scale, a hard
correctness or performance bar, and a measurable outcome. This shaped the final
multi-phase plan (foundation → correctness → scale → research → trading).

## How the competencies map to MarketForge phases

| Competency | Phase |
| --- | --- |
| Vectorized data manipulation | 1, 3 (Polars/PySpark) |
| Algorithm design & optimization | 2, 3 (correctness, scale) |
| Data orchestration | 1 (Dagster) |
| Modelling features | 3 (feature store) |
| Engineering in a quant shop | 0 (env, CI, reproducibility) |
