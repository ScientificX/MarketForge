"""Ingestion: land a dataset in the lakehouse layout per its registry contract.

Milestone M1.1's ingestion path reads a source Parquet file (today: the Phase 0
generator output; later: real-source normalizers), checks it against the
dataset's schema contract, and writes it into the lakehouse either as a plain
Parquet file or as a hive-partitioned dataset, exactly as the registry declares.
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from marketforge.catalog import get_spec
from marketforge.schemas import schema_signature


class SchemaContractError(ValueError):
    """Raised when a source dataset does not conform to its registry contract."""


def ingest_dataset(name: str, source_dir: Path, lakehouse_dir: Path) -> dict[str, Path]:
    """Ingest ``name`` from ``source_dir`` into ``lakehouse_dir``.

    Reads ``<source_dir>/<name>.parquet``, validates its schema signature against
    the registry contract, and writes the dataset under ``<lakehouse_dir>/<name>``
    — partitioned when the contract declares partition columns, a plain file
    otherwise. Returns ``{"dataset": <target path>}``.
    """
    spec = get_spec(name)
    source = source_dir / f"{name}.parquet"
    table = pq.read_table(source)

    if schema_signature(table.schema) != schema_signature(spec.schema):
        raise SchemaContractError(
            f"{name}: source schema {schema_signature(table.schema)} does not match "
            f"contract {schema_signature(spec.schema)}"
        )

    target = lakehouse_dir / name
    if spec.partition_cols:
        partitioning = ds.partitioning(
            pa.schema([table.schema.field(c) for c in spec.partition_cols]), flavor="hive"
        )
        ds.write_dataset(
            table,
            target,
            format="parquet",
            partitioning=partitioning,
            existing_data_behavior="overwrite_or_ignore",
        )
    else:
        target.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, target / "part-0.parquet")

    return {"dataset": target}
