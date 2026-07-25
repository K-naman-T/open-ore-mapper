#!/usr/bin/env python3
"""Multi-seed gradient boosting on Cuprite spatial protocol.

Usage:
  .venv/bin/python scripts/ml_spatial_boost_baseline.py \\
    --seeds 42,7,99,123,2024 \\
    --feature-sets mnf,refl_mnf_mtmf \\
    --backend hist \\
    --out outputs/research_ml_boost
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from open_ore_mapper.ml_boost import BOOST_BACKENDS, run_boost_spatial_seed  # noqa: E402
from open_ore_mapper.ml_rf import FEATURE_SETS  # noqa: E402


def _parse_int_list(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def _parse_str_list(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def _mean_std(vals: list[float]) -> dict[str, float | None]:
    if not vals:
        return {"mean": None, "std": None, "n": 0}
    arr = np.asarray(vals, dtype=np.float64)
    return {"mean": float(arr.mean()), "std": float(arr.std(ddof=0)), "n": int(arr.size)}


def _load_rf_means(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description="Multi-seed boosting spatial baseline")
    p.add_argument("--bench", type=Path, default=ROOT / "benchmarks" / "cuprite_real")
    p.add_argument("--out", type=Path, default=ROOT / "outputs" / "research_ml_boost")
    p.add_argument("--seeds", type=str, default="42,7,99,123,2024")
    p.add_argument("--feature-sets", type=str, default="mnf,refl_mnf_mtmf")
    p.add_argument("--backend", type=str, default="hist", help=f"one of {BOOST_BACKENDS}")
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--n-estimators", type=int, default=200)
    p.add_argument("--learning-rate", type=float, default=0.1)
    p.add_argument("--min-samples-leaf", type=int, default=20)
    p.add_argument("--mnf-components", type=int, default=20)
    p.add_argument("--max-train-per-class", type=int, default=2000)
    p.add_argument(
        "--rf-summary",
        type=Path,
        default=ROOT / "outputs" / "research_ml_rf" / "summary.json",
    )
    args = p.parse_args()

    bench = args.bench
    missing = [f for f in ("scene.tif", "reference.tif", "legend.json", "wavelengths.json") if not (bench / f).is_file()]
    if missing:
        print(f"Missing benchmark files in {bench}: {missing}")
        return 1

    seeds = _parse_int_list(args.seeds)
    feature_sets = _parse_str_list(args.feature_sets)
    for fs in feature_sets:
        if fs not in FEATURE_SETS:
            print(f"Unknown feature set {fs!r}")
            return 1

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    backend = args.backend

    print(f"Benchmark: {bench}")
    print(f"Output:    {out_root}")
    print(f"Seeds:     {seeds}")
    print(f"Features:  {feature_sets}")
    print(f"Backend:   {backend}")

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for seed in seeds:
        for fs in feature_sets:
            run_dir = out_root / f"seed_{seed}" / f"{backend}_{fs}"
            print(f"\n[ml_boost] seed={seed} backend={backend} feature_set={fs} → {run_dir}")
            try:
                summary = run_boost_spatial_seed(
                    bench,
                    run_dir,
                    seed=seed,
                    feature_set=fs,
                    backend=backend,
                    n_row_blocks=args.rows,
                    n_col_blocks=args.cols,
                    n_estimators=args.n_estimators,
                    learning_rate=args.learning_rate,
                    min_samples_leaf=args.min_samples_leaf,
                    mnf_components=args.mnf_components,
                    max_train_samples_per_class=args.max_train_per_class,
                )
                row = {
                    "seed": seed,
                    "feature_set": fs,
                    "backend": backend,
                    "method": summary["method"],
                    "oa": summary["overall_accuracy"],
                    "kappa": summary["kappa"],
                    "n": summary["n_labeled"],
                    "kaolinite_recall": summary.get("kaolinite_recall"),
                    "n_train_samples": summary.get("n_train_samples"),
                    "available": True,
                }
                rows.append(row)
                print(
                    f"  OA={row['oa']:.4f}  kappa={row['kappa']:.4f}  "
                    f"kaol_R={row['kaolinite_recall']}  n={row['n']}"
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  FAILED: {exc}")
                traceback.print_exc()
                failures.append({"seed": seed, "feature_set": fs, "error": str(exc)})
                rows.append(
                    {
                        "seed": seed,
                        "feature_set": fs,
                        "backend": backend,
                        "oa": None,
                        "kappa": None,
                        "n": 0,
                        "available": False,
                        "error": str(exc),
                    }
                )

    aggregates: dict[str, Any] = {}
    for fs in feature_sets:
        ok = [r for r in rows if r["feature_set"] == fs and r.get("available")]
        oas = [float(r["oa"]) for r in ok if r["oa"] is not None]
        kappas = [float(r["kappa"]) for r in ok if r["kappa"] is not None]
        kaos = [float(r["kaolinite_recall"]) for r in ok if r.get("kaolinite_recall") is not None]
        key = f"{backend}_{fs}"
        aggregates[key] = {
            "oa": _mean_std(oas),
            "kappa": _mean_std(kappas),
            "kaolinite_recall": _mean_std(kaos),
            "n_ok": len(ok),
        }

    rf_summary = _load_rf_means(Path(args.rf_summary))
    all_payload = {
        "benchmark": str(bench),
        "seeds": seeds,
        "feature_sets": feature_sets,
        "backend": backend,
        "rows": rows,
        "failures": failures,
        "aggregates": aggregates,
        "rf_comparison": rf_summary.get("aggregates") if rf_summary else None,
        "n_failures": len(failures),
        "protocol": {
            "split": "spatial_block",
            "score_region": "test_blocks_only",
            "train": "train-block pure GT only",
            "transforms": "train-block only",
        },
    }
    (out_root / "all_seeds.json").write_text(json.dumps(all_payload, indent=2), encoding="utf-8")
    (out_root / "summary.json").write_text(json.dumps(all_payload, indent=2), encoding="utf-8")

    lines = [
        "# Boosting spatial multi-seed baseline",
        "",
        f"- Benchmark: `{bench}`",
        f"- Backend: `{backend}`",
        f"- Seeds: {seeds}",
        f"- Feature sets: {feature_sets}",
        "- Protocol: train-block pure GT → closed-set boost → test-block evaluate_maps",
        "",
        "## Scoreboard (mean ± std)",
        "",
        "| Config | OA | Kappa | Kaolinite R | N seeds |",
        "|--------|----|-------|-------------|---------|",
    ]
    for key, agg in aggregates.items():
        oa, kap, kao = agg["oa"], agg["kappa"], agg["kaolinite_recall"]
        oa_s = f"{oa['mean']:.4f}±{oa['std']:.4f}" if oa["mean"] is not None else "—"
        kap_s = f"{kap['mean']:.4f}±{kap['std']:.4f}" if kap["mean"] is not None else "—"
        kao_s = f"{kao['mean']:.4f}±{kao['std']:.4f}" if kao["mean"] is not None else "—"
        lines.append(f"| {key} | {oa_s} | {kap_s} | {kao_s} | {agg['n_ok']} |")

    if rf_summary and rf_summary.get("aggregates"):
        lines.extend(
            [
                "",
                "## RF multi-seed comparison",
                "",
                "| Feature set | OA mean±std |",
                "|-------------|-------------|",
            ]
        )
        for fs, agg in rf_summary["aggregates"].items():
            oa = agg["oa"]
            if oa.get("mean") is not None:
                lines.append(f"| rf_{fs} | {oa['mean']:.4f}±{oa['std']:.4f} |")

    lines.extend(
        [
            "",
            "## Leakage controls",
            "",
            "- MNF/MTMF fit on train blocks only",
            "- Labels: train pure GT only",
            "- Metrics: test blocks only",
            "",
        ]
    )
    (out_root / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {out_root / 'summary.json'} and report.md")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
