"""MarketForge CLI (typer)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer

from marketforge.config import GeneratorConfig, UniverseConfig
from marketforge.schemas import BARS_SCHEMA, MANIFEST_SCHEMA, REFERENCE_SCHEMA
from marketforge.synthetic.generate import generate
from marketforge.verify import verify as verify_dataset

app = typer.Typer(help="MarketForge — synthetic equity market-data platform (Phase 0)")


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
    for name, s in (
        ("reference", REFERENCE_SCHEMA),
        ("bars", BARS_SCHEMA),
        ("manifest", MANIFEST_SCHEMA),
    ):
        typer.echo(f"{name}:")
        for field in s:
            typer.echo(f"  {field.name}: {field.type}")
        typer.echo()


if __name__ == "__main__":
    app()
