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
  │            ├─ generate_bars (synthetic/bars.py)
  │            ├─ apply_events (synthetic/events.py)
  │            ├─ build_manifest + manifest_to_json (synthetic/manifest.py)
  │            └─ export (synthetic/export.py)
  ├─ verify ─> verify (verify.py)
  └─ schema ─> production schemas (schemas.py)

calendar.py is called by universe, bars, and events.
schemas.py is imported by events, export, verify, and the command-line interface.
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
   skip a draw for an entire symbol (see sections 8 and 9) but never reorders
   draws.

The full per-module draw order is:

| Stage | Draws per symbol | Section |
| --- | --- | --- |
| Universe | one integer draw for the listing date | 8 |
| Bars | one uniform (start price), one uniform (volatility), then per bar: normal (return), normal (open gap), normal (high), normal (low), integer (volume) | 9 |
| Events | per event type in `EVENT_TYPES` order: one uniform (decision), then the type-specific parameter draws | 10 |

### 3.2 Row dictionary shapes

These shapes are the shared vocabulary between `universe`, `bars`, `events`,
`manifest`, `export`, and `verify`. A row that misses a key or changes a type is
a contract violation; `export` catches type mismatches by building Arrow tables
against the production schemas.

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
| `volume` | `int` | Traded volume, non-negative. |
| `as_of` | `datetime` or `None` | Delivery timestamp; `None` for on-time records. |

**Event row** (produced by `apply_events`, consumed by `build_manifest`):

| Key | Type | Meaning |
| --- | --- | --- |
| `symbol` | `str` | The symbol the event applies to; for a symbol change, the original symbol. |
| `event_type` | `str` | One of `EVENT_TYPES`. |
| `event_date` | `date` | The day the event takes effect. |
| `payload` | `dict` | Type-specific fields; see the per-type tables in section 10. |

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

`generate` always writes these four files into the output directory; names are
part of the contract:

| File | Written by | Schema or format |
| --- | --- | --- |
| `reference.parquet` | `export` | `REFERENCE_SCHEMA` |
| `bars.parquet` | `export` | `BARS_SCHEMA` |
| `manifest.parquet` | `export` | `MANIFEST_SCHEMA` |
| `manifest.json` | `generate` via `manifest_to_json` | deterministic JSON: sorted keys, two-space indent, trailing newline |

### 3.4 Error handling

- **Generation raises.** Invalid configuration (for example a universe whose
  start is after its end) or a data shape that does not match a production
  schema raises an exception at generation time. The generator does not swallow
  errors into a report.
- **Verification reports.** Data problems never raise; `verify` returns
  `(False, report lines)`. Only missing files short-circuit the check.
- **The command-line interface maps these.** `gen` failures surface as Typer
  errors (non-zero exit); `verify` failures exit with code 1.

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

### 4.2 `GeneratorConfig`

```python
@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 42
    universe: UniverseConfig = UniverseConfig()
    start_price_range: tuple[float, float] = (5.0, 500.0)
    annual_vol: tuple[float, float] = (0.15, 0.60)
    annual_drift: float = 0.05
    event_rates: dict[str, float] = field(default_factory=...)
```

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `seed` | `int` | `42` | The one seed for the whole run. |
| `universe` | `UniverseConfig` | defaults above | Universe window. |
| `start_price_range` | `tuple[float, float]` | `(5.0, 500.0)` | Uniform range for each symbol's starting price. |
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
Modules draw from it in the fixed order documented in sections 8 through 10. The
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

### 7.5 Field-order helpers and the evolution protocol

