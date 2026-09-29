# 05 — Money & trading

Recorded because the user explicitly asked whether the project could "eventually
earn money". The honest answer drives the plan.

## The three paths, ranked by expected value

1. **The portfolio (highest EV).** The project is a portfolio, not a product. Its
   real value is the demonstrated engineering — an end-to-end data platform —
   which is more durable than any retail-trading outcome.
2. **Trading your own capital (low probability).** Naive retail stat-arb on free
   data looks profitable in backtest and dies live. Killers: transaction costs +
   slippage, survivorship bias (trading names/prices that weren't available),
   overfitting to a few pairs, capacity/adverse selection.
3. **Selling data/signals (low probability + regulatory).** Crowded; can cross
   into investment-advice territory.

## The stat-arb layer

Purpose = **prove the lakehouse earns its keep** (a data platform is only
credible when a research workflow consumes it). Built as: universe/data load from
the lakehouse → cointegration screener → backtest with realistic costs +
walk-forward + delisted names → honest report.

The deepest lesson: building the reconstructor (#3) properly will likely *destroy*
most "profitable" backtests — and demonstrating that is the single most valuable
signal of real engineering depth.

## Trading guardrail

> Paper trade first, for months. Only ever run **toy money you can afford to
> lose**. The real asset is the **engineering + honest backtest-to-live gap**,
> not the P&L.

A project that says "I built the pipeline, corrected survivorship bias,
paper-traded 3 months, and here's where my backtest was wrong" beats one that
says "I made 8%."
