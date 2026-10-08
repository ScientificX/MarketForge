"""Ground-truth coverage: the crowdedness axis (liquidity and capacity tiers).

Every symbol gets a crowdedness tier, ordered most-crowded first (mega-cap down
to micro-cap). The tier is *latent* ground truth: it lives only in this artifact
(and its JSON twin), never as a column of the production schemas, so Phase 4's
crowdedness ranking can be tested for whether it recovers the true thin-to-crowded
ordering from observables (tiered volume and price) alone.
"""

from __future__ import annotations

import json
import math

from numpy.random import Generator

from marketforge.config import GeneratorConfig


def build_coverage(reference: list[dict], cfg: GeneratorConfig, rng: Generator) -> list[dict]:
    """Assign every reference symbol a crowdedness tier and latent values.

    Tiers are assigned round-robin in sorted-symbol order, so every tier is
    populated evenly and the axis spans the whole configured set. Each symbol
    then draws its latent market capitalisation and average daily volume from its
    tier's log-spaced, disjoint slice of the configured spans. Draws come from
    the single seeded generator in a fixed order, keeping the run deterministic.
    """
    tiers = cfg.coverage.tiers
    n_tiers = len(tiers)
    rows: list[dict] = []
    for i, ref in enumerate(sorted(reference, key=lambda r: r["symbol"])):
        tier_idx = i % n_tiers
        tier = tiers[tier_idx]
        adv_lo, adv_hi = _log_slice(cfg.coverage.adv_lo, cfg.coverage.adv_hi, n_tiers, tier_idx)
        cap_lo, cap_hi = _log_slice(
            cfg.coverage.market_cap_lo, cfg.coverage.market_cap_hi, n_tiers, tier_idx
        )
        rows.append(
            {
                "symbol": ref["symbol"],
                "tier": tier,
                "market_cap": float(rng.uniform(cap_lo, cap_hi)),
                "avg_daily_volume": int(rng.uniform(adv_lo, adv_hi)),
            }
        )
    return rows


def coverage_by_symbol(coverage: list[dict]) -> dict[str, dict]:
    """Index coverage rows by symbol."""
    return {row["symbol"]: row for row in coverage}


def tier_price_slice(cfg: GeneratorConfig, tier: str) -> tuple[float, float]:
    """Return the start-price slice for a tier over ``start_price_range``.

    The global range is sliced top-first, so the most-crowded tier gets the
    highest price band (a capacity proxy) and the thinnest tier the lowest.
    """
    idx = cfg.coverage.tiers.index(tier)
    return _log_slice(
        cfg.start_price_range[0], cfg.start_price_range[1], len(cfg.coverage.tiers), idx
    )


def coverage_to_json(rows: list[dict], cfg: GeneratorConfig) -> str:
    """Serialize coverage ground truth as deterministic, human-readable JSON."""
    doc = {
        "seed": cfg.seed,
        "tiers": list(cfg.coverage.tiers),
        "symbols": [
            {
                "symbol": r["symbol"],
                "tier": r["tier"],
                "market_cap": r["market_cap"],
                "avg_daily_volume": r["avg_daily_volume"],
            }
            for r in sorted(rows, key=lambda r: r["symbol"])
        ],
    }
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def _log_slice(lo: float, hi: float, n_tiers: int, tier_idx: int) -> tuple[float, float]:
    """Return the log-spaced slice for ``tier_idx`` of ``n_tiers``, top-first.

    Slice 0 spans the top of the range (most crowded) and slice ``n_tiers - 1``
    the bottom (least crowded); adjacent slices are disjoint and increasing in
    tier order, so tier observables cannot cross by construction.
    """
    log_lo, log_hi = math.log(lo), math.log(hi)
    step = (log_hi - log_lo) / n_tiers
    return math.exp(log_hi - (tier_idx + 1) * step), math.exp(log_hi - tier_idx * step)
