"""Raw as-traded daily OHLCV bar generation (seeded geometric random walk)."""

from __future__ import annotations

import numpy as np
from numpy.random import Generator

from marketforge.calendar import business_days
from marketforge.config import GeneratorConfig


def generate_bars(reference: list[dict], cfg: GeneratorConfig, rng: Generator) -> list[dict]:
    """Generate raw OHLCV bars for every symbol, sorted by (symbol, date).

    Prices are as-traded (raw); corporate actions are applied separately and
    recorded in the manifest. ``as_of`` is ``None`` for on-time records.
    """
    days = business_days(cfg.universe.start, cfg.universe.end)
    trading_days_per_year = 252.0

    rows: list[dict] = []
    for ref in sorted(reference, key=lambda r: r["symbol"]):
        symbol = ref["symbol"]
        symbol_days = [d for d in days if d >= ref["listing_date"]]
        n = len(symbol_days)
        if n == 0:
            continue

        start_price = float(rng.uniform(*cfg.start_price_range))
        sigma_annual = float(rng.uniform(*cfg.annual_vol))
        sigma_daily = sigma_annual / np.sqrt(trading_days_per_year)
        mu_daily = cfg.annual_drift / trading_days_per_year - 0.5 * sigma_daily**2

        z = rng.normal(0.0, 1.0, size=n)
        log_close = np.log(start_price) + np.cumsum(mu_daily + sigma_daily * z)
        close = np.exp(log_close)

        prev_close = np.empty_like(close)
        prev_close[0] = close[0]
        prev_close[1:] = close[:-1]

        open_ = prev_close * np.exp(rng.normal(0.0, 0.002, size=n))

        up = np.abs(rng.normal(0.0, 0.005, size=n))
        down = np.abs(rng.normal(0.0, 0.005, size=n))
        high = np.maximum(open_, close) * (1.0 + up)
        low = np.minimum(open_, close) * (1.0 - down)

        volume = rng.integers(100_000, 10_000_000, size=n)

        for d, o, h, l, c, v in zip(symbol_days, open_, high, low, close, volume):
            rows.append(
                {
                    "symbol": symbol,
                    "date": d,
                    "open": float(o),
                    "high": float(h),
                    "low": float(l),
                    "close": float(c),
                    "volume": int(v),
                    "as_of": None,
                }
            )

    rows.sort(key=lambda r: (r["symbol"], r["date"]))
    return rows