```python
REFERENCE_FIELDS = ["symbol", "name", "sector", "listing_date", "currency", "exchange"]
BARS_FIELDS = ["symbol", "date", "open", "high", "low", "close", "volume", "as_of"]
MANIFEST_FIELDS = ["event_id", "symbol", "event_type", "event_date", "payload"]
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

## 9. `marketforge.synthetic.bars`

```python
def generate_bars(reference: list[dict], cfg: GeneratorConfig, rng: Generator) -> list[dict]
```

**Contract.** Raw as-traded daily bars from a seeded geometric random walk, one
walk per symbol. Corporate actions are applied later by `apply_events`; these
bars are what the market actually traded, before adjustment.

**Algorithm.**

1. `days = business_days(cfg.universe.start, cfg.universe.end)`.
2. For each reference row in ascending `symbol` order:
   - `symbol_days` = the days at or after the symbol's listing date.
   - If there are no such days, the symbol contributes no bars and consumes **no
     draws** (the check happens before any draw).
   - Otherwise `n = len(symbol_days)` and the per-symbol parameters are:
     - `start_price` = one `rng.uniform(*cfg.start_price_range)` draw;
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
   - `volume` = one `rng.integers(100_000, 10_000_000)` per day.
3. Sort the rows by `(symbol, date)`.

**Draws per symbol with `n` trading days:** one uniform, one uniform, `n`
normals (returns), `n` normals (open gaps), `n` normals (high), `n` normals
(low), `n` integers (volume) — in exactly that order.

**Postconditions.** Rows sorted by `(symbol, date)`; no bar before a symbol's
listing date; `as_of` is `None` on every bar; `high >= max(open, close)`;
`low <= min(open, close)`; `low > 0`; `volume >= 0`. The `(symbol, date)` pair
is unique.

## 10. `marketforge.synthetic.events`

```python
def apply_events(
    bars: list[dict], reference: list[dict], cfg: GeneratorConfig, rng: Generator
) -> tuple[list[dict], list[dict]]
```

**Contract.** Decide, apply, and record events. Returns `(bars, events)` — the
mutated bars and the list of applied event rows. Only events that were actually
applied are recorded, so every manifest record is verifiable against the data.

### 10.1 Iteration and decision order

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

### 10.2 Event-type contracts

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

## 11. `marketforge.synthetic.manifest`

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

## 12. `marketforge.synthetic.export`

```python
def export(
    reference: list[dict], bars: list[dict], manifest: list[dict], out_dir: Path
) -> dict[str, Path]
```

**Contract.**

1. Creates `out_dir` with `mkdir(parents=True, exist_ok=True)`.
2. Builds one Arrow table per input using the production schemas:
   `pa.Table.from_pydict(_columns(rows, FIELDS), schema=SCHEMA)`. A value whose
   type does not fit the schema raises here — this is the write-time enforcement
   of the schema contract.
3. Writes `reference.parquet`, `bars.parquet`, and `manifest.parquet` with
   `pq.write_table`.
4. Returns `{"reference": Path, "bars": Path, "manifest": Path}`.

**Helper.** `_columns(rows, names)` (private) returns
`{name: [r[name] for r in rows] for name in names}` — every schema field is
always present as a column, even for empty input, so empty tables still carry
the full schema.

**Postconditions.** The three files exist, and their schemas match the
production schemas (as `verify` checks them).

## 13. `marketforge.synthetic.generate`

```python
def generate(cfg: GeneratorConfig, out_dir: Path) -> dict[str, Path]
```

**Contract.** The orchestrator. The exact sequence — the wiring between the
objects — is:

1. `rng = make_rng(cfg.seed)`
2. `reference = build_reference(cfg.universe, rng)`
3. `bars = generate_bars(reference, cfg, rng)`
4. `bars, events = apply_events(bars, reference, cfg, rng)`
5. `manifest = build_manifest(events, cfg.seed)`
6. `paths = export(reference, bars, manifest, out_dir)`
7. Write `manifest.json` from `manifest_to_json(manifest, cfg.seed)` and add the
   `"manifest_json"` key to the returned mapping.

Returns the path mapping with the four keys `reference`, `bars`, `manifest`, and
`manifest_json`. Any change to this sequence — including the order of steps or
the threading of the random number generator — changes the bytes the seed
produces and is a breaking change to the data contract.

## 14. `marketforge.verify`

```python
def verify(data_dir: Path) -> tuple[bool, list[str]]
```

**Contract.** Re-reads the artifacts and checks schema conformance, bar
invariants, and manifest consistency. Returns `(ok, report_lines)`; it never
raises for bad data.

**Check order.**

1. All four files must exist; the first missing file returns
   `(False, ["MISSING: <path>"])` immediately.
2. The schema signature of each Parquet file must equal the production schema
   signature (field names and types; timestamp timezones are normalized away —
   see `_signature`).
3. Per bar row: the `(symbol, date)` pair must be unique; `high >= max(open,
   close)`; `low <= min(open, close)`; `low > 0`; `volume >= 0`.
4. Every manifest event must satisfy its event-type rule (section 14.1).

The report's first line is always the summary
`bars=<n> reference=<n> events=<n>`; every failure appends one line of detail.

### 14.1 `_verify_event` rules

| Event type | Rule that must hold |
| --- | --- |
| `split` | A bar exists at `(symbol, event_date)` and a previous bar exists for the symbol; `0.5 < close * ratio / previous_close < 2.0` (price continuity across the adjustment). |
| `dividend` | The payload contains `amount`. |
| `restatement` | A bar exists at `(symbol, event_date)` and `abs(close - payload["new"]) <= 1e-4`. |
| `bad_tick` | A bar exists at `(symbol, event_date)` and `abs(high - payload["value"]) <= 1e-4`. |
| `late_record`, `backfill` | A bar exists, its `as_of` is not null, and `as_of > datetime.combine(event_date, 23:59:59)` — delivery strictly after the trade day. |
| `data_gap` | Every date in `payload["missing_dates"]` is absent from the bars. |
| `delisting` | No bar for the symbol after `event_date`; the symbol is present in the reference table. |
| `symbol_change` | No bar with the old symbol at or after `event_date`; no bar with the new symbol before `event_date`. |

**Helpers (private).** `_prev_bar_date(bars_idx, symbol, d)` returns the latest
bar date for the symbol strictly before `d`, or `None`. `_signature(schema)`
returns `(field name, type string)` pairs, normalizing every timestamp field to
`timestamp[unit]` because the Parquet round trip may alter the timezone
attribute; comparison is therefore unit-aware and timezone-agnostic.

## 15. `marketforge.cli` and `__main__`

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
| `gen` | `--seed` int `42`; `--universe-size` int `50`; `--start` string `"2023-01-02"`; `--end` string `"2024-12-31"`; `--out-dir` string `"data/synthetic"` | Builds a `GeneratorConfig` from the options (dates parsed with `date.fromisoformat`; currency and exchange keep their defaults), runs `generate`, echoes one line per written file. | `0`; Typer's error exit for unparsable input |
| `verify` | `--data-dir` string `"data/synthetic"` | Runs `verify`, prints every report line, then `VERIFY OK` or `VERIFY FAILED`. | `0` on success, `1` on failure |
| `schema` | none | Prints `reference`, `bars`, and `manifest` schemas field by field. | `0` |

## 16. Contract change protocol

- **Signature, shape, sequence, artifact, or command changes** must update this
  document in the same pull request; structural changes must also update
  [`architecture.md`](architecture.md). The code and the documents must not
  drift.
- **Draw-order changes** change the bytes a seed produces. Treat them as
  breaking changes to the data contract: state them explicitly in the pull
  request and update section 3.1 and the affected module section.
- **Schema changes** follow the evolution protocol in `agents.md` and section
  7.5: prefer adding fields; define absence semantics; enforce requiredness in
  the quality gate; carry schema, generator, verification, tests, and the
  dataset registry in one pull request with the reason.
- **Decision changes** are recorded in `docs/thoughts/` and reflected here.

## 17. Testing contract

One test module per source module, plus cross-cutting tests; shared fixtures in
`tests/conftest.py`.

| Test module | Covers |
| --- | --- |
| `tests/conftest.py` | `small_config`: a fast universe of eight symbols from `2023-01-02` to `2023-12-29`, seed `42`. |
| `tests/test_bars.py` | `generate_bars` |
| `tests/test_universe.py` | `build_reference` |
| `tests/test_events.py` | `apply_events` |
| `tests/test_manifest.py` | `build_manifest`, `manifest_to_json` |
| `tests/test_export.py` | `export` |
| `tests/test_verify.py` | `verify` |
| `tests/test_rng.py` | `make_rng` |
| `tests/test_cli.py` | the three commands |
| `tests/test_determinism.py` | byte-identical artifacts across runs and directories for one seed; different bytes for a different seed |
| `tests/test_duckdb.py` | DuckDB can read `bars.parquet` and count rows |

Tests must stay fast and deterministic: no network, no wall clock, no reliance
on ordering that is not guaranteed. Every behavior change ships with its test in
the same pull request.
