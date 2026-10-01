from __future__ import annotations

import duckdb

from marketforge.synthetic.generate import generate


def test_duckdb_reads_bars(small_config, tmp_path):
    generate(small_config, tmp_path)
    con = duckdb.connect()
    n = con.execute(
        "SELECT count(*) FROM read_parquet(?)", [str(tmp_path / "bars.parquet")]
    ).fetchone()[0]
    assert n > 0
    con.close()
