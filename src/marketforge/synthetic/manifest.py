"""Ground-truth manifest: serializes every injected event."""

from __future__ import annotations

import json


def build_manifest(events: list[dict], seed: int) -> list[dict]:
    """Turn applied events into manifest records (Parquet-shaped)."""
    records: list[dict] = []
    for i, ev in enumerate(events):
        event_id = f"{ev['symbol']}-{ev['event_type']}-{ev['event_date'].isoformat()}-{i:04d}"
        records.append(
            {
                "event_id": event_id,
                "symbol": ev["symbol"],
                "event_type": ev["event_type"],
                "event_date": ev["event_date"],
                "payload": json.dumps(ev["payload"], sort_keys=True),
            }
        )
    return records


def manifest_to_json(records: list[dict], seed: int) -> str:
    """Serialize the manifest as deterministic, human-readable JSON."""
    doc = {
        "seed": seed,
        "events": [
            {
                "event_id": r["event_id"],
                "symbol": r["symbol"],
                "event_type": r["event_type"],
                "event_date": r["event_date"].isoformat(),
                "payload": json.loads(r["payload"]),
            }
            for r in records
        ],
    }
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"
