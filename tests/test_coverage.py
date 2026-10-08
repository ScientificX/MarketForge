from __future__ import annotations

import json
import statistics
from itertools import pairwise

import pyarrow.parquet as pq

from marketforge.rng import make_rng
from marketforge.schemas import COVERAGE_SCHEMA
from marketforge.synthetic.coverage import build_coverage, coverage_to_json
from marketforge.synthetic.generate import generate
from marketforge.synthetic.universe import build_reference


def _coverage(small_config):
    rng = make_rng(small_config.seed)
    ref = build_reference(small_config.universe, rng)
    return ref, build_coverage(ref, small_config, rng)


def test_every_symbol_has_a_valid_tier(small_config):
    ref, coverage = _coverage(small_config)
    assert {r["symbol"] for r in ref} == {c["symbol"] for c in coverage}
    tiers = set(small_config.coverage.tiers)
    for c in coverage:
        assert c["tier"] in tiers
        assert c["market_cap"] > 0
        assert c["avg_daily_volume"] > 0


def test_tiers_assigned_round_robin_in_symbol_order(small_config):
    ref, coverage = _coverage(small_config)
    symbols = sorted(r["symbol"] for r in ref)
    tiers = small_config.coverage.tiers
    expected = [tiers[i % len(tiers)] for i in range(len(symbols))]
    by_symbol = {c["symbol"]: c["tier"] for c in coverage}
    assert [by_symbol[s] for s in symbols] == expected


def test_latent_values_stay_within_configured_spans(small_config):
    _, coverage = _coverage(small_config)
    for c in coverage:
        assert small_config.coverage.adv_lo <= c["avg_daily_volume"] <= small_config.coverage.adv_hi
        assert (
            small_config.coverage.market_cap_lo
            <= c["market_cap"]
            <= small_config.coverage.market_cap_hi
        )


def test_tier_ranges_are_disjoint_and_ordered(small_config):
    _, coverage = _coverage(small_config)
    tiers = small_config.coverage.tiers
    for crowded, thin in pairwise(tiers):
        crowded_advs = [c["avg_daily_volume"] for c in coverage if c["tier"] == crowded]
        thin_advs = [c["avg_daily_volume"] for c in coverage if c["tier"] == thin]
        assert crowded_advs and thin_advs
        assert min(crowded_advs) > max(thin_advs)


def test_coverage_deterministic(small_config):
    assert _coverage(small_config)[1] == _coverage(small_config)[1]


def test_coverage_json_deterministic(small_config):
    a = coverage_to_json(_coverage(small_config)[1], small_config)
    b = coverage_to_json(_coverage(small_config)[1], small_config)
    assert a == b


def test_generate_writes_coverage_artifacts(small_config, tmp_path):
    generate(small_config, tmp_path)
    assert (tmp_path / "coverage.parquet").exists()
    doc = json.loads((tmp_path / "coverage.json").read_text(encoding="utf-8"))
    assert doc["seed"] == small_config.seed
    assert doc["tiers"] == list(small_config.coverage.tiers)
    assert len(doc["symbols"]) == small_config.universe.n_symbols
    table = pq.read_table(tmp_path / "coverage.parquet")
    assert set(table.column_names) == set(COVERAGE_SCHEMA.names)


def test_median_volume_recovers_tier_order(small_config, tmp_path):
    generate(small_config, tmp_path)
    doc = json.loads((tmp_path / "coverage.json").read_text(encoding="utf-8"))
    tier_by_symbol = {s["symbol"]: s["tier"] for s in doc["symbols"]}
    bars = pq.read_table(tmp_path / "bars.parquet").to_pylist()
    volumes_by_tier: dict[str, list[int]] = {}
    for r in bars:
        tier = tier_by_symbol.get(r["symbol"])
        if tier is not None:
            volumes_by_tier.setdefault(tier, []).append(r["volume"])
    medians = {t: statistics.median(vs) for t, vs in volumes_by_tier.items() if vs}
    for crowded, thin in pairwise(doc["tiers"]):
        assert medians[crowded] > medians[thin]
