"""Verify a generated dataset against its ground-truth manifest."""

from __future__ import annotations

import json
from datetime import date, datetime, time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from marketforge.schemas import BARS_SCHEMA, MANIFEST_SCHEMA, REFERENCE_SCHEMA


def verify(data_dir: Path) -> tuple[bool, list[str]]:
    """Check schema conformance, invariants, and manifest consistency.

    Returns ``(ok, report_lines)``.
    """
    report: list[str] = []
    ok = True

    ref_path = data_dir / "reference.parquet"
    bars_path = data_dir / "bars.parquet"
    manifest_path = data_dir / "manifest.parquet"
    manifest_json_path = data_dir / "manifest.json"

    for p in (ref_path, bars_path, manifest_path, manifest_json_path):
        if not p.exists():
            return False, [f"MISSING: {p}"]

    ref = pq.read_table(ref_path)
    bars = pq.read_table(bars_path)
    manifest = pq.read_table(manifest_path)

    if _signature(ref.schema) != _signature(REFERENCE_SCHEMA):
        ok = False
        report.append(f"reference schema mismatch: {_signature(ref.schema)}")
    if _signature(bars.schema) != _signature(BARS_SCHEMA):
        ok = False
        report.append(f"bars schema mismatch: {_signature(bars.schema)}")
    if _signature(manifest.schema) != _signature(MANIFEST_SCHEMA):
        ok = False
        report.append(f"manifest schema mismatch: {_signature(manifest.schema)}")

    bars_rows = bars.to_pylist()

    seen: set[tuple[str, date]] = set()
    bars_idx: dict[tuple[str, date], dict] = {}
    for r in bars_rows:
        key = (r["symbol"], r["date"])
        if key in seen:
            ok = False
            report.append(f"duplicate bar: {key}")
        seen.add(key)
        bars_idx[key] = r

        if r["high"] < max(r["open"], r["close"]):
            ok = False
            report.append(f"high < max(open,close): {key}")
        if r["low"] > min(r["open"], r["close"]):
            ok = False
            report.append(f"low > min(open,close): {key}")
        if r["low"] <= 0:
            ok = False
            report.append(f"non-positive low: {key}")
        if r["volume"] < 0:
            ok = False
            report.append(f"negative volume: {key}")

    manifest_rows = manifest.to_pylist()
    for ev in manifest_rows:
        ok = _verify_event(ev, bars_idx, ref, report) and ok

    report.insert(0, f"bars={bars.num_rows} reference={ref.num_rows} events={manifest.num_rows}")
    return ok, report


def _verify_event(
    ev: dict, bars_idx: dict[tuple[str, date], dict], ref: pa.Table, report: list[str]
) -> bool:
    etype = ev["event_type"]
    sym = ev["symbol"]
    d: date = ev["event_date"]
    payload = json.loads(ev["payload"])

    if etype == "split":
        ratio = float(payload["ratio"])
        row = bars_idx.get((sym, d))
        if row is None:
            report.append(f"split: missing bar {sym}@{d}")
            return False
        prev = _prev_bar_date(bars_idx, sym, d)
        if prev is None:
            report.append(f"split: no prior bar for {sym}@{d}")
            return False
        if not (0.5 < row["close"] * ratio / bars_idx[(sym, prev)]["close"] < 2.0):
            report.append(f"split continuity failed for {sym}@{d}")
            return False

    elif etype == "dividend":
        if "amount" not in payload:
            report.append(f"dividend: missing amount {sym}@{d}")
            return False

    elif etype == "restatement":
        row = bars_idx.get((sym, d))
        if row is None or abs(row["close"] - float(payload["new"])) > 1e-4:
            report.append(f"restatement not reflected: {sym}@{d}")
            return False

    elif etype == "bad_tick":
        row = bars_idx.get((sym, d))
        if row is None or abs(row["high"] - float(payload["value"])) > 1e-4:
            report.append(f"bad_tick not reflected: {sym}@{d}")
            return False

    elif etype in ("late_record", "backfill"):
        row = bars_idx.get((sym, d))
        if row is None or row["as_of"] is None:
            report.append(f"{etype}: missing as_of {sym}@{d}")
            return False
        if row["as_of"] <= datetime.combine(d, time(23, 59, 59)):
            report.append(f"{etype}: as_of not later than trade date {sym}@{d}")
            return False

    elif etype == "data_gap":
        for md in payload.get("missing_dates", []):
            if (sym, date.fromisoformat(md)) in bars_idx:
                report.append(f"data_gap: {sym}@{md} still present")
                return False

    elif etype == "delisting":
        for s, dt in bars_idx:
            if s == sym and dt > d:
                report.append(f"delisting: {sym} has bars after {d}")
                return False
        ref_symbols = {r["symbol"] for r in ref.to_pylist()}
        if sym not in ref_symbols:
            report.append(f"delisting: {sym} missing from reference")
            return False

    elif etype == "symbol_change":
        old = payload["old_symbol"]
        new = payload["new_symbol"]
        for s, dt in bars_idx:
            if s == old and dt >= d:
                report.append(f"symbol_change: {old} still present at/after {d}")
                return False
            if s == new and dt < d:
                report.append(f"symbol_change: {new} present before {d}")
                return False

    return True


def _prev_bar_date(bars_idx: dict[tuple[str, date], dict], sym: str, d: date) -> date | None:
    dates = sorted(dt for (s, dt) in bars_idx if s == sym and dt < d)
    return dates[-1] if dates else None


def _signature(schema: pa.Schema) -> list[tuple[str, str]]:
    """Field name + type signature, normalizing timestamp tz (parquet round-trip)."""
    sig: list[tuple[str, str]] = []
    for field in schema:
        t = field.type
        if pa.types.is_timestamp(t):
            sig.append((field.name, f"timestamp[{t.unit}]"))
        else:
            sig.append((field.name, str(t)))
    return sig
