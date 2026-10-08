# MarketForge — Low-Level Design and Interface Contracts

> **Status:** normative. This document is the exact application-programming-
> interface contract between the classes, functions, and data objects of the
> `marketforge` package, as the code exists today (Phase 0). It is a living
> document: any change that alters a signature, a data shape, the generation
> sequence, the random-draw order, a file artifact, or a command must update it
> in the same pull request (see `agents.md`). The "what and why" view lives in
> [`architecture.md`](architecture.md).

## 1. How to read this document

- Signatures are written as `function(argument: type) -> return type`.
- A **row dictionary** is a plain `dict[str, object]` with the exact keys listed
  in its shape table. All modules pass row dictionaries, never classes, except
  for the frozen configuration dataclasses.
- **Preconditions** state what the caller must guarantee; **postconditions**
  state what the function guarantees on return.
- **Draws** mean calls into the shared `numpy.random.Generator`. The draw order
  is part of the byte-level data contract; changing it changes the bytes a seed
  produces and must be deliberate and recorded.
- Values shown as `None` in the `as_of` field mean "no delivery timestamp
  recorded; treated as available on the trade date".

## 2. The object graph at a glance

```text
command-line interface (cli.py)
  ├─ gen ──> generate (synthetic/generate.py)
  │            ├─ make_rng (rng.py)
  │            ├─ build_reference (synthetic/universe.py)
  │            ├─ build_coverage (synthetic/coverage.py)
  │            ├─ generate_bars (synthetic/bars.py)
  │            ├─ apply_events (synthetic/events.py)
  │            ├─ build_manifest + manifest_to_json (synthetic/manifest.py)
  │            └─ export (synthetic/export.py)
  ├─ verify ─> verify (verify.py)
  ├─ schema ─> production schemas (schemas.py)
  ├─ datasets ─> dataset registry (catalog.py)
  └─ ingest ─> ingest_dataset (ingest.py) ─> dataset registry (catalog.py)

calendar.py is called by universe, bars, and events.
schemas.py is imported by events, export, verify, catalog, ingest, and the
command-line interface.
config.py supplies the configuration objects consumed by everything above.
```

Each object in this graph is documented below, in the order data flows through
it.

## 3. Shared contracts

### 3.1 The single random number generator

`marketforge.rng.make_rng(seed)` creates the **one** `numpy.random.Generator` for
a run. Every module receives it as the `rng` argument and draws from it in the
fixed order documented in each section below. Two rules keep the run a pure
function of the seed:

1. No module creates its own generator, draws from a module-level generator, or
   uses unseeded randomness.
2. The number and order of draws per input row are fixed; conditional logic may
   skip a draw for an entire symbol (see sections 8 through 11) but never
   reorders draws.

The full per-module draw order is:

