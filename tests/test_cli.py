from __future__ import annotations

from typer.testing import CliRunner

from marketforge.cli import app

runner = CliRunner()


def test_gen_and_verify(tmp_path):
    out = tmp_path / "data"
    res = runner.invoke(app, ["gen", "--out-dir", str(out), "--universe-size", "8"])
    assert res.exit_code == 0, res.output
    assert (out / "bars.parquet").exists()
    assert (out / "coverage.parquet").exists()
    assert (out / "coverage.json").exists()

    res2 = runner.invoke(app, ["verify", "--data-dir", str(out)])
    assert res2.exit_code == 0, res2.output


def test_verify_flags_missing(tmp_path):
    from marketforge.synthetic.generate import generate

    generate(gen_default_config(), tmp_path)
    (tmp_path / "bars.parquet").unlink()
    res = runner.invoke(app, ["verify", "--data-dir", str(tmp_path)])
    assert res.exit_code != 0
    assert "MISSING" in res.output


def gen_default_config():
    from marketforge.config import GeneratorConfig, UniverseConfig

    return GeneratorConfig(seed=7, universe=UniverseConfig(n_symbols=4))
