# 06 — The repositioning: a usable tool for less-crowded markets

Recorded because the project's framing changed materially: from "a data platform
that demonstrates engineering" to "a **real, usable tool** for finding
statistical-arbitrage opportunities in **less-crowded markets**."

## What changed

| Before | After |
| --- | --- |
| A market-data platform, built to demonstrate data-engineering capability. | A stat-arb tool, built to be used; the platform is its trust substrate. |
| Stat-arb = a validation layer that "proves the lakehouse earns its keep". | Stat-arb = the point; the lakehouse earns its keep by making the screener trustworthy. |
| Universe = generic equity synthetic data. | Universe = less-covered equities + crypto, with a crowdedness axis. |

## What "less crowded" means

Statistical arbitrage is a crowded trade in large-cap liquid names: many funds
run the same cointegrated pairs, so the edge is arbed away. "Less crowded" means
markets with thinner systematic competition:

- **Less-covered equities** — small/mid caps, cross-listings, delisted-adjacent
  and regional names with few analysts and little institutional stat-arb.
- **Crypto (complement)** — 24/7, retail-dominated, many pair relationships
  (perp↔spot, cross-exchange, basket/rotation), free tick data.

"Crowdedness" is operationalised as a first-class signal in the screener (Phase
4): rank candidates by capacity/liquidity, analyst coverage, index correlation,
and turnover/flow proxies, and prefer the names everyone else ignores.

## What did not change

- **The phased, learn-then-scale structure.** The plan still walks Phase 0 → 5
  with explicit acceptance criteria per milestone; the tool is not a one-shot
  black box but a sequence of understandable, testable steps.
- **Correctness first, honesty over P&L.** Synthetic ground truth, PIT
  reconstruction, and the backtest-to-live gap remain the load-bearing ideas.
- **The toy-money guardrail.** Paper-trade first, only money you can afford to
  lose; the edge is the honest gap, not the P&L.
