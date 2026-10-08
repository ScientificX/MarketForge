# 02 — Idea exploration

Three rounds of ideation, ending in the data-first selection. Recorded so the
rejected options and the pivot are not lost.

## Round 1 — general project ideas (6)

(After "no, completely different project ideas.")

1. Market-data pipeline + feature store
2. Order-book microstructure engine
3. Vectorized derivatives pricing + implied-vol
4. P&L attribution / risk engine (Python port of the Scala concepts)
5. Statistical arbitrage research system
6. Streaming data pipeline

Leaning at the time: #5 (broadest), #2 (most "optimize quant code"),
#4 (reuses domain).

## Round 2 — advanced, multi-month (A–F)

(After "even more advanced ones that would take months.")

A. Options volatility & market-making research platform
B. HFT order-book replay & market-making engine
C. Systematic trading research platform ("mini quant fund")
D. Multi-curve derivatives pricing & risk engine
E. Distributed research infrastructure / compute platform
F. Alternative-data + NLP signal research pipeline

Leaning at the time: A or B (both options-market-making adjacent), C for breadth.

## The pivot — data-first (Round 3)

User: "what about the data aspect — I don't see it emphasized."

Reframe: the project is **data-first** ("creating datasets", "analyse datasets",
"define data orchestration"). The deliverable is a *dataset* or *data platform*,
not a trading strategy. This produced six data-first projects:

1. Market-data platform / lakehouse ⭐
2. Tick/LOB processing + feature store
3. Historical-data reconstructor / backfill ⭐ (hardest correctness)
4. Alternative-data processing pipeline
5. Data-quality & anomaly-detection framework
6. Research data-orchestration platform ("dataset factory")

## Selection & deferral

- **Chosen:** #1 (lakehouse) → #3 (reconstructor) → #2 (tick + feature store).
- **Deferred (not rejected):** #4 (alt-data/NLP), #5 (standalone quality),
  #6 (dataset factory) — possible future phases; #5's ideas folded into #1's
  quality gates.

## Why the strategy-flavoured ideas were set aside

A–D (options/HFT/rates) are strong *quant* projects but lead with pricing and
performance rather than data. They remain valuable and could be layered on later
(e.g. an options-vol layer on top of MarketForge), but they are not the spine of
a data-engineering portfolio. E and F are data projects but lower signal-to-effort than the
lakehouse spine.

## Round 4 — the repositioning pivot

(After "make the project a real, usable tool for finding statistical arbitrage
in less crowded markets.")

The data-first selection stood, but the *framing* changed: from "a data platform
that demonstrates engineering" to "a **usable tool** for finding stat-arb
opportunities in **less-crowded markets**." Two ideas came in:

1. **The tool is the point.** The lakehouse / reconstructor / feature store
   become the trust substrate — the reason the tool's opportunities are real —
   rather than the headline deliverable.
2. **Less crowded is the edge.** Large-cap pairs are crowded and their edge is
   arbed away; the tool targets less-covered equities (small/mid caps,
   cross-listings) plus crypto (perp↔spot, cross-exchange) as a complement.

This did not resurrect the earlier "strategy-first" idea. The strategy layer is
still a *consumer* of the platform — but now it is the consumer the whole
platform exists to serve. See [06](06-refocus-usable-tool.md).
