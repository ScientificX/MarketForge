"""Dataset registry: name → schema, partitioning, point-in-time field, lineage.

Milestone M1.1's registry is a code artifact on purpose: the top-level
``catalog/`` directory is git-ignored as generated storage, while this module is
tracked and reviewed like any other contract. ``registry_to_json`` and
``registry_from_json`` exist for lineage export and audit; the canonical schemas
always come from :mod:`marketforge.schemas`, never from the JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pyarrow as pa

from marketforge.schemas import SCHEMAS


@dataclass(frozen=True)
class DatasetSpec:
    """The contract for one dataset: schema, partitioning, PIT field, lineage.

    ``partition_cols`` is the hive-partitioning column order. ``pit_field`` names
    the column that carries the point-in-time delivery timestamp (``as_of``);
    ``None`` means the dataset has no point-in-time dimension. ``lineage`` is a
    short chain of "source → transform" steps recorded as strings.
    """

    name: str
    version: int
    schema: pa.Schema
    partition_cols: tuple[str, ...] = ()
    pit_field: str | None = None
    lineage: tuple[str, ...] = ()


REGISTRY: dict[str, DatasetSpec] = {
    "reference": DatasetSpec(
        name="reference",
        version=1,
        schema=SCHEMAS["reference"],
        lineage=("synthetic generator (phase 0)",),
    ),
    "bars": DatasetSpec(
        name="bars",
        version=1,
        schema=SCHEMAS["bars"],
        partition_cols=("symbol",),
        pit_field="as_of",
        lineage=("synthetic generator (phase 0)",),
    ),
    "coverage": DatasetSpec(
        name="coverage",
        version=1,
        schema=SCHEMAS["coverage"],
        lineage=("synthetic generator (phase 0)", "ground truth: crowdedness tier"),
    ),
    "manifest": DatasetSpec(
        name="manifest",
        version=1,
        schema=SCHEMAS["manifest"],
        lineage=("synthetic generator (phase 0)", "ground truth: injected events"),
    ),
    "ticks": DatasetSpec(
        name="ticks",
        version=1,
        schema=SCHEMAS["ticks"],
        partition_cols=("symbol",),
        pit_field="as_of",
        lineage=("synthetic tick generator (phase 3)", "real exchange feed (phase 3)"),
    ),
    "quotes": DatasetSpec(
        name="quotes",
        version=1,
        schema=SCHEMAS["quotes"],
        partition_cols=("symbol",),
        pit_field="as_of",
        lineage=("exchange feed (phase 3)",),
    ),
    "events": DatasetSpec(
        name="events",
        version=1,
        schema=SCHEMAS["events"],
        partition_cols=("symbol",),
        pit_field="as_of",
        lineage=("corporate-actions vendor (phase 2)",),
    ),
}


def get_spec(name: str) -> DatasetSpec:
    """Return the contract for ``name``, or raise ``KeyError`` listing valid names."""
    if name not in REGISTRY:
        valid = ", ".join(sorted(REGISTRY))
        raise KeyError(f"unknown dataset {name!r}; registered datasets: {valid}")
    return REGISTRY[name]


def list_datasets() -> tuple[str, ...]:
    """Return the registered dataset names in registration order."""
    return tuple(REGISTRY)


def registry_to_json() -> str:
    """Serialize registry metadata (without schema objects) as readable JSON."""
    doc = {
        name: {
            "name": spec.name,
            "version": spec.version,
            "partition_cols": list(spec.partition_cols),
            "pit_field": spec.pit_field,
            "lineage": list(spec.lineage),
            "fields": [(f.name, str(f.type)) for f in spec.schema],
        }
        for name, spec in REGISTRY.items()
    }
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def registry_from_json(text: str) -> dict[str, DatasetSpec]:
    """Rebuild registry specs from ``registry_to_json`` output.

    Schemas are looked up from :mod:`marketforge.schemas` by dataset name, so the
    JSON can never smuggle in a schema the code does not define.
    """
    doc = json.loads(text)
    specs: dict[str, DatasetSpec] = {}
    for name, meta in doc.items():
        specs[name] = DatasetSpec(
            name=meta["name"],
            version=int(meta["version"]),
            schema=SCHEMAS[meta["name"]],
            partition_cols=tuple(meta["partition_cols"]),
            pit_field=meta["pit_field"],
            lineage=tuple(meta["lineage"]),
        )
    return specs


def _registry_fields(spec: DatasetSpec) -> dict:
    """Project a spec to plain fields for comparison (schema excluded)."""
    return {
        "name": spec.name,
        "version": spec.version,
        "partition_cols": spec.partition_cols,
        "pit_field": spec.pit_field,
        "lineage": spec.lineage,
    }


def specs_equivalent(a: DatasetSpec, b: DatasetSpec) -> bool:
    """True when two specs agree on everything except the Arrow schema object."""
    return _registry_fields(a) == _registry_fields(b) and list(a.schema) == list(b.schema)
