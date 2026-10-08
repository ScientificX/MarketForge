from marketforge.rng import make_rng
from marketforge.synthetic.bars import generate_bars
from marketforge.synthetic.coverage import build_coverage
from marketforge.synthetic.universe import build_reference


def _generate(small_config):
    rng = make_rng(small_config.seed)
    ref = build_reference(small_config.universe, rng)
    coverage = build_coverage(ref, small_config, rng)
    return generate_bars(ref, coverage, small_config, rng)


def test_ohlc_invariants(small_config):
    bars = _generate(small_config)
    assert bars
    keys = set()
    for r in bars:
        k = (r["symbol"], r["date"])
        assert k not in keys, "duplicate (symbol, date)"
        keys.add(k)
        assert r["high"] >= max(r["open"], r["close"])
        assert r["low"] <= min(r["open"], r["close"])
        assert r["low"] > 0
        assert r["volume"] > 0
        assert r["date"].weekday() < 5
        assert r["as_of"] is None
    assert bars == sorted(bars, key=lambda r: (r["symbol"], r["date"]))


def test_every_symbol_has_bars(small_config):
    bars = _generate(small_config)
    rng = make_rng(small_config.seed)
    ref = build_reference(small_config.universe, rng)
    syms = {r["symbol"] for r in bars}
    for r in ref:
        assert r["symbol"] in syms
