# Thoughts & decision log

This directory records the *reasoning* behind the MarketForge plan: the skills
analysis, the project ideas explored and rejected, and the decision paths walked
to arrive at [`../plan.md`](../plan.md). `plan.md` is the **what**; these docs
are the **why**.

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
                                      ├─ money: the portfolio (not alpha)
                                      └─ stat-arb: validation layer, then paper/toy trading
```
