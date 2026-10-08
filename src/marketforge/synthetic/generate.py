"""Orchestrator: seed -> universe -> coverage -> bars -> events -> manifest -> export."""

from __future__ import annotations

from pathlib import Path

from marketforge.config import GeneratorConfig
from marketforge.rng import make_rng
from marketforge.synthetic.bars import generate_bars
from marketforge.synthetic.coverage import build_coverage, coverage_to_json
from marketforge.synthetic.events import apply_events
from marketforge.synthetic.export import export
from marketforge.synthetic.manifest import build_manifest, manifest_to_json
from marketforge.synthetic.universe import build_reference


def generate(cfg: GeneratorConfig, out_dir: Path) -> dict[str, Path]:
    """Run the full synthetic-data generation pipeline."""
    rng = make_rng(cfg.seed)
    reference = build_reference(cfg.universe, rng)
    coverage = build_coverage(reference, cfg, rng)
    bars = generate_bars(reference, coverage, cfg, rng)
    bars, events = apply_events(bars, reference, cfg, rng)
    manifest = build_manifest(events, cfg.seed)

    paths = export(reference, bars, coverage, manifest, out_dir)
    manifest_json_path = out_dir / "manifest.json"
    manifest_json_path.write_text(manifest_to_json(manifest, cfg.seed), encoding="utf-8")
    paths["manifest_json"] = manifest_json_path
    coverage_json_path = out_dir / "coverage.json"
    coverage_json_path.write_text(coverage_to_json(coverage, cfg), encoding="utf-8")
    paths["coverage_json"] = coverage_json_path
    return paths
