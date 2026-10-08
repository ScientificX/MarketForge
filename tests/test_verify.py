from datetime import date

from marketforge.config import GeneratorConfig, UniverseConfig
from marketforge.synthetic.generate import generate
from marketforge.verify import _absence_explained, _resolve_symbol, verify


def test_verify_passes_on_valid_data(small_config, tmp_path):
    generate(small_config, tmp_path)
    ok, report = verify(tmp_path)
    assert ok, "\n".join(report)


def test_verify_detects_missing_file(small_config, tmp_path):
    generate(small_config, tmp_path)
    (tmp_path / "bars.parquet").unlink()
    ok, report = verify(tmp_path)
    assert not ok
    assert any("MISSING" in line for line in report)


def test_verify_detects_missing_coverage(small_config, tmp_path):
    generate(small_config, tmp_path)
    (tmp_path / "coverage.parquet").unlink()
    ok, report = verify(tmp_path)
    assert not ok
    assert any("MISSING" in line for line in report)


def test_verify_passes_on_default_universe(tmp_path):
    # The documented quickstart (`make gen` + `make verify`) must pass. This
    # configuration triggers cross-event interactions (a split recorded under a
    # symbol later renamed, bars removed by later gaps), which verification must
    # resolve through the manifest instead of failing.
    cfg = GeneratorConfig(seed=42, universe=UniverseConfig(n_symbols=50))
    generate(cfg, tmp_path)
    ok, report = verify(tmp_path)
    assert ok, "\n".join(report)


def test_resolve_symbol_through_rename():
    renames = {"AAA1": (date(2024, 1, 15), "AAA1A")}
    assert _resolve_symbol("AAA1", date(2024, 1, 14), renames) == "AAA1"
    assert _resolve_symbol("AAA1", date(2024, 1, 15), renames) == "AAA1A"
    assert _resolve_symbol("BBB2", date(2024, 6, 1), renames) == "BBB2"


def test_absence_explained_by_later_events():
    d = date(2024, 6, 1)
    assert _absence_explained("AAA1", d, {("AAA1", d)}, {})
    assert _absence_explained("AAA1", d, set(), {"AAA1": date(2024, 1, 1)})
    assert not _absence_explained("AAA1", d, set(), {})
    assert not _absence_explained("AAA1", d, set(), {"AAA1": d})
