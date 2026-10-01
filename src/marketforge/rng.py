"""Seeded RNG — the single deterministic source of randomness for a run."""

from __future__ import annotations

import numpy as np
from numpy.random import Generator


def make_rng(seed: int) -> Generator:
    """Create the one RNG for a generation run.

    Every generator module receives this object explicitly and draws from it in a
    fixed order, so a run is a pure function of the seed.
    """
    return np.random.default_rng(seed)
