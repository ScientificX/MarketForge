"""Verify a generated dataset against its ground-truth manifest and coverage."""

from __future__ import annotations

import json
import statistics
from datetime import date, datetime, time
from itertools import pairwise
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from marketforge.schemas import BARS_SCHEMA, COVERAGE_SCHEMA, MANIFEST_SCHEMA, REFERENCE_SCHEMA


def verify(data_dir: Path) -> tuple[bool, list[str]]:
    """Check schema conformance, invariants, manifest and coverage consistency.

    Returns ``(ok, report_lines)``.
    """
    report: list[str] = []
    ok = True

    ref_path = data_dir / "reference.parquet"
    bars_path = data_dir / "bars.parquet"
    coverage_path = data_dir / "coverage.parquet"
    coverage_json_path = data_dir / "coverage.json"
    manifest_path = data_dir / "manifest.parquet"
    manifest_json_path = data_dir / "manifest.json"

    for p in (
        ref_path,
        bars_path,
        coverage_path,
        coverage_json_path,
        manifest_path,
        manifest_json_path,
    ):
        if not p.exists():
            return False, [f"MISSING: {p}"]

    ref = pq.read_table(ref_path)
    bars = pq.read_table(bars_path)
    coverage = pq.read_table(coverage_path)
    coverage_json = json.loads(coverage_json_path.read_text(encoding="utf-8"))
    manifest = pq.read_table(manifest_path)

    if _signature(ref.schema) != _signature(REFERENCE_SCHEMA):
        ok = False
        report.append(f"reference schema mismatch: {_signature(ref.schema)}")
    if _signature(bars.schema) != _signature(BARS_SCHEMA):
        ok = False
        report.append(f"bars schema mismatch: {_signature(bars.schema)}")
    if _signature(coverage.schema) != _signature(COVERAGE_SCHEMA):
        ok = False
        report.append(f"coverage schema mismatch: {_signature(coverage.schema)}")
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

    coverage_rows = coverage.to_pylist()
    ok = _verify_coverage(coverage_rows, coverage_json, ref, bars_rows, report) and ok

    manifest_rows = manifest.to_pylist()
    renames: dict[str, tuple[date, str]] = {}
    gap_days: set[tuple[str, date]] = set()
    delist_dates: dict[str, date] = {}
    for ev in manifest_rows:
        payload = json.loads(ev["payload"])
        if ev["event_type"] == "symbol_change":
            renames[payload["old_symbol"]] = (ev["event_date"], payload["new_symbol"])
        elif ev["event_type"] == "data_gap":
            for md in payload.get("missing_dates", []):
                gap_days.add((ev["symbol"], date.fromisoformat(md)))
        elif ev["event_type"] == "delisting":
            delist_dates[ev["symbol"]] = ev["event_date"]

    for ev in manifest_rows:
        ok = _verify_event(ev, bars_idx, ref, renames, gap_days, delist_dates, report) and ok

    report.insert(
        0,
        f"bars={bars.num_rows} reference={ref.num_rows} "
        f"coverage={coverage.num_rows} events={manifest.num_rows}",
    )
    return ok, report


def _verify_coverage(
    coverage_rows: list[dict],
    coverage_json: dict,
    ref: pa.Table,
    bars_rows: list[dict],
    report: list[str],
) -> bool:
    """Check coverage artifact consistency and tier recoverability."""
    ok = True
    tiers = coverage_json.get("tiers", [])
    ref_symbols = {r["symbol"] for r in ref.to_pylist()}
    cov_symbols = [r["symbol"] for r in coverage_rows]
    if len(cov_symbols) != len(set(cov_symbols)):
        ok = False
        report.append("coverage: duplicate symbol rows")
    if set(cov_symbols) != ref_symbols:
        ok = False
        report.append("coverage: symbol set does not match reference")

    tier_by_symbol: dict[str, str] = {}
    for r in coverage_rows:
        tier = r["tier"]
        if not tier or (tiers and tier not in tiers):
            ok = False
            report.append(f"coverage: unknown tier {tier!r} for {r['symbol']}")
        if r["market_cap"] <= 0:
            ok = False
            report.append(f"coverage: non-positive market_cap for {r['symbol']}")
        if r["avg_daily_volume"] <= 0:
            ok = False
            report.append(f"coverage: non-positive avg_daily_volume for {r['symbol']}")
        tier_by_symbol[r["symbol"]] = tier

    # Recoverability: median daily volume (the observable) must order tiers
    # exactly as the ground-truth tier list declares, most-crowded first.
    volumes_by_tier: dict[str, list[int]] = {}
    for r in bars_rows:
        tier = tier_by_symbol.get(r["symbol"])
        if tier is not None:
            volumes_by_tier.setdefault(tier, []).append(r["volume"])
    medians = {t: statistics.median(vs) for t, vs in volumes_by_tier.items() if vs}
    for crowded, thin in pairwise(tiers):
        if crowded not in medians or thin not in medians:
            continue  # a tier with no surviving bars is skipped, not a failure
        if medians[crowded] <= medians[thin]:
            ok = False
            report.append(
                f"coverage: tier order not recovered ({crowded} median volume "
                f"{medians[crowded]:.0f} <= {thin} {medians[thin]:.0f})"
            )
    return ok


