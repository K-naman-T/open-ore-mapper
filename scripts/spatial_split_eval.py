#!/usr/bin/env python3
"""Spatial block train/val/test evaluation for Cuprite (research protocol).

Loads benchmarks/cuprite_real, builds scene endmembers from TRAIN blocks only,
runs classical baselines, scores TEST blocks only, writes:

  outputs/research_spatial_split/
    metrics_*.json
    report.md
    summary.json
    train_library.csv
    spatial_split.json

Usage:
  .venv/bin/python scripts/spatial_split_eval.py
  .venv/bin/python scripts/spatial_split_eval.py --rows 5 --cols 4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from open_ore_mapper.spatial_eval import run_spatial_split_eval  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Spatial-split Cuprite evaluation")
    p.add_argument(
        "--bench",
        type=Path,
        default=ROOT / "benchmarks" / "cuprite_real",
        help="Benchmark package directory",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "research_spatial_split",
        help="Output directory",
    )
    p.add_argument("--rows", type=int, default=4, help="Row blocks (default 4)")
    p.add_argument("--cols", type=int, default=4, help="Col blocks (default 4)")
    p.add_argument("--train-frac", type=float, default=0.5)
    p.add_argument("--val-frac", type=float, default=0.25)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--methods",
        type=str,
        default="sam,continuum_removal,mtmf,mnf_sam",
        help="Comma-separated methods",
    )
    p.add_argument("--sam-threshold-deg", type=float, default=12.0)
    p.add_argument("--min-confidence", type=float, default=0.50)
    p.add_argument("--mtmf-mf", type=float, default=0.3)
    p.add_argument("--mtmf-infeas", type=float, default=15.0)
    p.add_argument("--mnf-components", type=int, default=20)
    args = p.parse_args()

    bench = args.bench
    required = ["scene.tif", "reference.tif", "legend.json", "wavelengths.json"]
    missing = [f for f in required if not (bench / f).is_file()]
    if missing:
        print(f"Missing benchmark files in {bench}: {missing}")
        print("Build cuprite_real first (scripts/run_cuprite_real_validation.py).")
        return 1

    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    print(f"Benchmark: {bench}")
    print(f"Output:    {args.out}")
    print(f"Grid:      {args.rows}x{args.cols} blocks  seed={args.seed}")
    print(f"Methods:   {methods}")

    summary = run_spatial_split_eval(
        bench,
        args.out,
        n_row_blocks=args.rows,
        n_col_blocks=args.cols,
        train_frac=args.train_frac,
        val_frac=args.val_frac,
        seed=args.seed,
        methods=methods,
        sam_threshold_deg=args.sam_threshold_deg,
        min_confidence=args.min_confidence,
        mtmf_mf_threshold=args.mtmf_mf,
        mtmf_infeas_threshold=args.mtmf_infeas,
        mnf_components=args.mnf_components,
    )

    print("\n=== TEST OA scoreboard ===")
    for name, m in summary["methods"].items():
        flag = "" if m["available"] else " [UNAVAILABLE]"
        print(
            f"  {name:20s}  OA={m['overall_accuracy']:.4f}  "
            f"kappa={m['kappa']:.4f}  n={m['n_labeled']}{flag}"
        )
    print(f"\nWrote {args.out / 'report.md'}")
    print(json.dumps({k: v["overall_accuracy"] for k, v in summary["methods"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
