# 03 — Decision paths

Each fork we hit, with options, chosen path, and rationale.

## 1. Continue the Scala project vs start a new project
- Options: extend WrithLang (Stages 4–9) | new Python project.
- **Chosen: new Python project.** The Scala codebase builds pricing/risk, not the
  data-engineering skills (Python, data manipulation, orchestration, scale).

## 2. Strategy-first vs data-first
- Options: lead with a trading strategy | lead with data.
- **Chosen: data-first.** Triggered by "data not emphasized". The project's
  deliverables are datasets and pipelines; the strategy is a *consumer*.

## 3. Which projects
- Options: any of the six Round-3 data projects.
- **Chosen:** lakehouse (#1) + reconstructor (#3) + tick/feature store (#2).
  Deferred #4/#5/#6.

## 4. Ordering
- Options: 1→2→3 | 1→3→2 | other.
- **Chosen: 1→3→2.** Foundation → correctness depth → scale. Learn PIT/
  survivorship-bias on small data before tick scale. 1→3 is coherent because the
  reconstructor plugs into the lakehouse built in 1.

## 5. Synthetic vs real data (first)
- Options: wire live APIs first | synthetic generator first.
- **Chosen: synthetic first, real later.** Synthetic gives provable ground truth
  (inject an event, verify exact reconstruction). Real data adds messy reality at
  the scale/research stage (Phase 3/4).

## 6. Synthetic universe: equity vs crypto
- Options: crypto (cleaner) | equity (forces corporate actions/delistings).
- **Chosen: equity-style.** Phase 2 must demonstrate splits/delistings/
  survivorship bias — equities force those; crypto sidesteps them.

## 7. Environment
- Options: Windows-native | WSL2/Linux | cloud VM.
- **Chosen: WSL2 + Ubuntu + Docker.** Spark/Delta/Kafka are painful on
  Windows-native, and Linux is their natural home. Single-node is enough. (See 04.)

## 8. Earning money
- Options: monetize as a product | trade own capital | sell data/signals.
- **Chosen: the project is a portfolio, not a product; trading is a validation
  exercise, not an income thesis.** (See 05.)

## 9. Stat-arb layer purpose
- Options: alpha generation | validation/consuming layer.
- **Chosen: validation/consuming layer.** It proves the platform serves real
  research; honest reporting (survivorship-bias artifacts) is the differentiator.

## 10. Trading: real vs paper
- Options: go live | paper first.
- **Chosen: paper first, toy money only.** (See 05 guardrail.)

## The one coherence discipline

Define a **dataset contract** early (schema, partitioning, PIT, lineage,
registry) in Phase 1; Phases 2 and 3 layer on it. Prevents three disconnected
repos.
