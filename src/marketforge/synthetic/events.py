"""Event injection: decide, apply, and record corporate-action / data events.

Events are decided and applied in a fixed, deterministic order (per symbol, in
``EVENT_TYPES`` order), so the full run is a pure function of the seed. The
resulting manifest records only events that were actually applied, so every
record is verifiable against the data.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from numpy.random import Generator

from marketforge.calendar import business_days
from marketforge.config import GeneratorConfig
from marketforge.schemas import EVENT_TYPES

_SPLIT_RATIOS = (2.0, 3.0, 4.0, 1.5)
_DELIST_REASONS = ("acquisition", "bankruptcy", "going_private")


def apply_events(
    bars: list[dict],
    reference: list[dict],
    cfg: GeneratorConfig,
    rng: Generator,
) -> tuple[list[dict], list[dict]]:
    """Apply seeded events to ``bars``; return ``(bars, events)``."""
    days = business_days(cfg.universe.start, cfg.universe.end)
    events: list[dict] = []

    for ref in sorted(reference, key=lambda r: r["symbol"]):
        sym = ref["symbol"]
        sym_days = [d for d in days if d >= ref["listing_date"]]

        for etype in EVENT_TYPES:
            if rng.random() >= cfg.event_rates.get(etype, 0.0):
                continue
            if len(sym_days) < 3:
                continue

            if etype == "split":
                pos = int(rng.integers(1, len(sym_days)))
                d = sym_days[pos]
                ratio = float(_SPLIT_RATIOS[int(rng.integers(0, len(_SPLIT_RATIOS)))])
                for r in bars:
                    if r["symbol"] == sym and r["date"] >= d:
                        r["open"] /= ratio
                        r["high"] /= ratio
                        r["low"] /= ratio
                        r["close"] /= ratio
                events.append(
                    {"symbol": sym, "event_type": etype, "event_date": d, "payload": {"ratio": ratio}}
                )

            elif etype == "dividend":
                pos = int(rng.integers(0, len(sym_days)))
                d = sym_days[pos]
                amount = round(float(rng.uniform(0.01, 2.0)), 4)
                events.append(
                    {
                        "symbol": sym,
                        "event_type": etype,
                        "event_date": d,
                        "payload": {"amount": amount, "currency": "USD"},
                    }
                )

            elif etype == "restatement":
                pos = int(rng.integers(0, len(sym_days)))
                d = sym_days[pos]
                row = _find(bars, sym, d)
                if row is None:
                    continue
                old = row["close"]
                new = float(old * (1.0 + rng.uniform(-0.05, 0.05)))
                row["close"] = new
                # Keep OHLC invariants valid when the corrected close moves outside
                # the original intraday range.
                row["high"] = max(row["high"], new)
                row["low"] = min(row["low"], new)
                events.append(
                    {
                        "symbol": sym,
                        "event_type": etype,
                        "event_date": d,
                        "payload": {"field": "close", "old": round(old, 6), "new": round(new, 6)},
                    }
                )

            elif etype == "bad_tick":
                pos = int(rng.integers(0, len(sym_days)))
                d = sym_days[pos]
                row = _find(bars, sym, d)
                if row is None:
                    continue
                outlier = float(row["high"] * 20.0)
                row["high"] = outlier
                events.append(
                    {
                        "symbol": sym,
                        "event_type": etype,
                        "event_date": d,
                        "payload": {"field": "high", "value": outlier},
                    }
                )

            elif etype in ("late_record", "backfill"):
                pos = int(rng.integers(0, len(sym_days)))
                d = sym_days[pos]
                row = _find(bars, sym, d)
                if row is None:
                    continue
                delay_days = int(rng.integers(1, 6))
                delivered = datetime.combine(d, datetime.min.time()) + timedelta(days=delay_days)
                row["as_of"] = delivered
                events.append(
                    {
                        "symbol": sym,
                        "event_type": etype,
                        "event_date": d,
                        "payload": {
                            "trade_date": d.isoformat(),
                            "delivered_at": delivered.isoformat(),
                            "kind": etype,
                        },
                    }
                )

            elif etype == "data_gap":
                pos = int(rng.integers(0, len(sym_days)))
                d = sym_days[pos]
                removed = [r for r in bars if r["symbol"] == sym and r["date"] == d]
                if removed:
                    bars[:] = [r for r in bars if not (r["symbol"] == sym and r["date"] == d)]
                    events.append(
                        {
                            "symbol": sym,
                            "event_type": etype,
                            "event_date": d,
                            "payload": {"missing_dates": [d.isoformat()]},
                        }
                    )

            elif etype == "delisting":
                pos = int(rng.integers(len(sym_days) // 2, len(sym_days)))
                d = sym_days[pos]
                reason = _DELIST_REASONS[int(rng.integers(0, len(_DELIST_REASONS)))]
                bars[:] = [r for r in bars if not (r["symbol"] == sym and r["date"] > d)]
                events.append(
                    {"symbol": sym, "event_type": etype, "event_date": d, "payload": {"reason": reason}}
                )

            elif etype == "symbol_change":
                pos = int(rng.integers(len(sym_days) // 3, len(sym_days)))
                d = sym_days[pos]
                new_symbol = f"{sym}A"
                existing = {r["symbol"] for r in bars}
                while new_symbol in existing:
                    new_symbol += "A"
                for r in bars:
                    if r["symbol"] == sym and r["date"] >= d:
                        r["symbol"] = new_symbol
                events.append(
                    {
                        "symbol": sym,
                        "event_type": etype,
                        "event_date": d,
                        "payload": {"old_symbol": sym, "new_symbol": new_symbol},
                    }
                )

    bars.sort(key=lambda r: (r["symbol"], r["date"]))
    return bars, events


def _find(bars: list[dict], symbol: str, d: date) -> dict | None:
    for r in bars:
        if r["symbol"] == symbol and r["date"] == d:
            return r
    return None
