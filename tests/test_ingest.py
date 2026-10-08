from __future__ import annotations

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import pytest

from marketforge.ingest import SchemaContractError, ingest_dataset
from marketforge.synthetic.generate import generate


def test_ingest_unpartitioned_dataset(small_config, tmp_path):
    src = tmp_path / "src"
    lake = tmp_path / "lake"
    generate(small_config, src)
    out = ingest_dataset("reference", src, lake)
    table = pq.read_table(out["dataset"] / "part-0.parquet")
    assert table.num_rows == small_config.universe.n_symbols


def test_ingest_partitioned_dataset(small_config, tmp_path):
    src = tmp_path / "src"
    lake = tmp_path / "lake"
    generate(small_config, src)
    out = ingest_dataset("bars", src, lake)
    landed = ds.dataset(out["dataset"], format="parquet", partitioning="hive")
    assert landed.count_rows() == pq.read_table(src / "bars.parquet").num_rows
    symbols = {r["symbol"] for r in landed.to_table().to_pylist()}
    for symbol in symbols:
        assert (out["dataset"] / f"symbol={symbol}").is_dir()


def test_ingest_rejects_schema_mismatch(small_config, tmp_path):
    src = tmp_path / "src"
    lake = tmp_path / "lake"
    generate(small_config, src)
    pq.write_table(pa.table({"wrong_column": [1, 2]}), src / "bars.parquet")
    with pytest.raises(SchemaContractError):
        ingest_dataset("bars", src, lake)


def test_ingest_unknown_dataset(tmp_path):
    with pytest.raises(KeyError):
        ingest_dataset("not-a-dataset", tmp_path, tmp_path / "lake")
