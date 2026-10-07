from marketforge.rng import make_rng
from marketforge.synthetic.bars import generate_bars
from marketforge.synthetic.universe import build_reference


def test_ohlc_invariants(small_config):
    rng = make_rng(small_config.seed)
    ref = build_reference(small_config.universe, rng)
    bars = generate_bars(ref, small_config, rng)
    assert bars
    keys = set()
    for r in bars:
        k = (r["symbol"], r["date"])
        assert k not in keys, "duplicate (symbol, date)"
        keys.add(k)
        assert r["high"] >= max(r["open"], r["close"])
        assert r["low"] <= min(r["open"], r["close"])
        assert r["low"] > 0
        assert r["volume"] >= 0
        assert r["date"].weekday() < 5
        assert r["as_of"] is None
    assert bars == sorted(bars, key=lambda r: (r["symbol"], r["date"]))


def test_every_symbol_has_bars(small_config):
    rng = make_rng(small_config.seed)
    ref = build_reference(small_config.universe, rng)
    bars = generate_bars(ref, small_config, rng)
    syms = {r["symbol"] for r in bars}
    for r in ref:
        assert r["symbol"] in syms
