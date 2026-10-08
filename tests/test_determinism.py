from __future__ import annotations

import dataclasses

from marketforge.synthetic.generate import generate


def test_byte_identical(small_config, tmp_path):
    d1, d2 = tmp_path / "a", tmp_path / "b"
    generate(small_config, d1)
    generate(small_config, d2)
    for name in (
        "reference.parquet",
        "bars.parquet",
        "coverage.parquet",
        "coverage.json",
        "manifest.parquet",
        "manifest.json",
    ):
        assert (d1 / name).read_bytes() == (d2 / name).read_bytes(), name


def test_different_seed_differs(small_config, tmp_path):
    d1, d2 = tmp_path / "a", tmp_path / "b"
    generate(small_config, d1)
    generate(dataclasses.replace(small_config, seed=999), d2)
    assert (d1 / "bars.parquet").read_bytes() != (d2 / "bars.parquet").read_bytes()
