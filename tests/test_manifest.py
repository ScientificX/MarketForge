from __future__ import annotations

import json

import pyarrow.parquet as pq

from marketforge.synthetic.generate import generate


def test_manifest_completeness(small_config, tmp_path):
    generate(small_config, tmp_path)
    doc = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    events = doc["events"]
    assert doc["seed"] == small_config.seed
    ids = [e["event_id"] for e in events]
    assert len(ids) == len(set(ids)), "event ids must be unique"

    table = pq.read_table(tmp_path / "manifest.parquet")
    assert table.num_rows == len(events)
    parquet_ids = {r["event_id"] for r in table.to_pylist()}
    assert parquet_ids == set(ids)
