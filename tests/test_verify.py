from marketforge.synthetic.generate import generate
from marketforge.verify import verify


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
