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

# Field order used when building Arrow tables from row dicts.
REFERENCE_FIELDS = [f.name for f in REFERENCE_SCHEMA]
BARS_FIELDS = [f.name for f in BARS_SCHEMA]
MANIFEST_FIELDS = [f.name for f in MANIFEST_SCHEMA]
COVERAGE_FIELDS = [f.name for f in COVERAGE_SCHEMA]
