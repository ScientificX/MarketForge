# 07 — Synthetic market structure (deferred)

> Line references are to revision `a089b5c`.

The Phase 0 synthetic corpus models **data-quality** reality — corporate actions,
delistings, gaps, late and backfilled records — but not **statistical** reality.
Every symbol is an independent, constant-volatility geometric random walk, so
there is no cointegration, no common factor, no volatility clustering, no regimes
and no fat tails. This document records that gap, every angle considered for
closing it, why it is **deferred rather than planned**, and why enriching the
generator would still have value *after* real market data is integrated, deep
into the plan.

## Status & decision

- **Decision: the Phase 0 corpus stays a correctness harness, and doubles as a
  null corpus for false-discovery calibration. No structure work is planned.**
- Nothing here is a commitment. It exists so the reasoning survives if one of the
  triggers in "Revisit triggers" fires.
- Rationale: M0.2's acceptance criteria are about *provability* — same seed →
  byte-identical output (`tests/test_determinism.py`) and every injected event
  verifiable against the manifest. Both hold today, and both are what Phases 1–2
  consume. Statistical realism is a Phase 3/4 concern.
- The plan's present answer to "the synthetic data has no tradeable structure" is
  to bring real data forward at Phase 3/4 (decisions log; risk row "Overfitting to
  synthetic data — mitigated by introducing real data at Phase 3/4").

## The gap as it stands

### What the generator actually models

Verified against `src/marketforge/synthetic/bars.py`:

- Each symbol's close is an **independent geometric random walk** sampled from the
  exact GBM transition — `close = exp(cumsum((mu − sigma²/2)/252 + sigma·z))`
  (`bars.py:29-36`) — with `sigma_annual` and `start_price` drawn once per symbol.
- Volatility is **constant** across the whole window: no clustering, no regime
  switching, no jumps, no fat tails. Log-returns are exactly normal.
- Symbols are **independent**: no market factor, no sector structure, no
  cross-sectional correlation, no β.
- `high`/`low` are `max(open, close)`/`min(open, close)` inflated by a half-normal
  factor (`bars.py:46-47`), so the OHLC brackets hold *by construction* and carry
  no information beyond open/close. Range-based volatility estimators applied to
  this corpus measure nothing but ±0.5% noise.
- `volume` is `rng.integers(100_000, 10_000_000)` (`bars.py:49`): uniform noise,
  **independent of price and volatility**.

Stated plainly: log-prices are random walks, so no linear combination of them is
stationary, so a cointegration screener has nothing to find except artifacts.

### The M0.2 crowdedness axis: reported done, not implemented

`plan.md`'s data section and M0.2 require a **crowdedness axis** — "the universe
spans liquid mega-caps (crowded) down to thinly-covered small/mid caps (less
crowded), so the tool can be tested on the very distinction it exploits" — and
"Next step" names extending it. `README.md` reports M0.2 as done. It is not
implemented:

- `REFERENCE_SCHEMA` (`schemas.py:29-38`) has no liquidity, capacity or coverage
  field.
- `GeneratorConfig` (`config.py:20-41`) carries seed, universe, price range,
  volatility range, drift and event rates — nothing structural.
- `volume` is undifferentiated (`bars.py:49`), so the one liquidity observable the
  schema *does* carry does not separate crowded from thin names.
- Per `docs/thoughts/04-environment-and-tooling.md`, crowdedness proxies are
  **computed in Phase 4, not fetched**, so the axis is a *latent* variable that
  must be recoverable from observables. Today it is not recoverable.

### Why the corpus cannot carry a stat-arb test today

| Planned piece | Behaviour on the current corpus |
| --- | --- |
| M4.2 Engle-Granger cointegration | Finds only *spurious* relationships (the classic spurious-regression trap). False positives are measurable; recall and P&L attribution are not, because no true pair exists. |
| M4.1 crowdedness ranking | One of its four proxies is index correlation; with no factor there is no index correlation to compute. Liquidity/turnover proxies are undifferentiated noise. |
| M4.3 realistic costs/slippage | Costs bite only through liquidity dispersion ("flags thin names where they dominate", `05-money-and-trading.md`). No dispersion → nothing to test. |
| M4.3 walk-forward CV | A walk-forward that never crosses a volatility regime cannot be shown to survive one. |
| Phase 3 leakage tests | With i.i.d. returns a rolling-vol feature is ~noise, so "prove no lookahead" has little statistical power. |
| M4.4 edge vs artifact | Needs a known truth to be honest against. |

## Angles considered (all deferred)

### A — Process realism (per symbol)

Markov regime switching (2–3 states, per-state μ/σ, optionally a *shared* market
state so regime timing is common), discretised GARCH(1,1) or log-OU stochastic
volatility, and compound-Poisson jumps for fat tails.

- **Would live in:** a new `src/marketforge/synthetic/processes.py` behind a small
  strategy interface (today's GBM becomes one implementation), plus new
  `StructureConfig` fields on `GeneratorConfig`.
- **Unlocks:** Phase 3 leakage tests with real power; Phase 4 risk sizing and cost
  behaviour observed across regimes; a backtest-to-live gap worth measuring.
- **Does not unlock:** cointegration. M4.2 still has nothing to find.
- **Cost:** moderate.
- **Risk:** the default parameters must reproduce today's bytes, or the determinism
  guarantees and any downstream fixtures shift.

### B — Cross-sectional structure and planted pairs

`r_i,t = alpha_i + beta_i·f_t + eps_i,t` with a common factor `f` (itself regime /
volatility clustered) and per-symbol betas, plus a designed fraction of symbols
generated as **cointegrated cohorts**: a shared stochastic trend plus a stationary
Ornstein-Uhlenbeck spread with a known half-life and spread volatility.

- **Would live in:** `synthetic/factor.py` and `synthetic/pairs.py`; ground truth
  (planted pairs, betas, half-lives, regime schedule) in a **separate artifact**
  (`structure.parquet` / `.json`), deliberately outside the three frozen schemas.
- **Unlocks:** recall/precision for M4.2 (does Engle-Granger *recover* the planted
  pairs, at the right half-life?), P&L attribution against known truth, a
  computable index-correlation proxy for M4.1, and a **latent** crowdedness axis
  encoded in observables (crowded = high beta, tight and fast-arbed spreads; thin =
  low beta, wide persistent spreads, higher cost).
- **Cost:** highest.
- **Risk:** a strategy can learn the DGP (see the counterpoints below).
- **Hard rule:** crowdedness must never become a column. It would break the frozen
  schema contract, contradict "computed, not fetched", and make M4.1 circular.

### C — Bring real data forward

Close the gap by substituting real data at Phase 3/4 rather than enriching the
generator. Cheapest, and strictly better for return dynamics — but it removes
ground truth, so the screener's recall can never be measured, and the
less-crowded names the thesis depends on are exactly the ones with the thinnest
free data. This is the plan's implicit present answer.

### D — Scope split by profile

`marketforge gen --profile correctness|research`: today's corpus stays the
correctness harness (unchanged bytes, unchanged acceptance), while a second corpus
carries planted structure for signal testing. Worth doing alongside A, B or E
regardless, because it is what keeps the existing guarantees from being
invalidated.

### E — Crypto perp↔spot basis

`S_perp = S_spot·exp(basis)` with a mean-reverting (OU) basis, plus a
cross-exchange variant. `plan.md` already commits to onboarding crypto in Phase
3/4, and a perp↔spot basis is *definitionally* a cointegrated pair with a funding
mechanism behind it — so this yields a legitimate stat-arb testbed with exact
ground truth at far lower complexity than engineering cointegration into the
equity generator, and it matches the "retail-dominated, less picked over" thesis.

### Cross-cutting constraints on all of the above

- **Determinism:** every new random draw must come from the single `make_rng`
  stream in a fixed order; the default profile must reproduce today's bytes.
- **Schema freeze:** `schemas.py` is the shared contract with real ingestion ("keep
  them stable"). No observable columns for latent variables; ground truth goes in
  its own artifact.
- **`verify()` contract:** any planted structure must be verifiable the same way
  events are — the signal-side analogue of "every injected event is verifiable
  against the manifest".
- **Honest limits:** proxies that need fields OHLCV + reference cannot carry
  (analyst coverage, quoted bid-ask spread) stay untestable synthetically, and
  `high`/`low` carry no information beyond open/close by construction.

## Why we would still add this after real data is integrated

Real data answers "what does this instrument actually do?". It cannot answer "did
my estimator, pipeline and screener get it *right*?". The arguments below survive
into Phases 4 and 5, and they are the reason this record exists rather than being
discarded.

1. **Labels only exist synthetically.** `plan.md` already buys ground truth for
   *data-quality* events ("inject a split/delisting/restatement and verify exact
   reconstruction"). Real data never labels the true pair, beta, half-life, regime
   boundary or spread. Extending the same principle to statistical structure
   completes the plan's own logic rather than adding a new idea.
2. **CI cannot depend on real data.** Real sources are licensed, large,
   DVC-versioned and rate-limited; a regression test needs seconds and determinism.
   Only a seeded corpus can host "the screener recovers planted pairs and holds
   its false-discovery rate" as a unit test — true in Phase 5 as well.
3. **Bias and statistical power, not just P&L.** With a known DGP you can detect an
   *estimator's* bias (finite-sample OU half-life bias is real) and measure a
   *detector's* power (ADF size and power, leakage detection). Against real data a
   biased estimator is indistinguishable from reality. This is the "separate real
   edge from artifact" mandate.
4. **A DGP is a distribution; one price history is one draw.** The regimes you most
   need to survive — stress, a volatility spike, a liquidity dry-up — may be absent
   from your real sample and cannot be scheduled. Monte Carlo over a DGP gives
   sample size that history cannot.
5. **Adversarial testing of the guardrails themselves.** Once you are live on real
   data, the only way to prove the leakage detector, PIT check and survivorship
   check still *fire* is to inject known defects into a synthetic corpus. Real data
   cannot be made to fail on demand. This argument never expires.
6. **Cost and liquidity stress sweeps.** Finding the break-even liquidity at which
   the edge dies needs controllable dispersion — exactly what "flags thin names
   where they dominate" requires.
7. **The generator is a written specification of beliefs** — a plausible half-life,
   how volatility clusters, what a round trip costs. Writing it down forces those
   assumptions into the open and produces an explicit prior to compare real-data
   estimates against.
8. **Reports stay reproducible offline.** A reader can rerun the synthetic path from
   a seed with no data licence, which is worth something for a project whose
   deliverable is an honest report.

Counterpoints, recorded with the same weight:

- **Synthetic is not real.** Return dynamics, fat tails, microstructure and
  corporate-action messiness are where real data strictly wins. The point is not to
  reimplement reality inside a generator.
- **The off-diagonal risk is DGP overfit.** A strategy can learn the generator's own
  parameters, producing a confident result that is an artifact of the fixture.
  Mitigations: parameter-holdout corpora (develop on one parameter set, report on
  another), never tune on the report corpus, and publish the DGP alongside the
  results.
- **Synthetic results are tests of the pipeline and the estimators — never evidence
  of edge.** They belong in the test suite and in the "is my machinery correct?"
  section, not in the opportunity list.
- **Scope discipline.** `plan.md` rules out gold-plating. This is deferred
  deliberately; the triggers below decide when it stops being gold-plating.

## What the current corpus is good for as it stands

- **A null corpus.** Statistical arbitrage's dominant failure mode is spurious
  discovery under multiple testing. A corpus with *known-zero* structure is the
  ideal calibration set for the screener's false-discovery rate — run the screener
  on it and count the "opportunities" it invents. That serves M4.4 directly, and it
  is a positive reason to keep the corpus structure-free rather than mutate it.
- **The Phase 2 correctness target:** known splits, delistings and restatements,
  reconstructed and diffed exactly.
- **Determinism and reproducibility:** same seed → byte-identical output, in CI,
  offline.
- **A complete event ground truth** covering the nine injectable event types.

## Constraints any future addition must respect

1. The default profile reproduces today's bytes; the determinism tests keep passing.
2. `REFERENCE_SCHEMA` / `BARS_SCHEMA` / `MANIFEST_SCHEMA` stay frozen; new ground
   truth goes in its own artifact and is tracked per the `.gitignore` policy
   (ground-truth manifests are meant to be tracked, while `data/` and `*.parquet`
   are ignored — so it needs a DVC pointer or a committed copy).
3. `verify()` gains structure checks: planted pairs genuinely stationary, recovered
   beta ≈ planted beta, regime volatility ratio present, jumps present.
4. New tests: structure recovery, volatility clustering measurable, determinism for
   both profiles.
5. Structural parameters are documented in the dataset registry (Phase 1), so a
   reader can see what was baked in.

## Revisit triggers

- M4.2 ships with no measurable recall metric, or its candidates cannot be separated
  from spurious pairs.
- Phase 3's leakage test cannot distinguish a seeded leak from noise.
- A walk-forward run never crosses a volatility-regime change.
- Real-data licensing or thinness blocks the less-crowded universe the thesis
  depends on.
- Phase 5 paper trading needs a fault-injection corpus to prove the guardrails still
  fire.

## Appendix — code-level findings from this review

Not generator enrichment, but recorded so they are not lost.

1. **The split-continuity band is coarse** (`verify.py:97`).
   `close[d] · ratio / close[prev]` is the split-adjusted gross return across the
   ex-date. Against the generator's own return distribution (daily sigma
   0.94%–3.78%, so the return is ≈1; 0.86–1.18 across Monte-Carlo draws), the
   `(0.5, 2.0)` band catches an unapplied or double-applied split ~50% of the time
   at ratio 2.0 and **0% of the time at ratio 1.5** (measured; ratios 3.0 and 4.0
   are caught ~100%). It is also blind to an incorrect adjustment *scope* (a
   whole-series rescale passes), to partial application (only the boundary pair is
   read), and to a payload ratio that disagrees with the data.
2. **The split branch is unguarded.** `float(payload["ratio"])` raises an uncaught
   `KeyError`, where the dividend branch explicitly checks `if "amount" not in
   payload` (`verify.py:101-104`); a zero prior close raises an uncaught
   `ZeroDivisionError`; a NaN close is reported as "split continuity failed" rather
   than as a non-finite price.
3. **Tolerance divergence.** `tests/test_events.py:40` asserts the same quantity
   with `0.6 < x < 1.4`, while production `verify()` allows `(0.5, 2.0)`. The test
   is the stricter oracle, and the two can drift apart silently.
4. **No negative test** for the split branch: `tests/test_verify.py` covers the
   happy path and a missing file only, so that assertion can never fire in CI.
5. **Cross-event interaction hazard.** Events are applied in `EVENT_TYPES` order,
   and later events can mutate or remove the bar that an earlier event's manifest
   record points at: `data_gap` can delete the split / restatement / bad-tick /
   late-record day, `delisting` trims bars after its date, and `symbol_change`
   renames bars at or after its date — so a split dated on or after the change date
   is recorded under the *old* symbol while the bar now carries the new one. A
   legitimately generated dataset can therefore fail `verify()` with `split: missing
   bar` or `restatement not reflected`. Reasoned from the code; not yet reproduced
   empirically (see 7). Deserves a targeted test.
6. **OHLC invariants hold by construction**, so the matching `verify()` checks and
   `tests/test_bars.py` assertions cannot fail on generated data — they only guard
   against generator regressions or hand-edited files.
7. **Local environment:** the working `.venv` is incomplete (only `lib64/` and
   `pyvenv.cfg`), so `uv run` and the `make` targets fail with `failed to remove
   file .venv\lib64: Access is denied`; `uv sync` is required before the suite can
   run. Recorded because it blocks re-running the test suite to reproduce the
   cross-event hazard (item 5) above.
