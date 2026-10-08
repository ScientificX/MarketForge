# 05 — Money & trading

Recorded because the user explicitly asked whether the project could "eventually
earn money". The honest answer drives the plan.

## The three paths, ranked by expected value

1. **The tool (highest EV).** The project's real value is the usable tool itself —
   an end-to-end stat-arb screener for less-crowded markets — and the engineering
   that makes its output trustworthy. That is more durable than any single
   retail-trading outcome.
2. **Trading your own capital (low probability).** Naive retail stat-arb on free
   large-cap data looks profitable in backtest and dies live. Killers: crowding
   (the same pairs everyone else trades), transaction costs + slippage,
   survivorship bias (trading names/prices that weren't available), overfitting
   to a few pairs, capacity/adverse selection.
3. **Selling data/signals (low probability + regulatory).** Crowded; can cross
   into investment-advice territory.

## The answer: go less crowded

The killers in path 2 are exactly what the tool is built to counter:

- **Crowding** → the screener ranks candidates by crowdedness and prefers
  less-covered equities + crypto.
- **Survivorship bias** → the reconstructor (Phase 2) rebuilds delisted names and
  point-in-time membership before any backtest.
- **Costs/slippage/capacity** → the backtester (Phase 4) models them explicitly
  and flags thin names where they dominate.

This is not a claim that the tool will "earn money". It is a claim that a small,
careful player's best shot is in less-crowded markets with bias-corrected data —
and that building that honestly is the valuable work.

## The stat-arb layer (the tool's core)

Purpose = **find real, less-crowded stat-arb opportunities**. Built as: universe
selection + crowdedness ranking → cointegration screener → backtest with
realistic costs + walk-forward + delisted names → honest report.

The deepest lesson still holds: building the reconstructor properly will likely
*destroy* most "profitable" backtests — and demonstrating that is the single most
valuable signal of real engineering depth.

## Trading guardrail

> Paper trade first, for months. Only ever run **toy money you can afford to
> lose**. The real asset is the **engineering + honest backtest-to-live gap**,
> not the P&L.

A project that says "I built the pipeline, corrected survivorship bias,
paper-traded 3 months, and here's where my backtest was wrong" beats one that
says "I made 8%."
