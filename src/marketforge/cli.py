"""MarketForge CLI (typer)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer

from marketforge.catalog import REGISTRY
from marketforge.config import GeneratorConfig, UniverseConfig
from marketforge.ingest import ingest_dataset
from marketforge.schemas import SCHEMAS
from marketforge.synthetic.generate import generate
from marketforge.verify import verify as verify_dataset

app = typer.Typer(
    help="MarketForge — statistical arbitrage in less crowded markets "
    "(Phase 0: synthetic data foundation)"
)


@app.command()
def gen(
    seed: int = typer.Option(42, help="RNG seed (same seed -> identical output)"),
    universe_size: int = typer.Option(50, help="Number of symbols"),
    start: str = typer.Option("2023-01-02", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option("2024-12-31", help="End date (YYYY-MM-DD)"),
    out_dir: str = typer.Option("data/synthetic", help="Output directory"),
) -> None:
    """Generate synthetic equity market data + ground-truth manifest."""
    cfg = GeneratorConfig(
        seed=seed,
        universe=UniverseConfig(
            n_symbols=universe_size,
            start=date.fromisoformat(start),
            end=date.fromisoformat(end),
        ),
    )
    paths = generate(cfg, Path(out_dir))
    typer.echo(f"Generated {len(paths)} files in {out_dir}:")
    for name, path in paths.items():
        typer.echo(f"  {name}: {path}")


@app.command()
def verify(
    data_dir: str = typer.Option("data/synthetic", help="Data directory"),
) -> None:
    """Verify a generated dataset against its manifest."""
    ok, report = verify_dataset(Path(data_dir))
    for line in report:
        typer.echo(line)
    if not ok:
        typer.echo("VERIFY FAILED")
        raise typer.Exit(code=1)
    typer.echo("VERIFY OK")


@app.command()
def schema() -> None:
    """Print the production schemas."""
    for name, s in SCHEMAS.items():
        typer.echo(f"{name}:")
        for field in s:
            typer.echo(f"  {field.name}: {field.type}")
        typer.echo()


@app.command()
def datasets() -> None:
    """List the registered datasets and their contracts."""
    for name, spec in REGISTRY.items():
        partition = ",".join(spec.partition_cols) or "-"
        pit = spec.pit_field or "-"
        lineage = " -> ".join(spec.lineage)
        typer.echo(
            f"{name}: version={spec.version} partition=({partition}) pit={pit} lineage={lineage}"
        )


@app.command()
def ingest(
    dataset: str = typer.Argument(..., help="Dataset name (see `marketforge datasets`)"),
    source_dir: str = typer.Option("data/synthetic", help="Directory holding <name>.parquet"),
    lakehouse: str = typer.Option("lake", help="Lakehouse root directory"),
) -> None:
    """Land a dataset in the lakehouse layout per its registry contract."""
    out = ingest_dataset(dataset, Path(source_dir), Path(lakehouse))
    typer.echo(f"Ingested {dataset} into {out['dataset']}")


if __name__ == "__main__":
    app()