def _verify_event(
    ev: dict,
    bars_idx: dict[tuple[str, date], dict],
    ref: pa.Table,
    renames: dict[str, tuple[date, str]],
    gap_days: set[tuple[str, date]],
    delist_dates: dict[str, date],
    report: list[str],
) -> bool:
    etype = ev["event_type"]
    sym = ev["symbol"]
    d: date = ev["event_date"]
    payload = json.loads(ev["payload"])

    if etype == "split":
        ratio = float(payload["ratio"])
        actual, row = _bar_at(bars_idx, sym, d, renames)
        if row is None:
            if _absence_explained(sym, d, gap_days, delist_dates):
                return True
            report.append(f"split: missing bar {sym}@{d}")
            return False
        prev_key = _prev_bar_key(bars_idx, {sym, actual}, d)
        if prev_key is None:
            report.append(f"split: no prior bar for {sym}@{d}")
            return False
        if not (0.5 < row["close"] * ratio / bars_idx[prev_key]["close"] < 2.0):
            report.append(f"split continuity failed for {sym}@{d}")
            return False

    elif etype == "dividend":
        if "amount" not in payload:
            report.append(f"dividend: missing amount {sym}@{d}")
            return False

    elif etype == "restatement":
        actual, row = _bar_at(bars_idx, sym, d, renames)
        if row is None:
            if _absence_explained(sym, d, gap_days, delist_dates):
                return True
            report.append(f"restatement not reflected: {sym}@{d}")
            return False
        if abs(row["close"] - float(payload["new"])) > 1e-4:
            report.append(f"restatement not reflected: {sym}@{d}")
            return False

    elif etype == "bad_tick":
        actual, row = _bar_at(bars_idx, sym, d, renames)
        if row is None:
            if _absence_explained(sym, d, gap_days, delist_dates):
                return True
            report.append(f"bad_tick not reflected: {sym}@{d}")
            return False
        if abs(row["high"] - float(payload["value"])) > 1e-4:
            report.append(f"bad_tick not reflected: {sym}@{d}")
            return False

    elif etype in ("late_record", "backfill"):
        actual, row = _bar_at(bars_idx, sym, d, renames)
        if row is None:
            if _absence_explained(sym, d, gap_days, delist_dates):
                return True
            report.append(f"{etype}: missing bar {sym}@{d}")
            return False
        if row["as_of"] is None:
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


def _bar_at(
    bars_idx: dict[tuple[str, date], dict],
    sym: str,
    d: date,
    renames: dict[str, tuple[date, str]],
) -> tuple[str, dict | None]:
    """Return the symbol a bar actually carries at date ``d`` and the bar itself."""
    actual = _resolve_symbol(sym, d, renames)
    return actual, bars_idx.get((actual, d))


def _resolve_symbol(sym: str, d: date, renames: dict[str, tuple[date, str]]) -> str:
    """Resolve the symbol that holds ``sym``'s bars at date ``d``.

    A symbol change recorded in the manifest renames bars at or after its date,
    so an event recorded earlier in the application order under the old symbol
    may live under the new symbol in the final data.
    """
    rename = renames.get(sym)
    if rename is not None and d >= rename[0]:
        return rename[1]
    return sym


def _absence_explained(
    sym: str, d: date, gap_days: set[tuple[str, date]], delist_dates: dict[str, date]
) -> bool:
    """True when a later recorded event legitimately removed the bar at (sym, d).

    Events are applied in a fixed order, so an earlier event's bar can be deleted
    by a later data gap or trimmed by a later delisting. An absent bar that the
    manifest itself explains is ground truth, not a verification failure.
    """
    if (sym, d) in gap_days:
        return True
    delist_date = delist_dates.get(sym)
    return delist_date is not None and d > delist_date


def _prev_bar_key(
    bars_idx: dict[tuple[str, date], dict], syms: set[str], d: date
) -> tuple[str, date] | None:
    """Return the key of the latest bar before ``d`` for any symbol in ``syms``."""
    keys = [(s, dt) for (s, dt) in bars_idx if s in syms and dt < d]
    return max(keys, key=lambda k: k[1], default=None)


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
