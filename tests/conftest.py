from __future__ import annotations

from datetime import date

import pytest

from marketforge.config import GeneratorConfig, UniverseConfig


@pytest.fixture
def small_config() -> GeneratorConfig:
    """A small, fast universe for tests."""
    return GeneratorConfig(
        seed=42,
        universe=UniverseConfig(n_symbols=8, start=date(2023, 1, 2), end=date(2023, 12, 29)),
    )
