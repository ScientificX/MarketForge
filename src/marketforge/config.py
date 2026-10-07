"""Configuration dataclasses for the synthetic generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class UniverseConfig:
    """Size and calendar window of the synthetic equity universe."""

    n_symbols: int = 50
    start: date = date(2023, 1, 2)
    end: date = date(2024, 12, 31)
    currency: str = "USD"
    exchange: str = "XNAS"


@dataclass(frozen=True)
class GeneratorConfig:
    """Top-level generator configuration (seed + universe + price + events)."""

    seed: int = 42
    universe: UniverseConfig = UniverseConfig()
    start_price_range: tuple[float, float] = (5.0, 500.0)
    annual_vol: tuple[float, float] = (0.15, 0.60)
    annual_drift: float = 0.05
    event_rates: dict[str, float] = field(
        default_factory=lambda: {
            "split": 0.05,
            "dividend": 0.10,
            "restatement": 0.05,
            "bad_tick": 0.06,
            "late_record": 0.07,
            "backfill": 0.05,
            "data_gap": 0.08,
            "delisting": 0.04,
            "symbol_change": 0.03,
        }
    )