| Stage | Draws per symbol | Section |
| --- | --- | --- |
| Universe | one integer draw for the listing date | 8 |
| Coverage | one uniform (market capitalisation), one uniform (average daily volume), in ascending symbol order | 9 |
| Bars | one uniform (start price, within the tier's slice), one uniform (volatility), then per bar: normal (return), normal (open gap), normal (high), normal (low), normal (volume noise) | 10 |
| Events | per event type in `EVENT_TYPES` order: one uniform (decision), then the type-specific parameter draws | 11 |

### 3.2 Row dictionary shapes

These shapes are the shared vocabulary between `universe`, `coverage`, `bars`,
`events`, `manifest`, `export`, and `verify`. A row that misses a key or changes
a type is a contract violation; `export` catches type mismatches by building
Arrow tables against the production schemas.

**Reference row** (produced by `build_reference`, consumed by `generate_bars`,
`apply_events`, `export`, and `verify`):

| Key | Type | Meaning |
| --- | --- | --- |
| `symbol` | `str` | Unique ticker, for example `ACME0`. |
| `name` | `str` | Company name from `COMPANY_NAMES`. |
| `sector` | `str` | Sector from `SECTORS`. |
| `listing_date` | `date` | First day with a bar for this symbol. |
| `currency` | `str` | From `UniverseConfig.currency`. |
| `exchange` | `str` | From `UniverseConfig.exchange`. |

**Bar row** (produced by `generate_bars`, mutated by `apply_events`, consumed by
`export` and `verify`):

| Key | Type | Meaning |
| --- | --- | --- |
| `symbol` | `str` | Ticker; may be renamed by a symbol-change event. |
| `date` | `date` | The trading day. |
| `open` | `float` | Opening price. |
| `high` | `float` | Highest price of the day. |
| `low` | `float` | Lowest price of the day. |
| `close` | `float` | Closing price. |
| `volume` | `int` | Traded volume, positive (at least one share). |
| `as_of` | `datetime` or `None` | Delivery timestamp; `None` for on-time records. |

**Coverage row** (produced by `build_coverage`, consumed by `generate_bars`,
`export`, and `verify`):

| Key | Type | Meaning |
| --- | --- | --- |
| `symbol` | `str` | The reference symbol the row applies to. |
| `tier` | `str` | The crowdedness tier, one of `CoverageConfig.tiers` in order. |
| `market_cap` | `float` | Latent market capitalisation drawn from the tier's slice. |
| `avg_daily_volume` | `int` | Latent average daily volume drawn from the tier's slice; the anchor that daily bar volume is noise around. |

**Event row** (produced by `apply_events`, consumed by `build_manifest`):

| Key | Type | Meaning |
| --- | --- | --- |
| `symbol` | `str` | The symbol the event applies to; for a symbol change, the original symbol. |
| `event_type` | `str` | One of `EVENT_TYPES`. |
| `event_date` | `date` | The day the event takes effect. |
| `payload` | `dict` | Type-specific fields; see the per-type tables in section 11. |

**Manifest row** (produced by `build_manifest`, consumed by `export`,
`manifest_to_json`, and `verify`):

| Key | Type | Meaning |
| --- | --- | --- |
| `event_id` | `str` | `"<symbol>-<event_type>-<event_date>-<index:04d>"`, where index counts every applied event across the run. |
| `symbol` | `str` | As in the event row. |
| `event_type` | `str` | As in the event row. |
| `event_date` | `date` | As in the event row. |
| `payload` | `str` | JSON serialization of the event payload with sorted keys. |

### 3.3 File artifacts

`generate` always writes these six files into the output directory; names are
part of the contract:

| File | Written by | Schema or format |
| --- | --- | --- |
| `reference.parquet` | `export` | `REFERENCE_SCHEMA` |
| `bars.parquet` | `export` | `BARS_SCHEMA` |
| `coverage.parquet` | `export` | `COVERAGE_SCHEMA` |
| `coverage.json` | `generate` via `coverage_to_json` | deterministic JSON: sorted keys, two-space indent, trailing newline; carries the tier list in crowded-to-thin order |
| `manifest.parquet` | `export` | `MANIFEST_SCHEMA` |
| `manifest.json` | `generate` via `manifest_to_json` | deterministic JSON: sorted keys, two-space indent, trailing newline |

### 3.4 Error handling

- **Generation raises.** Invalid configuration (for example a universe whose
  start is after its end) or a data shape that does not match a production
  schema raises an exception at generation time. The generator does not swallow
  errors into a report.
- **Ingestion raises on contract violations.** `ingest_dataset` raises
  `SchemaContractError` when the source file's schema signature does not match
  the registry contract, and `KeyError` for an unregistered dataset name (see
  section 17).
- **Verification reports.** Data problems never raise; `verify` returns
  `(False, report lines)`. Only missing files short-circuit the check.
- **The command-line interface maps these.** `gen` and `ingest` failures surface
  as Typer errors (non-zero exit); `verify` failures exit with code 1.

## 4. `marketforge.config` — configuration objects

Frozen dataclasses; treat instances as immutable configuration values.

### 4.1 `UniverseConfig`

```python
@dataclass(frozen=True)
class UniverseConfig:
    n_symbols: int = 50
    start: date = date(2023, 1, 2)
    end: date = date(2024, 12, 31)
    currency: str = "USD"
    exchange: str = "XNAS"
```

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `n_symbols` | `int` | `50` | Number of symbols in the reference table. |
| `start` | `date` | `2023-01-02` | First business day of the window (inclusive). |
| `end` | `date` | `2024-12-31` | Last business day of the window (inclusive). |
| `currency` | `str` | `"USD"` | Copied into every reference row. |
| `exchange` | `str` | `"XNAS"` | Copied into every reference row. |

**Precondition:** `start` must not be after `end`; otherwise the listing-date
draw in `build_reference` raises (see section 8).

### 4.2 `CoverageConfig`

```python
@dataclass(frozen=True)
class CoverageConfig:
    tiers: tuple[str, ...] = ("mega", "large", "mid", "small", "micro")
    adv_lo: int = 20_000
    adv_hi: int = 20_000_000
    market_cap_lo: float = 20_000_000.0
    market_cap_hi: float = 200_000_000_000.0
    volume_noise: float = 0.35
```

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `tiers` | `tuple[str, ...]` | `("mega", "large", "mid", "small", "micro")` | Tier labels, most crowded first; also the ground-truth order `verify` checks. |
| `adv_lo` / `adv_hi` | `int` | `20_000` / `20_000_000` | The average-daily-volume span, sliced log-spaced into one disjoint range per tier. |
| `market_cap_lo` / `market_cap_hi` | `float` | `2e7` / `2e11` | The market-capitalisation span, sliced the same way. |
| `volume_noise` | `float` | `0.35` | Log-normal standard deviation of daily volume around the tier's average daily volume. |

**Contract notes.** The tier list's order is part of the data contract: slice 0
is the top (most crowded) of every span and the last tier the bottom, so tier
observables cannot cross by construction. The tier is ground truth and lives
only in the coverage artifacts — it is never written into the bars or the
reference table.

### 4.3 `GeneratorConfig`

```python
@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 42
    universe: UniverseConfig = UniverseConfig()
    coverage: CoverageConfig = CoverageConfig()
    start_price_range: tuple[float, float] = (5.0, 500.0)
    annual_vol: tuple[float, float] = (0.15, 0.60)
    annual_drift: float = 0.05
    event_rates: dict[str, float] = field(default_factory=...)
```

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `seed` | `int` | `42` | The one seed for the whole run. |
| `universe` | `UniverseConfig` | defaults above | Universe window. |
| `coverage` | `CoverageConfig` | defaults above | Crowdedness-axis tiers and spans. |
| `start_price_range` | `tuple[float, float]` | `(5.0, 500.0)` | Global starting-price span, sliced per tier for each symbol's starting price. |
| `annual_vol` | `tuple[float, float]` | `(0.15, 0.60)` | Uniform range for each symbol's annual volatility. |
| `annual_drift` | `float` | `0.05` | Shared annual log-drift for the random walk. |
| `event_rates` | `dict[str, float]` | see below | Per-event-type probability that an event applies to a symbol. |

`event_rates` defaults:

| Event type | Rate | Event type | Rate |
| --- | --- | --- | --- |
| `split` | `0.05` | `backfill` | `0.05` |
| `dividend` | `0.10` | `data_gap` | `0.08` |
| `restatement` | `0.05` | `delisting` | `0.04` |
| `bad_tick` | `0.06` | `symbol_change` | `0.03` |
| `late_record` | `0.07` | — | — |

**Contract notes.** The dataclass is frozen, but `event_rates` is a plain
dictionary: its contents remain technically mutable. Callers must treat it as
read-only configuration. `apply_events` looks rates up with
`cfg.event_rates.get(etype, 0.0)`, so a missing key means "never apply", and an
unknown extra key is ignored.

## 5. `marketforge.rng`

```python
def make_rng(seed: int) -> numpy.random.Generator
```

**Contract.** Returns `numpy.random.default_rng(seed)`. There is exactly one such
object per run, created by `generate` and threaded through the generator modules.
Modules draw from it in the fixed order documented in sections 8 through 11. The
returned object carries the whole state of the run; nothing else does.

## 6. `marketforge.calendar`

```python
def business_days(start: date, end: date) -> list[date]
```

**Contract.** Returns every Monday-through-Friday date in `[start, end]`,
inclusive, in ascending order. There is no holiday table in Phase 0; a
holiday-aware calendar may be layered in later without changing the data
contract. Returns an empty list when `start` is after `end`.

**Callers.** `build_reference` (listing window), `generate_bars` (bar dates),
`apply_events` (event dates). All three callers therefore share one calendar
definition.

## 7. `marketforge.schemas`

The production schemas are the stable contract between the synthetic generator
and the future real-data ingestion layer.

### 7.1 `EVENT_TYPES`

```python
EVENT_TYPES: tuple[str, ...] = (
    "split",
    "dividend",
    "restatement",
    "bad_tick",
    "late_record",
    "backfill",
    "data_gap",
    "delisting",
    "symbol_change",
)
```

**Contract.** This tuple is both the set of valid event types and the
deterministic application order inside `apply_events`: for each symbol, events
are decided and applied in exactly this order. Do not reorder it without
treating the change as a change to the byte-level data contract.

### 7.2 `REFERENCE_SCHEMA`

| Field | Arrow type | Meaning |
| --- | --- | --- |
| `symbol` | `string` | Unique ticker. |
| `name` | `string` | Company name. |
| `sector` | `string` | Sector label. |
| `listing_date` | `date32` | First trading day. |
| `currency` | `string` | Currency, for example `"USD"`. |
| `exchange` | `string` | Exchange, for example `"XNAS"`. |

### 7.3 `BARS_SCHEMA`

| Field | Arrow type | Meaning |
| --- | --- | --- |
| `symbol` | `string` | Ticker. |
| `date` | `date32` | Trading day. |
| `open` | `float64` | Opening price. |
| `high` | `float64` | Highest price. |
| `low` | `float64` | Lowest price. |
| `close` | `float64` | Closing price. |
| `volume` | `int64` | Traded volume. |
| `as_of` | `timestamp("us")` | Delivery timestamp; null for on-time records. |

### 7.4 `MANIFEST_SCHEMA`

| Field | Arrow type | Meaning |
| --- | --- | --- |
| `event_id` | `string` | Unique event identifier. |
| `symbol` | `string` | Affected symbol. |
| `event_type` | `string` | One of `EVENT_TYPES`. |
| `event_date` | `date32` | Effective day. |
| `payload` | `string` | JSON payload with sorted keys. |

### 7.5 `COVERAGE_SCHEMA`

| Field | Arrow type | Meaning |
| --- | --- | --- |
| `symbol` | `string` | The reference symbol. |
| `tier` | `string` | The crowdedness tier, one of `CoverageConfig.tiers`. |
| `market_cap` | `float64` | Latent market capitalisation. |
| `avg_daily_volume` | `int64` | Latent average daily volume. |

This is the ground-truth crowdedness axis, a separate artifact on purpose: the
tier must never become a column of the production schemas (reference, bars,
manifest), so Phase 4's crowdedness ranking can be tested for whether it
recovers the tier from observables alone.

### 7.6 Phase 1 unified contracts: `TICKS_SCHEMA`, `QUOTES_SCHEMA`, `EVENTS_SCHEMA`

These datasets are defined now, in milestone M1.1, so real sources can drop into
the ingestion layer later without schema churn. The Phase 0 generator does not
produce them yet.

| Schema | Fields (Arrow types) |
| --- | --- |
| `TICKS_SCHEMA` | `symbol` string; `ts` timestamp(us); `price` float64; `size` int64; `side` string; `venue` string; `as_of` timestamp(us) |
| `QUOTES_SCHEMA` | `symbol` string; `ts` timestamp(us); `bid` float64; `ask` float64; `bid_size` int64; `ask_size` int64; `venue` string; `as_of` timestamp(us) |
| `EVENTS_SCHEMA` | `event_id` string; `symbol` string; `event_type` string; `event_date` date32; `payload` string; `source` string; `as_of` timestamp(us) |

`EVENTS_SCHEMA` is the production corporate-action event table, distinct from
the Phase 0 `MANIFEST_SCHEMA` (generator ground truth): it carries `source` and
the point-in-time delivery field `as_of`.

### 7.7 The name-to-schema map and the schema signature

```python
SCHEMAS: dict[str, pa.Schema] = {
    "reference": REFERENCE_SCHEMA,
    "bars": BARS_SCHEMA,
    "coverage": COVERAGE_SCHEMA,
    "manifest": MANIFEST_SCHEMA,
    "ticks": TICKS_SCHEMA,
    "quotes": QUOTES_SCHEMA,
    "events": EVENTS_SCHEMA,
}


def schema_signature(schema: pa.Schema) -> list[tuple[str, str]]
```

**Contract.** `SCHEMAS` is the canonical name-to-schema map: the dataset
registry (`catalog.py`) and the ingestion layer look schemas up here by name.
`schema_signature` returns `(field name, type string)` pairs, normalizing every
timestamp field to `timestamp[unit]` because the Parquet round trip may alter
the timezone attribute; comparison is therefore unit-aware and
timezone-agnostic. Nullability is deliberately excluded from the signature:
Parquet does not persist Arrow nullability, so requiredness is enforced by the
quality gate, never through storage nullability.

### 7.8 Field-order helpers and the evolution protocol

```python
REFERENCE_FIELDS = ["symbol", "name", "sector", "listing_date", "currency", "exchange"]
BARS_FIELDS = ["symbol", "date", "open", "high", "low", "close", "volume", "as_of"]
COVERAGE_FIELDS = ["symbol", "tier", "market_cap", "avg_daily_volume"]
MANIFEST_FIELDS = ["event_id", "symbol", "event_type", "event_date", "payload"]
TICKS_FIELDS = ["symbol", "ts", "price", "size", "side", "venue", "as_of"]
QUOTES_FIELDS = ["symbol", "ts", "bid", "ask", "bid_size", "ask_size", "venue", "as_of"]
EVENTS_FIELDS = ["event_id", "symbol", "event_type", "event_date", "payload", "source", "as_of"]
```

These lists are derived from the schemas and are the column order `export` uses
when building Arrow tables. **Nullability note:** all fields stay at Arrow's
default (nullable) because Parquet does not persist nullability flags;
per-field requiredness is enforced at the application layer (pandera from
Phase 1), never through storage nullability. **Evolution protocol:** prefer
adding fields over renaming or retyping; state what absence means for each new
field; carry schema, generator, verification, tests, and the dataset registry in
one pull request, recording the reason.

## 8. `marketforge.synthetic.universe`

Constants: `COMPANY_NAMES` (twenty fixed names) and `SECTORS` (ten fixed sector
labels). Both are fixed word lists so names and sectors are deterministic with
no external dependencies.

```python
def build_reference(cfg: UniverseConfig, rng: Generator) -> list[dict]
```

**Precondition.** `cfg.start <= cfg.end`; with an empty business-day list the
listing-date draw calls `rng.integers` with an empty range and raises.

**Algorithm.**

1. Compute `days = business_days(cfg.start, cfg.end)`.
2. The listing window is the first forty percent of `days`
   (`days[: max(1, int(len(days) * 0.4))]`).
3. For `i` from `0` to `cfg.n_symbols - 1`, in order:
   - `name = COMPANY_NAMES[i % len(COMPANY_NAMES)]`
   - `sector = SECTORS[(i // len(COMPANY_NAMES)) % len(SECTORS)]`
   - **Draw:** one `rng.integers(0, len(listing_window))` for the listing date.
   - Append the reference row with `symbol = _ticker_for(name, i)`.

**Draws.** Exactly one integer draw per symbol, in symbol-index order.

**Ticker rule** (`_ticker_for`, private). First four alphabetic characters of the
name, uppercased, plus the zero-based index — `"Acme"` becomes `ACME0`, `"Pied
Piper"` becomes `PIED1`; a name with no letters falls back to `SYM`. The index
suffix guarantees uniqueness regardless of name collisions.

**Postconditions.** One row per requested symbol; rows sorted by `symbol`;
`listing_date` always inside the listing window; every row carries the configured
currency and exchange.

## 9. `marketforge.synthetic.coverage`

```python
def build_coverage(reference: list[dict], cfg: GeneratorConfig, rng: Generator) -> list[dict]
```

```python
def coverage_by_symbol(coverage: list[dict]) -> dict[str, dict]
```

```python
def tier_price_slice(cfg: GeneratorConfig, tier: str) -> tuple[float, float]
```

```python
def coverage_to_json(rows: list[dict], cfg: GeneratorConfig) -> str
```

**Contract.** `build_coverage` assigns every reference symbol a crowdedness tier
and latent values. Tiers are assigned round-robin in ascending symbol order, so
every tier is populated evenly; the tier list is ordered most crowded first. For
each symbol, `market_cap` and `avg_daily_volume` are drawn from the symbol's
tier's log-spaced, disjoint slice of the configured spans. `coverage_by_symbol`
indexes rows by symbol. `tier_price_slice` returns the tier's slice of
`cfg.start_price_range` for `generate_bars` to draw the starting price from.
`coverage_to_json` serializes the ground truth deterministically: a document
`{"seed": ..., "tiers": [...], "symbols": [...]}`, sorted keys, two-space
indent, trailing newline — byte-identical across runs.

**Draws.** Two per symbol, in ascending symbol order: one uniform (market
capitalisation), then one uniform (average daily volume).

**Slice rule** (`_log_slice`, private). A span is cut into `n_tiers` disjoint
log-spaced slices, slice 0 at the top: with `step = (log_hi - log_lo) / n_tiers`,
slice `i` is `[exp(log_hi - (i + 1) * step), exp(log_hi - i * step))`. Adjacent
slices touch without overlapping, and every slice lies entirely above the next,
so tier observables cannot cross by construction.

**Postconditions.** One row per reference symbol; every row carries a declared
tier; `market_cap` and `avg_daily_volume` lie inside their tier's slice.

## 10. `marketforge.synthetic.bars`

```python
def generate_bars(
    reference: list[dict], coverage: list[dict], cfg: GeneratorConfig, rng: Generator
) -> list[dict]
```

**Contract.** Raw as-traded daily bars from a seeded geometric random walk, one
walk per symbol, with the crowdedness axis baked into the observables: the
starting price is drawn from the symbol's tier slice of `start_price_range` and
daily volume is log-normal noise around the symbol's tier-anchored average daily
volume. Corporate actions are applied later by `apply_events`; these bars are
what the market actually traded, before adjustment.

**Algorithm.**

1. `days = business_days(cfg.universe.start, cfg.universe.end)`; index the
   coverage rows by symbol.
2. For each reference row in ascending `symbol` order:
   - `symbol_days` = the days at or after the symbol's listing date.
   - If there are no such days, the symbol contributes no bars and consumes **no
     draws** (the check happens before any draw).
   - Otherwise `n = len(symbol_days)` and the per-symbol parameters are:
     - `price_lo, price_hi = tier_price_slice(cfg, tier)` for the symbol's tier;
     - `start_price` = one `rng.uniform(price_lo, price_hi)` draw;
     - `sigma_annual` = one `rng.uniform(*cfg.annual_vol)` draw;
     - `sigma_daily = sigma_annual / sqrt(252)`;
     - `mu_daily = cfg.annual_drift / 252 - 0.5 * sigma_daily ** 2`.
   - Log-close path: `log_close = log(start_price) + cumsum(mu_daily + sigma_daily * z)`
     with `z` = `n` standard-normal draws.
   - `close = exp(log_close)`; `open` = previous close times
     `exp(normal(0.0, 0.002))` per day (the first open is the first close scaled
     by the same small gap).
   - `high = max(open, close) * (1 + |normal(0.0, 0.005)|)`;
     `low = min(open, close) * (1 - |normal(0.0, 0.005)|)` per day.
   - `volume = avg_daily_volume * exp(normal(0.0, cfg.coverage.volume_noise))`
     per day, clipped to at least one share and stored as `int`.
3. Sort the rows by `(symbol, date)`.

**Draws per symbol with `n` trading days:** one uniform (start price), one
uniform (volatility), `n` normals (returns), `n` normals (open gaps), `n`
normals (high), `n` normals (low), `n` normals (volume) — in exactly that order.

**Postconditions.** Rows sorted by `(symbol, date)`; no bar before a symbol's
listing date; `as_of` is `None` on every bar; `high >= max(open, close)`;
`low <= min(open, close)`; `low > 0`; `volume >= 1`. The `(symbol, date)` pair
is unique. The tier is not stored on the bar row; it is recoverable from the
volume distribution alone.

## 11. `marketforge.synthetic.events`

```python
def apply_events(
    bars: list[dict], reference: list[dict], cfg: GeneratorConfig, rng: Generator
) -> tuple[list[dict], list[dict]]
```

**Contract.** Decide, apply, and record events. Returns `(bars, events)` — the
mutated bars and the list of applied event rows. Only events that were actually
applied are recorded, so every manifest record is verifiable against the data.

### 11.1 Iteration and decision order

1. `days = business_days(cfg.universe.start, cfg.universe.end)`.
2. For each reference row in ascending `symbol` order, let `sym_days` be the
   days at or after its listing date.
3. For each `etype` in `EVENT_TYPES` order, for this symbol:
   - **Decision draw:** one `rng.random()`. If it is at or above
     `cfg.event_rates.get(etype, 0.0)`, the event is skipped (the draw is still
     consumed).
   - If `len(sym_days) < 3`, the event is skipped for this symbol.
   - Otherwise the event is applied as specified below.
4. After all symbols, re-sort the bars by `(symbol, date)`.

**Draw-order note.** The decision draw happens before the trading-day-length
check, so it is consumed even for symbols with fewer than three days. Parameter
draws happen only when the event is applied; when an applied event finds no
target bar (impossible for the current event order, but guarded defensively),
its draws are consumed and the event is recorded neither in the data nor in the
manifest.

### 11.2 Event-type contracts

For every event, the position `pos` selects the effective date `d = sym_days[pos]`.

| Event type | Position draw | Parameter draws | Mutation applied to bars | Payload keys |
| --- | --- | --- | --- | --- |
| `split` | `integers(1, len(sym_days))` | `ratio` from `(2.0, 3.0, 4.0, 1.5)` | Divide `open`, `high`, `low`, `close` by `ratio` for every bar of the symbol at or after `d`. | `ratio`: `float` |
| `dividend` | `integers(0, len(sym_days))` | `amount = round(uniform(0.01, 2.0), 4)` | None — a cash dividend is recorded only. | `amount`: `float`; `currency`: `"USD"` |
| `restatement` | `integers(0, len(sym_days))` | `new = old * (1 + uniform(-0.05, 0.05))` | `close = new`; `high = max(high, new)`; `low = min(low, new)` so the bar invariants survive the correction. | `field`: `"close"`; `old`: `float`; `new`: `float` (both rounded to six decimals) |
| `bad_tick` | `integers(0, len(sym_days))` | `outlier = high * 20` | `high = outlier`. | `field`: `"high"`; `value`: `float` |
| `late_record` | `integers(0, len(sym_days))` | `delay = integers(1, 6)` | `as_of = midnight(d) + delay days`. | `trade_date`: ISO string; `delivered_at`: ISO string; `kind`: `"late_record"` |
| `backfill` | `integers(0, len(sym_days))` | `delay = integers(1, 6)` | `as_of = midnight(d) + delay days`. | `trade_date`: ISO string; `delivered_at`: ISO string; `kind`: `"backfill"` |
| `data_gap` | `integers(0, len(sym_days))` | none | Remove the bar at `d`, if present. | `missing_dates`: list of ISO strings (one entry) |
| `delisting` | `integers(len(sym_days) // 2, len(sym_days))` | `reason` from `("acquisition", "bankruptcy", "going_private")` | Remove every bar of the symbol with date after `d`. | `reason`: `str` |
| `symbol_change` | `integers(len(sym_days) // 3, len(sym_days))` | none | Rename every bar of the symbol at or after `d` to `new_symbol`. | `old_symbol`: `str`; `new_symbol`: `str` |

**Per-type notes.**

- `late_record` and `backfill` behave identically; the `kind` field
  distinguishes them in the payload. A delivery delay of one to five days puts
  `as_of` strictly after the trade day's end.
- `symbol_change` builds `new_symbol = old + "A"`, appending further `"A"`
  characters while the candidate already exists among the bars, so the new
  ticker is unique. The event row's `symbol` field keeps the **original**
  symbol.
- The constants `_SPLIT_RATIOS` and `_DELIST_REASONS` are private and part of
  the byte-level contract.

**Postconditions.** Bars sorted by `(symbol, date)`; bar invariants still hold
after every mutation; delisted symbols have no bars after the delisting date;
a renamed symbol has no bars under the old ticker at or after the change date;
the events list is in application order and contains only applied events.

**Helper.** `_find(bars, symbol, d) -> dict | None` (private) returns the bar at
exactly `(symbol, d)` or `None`.

## 12. `marketforge.synthetic.manifest`

```python
def build_manifest(events: list[dict], seed: int) -> list[dict]
```

**Contract.** Turns applied event rows into manifest rows (Parquet-shaped).
`event_id` is `"<symbol>-<event_type>-<event_date>-<index:04d>"` with the index
counting every applied event across the whole run, so identifiers are unique
even when symbol, type, and date repeat. The payload is serialized with
`json.dumps(payload, sort_keys=True)`.

**Contract note.** The `seed` parameter is accepted for forward compatibility
but the current implementation does not use it; keep the signature stable so
callers do not need to change when it is used.

```python
def manifest_to_json(records: list[dict], seed: int) -> str
```

**Contract.** Serializes the manifest as deterministic, human-readable JSON: a
document `{"seed": <seed>, "events": [...]}` where each event carries
`event_id`, `symbol`, `event_type`, the ISO `event_date`, and the decoded
`payload`; written with `json.dumps(indent=2, sort_keys=True)` plus a trailing
newline. Byte-identical across runs and directories; covered by
`tests/test_determinism.py`.

## 13. `marketforge.synthetic.export`

```python
def export(
    reference: list[dict],
    bars: list[dict],
    coverage: list[dict],
    manifest: list[dict],
    out_dir: Path,
) -> dict[str, Path]
```

**Contract.**

1. Creates `out_dir` with `mkdir(parents=True, exist_ok=True)`.
2. Builds one Arrow table per input using the production schemas:
   `pa.Table.from_pydict(_columns(rows, FIELDS), schema=SCHEMA)`. A value whose
   type does not fit the schema raises here — this is the write-time enforcement
   of the schema contract.
3. Writes `reference.parquet`, `bars.parquet`, `coverage.parquet`, and
   `manifest.parquet` with `pq.write_table`.
4. Returns `{"reference": Path, "bars": Path, "coverage": Path, "manifest": Path}`.

**Helper.** `_columns(rows, names)` (private) returns
`{name: [r[name] for r in rows] for name in names}` — every schema field is
always present as a column, even for empty input, so empty tables still carry
the full schema.

**Postconditions.** The four files exist, and their schemas match the
production schemas (as `verify` checks them).

## 14. `marketforge.synthetic.generate`

```python
def generate(cfg: GeneratorConfig, out_dir: Path) -> dict[str, Path]
```

**Contract.** The orchestrator. The exact sequence — the wiring between the
objects — is:

1. `rng = make_rng(cfg.seed)`
2. `reference = build_reference(cfg.universe, rng)`
3. `coverage = build_coverage(reference, cfg, rng)`
4. `bars = generate_bars(reference, coverage, cfg, rng)`
5. `bars, events = apply_events(bars, reference, cfg, rng)`
6. `manifest = build_manifest(events, cfg.seed)`
7. `paths = export(reference, bars, coverage, manifest, out_dir)`
8. Write `manifest.json` from `manifest_to_json(manifest, cfg.seed)` and
   `coverage.json` from `coverage_to_json(coverage, cfg)`, adding the
   `"manifest_json"` and `"coverage_json"` keys to the returned mapping.

Returns the path mapping with the six keys `reference`, `bars`, `coverage`,
`manifest`, `manifest_json`, and `coverage_json`. Any change to this sequence —
including the order of steps or the threading of the random number generator —
changes the bytes the seed produces and is a breaking change to the data
contract.

## 15. `marketforge.verify`

```python
def verify(data_dir: Path) -> tuple[bool, list[str]]
```

**Contract.** Re-reads the artifacts and checks schema conformance, bar
invariants, coverage consistency and tier recoverability, and manifest
consistency. Returns `(ok, report_lines)`; it never raises for bad data.

**Check order.**

1. All six files must exist; the first missing file returns
   `(False, ["MISSING: <path>"])` immediately.
2. The schema signature of each Parquet file must equal the production schema
   signature (field names and types; timestamp timezones are normalized away —
   see `_signature`).
3. Per bar row: the `(symbol, date)` pair must be unique; `high >= max(open,
   close)`; `low <= min(open, close)`; `low > 0`; `volume >= 0`.
4. Coverage must be consistent: every reference symbol has exactly one coverage
   row with a declared tier, market capitalisation and average daily volume are
   positive, and the median daily volume per tier orders the tiers exactly as
   the coverage JSON declares them, most crowded first (tier recoverability;
   tiers with no surviving bars are skipped, not failed).
5. Every manifest event must satisfy its event-type rule (section 15.1),
   resolved through the manifest's recorded event sequence.

The report's first line is always the summary
`bars=<n> reference=<n> coverage=<n> events=<n>`; every failure appends one
line of detail.

**Cross-event resolution.** Events are applied in `EVENT_TYPES` order, so an
earlier event's bar can be deleted by a later data gap, trimmed by a later
delisting, or renamed by a later symbol change. Before verification, the
manifest is scanned into three indexes: renames (old symbol to change date and
new symbol), gap days, and delisting dates. Bar-reading event rules resolve the
symbol at the event date through the renames; when the bar is absent but the
absence is explained by a recorded gap or delisting, the rule passes — the
manifest itself is the ground truth for why the bar is gone.

### 15.1 `_verify_event` rules

| Event type | Rule that must hold |
| --- | --- |
| `split` | The bar exists at the resolved `(symbol, event_date)` and a previous bar exists; `0.5 < close * ratio / previous_close < 2.0` (price continuity across the adjustment). An absence explained by a recorded gap or delisting passes. |
| `dividend` | The payload contains `amount`. |
| `restatement` | The bar exists at the resolved `(symbol, event_date)` and `abs(close - payload["new"]) <= 1e-4`; an explained absence passes. |
| `bad_tick` | The bar exists at the resolved `(symbol, event_date)` and `abs(high - payload["value"]) <= 1e-4`; an explained absence passes. |
| `late_record`, `backfill` | The bar exists at the resolved `(symbol, event_date)`, its `as_of` is not null, and `as_of > datetime.combine(event_date, 23:59:59)` — delivery strictly after the trade day; an explained absence passes. |
| `data_gap` | Every date in `payload["missing_dates"]` is absent from the bars. |
| `delisting` | No bar for the symbol after `event_date`; the symbol is present in the reference table. |
| `symbol_change` | No bar with the old symbol at or after `event_date`; no bar with the new symbol before `event_date`. |

**Helpers (private).** `_bar_at(bars_idx, symbol, d, renames)` resolves the
symbol at date `d` through the rename index and returns the bar, if present.
`_resolve_symbol(symbol, d, renames)` maps a symbol through its recorded rename.
`_absence_explained(symbol, d, gap_days, delist_dates)` is true when a recorded
gap or delisting removed the bar. `_prev_bar_key(bars_idx, symbols, d)` returns
the latest bar key strictly before `d` among the given symbols, or `None`.
`_signature(schema)` returns `(field name, type string)` pairs, normalizing
every timestamp field to `timestamp[unit]` because the Parquet round trip may
alter the timezone attribute; comparison is therefore unit-aware and
timezone-agnostic.

## 16. `marketforge.catalog`

```python
@dataclass(frozen=True)
class DatasetSpec:
    name: str
    version: int
    schema: pa.Schema
    partition_cols: tuple[str, ...] = ()
    pit_field: str | None = None
    lineage: tuple[str, ...] = ()
```

```python
REGISTRY: dict[str, DatasetSpec]
```

```python
def get_spec(name: str) -> DatasetSpec
```

```python
def list_datasets() -> tuple[str, ...]
```

```python
def registry_to_json() -> str
```

```python
def registry_from_json(text: str) -> dict[str, DatasetSpec]
```

**Contract.** The dataset registry is the milestone M1.1 record
`name → schema, partitioning, point-in-time, lineage`. It is a code artifact on
purpose (the top-level `catalog/` directory is git-ignored as generated
storage). `get_spec` raises `KeyError` with the list of valid names for an
unknown dataset. `partition_cols` is the hive-partitioning column order;
`pit_field` names the point-in-time delivery column (`"as_of"` where
applicable); `lineage` is a short "source → transform" chain of strings.

`registry_to_json` serializes the metadata (version, partition columns,
point-in-time field, lineage, and field names and types) without schema
objects; `registry_from_json` rebuilds specs and always looks schemas up from
`marketforge.schemas.SCHEMAS` by name, so the JSON can never smuggle in a
schema the code does not define.

Registered datasets: `reference`, `bars`, `coverage`, `manifest` (Phase 0),
and `ticks`, `quotes`, `events` (Phase 1 contracts). `bars`, `ticks`, `quotes`,
and `events` declare `partition_cols=("symbol",)` and `pit_field="as_of"`; the
rest are unpartitioned with no point-in-time field.

## 17. `marketforge.ingest`

```python
class SchemaContractError(ValueError): ...
```

```python
def ingest_dataset(name: str, source_dir: Path, lakehouse_dir: Path) -> dict[str, Path]
```

**Contract.** The milestone M1.1 ingestion path. Reads
`<source_dir>/<name>.parquet`, compares its schema signature against the
registry contract (`get_spec`), and lands the dataset under
`<lakehouse_dir>/<name>` — hive-partitioned by the declared partition columns
(symbol) when the contract declares them, a plain `part-0.parquet` otherwise.
Returns `{"dataset": <target path>}`.

**Errors.** Raises `SchemaContractError` when the source schema signature does
not match the contract; raises `KeyError` (from `get_spec`) for an unregistered
dataset name.

**Postconditions.** The target directory exists; the landed dataset's schema
matches the registry contract; partitioned datasets carry `symbol=<value>`
hive directories readable with `pyarrow.dataset.dataset(..., partitioning="hive")`.

## 18. `marketforge.cli` and `__main__`

```python
app = typer.Typer(
    help="MarketForge — statistical arbitrage in less crowded markets "
    "(Phase 0: synthetic data foundation)"
)
```

The console script `marketforge` (declared in `pyproject.toml` as
`marketforge.cli:app`) and `python -m marketforge` (via `__main__.py`) run the
same Typer app. `marketforge/__init__.py` exposes `__version__ = "0.1.0"`.

| Command | Options (name, type, default) | Behavior | Exit code |
| --- | --- | --- | --- |
| `gen` | `--seed` int `42`; `--universe-size` int `50`; `--start` string `"2023-01-02"`; `--end` string `"2024-12-31"`; `--out-dir` string `"data/synthetic"` | Builds a `GeneratorConfig` from the options (dates parsed with `date.fromisoformat`; currency, exchange, and coverage keep their defaults), runs `generate`, echoes one line per written file. | `0`; Typer's error exit for unparsable input |
| `verify` | `--data-dir` string `"data/synthetic"` | Runs `verify`, prints every report line, then `VERIFY OK` or `VERIFY FAILED`. | `0` on success, `1` on failure |
| `schema` | none | Prints all seven production schemas field by field. | `0` |
| `datasets` | none | Lists the registry: version, partition columns, point-in-time field, and lineage per dataset. | `0` |
| `ingest` | `dataset` string (argument); `--source-dir` string `"data/synthetic"`; `--lakehouse` string `"lake"` | Runs `ingest_dataset` and echoes the landed path. | `0`; Typer's error exit for unparsable input or a contract violation |

## 19. Contract change protocol

- **Signature, shape, sequence, artifact, or command changes** must update this
  document in the same pull request; structural changes must also update
  [`architecture.md`](architecture.md). The code and the documents must not
  drift.
- **Draw-order changes** change the bytes a seed produces. Treat them as
  breaking changes to the data contract: state them explicitly in the pull
  request and update section 3.1 and the affected module section.
- **Schema changes** follow the evolution protocol in `agents.md` and section
  7.8: prefer adding fields; define absence semantics; enforce requiredness in
  the quality gate; carry schema, generator, verification, tests, and the
  dataset registry in one pull request with the reason.
- **Decision changes** are recorded in `docs/thoughts/` and reflected here.

## 20. Testing contract

One test module per source module, plus cross-cutting tests; shared fixtures in
`tests/conftest.py`.

| Test module | Covers |
| --- | --- |
| `tests/conftest.py` | `small_config`: a fast universe of eight symbols from `2023-01-02` to `2023-12-29`, seed `42`. |
| `tests/test_bars.py` | `generate_bars` |
| `tests/test_universe.py` | `build_reference` |
| `tests/test_coverage.py` | `build_coverage`, `coverage_to_json`, tier assignment and slice ordering, artifact writing, and median-volume tier recovery |
| `tests/test_events.py` | `apply_events` |
| `tests/test_manifest.py` | `build_manifest`, `manifest_to_json` |
| `tests/test_export.py` | `export` |
| `tests/test_verify.py` | `verify`, including coverage checks, the cross-event resolution helpers, and the default-universe regression |
| `tests/test_catalog.py` | the registry: dataset coverage, point-in-time fields, partition columns, and the JSON round trip |
| `tests/test_ingest.py` | `ingest_dataset`: partitioned and unpartitioned landings, schema-mismatch rejection, unknown datasets |
| `tests/test_rng.py` | `make_rng` |
| `tests/test_cli.py` | the five commands |
| `tests/test_determinism.py` | byte-identical artifacts across runs and directories for one seed; different bytes for a different seed |
| `tests/test_duckdb.py` | DuckDB can read `bars.parquet` and count rows |

Tests must stay fast and deterministic: no network, no wall clock, no reliance
on ordering that is not guaranteed. Every behavior change ships with its test in
the same pull request.
