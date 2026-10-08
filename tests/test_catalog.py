from __future__ import annotations

import pytest

from marketforge.catalog import (
    REGISTRY,
    get_spec,
    list_datasets,
    registry_from_json,
    registry_to_json,
    specs_equivalent,
)
from marketforge.schemas import SCHEMAS


def test_all_planned_datasets_registered():
    assert set(REGISTRY) == {
        "reference",
        "bars",
        "coverage",
        "manifest",
        "ticks",
        "quotes",
        "events",
    }


def test_every_spec_has_schema_and_version():
    for name, spec in REGISTRY.items():
        assert spec.name == name
        assert spec.version >= 1
        assert spec.schema == SCHEMAS[name]


def test_point_in_time_fields_declared():
    for name in ("bars", "ticks", "quotes", "events"):
        assert REGISTRY[name].pit_field == "as_of"
    for name in ("reference", "coverage", "manifest"):
        assert REGISTRY[name].pit_field is None


def test_partition_columns_declared():
    for name in ("bars", "ticks", "quotes", "events"):
        assert REGISTRY[name].partition_cols == ("symbol",)
    for name in ("reference", "coverage", "manifest"):
        assert REGISTRY[name].partition_cols == ()


def test_get_spec_and_list_datasets():
    assert get_spec("bars") is REGISTRY["bars"]
    assert list_datasets() == tuple(REGISTRY)
    with pytest.raises(KeyError):
        get_spec("not-a-dataset")


def test_registry_json_round_trip():
    rebuilt = registry_from_json(registry_to_json())
    assert set(rebuilt) == set(REGISTRY)
    for name, spec in REGISTRY.items():
        assert specs_equivalent(rebuilt[name], spec)
