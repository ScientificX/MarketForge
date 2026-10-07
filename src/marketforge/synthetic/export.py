"""Parquet export using the production schemas."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from marketforge.schemas import (
    BARS_FIELDS,
    BARS_SCHEMA,
    MANIFEST_FIELDS,
    MANIFEST_SCHEMA,
    REFERENCE_FIELDS,
    REFERENCE_SCHEMA,
)


def export(
    reference: list[dict], bars: list[dict], manifest: list[dict], out_dir: Path
) -> dict[str, Path]:
    """Write ``reference``, ``bars``, and ``manifest`` as Parquet using production schemas."""
    out_dir.mkdir(parents=True, exist_ok=True)

    ref_table = pa.Table.from_pydict(_columns(reference, REFERENCE_FIELDS), schema=REFERENCE_SCHEMA)
    bars_table = pa.Table.from_pydict(_columns(bars, BARS_FIELDS), schema=BARS_SCHEMA)
    manifest_table = pa.Table.from_pydict(
        _columns(manifest, MANIFEST_FIELDS), schema=MANIFEST_SCHEMA
    )

    paths = {
        "reference": out_dir / "reference.parquet",
        "bars": out_dir / "bars.parquet",
        "manifest": out_dir / "manifest.parquet",
    }
    pq.write_table(ref_table, paths["reference"])
    pq.write_table(bars_table, paths["bars"])
    pq.write_table(manifest_table, paths["manifest"])
    return paths


def _columns(rows: list[dict], names: list[str]) -> dict[str, list]:
    """Column-wise extraction (always returns every field, even for empty rows)."""
    return {name: [r[name] for r in rows] for name in names}
