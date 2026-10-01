from __future__ import annotations

from datetime import date, datetime, time

from marketforge.config import GeneratorConfig, UniverseConfig
from marketforge.rng import make_rng
from marketforge.schemas import EVENT_TYPES
from marketforge.synthetic.bars import generate_bars
from marketforge.synthetic.events import apply_events
from marketforge.synthetic.universe import build_reference


def _run(event_type: str):
    """Generate data with only ``event_type`` enabled (rate 1.0)."""
    rates = {e: 0.0 for e in EVENT_TYPES}
    rates[event_type] = 1.0
    cfg = GeneratorConfig(
        seed=42,
        universe=UniverseConfig(n_symbols=5, start=date(2023, 1, 2), end=date(2023, 12, 29)),
        event_rates=rates,
    )
    rng = make_rng(cfg.seed)
    ref = build_reference(cfg.universe, rng)
    bars = generate_bars(ref, cfg, rng)
    bars, events = apply_events(bars, ref, cfg, rng)
    return ref, bars, events


def test_split():
    _, bars, events = _run("split")
    assert events and all(e["event_type"] == "split" for e in events)
    by = {}
    for r in bars:
        by.setdefault(r["symbol"], []).append(r)
    for e in events:
        sym, d, ratio = e["symbol"], e["event_date"], e["payload"]["ratio"]
        rows = sorted(by[sym], key=lambda r: r["date"])
        i = next(i for i, r in enumerate(rows) if r["date"] == d)
        assert i > 0, "split ex-date should have a prior bar"
        assert 0.6 < rows[i]["close"] * ratio / rows[i - 1]["close"] < 1.4


def test_dividend():
    _, _, events = _run("dividend")
    assert events and all(e["event_type"] == "dividend" for e in events)
    for e in events:
        assert "amount" in e["payload"] and "currency" in e["payload"]


def test_restatement():
    _, bars, events = _run("restatement")
    assert events
    idx = {(r["symbol"], r["date"]): r for r in bars}
    for e in events:
        r = idx[(e["symbol"], e["event_date"])]
        assert abs(r["close"] - e["payload"]["new"]) < 1e-4
        assert e["payload"]["old"] != e["payload"]["new"]


def test_bad_tick():
    _, bars, events = _run("bad_tick")
    assert events
    idx = {(r["symbol"], r["date"]): r for r in bars}
    for e in events:
        assert abs(idx[(e["symbol"], e["event_date"])]["high"] - e["payload"]["value"]) < 1e-3


def test_late_and_backfill():
    for t in ("late_record", "backfill"):
        _, bars, events = _run(t)
        assert events
        idx = {(r["symbol"], r["date"]): r for r in bars}
        for e in events:
            r = idx[(e["symbol"], e["event_date"])]
            assert r["as_of"] is not None
            assert r["as_of"] > datetime.combine(e["event_date"], time(23, 59, 59))


def test_data_gap():
    _, bars, events = _run("data_gap")
    assert events
    idx = {(r["symbol"], r["date"]) for r in bars}
    for e in events:
        for md in e["payload"]["missing_dates"]:
            assert (e["symbol"], date.fromisoformat(md)) not in idx


def test_delisting():
    ref, bars, events = _run("delisting")
    assert events
    for e in events:
        assert not any(r["symbol"] == e["symbol"] and r["date"] > e["event_date"] for r in bars)
    ref_syms = {r["symbol"] for r in ref}
    assert all(e["symbol"] in ref_syms for e in events), "delisted symbol must stay in reference"


def test_symbol_change():
    _, bars, events = _run("symbol_change")
    assert events
    for e in events:
        old, new, d = e["payload"]["old_symbol"], e["payload"]["new_symbol"], e["event_date"]
        assert not any(r["symbol"] == old and r["date"] >= d for r in bars)
        assert not any(r["symbol"] == new and r["date"] < d for r in bars)
        assert any(r["symbol"] == new and r["date"] >= d for r in bars)
