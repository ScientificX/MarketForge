from marketforge.rng import make_rng
from marketforge.synthetic.universe import build_reference


def test_reference_shape(small_config):
    rng = make_rng(small_config.seed)
    ref = build_reference(small_config.universe, rng)
    assert len(ref) == small_config.universe.n_symbols
    symbols = [r["symbol"] for r in ref]
    assert len(set(symbols)) == len(symbols), "symbols must be unique"
    for r in ref:
        assert small_config.universe.start <= r["listing_date"] <= small_config.universe.end
        assert r["symbol"] and r["name"] and r["sector"]
        assert r["currency"] == "USD"
        assert r["exchange"] == "XNAS"


def test_reference_deterministic(small_config):
    a = build_reference(small_config.universe, make_rng(small_config.seed))
    b = build_reference(small_config.universe, make_rng(small_config.seed))
    assert a == b
