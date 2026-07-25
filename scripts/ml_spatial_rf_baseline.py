#!/usr/bin/env python3
"""Multi-seed sklearn RF baseline on Cuprite spatial protocol (Phase A).

Matches classical spatial_split_eval: train-block pure GT only, test-block metrics.

Usage:
  .venv/bin/python scripts/ml_spatial_rf_baseline.py \\
    --seeds 42,7,99,123,2024 \\
    --feature-sets reflectance,mnf,mtmf_scores,refl_mnf_mtmf \\
    --out outputs/research_ml_rf
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

from open_ore_mapper.ml_rf import FEATURE_SETS, run_rf_spatial_seed  # noqa: E402


def _parse_int_list(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def _parse_str_list(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def _mean_std(vals: list[float]) -> dict[str, float | None]:
    if not vals:
        return {"mean": None, "std": None, "n": 0}
    arr = np.asarray(vals, dtype=np.float64)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=0)),
        "n": int(arr.size),
    }


def _load_classical_means(path: Path) -> dict[str, dict[str, Any]] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows") or data
    by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if isinstance(rows, list):
        for r in rows:
            by_method[str(r["method"])].append(r)
    out: dict[str, dict[str, Any]] = {}
    for method, items in by_method.items():
        oas = [float(x["oa"]) for x in items]
        kappas = [float(x["kappa"]) for x in items]
        out[method] = {
            "oa": _mean_std(oas),
            "kappa": _mean_std(kappas),
            "n_seeds": len(items),
        }
    return out


def _write_report(
    path: Path,
    *,
    summary: dict[str, Any],
    classical: dict[str, dict[str, Any]] | None,
) -> None:
    lines = [
        "# RF spatial multi-seed baseline (Phase A)",
        "",
        f"- Benchmark: `{summary['benchmark']}`",
        f"- Seeds: {summary['seeds']}",
        f"- Feature sets: {summary['feature_sets']}",
        f"- Protocol: train-block pure GT → closed-set RF → test-block `evaluate_maps`",
        "",
        "## Scoreboard (mean ± std)",
        "",
        "| Feature set | OA | Kappa | Kaolinite R | N seeds |",
        "|-------------|----|-------|-------------|---------|",
    ]
    for fs, agg in summary["aggregates"].items():
        oa = agg["oa"]
        kap = agg["kappa"]
        kao = agg["kaolinite_recall"]
        oa_s = (
            f"{oa['mean']:.4f}±{oa['std']:.4f}" if oa["mean"] is not None else "—"
        )
        kap_s = (
            f"{kap['mean']:.4f}±{kap['std']:.4f}" if kap["mean"] is not None else "—"
        )
        if kao["mean"] is not None:
            kao_s = f"{kao['mean']:.4f}±{kao['std']:.4f}"
        else:
            kao_s = "—"
        lines.append(
            f"| {fs} | {oa_s} | {kap_s} | {kao_s} | {agg['n_ok']} |"
        )

    if classical:
        lines.extend(
            [
                "",
                "## Classical multi-seed (from `research_spatial_multi`)",
                "",
                "| Method | OA mean±std | Kappa mean±std | N seeds |",
                "|--------|-------------|----------------|---------|",
            ]
        )
        for method, agg in sorted(classical.items()):
            oa, kap = agg["oa"], agg["kappa"]
            lines.append(
                f"| {method} | {oa['mean']:.4f}±{oa['std']:.4f} | "
                f"{kap['mean']:.4f}±{kap['std']:.4f} | {agg['n_seeds']} |"
            )

    lines.extend(
        [
            "",
            "## Feature notes",
            "",
            "- `reflectance` — raw spectra",
            "- `mnf` — MNF (train-bg fit)",
            "- `mtmf_scores` — MF + infeasibility vs train endmembers",
            "- `refl_mnf_mtmf` — primary rich set (no full-scene CR)",
            "- `cr` / `cr_mnf` / `full` — CR only on train labels + valid predict pixels (chunked)",
            "",
            "## Leakage controls",
            "",
            "- Endmembers and MNF/MTMF stats from **train blocks only**",
            "- RF trained on **train pure GT** only (per-class sample cap)",
            "- Metrics on **test blocks only**",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Multi-seed RF spatial baseline")
    p.add_argument(
        "--bench",
        type=Path,
        default=ROOT / "benchmarks" / "cuprite_real",
        help="Benchmark package directory",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "research_ml_rf",
        help="Output root directory",
    )
    p.add_argument(
        "--seeds",
        type=str,
        default="42,7,99,123,2024",
        help="Comma-separated spatial split seeds",
    )
    p.add_argument(
        "--feature-sets",
        type=str,
        default="reflectance,mnf,mtmf_scores,refl_mnf_mtmf",
        help=f"Comma-separated feature sets (available: {','.join(FEATURE_SETS)})",
    )
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--train-frac", type=float, default=0.5)
    p.add_argument("--val-frac", type=float, default=0.25)
    p.add_argument("--n-estimators", type=int, default=200)
    p.add_argument("--max-depth", type=int, default=None)
    p.add_argument("--min-samples-leaf", type=int, default=2)
    p.add_argument("--rf-seed", type=int, default=0)
    p.add_argument("--mnf-components", type=int, default=20)
    p.add_argument("--max-train-per-class", type=int, default=2000)
    p.add_argument(
        "--classical-json",
        type=Path,
        default=ROOT / "outputs" / "research_spatial_multi" / "all_seeds.json",
        help="Optional classical multi-seed results for comparison table",
    )
    args = p.parse_args()

    bench = args.bench
    required = ["scene.tif", "reference.tif", "legend.json", "wavelengths.json"]
    missing = [f for f in required if not (bench / f).is_file()]
    if missing:
        print(f"Missing benchmark files in {bench}: {missing}")
        return 1

    seeds = _parse_int_list(args.seeds)
    feature_sets = _parse_str_list(args.feature_sets)
    for fs in feature_sets:
        if fs not in FEATURE_SETS:
            print(f"Unknown feature set {fs!r}; choose from {FEATURE_SETS}")
            return 1

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"Benchmark: {bench}")
    print(f"Output:    {out_root}")
    print(f"Seeds:     {seeds}")
    print(f"Features:  {feature_sets}")

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for seed in seeds:
        for fs in feature_sets:
            run_dir = out_root / f"seed_{seed}" / fs
            print(f"\n[ml_rf] seed={seed} feature_set={fs} → {run_dir}")
            try:
                summary = run_rf_spatial_seed(
                    bench,
                    run_dir,
                    seed=seed,
                    feature_set=fs,
                    n_row_blocks=args.rows,
                    n_col_blocks=args.cols,
                    train_frac=args.train_frac,
                    val_frac=args.val_frac,
                    n_estimators=args.n_estimators,
                    max_depth=args.max_depth,
                    min_samples_leaf=args.min_samples_leaf,
                    rf_seed=args.rf_seed,
                    mnf_components=args.mnf_components,
                    max_train_samples_per_class=args.max_train_per_class,
                )
                row = {
                    "seed": seed,
                    "feature_set": fs,
                    "method": f"rf_{fs}",
                    "oa": summary["overall_accuracy"],
                    "kappa": summary["kappa"],
                    "n": summary["n_labeled"],
                    "kaolinite_recall": summary.get("kaolinite_recall"),
                    "n_train_samples": summary.get("n_train_samples"),
                    "n_features": summary.get("n_features"),
                    "available": True,
                }
                rows.append(row)
                print(
                    f"  OA={row['oa']:.4f}  kappa={row['kappa']:.4f}  "
                    f"kaol_R={row['kaolinite_recall']}  n={row['n']}"
                )
            except Exception as exc:  # noqa: BLE001 — multi-seed runner continues
                print(f"  FAILED: {exc}")
                traceback.print_exc()
                failures.append(
                    {"seed": seed, "feature_set": fs, "error": str(exc)}
                )
                rows.append(
                    {
                        "seed": seed,
                        "feature_set": fs,
                        "method": f"rf_{fs}",
                        "oa": None,
                        "kappa": None,
                        "n": 0,
                        "kaolinite_recall": None,
                        "available": False,
                        "error": str(exc),
                    }
                )

    # Aggregate per feature set
    aggregates: dict[str, Any] = {}
    for fs in feature_sets:
        ok = [r for r in rows if r["feature_set"] == fs and r.get("available")]
        oas = [float(r["oa"]) for r in ok if r["oa"] is not None]
        kappas = [float(r["kappa"]) for r in ok if r["kappa"] is not None]
        kaos = [
            float(r["kaolinite_recall"])
            for r in ok
            if r.get("kaolinite_recall") is not None
        ]
        aggregates[fs] = {
            "oa": _mean_std(oas),
            "kappa": _mean_std(kappas),
            "kaolinite_recall": _mean_std(kaos),
            "n_ok": len(ok),
        }

    classical = _load_classical_means(Path(args.classical_json))

    all_payload = {
        "benchmark": str(bench),
        "seeds": seeds,
        "feature_sets": feature_sets,
        "rows": rows,
        "failures": failures,
    }
    (out_root / "all_seeds.json").write_text(
        json.dumps(all_payload, indent=2), encoding="utf-8"
    )

    summary_payload = {
        "benchmark": str(bench),
        "output_dir": str(out_root),
        "seeds": seeds,
        "feature_sets": feature_sets,
        "aggregates": aggregates,
        "classical_comparison": classical,
        "n_failures": len(failures),
        "rf_defaults": {
            "n_estimators": args.n_estimators,
            "max_depth": args.max_depth,
            "min_samples_leaf": args.min_samples_leaf,
            "rf_seed": args.rf_seed,
            "mnf_components": args.mnf_components,
            "max_train_per_class": args.max_train_per_class,
        },
    }
    (out_root / "summary.json").write_text(
        json.dumps(summary_payload, indent=2), encoding="utf-8"
    )
    _write_report(out_root / "report.md", summary=summary_payload, classical=classical)

    print("\n=== RF multi-seed scoreboard (mean±std OA) ===")
    for fs, agg in aggregates.items():
        m, s = agg["oa"]["mean"], agg["oa"]["std"]
        if m is None:
            print(f"  {fs:20s}  unavailable")
        else:
            print(f"  {fs:20s}  OA={m:.4f}±{s:.4f}  n={agg['n_ok']}")
    if classical:
        print("\n=== Classical (for comparison) ===")
        for method, agg in sorted(classical.items()):
            print(
                f"  {method:20s}  OA={agg['oa']['mean']:.4f}±{agg['oa']['std']:.4f}"
            )
    print(f"\nWrote {out_root / 'report.md'}")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
