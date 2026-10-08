# MarketForge — development targets.
# Uses `>` as the recipe prefix (`.RECIPEPREFIX`) so this file is tab-free and
# portable. Requires GNU Make >= 4.0 (WSL2/Ubuntu and GitHub Actions both ship it).
.RECIPEPREFIX = >

.PHONY: sync test lint type fmt ci up down gen verify schema duckdb datasets ingest clean

## Install the pinned environment (Python 3.12 + all deps).
sync:
> uv sync

## Run the test suite.
test:
> uv run pytest

## Lint (ruff) and check formatting.
lint:
> uv run ruff check .
> uv run ruff format --check .

## Type-check the package.
type:
> uv run mypy src tests

## Auto-format.
fmt:
> uv run ruff check --fix .
> uv run ruff format .

## Full CI gate: lint + format + type + tests (incl. DuckDB smoke test).
ci:
> uv run ruff check .
> uv run ruff format --check .
> uv run mypy src tests
> uv run pytest

## Start the local services (Redpanda broker; DuckDB is embedded, see `duckdb` target).
up:
> docker compose up -d

## Stop the local services.
down:
> docker compose down

## Generate synthetic data (default seed 42).
gen:
> uv run marketforge gen

## Verify a generated dataset against its ground-truth manifest.
verify:
> uv run marketforge verify

## Print the production schemas.
schema:
> uv run marketforge schema

## List the dataset registry contracts.
datasets:
> uv run marketforge datasets

## Land the generated bars in the lakehouse layout (per the registry contract).
ingest:
> uv run marketforge ingest bars

## Open an interactive DuckDB SQL shell (one-off container) over the generated data.
duckdb:
> docker run --rm -it -v "${PWD}/data:/data" -w /data duckdb/duckdb duckdb /data/catalog.db

## Remove generated data and caches.
clean:
> rm -rf data lake .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
