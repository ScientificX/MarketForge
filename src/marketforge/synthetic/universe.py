"""Deterministic reference (universe) table generation."""

from __future__ import annotations

from numpy.random import Generator

from marketforge.calendar import business_days
from marketforge.config import UniverseConfig

# Fixed word lists -> deterministic names/sectors with no external dependencies.
COMPANY_NAMES = [
    "Acme",
    "Globex",
    "Initech",
    "Umbrella",
    "Stark",
    "Wayne",
    "Cyberdyne",
    "Vandelay",
    "Wonka",
    "Soylent",
    "Massive",
    "Pied Piper",
    "Hooli",
    "Tyrell",
    "Weyland",
    "Aperture",
    "Black Mesa",
    "Oscorp",
    "LexCorp",
    "Waystar",
]
SECTORS = [
    "Technology",
    "Financials",
    "Health Care",
    "Consumer Discretionary",
    "Energy",
    "Industrials",
    "Materials",
    "Utilities",
    "Communication Services",
    "Real Estate",
]


def _ticker_for(name: str, i: int) -> str:
    base = "".join(ch for ch in name if ch.isalpha()).upper()[:4] or "SYM"
    return f"{base}{i}"


def build_reference(cfg: UniverseConfig, rng: Generator) -> list[dict]:
    """Build the reference table (one row per symbol), deterministically."""
    days = business_days(cfg.start, cfg.end)
    # Listing dates are spread over the first 40% of the calendar.
    listing_window = days[: max(1, int(len(days) * 0.4))]

    rows: list[dict] = []
    for i in range(cfg.n_symbols):
        name = COMPANY_NAMES[i % len(COMPANY_NAMES)]
        sector = SECTORS[(i // len(COMPANY_NAMES)) % len(SECTORS)]
        listing_date = listing_window[int(rng.integers(0, len(listing_window)))]
        rows.append(
            {
                "symbol": _ticker_for(name, i),
                "name": name,
                "sector": sector,
                "listing_date": listing_date,
                "currency": cfg.currency,
                "exchange": cfg.exchange,
            }
        )

    rows.sort(key=lambda r: r["symbol"])
    return rows
