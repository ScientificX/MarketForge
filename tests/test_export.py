from __future__ import annotations

import pyarrow as pa
import pyarrow.parquet as pq

from marketforge.schemas import BARS_SCHEMA, MANIFEST_SCHEMA, REFERENCE_SCHEMA
from marketforge.synthetic.generate import generate


def _sig(schema: pa.Schema) -> list[tuple[str, str]]:
    out = []
    for f in schema:
        t = f.type
        if pa.types.is_timestamp(t):
            out.append((f.name, f"timestamp[{t.unit}]"))
        else:
            out.append((f.name, str(t)))
    return out


def test_schemas_conform(small_config, tmp_path):
    generate(small_config, tmp_path)
    assert _sig(pq.read_table(tmp_path / "reference.parquet").schema) == _sig(REFERENCE_SCHEMA)
    assert _sig(pq.read_table(tmp_path / "bars.parquet").schema) == _sig(BARS_SCHEMA)
    assert _sig(pq.read_table(tmp_path / "manifest.parquet").schema) == _sig(MANIFEST_SCHEMA)


def test_roundtrip_nonempty(small_config, tmp_path):
    generate(small_config, tmp_path)
    bars = pq.read_table(tmp_path / "bars.parquet")
    assert bars.num_rows > 0
    assert set(bars.column_names) == set(BARS_SCHEMA.names)
