#!/usr/bin/env python3
"""Multi-seed 1D-CNN on Cuprite spatial protocol.

Usage:
  .venv/bin/python scripts/ml_spatial_cnn1d_baseline.py \\
    --seeds 42,7,99,123,2024 \\
    --feature-mode mnf \\
    --epochs 15 \\
    --out outputs/research_ml_cnn1d
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from open_ore_mapper.ml_cnn1d import run_cnn1d_spatial_seed  # noqa: E402


def _parse_int_list(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def _mean_std(vals: list[float]) -> dict[str, float | None]:
    if not vals:
        return {"mean": None, "std": None, "n": 0}
    arr = np.asarray(vals, dtype=np.float64)
    return {"mean": float(arr.mean()), "std": float(arr.std(ddof=0)), "n": int(arr.size)}


def main() -> int:
    p = argparse.ArgumentParser(description="Multi-seed 1D-CNN spatial baseline")
    p.add_argument("--bench", type=Path, default=ROOT / "benchmarks" / "cuprite_real")
    p.add_argument("--out", type=Path, default=ROOT / "outputs" / "research_ml_cnn1d")
    p.add_argument("--seeds", type=str, default="42,7,99,123,2024")
    p.add_argument("--feature-mode", type=str, default="mnf", choices=["mnf", "reflectance"])
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--mnf-components", type=int, default=30)
    p.add_argument("--max-train-per-class", type=int, default=2000)
    p.add_argument("--epochs", type=int, default=15)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--channels", type=int, default=32)
    p.add_argument("--device", type=str, default=None)
    p.add_argument(
        "--rf-summary",
        type=Path,
        default=ROOT / "outputs" / "research_ml_rf" / "summary.json",
    )
    p.add_argument(
        "--boost-summary",
        type=Path,
        default=ROOT / "outputs" / "research_ml_boost" / "summary.json",
    )
    args = p.parse_args()

    bench = args.bench
    missing = [
        f
        for f in ("scene.tif", "reference.tif", "legend.json", "wavelengths.json")
        if not (bench / f).is_file()
    ]
    if missing:
        print(f"Missing benchmark files in {bench}: {missing}")
        return 1

    seeds = _parse_int_list(args.seeds)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    mode = args.feature_mode

    print(f"Benchmark: {bench}")
    print(f"Output:    {out_root}")
    print(f"Seeds:     {seeds}")
    print(f"Mode:      {mode}")
    print(f"Epochs:    {args.epochs}")

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for seed in seeds:
        run_dir = out_root / f"seed_{seed}" / mode
        print(f"\n[ml_cnn1d] seed={seed} mode={mode} → {run_dir}")
        try:
            summary = run_cnn1d_spatial_seed(
                bench,
                run_dir,
                seed=seed,
                feature_mode=mode,
                n_row_blocks=args.rows,
                n_col_blocks=args.cols,
                mnf_components=args.mnf_components,
                max_train_samples_per_class=args.max_train_per_class,
                epochs=args.epochs,
                batch_size=args.batch_size,
                lr=args.lr,
                channels=args.channels,
                device=args.device,
            )
            row = {
                "seed": seed,
                "feature_mode": mode,
                "method": summary["method"],
                "oa": summary["overall_accuracy"],
                "kappa": summary["kappa"],
                "n": summary["n_labeled"],
                "kaolinite_recall": summary.get("kaolinite_recall"),
                "n_train_samples": summary.get("n_train_samples"),
                "device": summary.get("device"),
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
            failures.append({"seed": seed, "error": str(exc)})
            rows.append(
                {
                    "seed": seed,
                    "feature_mode": mode,
                    "oa": None,
                    "kappa": None,
                    "n": 0,
                    "available": False,
                    "error": str(exc),
                }
            )

    ok = [r for r in rows if r.get("available")]
    oas = [float(r["oa"]) for r in ok if r["oa"] is not None]
    kappas = [float(r["kappa"]) for r in ok if r["kappa"] is not None]
    kaos = [float(r["kaolinite_recall"]) for r in ok if r.get("kaolinite_recall") is not None]
    aggregates = {
        f"cnn1d_{mode}": {
            "oa": _mean_std(oas),
            "kappa": _mean_std(kappas),
            "kaolinite_recall": _mean_std(kaos),
            "n_ok": len(ok),
        }
    }

    rf = json.loads(args.rf_summary.read_text()) if args.rf_summary.is_file() else None
    boost = json.loads(args.boost_summary.read_text()) if args.boost_summary.is_file() else None

    all_payload = {
        "benchmark": str(bench),
        "seeds": seeds,
        "feature_mode": mode,
        "epochs": args.epochs,
        "rows": rows,
        "failures": failures,
        "aggregates": aggregates,
        "rf_comparison": rf.get("aggregates") if rf else None,
        "boost_comparison": boost.get("aggregates") if boost else None,
        "n_failures": len(failures),
        "protocol": {
            "split": "spatial_block",
            "score_region": "test_blocks_only",
            "train": "train-block pure GT only",
            "transforms": "train-block MNF only when mode=mnf",
        },
    }
    (out_root / "all_seeds.json").write_text(json.dumps(all_payload, indent=2), encoding="utf-8")
    (out_root / "summary.json").write_text(json.dumps(all_payload, indent=2), encoding="utf-8")

    lines = [
        "# 1D-CNN spatial multi-seed baseline",
        "",
        f"- Benchmark: `{bench}`",
        f"- Feature mode: `{mode}`",
        f"- Seeds: {seeds}",
        f"- Epochs: {args.epochs}",
        "- Protocol: train-block pure GT → closed-set 1D-CNN → test-block evaluate_maps",
        "",
        "## Scoreboard (mean ± std)",
        "",
        "| Method | OA | Kappa | Kaolinite R | N seeds |",
        "|--------|----|-------|-------------|---------|",
    ]
    for key, agg in aggregates.items():
        oa, kap, kao = agg["oa"], agg["kappa"], agg["kaolinite_recall"]
        oa_s = f"{oa['mean']:.4f}±{oa['std']:.4f}" if oa["mean"] is not None else "—"
        kap_s = f"{kap['mean']:.4f}±{kap['std']:.4f}" if kap["mean"] is not None else "—"
        kao_s = f"{kao['mean']:.4f}±{kao['std']:.4f}" if kao["mean"] is not None else "—"
        lines.append(f"| {key} | {oa_s} | {kap_s} | {kao_s} | {agg['n_ok']} |")

    if rf and rf.get("aggregates"):
        lines.extend(["", "## RF comparison", "", "| FS | OA |", "|----|----|"])
        for fs, agg in rf["aggregates"].items():
            if agg["oa"].get("mean") is not None:
                lines.append(f"| rf_{fs} | {agg['oa']['mean']:.4f}±{agg['oa']['std']:.4f} |")

    lines.extend(
        [
            "",
            "## Leakage controls",
            "",
            "- MNF fit on train blocks only (when mode=mnf)",
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
