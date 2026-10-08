# Thoughts & decision log

This directory records the *reasoning* behind the MarketForge plan: the skills
analysis, the project ideas explored and rejected, the decision paths walked,
and the repositioning that made MarketForge a usable tool rather than a
portfolio demo. [`../plan.md`](../plan.md) is the **what**; these docs are the
**why**.

## How to read

- [01 — Skills & competencies](01-role-analysis.md) — the competencies the
  project is built to demonstrate.
- [02 — Idea exploration](02-idea-exploration.md) — the three rounds of project
  ideas, the data-first pivot, and what was rejected/deferred.
- [03 — Decision paths](03-decision-paths.md) — each fork, the options, and the
  chosen path with rationale.
- [04 — Environment & tooling](04-environment-and-tooling.md) — why WSL2/Linux,
  and the locked toolchain with per-tool reasoning.
- [05 — Money & trading](05-money-and-trading.md) — the earning-money reality
  check, and the toy-trading guardrail.
- [06 — The repositioning: less crowded](06-refocus-usable-tool.md) — why
  MarketForge became a usable stat-arb tool targeting less-crowded markets, and
  what "less crowded" means in practice.
- [07 — Synthetic market structure (deferred)](07-synthetic-market-structure.md) —
  why the Phase 0 corpus stays a correctness and *null* harness for now, the
  structure angles considered, and why they would still matter after real data
  arrives.

## Decision tree at a glance

```
Scala risk project (continue?)
 └─ No ──→ new Python project (data-engineering skills)
             │
             ├─ strategy-first? ── No (user: "data not emphasized")
             └─ data-first ───────→ pick lakehouse + reconstructor + tick/feature
                                      │
                                      ├─ order: 1 → 3 → 2
                                      ├─ data: synthetic-first, equity-style
                                      ├─ env: WSL2/Linux
                                      └─ stat-arb: validation layer, then paper/toy trading
                                          │
                                          └─ reposition: usable stat-arb TOOL,
                                             less-crowded markets (equities + crypto),
                                             stat-arb = the point, not validation
```
