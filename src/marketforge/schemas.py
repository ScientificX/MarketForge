"""Production schemas for MarketForge datasets.

These PyArrow schemas are the shared contract between the synthetic generator
(Phase 0) and the real-data ingestion layer (Phase 1). Keep them stable.

Note: nullability is left at Arrow's default (nullable) because Parquet does not
persist nullability flags; per-field validation is enforced at the application
layer (pandera in Phase 1).
"""

from __future__ import annotations

import pyarrow as pa

# Event types the generator can inject (plan.md §Data). The order is also the
# deterministic application order inside the generator.
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

REFERENCE_SCHEMA = pa.schema(
    [
        pa.field("symbol", pa.string()),
        pa.field("name", pa.string()),
        pa.field("sector", pa.string()),
        pa.field("listing_date", pa.date32()),
        pa.field("currency", pa.string()),
        pa.field("exchange", pa.string()),
    ]
)

BARS_SCHEMA = pa.schema(
    [
        pa.field("symbol", pa.string()),
        pa.field("date", pa.date32()),
        pa.field("open", pa.float64()),
        pa.field("high", pa.float64()),
        pa.field("low", pa.float64()),
        pa.field("close", pa.float64()),
        pa.field("volume", pa.int64()),
        pa.field("as_of", pa.timestamp("us")),
    ]
)

MANIFEST_SCHEMA = pa.schema(
    [
        pa.field("event_id", pa.string()),
        pa.field("symbol", pa.string()),
        pa.field("event_type", pa.string()),
        pa.field("event_date", pa.date32()),
        pa.field("payload", pa.string()),
    ]
)

# Ground-truth crowdedness axis: which tier each symbol belongs to, plus the
# latent capacity and liquidity values behind it. This is a separate artifact on
# purpose — the tier is ground truth and must never become a column of the
# production schemas (reference/bars/manifest), so Phase 4's crowdedness ranking
# can be tested for whether it recovers the tier from observables alone.
COVERAGE_SCHEMA = pa.schema(
    [
        pa.field("symbol", pa.string()),
        pa.field("tier", pa.string()),
        pa.field("market_cap", pa.float64()),
        pa.field("avg_daily_volume", pa.int64()),
    ]
)

# Phase 1 unified contracts for the datasets later phases produce (plan.md M1.1).
# These are new datasets, not changes to the phase-0 schemas above.

TICKS_SCHEMA = pa.schema(
    [
        pa.field("symbol", pa.string()),
        pa.field("ts", pa.timestamp("us")),
        pa.field("price", pa.float64()),
        pa.field("size", pa.int64()),
        pa.field("side", pa.string()),
        pa.field("venue", pa.string()),
        pa.field("as_of", pa.timestamp("us")),
    ]
)

QUOTES_SCHEMA = pa.schema(
    [
        pa.field("symbol", pa.string()),
        pa.field("ts", pa.timestamp("us")),
        pa.field("bid", pa.float64()),
        pa.field("ask", pa.float64()),
        pa.field("bid_size", pa.int64()),
        pa.field("ask_size", pa.int64()),
        pa.field("venue", pa.string()),
        pa.field("as_of", pa.timestamp("us")),
    ]
)

# Canonical corporate-action event dataset. Distinct from the phase-0 manifest
# (generator ground truth): this is the production event table real sources land
# in, carrying source and delivery-time (point-in-time) fields.
EVENTS_SCHEMA = pa.schema(
    [
        pa.field("event_id", pa.string()),
        pa.field("symbol", pa.string()),
        pa.field("event_type", pa.string()),
        pa.field("event_date", pa.date32()),
        pa.field("payload", pa.string()),
        pa.field("source", pa.string()),
        pa.field("as_of", pa.timestamp("us")),
    ]
)

# Field order used when building Arrow tables from row dicts.
REFERENCE_FIELDS = [f.name for f in REFERENCE_SCHEMA]
BARS_FIELDS = [f.name for f in BARS_SCHEMA]
MANIFEST_FIELDS = [f.name for f in MANIFEST_SCHEMA]
COVERAGE_FIELDS = [f.name for f in COVERAGE_SCHEMA]
TICKS_FIELDS = [f.name for f in TICKS_SCHEMA]
QUOTES_FIELDS = [f.name for f in QUOTES_SCHEMA]
EVENTS_FIELDS = [f.name for f in EVENTS_SCHEMA]

# Canonical schemas by dataset name (the M1.1 schema contracts).
SCHEMAS: dict[str, pa.Schema] = {
    "reference": REFERENCE_SCHEMA,
    "bars": BARS_SCHEMA,
    "coverage": COVERAGE_SCHEMA,
    "manifest": MANIFEST_SCHEMA,
    "ticks": TICKS_SCHEMA,
    "quotes": QUOTES_SCHEMA,
    "events": EVENTS_SCHEMA,
}


def schema_signature(schema: pa.Schema) -> list[tuple[str, str]]:
    """Return field names and type signatures, normalizing timestamp units.

    Parquet does not persist Arrow nullability, so presence requirements are
    enforced by the quality gate (pandera from Phase 1), not by this signature.
    Timestamp units are normalized because Parquet stores timestamps without the
    Arrow unit, which would otherwise make round-tripped schemas look different.
    """
    sig: list[tuple[str, str]] = []
    for field in schema:
        t = field.type
        if pa.types.is_timestamp(t):
            sig.append((field.name, f"timestamp[{t.unit}]"))
        else:
            sig.append((field.name, str(t)))
    return sig
