from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .schemas import MatchOptions
from .engine import SpectralMatcher
from .wavelengths import parse_wavelengths_text


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spectral-match",
        description="Map exposed surface mineral signatures from hyperspectral raster cubes.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    predict = subparsers.add_parser("predict", help="Run SAM/NNLS mineral mapping on a raster cube")
    predict.add_argument("input", help="Input .tif, .tiff, .h5, .hdf5, or .mat raster cube")
    predict.add_argument("--sensor", default="cubert_ultris_s5", help="Sensor preset name")
    predict.add_argument("--wavelengths", help="Path to a JSON array of wavelengths")
    predict.add_argument("--library", help="Path to a user spectral library CSV")
    predict.add_argument("--classes", "--minerals", required=True, dest="classes", help="Comma-separated class names")
    predict.add_argument("--output-dir", required=True, help="Directory for result outputs")
    predict.add_argument("--sam-threshold-deg", type=float, default=12.0)
    predict.add_argument("--min-confidence", type=float, default=0.65)
    predict.add_argument("--tile-size", type=int, default=128)
    predict.add_argument("--normalization", choices=["none", "l2", "percentile"], default="l2")
    predict.add_argument("--exclude-bands", help="Comma-separated zero-based band indices to exclude (e.g. 0,3,10)")
    predict.add_argument("--min-band-valid-fraction", type=float, default=0.5)
    predict.add_argument(
        "--classifier",
        default="sam",
        choices=[
            "sam",
            "cr_sam",
            "mtmf",
            "mnf_sam",
            "mnf_mtmf",
            "fuse_classical",
        ],
        help=(
            "Classifier: sam=SAM+NNLS, cr_sam=CR region SAM, mtmf=mixture-tuned MF, "
            "mnf_sam=MNF+SAM, mnf_mtmf=MNF then MTMF, fuse_classical=MTMF+CR-SAM+MNF-SAM fusion"
        ),
    )
    predict.add_argument("--mf-threshold", type=float, default=0.5, help="MTMF MF acceptance threshold")
    predict.add_argument(
        "--infeas-threshold",
        type=float,
        default=10.0,
        help="MTMF infeasibility rejection threshold",
    )
    predict.add_argument(
        "--n-mnf-components",
        type=int,
        default=20,
        help="MNF components for mnf_sam / mnf_mtmf",
    )
    predict.set_defaults(func=_run_predict)

    qc = subparsers.add_parser("qc-raster", help="Run raster quality control and band analysis")
    qc.add_argument("input", help="Input .tif, .tiff, .h5, .hdf5, or .mat raster cube")
    qc.add_argument("--sensor", default="cubert_ultris_s5", help="Sensor preset name")
    qc.add_argument("--wavelengths", help="Path to a JSON array of wavelengths")
    qc.add_argument("--exclude-bands", help="Comma-separated zero-based band indices to exclude (e.g. 0,3,10)")
    qc.add_argument("--min-band-valid-fraction", type=float, default=0.5)
    qc.add_argument("--output", help="Path to write quality report JSON (default: stdout)")
    qc.set_defaults(func=_run_qc_raster)
    return parser


def _run_predict(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    wavelengths = None
    if args.wavelengths:
        wavelengths = parse_wavelengths_text(Path(args.wavelengths).read_text(encoding="utf-8"))

    classes = [name.strip() for name in args.classes.split(",") if name.strip()]

    excluded = []
    if args.exclude_bands:
        excluded = [int(i.strip()) for i in args.exclude_bands.split(",") if i.strip()]

    options = MatchOptions(
        wavelengths=wavelengths,
        sensor=str(args.sensor),
        classes=list(classes),
        spectral_library=args.library,
        sam_threshold_deg=float(args.sam_threshold_deg),
        min_confidence=float(args.min_confidence),
        tile_size=int(args.tile_size),
        normalization=str(args.normalization),
        excluded_band_indices=excluded,
        min_band_valid_fraction=float(args.min_band_valid_fraction),
        classifier=str(getattr(args, "classifier", "sam")),
        mf_threshold=float(getattr(args, "mf_threshold", 0.5)),
        infeas_threshold=float(getattr(args, "infeas_threshold", 10.0)),
        n_mnf_components=int(getattr(args, "n_mnf_components", 20)),
    )
    mapper = SpectralMatcher()
    result = mapper.predict_file(args.input, options)
    response = mapper.to_response(result)

    (output_dir / "result.json").write_text(json.dumps(response, indent=2), encoding="utf-8")
    print(f"Wrote results to {output_dir}")
    return 0


def _run_qc_raster(args: argparse.Namespace) -> int:
    wavelengths = None
    if args.wavelengths:
        wavelengths = parse_wavelengths_text(Path(args.wavelengths).read_text(encoding="utf-8"))

    excluded = []
    if args.exclude_bands:
        excluded = [int(i.strip()) for i in args.exclude_bands.split(",") if i.strip()]

    options = MatchOptions(
        wavelengths=wavelengths,
        sensor=str(args.sensor),
        excluded_band_indices=excluded,
        min_band_valid_fraction=float(args.min_band_valid_fraction),
    )
    mapper = SpectralMatcher()
    report = mapper.quality_file(args.input, options)
    response = mapper.to_quality_response(report)

    output_text = json.dumps(response, indent=2)
    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"Wrote quality report to {args.output}")
    else:
        print(output_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
