from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Sequence

from .public_scenes import download_scene, scene_catalog_as_json
from .schemas import DEFAULT_DEMO_MINERALS, MapperOptions
from .service import OreMapper
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
        prog="open-ore-mapper",
        description="Map exposed surface mineral signatures from hyperspectral raster cubes.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    predict = subparsers.add_parser("predict", help="Run SAM/NNLS mineral mapping on a raster cube")
    predict.add_argument("input", help="Input .tif, .tiff, .h5, .hdf5, or .mat raster cube")
    predict.add_argument("--sensor", default="cubert_ultris_s5", help="Sensor preset name")
    predict.add_argument("--wavelengths", help="Path to a JSON array of wavelengths")
    predict.add_argument("--library", help="Path to a user spectral library CSV")
    predict.add_argument("--minerals", help="Comma-separated mineral names")
    predict.add_argument("--output-dir", required=True, help="Directory for result outputs")
    predict.add_argument("--sam-threshold-deg", type=float, default=12.0)
    predict.add_argument("--min-confidence", type=float, default=0.65)
    predict.add_argument("--tile-size", type=int, default=128)
    predict.add_argument("--normalization", choices=["none", "l2", "percentile"], default="l2")
    predict.add_argument("--exclude-bands", help="Comma-separated zero-based band indices to exclude (e.g. 0,3,10)")
    predict.add_argument("--min-band-valid-fraction", type=float, default=0.5)
    predict.set_defaults(func=_run_predict)

    qc = subparsers.add_parser("qc-raster", help="Run raster quality control and band analysis")
    qc.add_argument("input", help="Input .tif, .tiff, .h5, .hdf5, or .mat raster cube")
    qc.add_argument("--sensor", default="cubert_ultris_s5", help="Sensor preset name")
    qc.add_argument("--wavelengths", help="Path to a JSON array of wavelengths")
    qc.add_argument("--exclude-bands", help="Comma-separated zero-based band indices to exclude (e.g. 0,3,10)")
    qc.add_argument("--min-band-valid-fraction", type=float, default=0.5)
    qc.add_argument("--output", help="Path to write quality report JSON (default: stdout)")
    qc.set_defaults(func=_run_qc_raster)

    list_scenes = subparsers.add_parser(
        "list-scenes", help="List available public hyperspectral scenes for download"
    )
    list_scenes.set_defaults(func=_run_list_scenes)

    download = subparsers.add_parser(
        "download-scene", help="Download a public hyperspectral scene (.mat) for testing"
    )
    download.add_argument("scene_id", help="Scene identifier from list-scenes")
    download.add_argument("--output-dir", required=True, help="Directory to save the downloaded .mat file")
    download.add_argument(
        "--source-url",
        help="Override download URL (for testing with local files)",
    )
    download.set_defaults(func=_run_download_scene)

    fetch = subparsers.add_parser("fetch-library", help="Download reference mineral spectra from RELAB")
    fetch.add_argument("--minerals", help="Comma-separated list of mineral names to fetch", default=None)
    fetch.add_argument("--class", dest="mineral_class", help="Mineral class filter", default=None)
    fetch.add_argument("--output", help="Output directory", default=None)
    fetch.set_defaults(func=_run_fetch_library)
    return parser


def _run_predict(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    wavelengths = None
    if args.wavelengths:
        wavelengths = parse_wavelengths_text(Path(args.wavelengths).read_text(encoding="utf-8"))

    minerals = DEFAULT_DEMO_MINERALS
    if args.minerals:
        minerals = [name.strip() for name in args.minerals.split(",") if name.strip()]

    excluded = []
    if args.exclude_bands:
        excluded = [int(i.strip()) for i in args.exclude_bands.split(",") if i.strip()]

    options = MapperOptions(
        wavelengths=wavelengths,
        sensor=str(args.sensor),
        minerals=list(minerals),
        spectral_library=args.library,
        sam_threshold_deg=float(args.sam_threshold_deg),
        min_confidence=float(args.min_confidence),
        tile_size=int(args.tile_size),
        normalization=str(args.normalization),
        excluded_band_indices=excluded,
        min_band_valid_fraction=float(args.min_band_valid_fraction),
    )
    mapper = OreMapper()
    result = mapper.predict_file(args.input, options)
    response = mapper.to_response(result)

    (output_dir / "result.json").write_text(json.dumps(response, indent=2), encoding="utf-8")
    if result.quality_report is not None:
        (output_dir / "quality_report.json").write_text(
            json.dumps(mapper.to_quality_response(result.quality_report), indent=2),
            encoding="utf-8",
        )
    _write_png(output_dir / "class_map.png", result.output_image)
    _write_png(output_dir / "confidence.png", result.confidence_image)
    _write_png(output_dir / "top_abundance.png", result.top_abundance_image)
    print(f"Wrote results to {output_dir}")
    return 0


def _run_qc_raster(args: argparse.Namespace) -> int:
    wavelengths = None
    if args.wavelengths:
        wavelengths = parse_wavelengths_text(Path(args.wavelengths).read_text(encoding="utf-8"))

    excluded = []
    if args.exclude_bands:
        excluded = [int(i.strip()) for i in args.exclude_bands.split(",") if i.strip()]

    options = MapperOptions(
        wavelengths=wavelengths,
        sensor=str(args.sensor),
        excluded_band_indices=excluded,
        min_band_valid_fraction=float(args.min_band_valid_fraction),
    )
    mapper = OreMapper()
    report = mapper.quality_file(args.input, options)
    response = mapper.to_quality_response(report)

    output_text = json.dumps(response, indent=2)
    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"Wrote quality report to {args.output}")
    else:
        print(output_text)
    return 0


def _run_list_scenes(args: argparse.Namespace) -> int:
    print(scene_catalog_as_json())
    return 0


def _run_download_scene(args: argparse.Namespace) -> int:
    dest = download_scene(
        args.scene_id,
        args.output_dir,
        source_url=args.source_url,
    )
    print(f"Downloaded {args.scene_id} to {dest}")
    return 0


def _run_fetch_library(args: argparse.Namespace) -> int:
    from .relab_fetcher import build_spectral_library, fetch_relab_entries, CACHE_DIR

    minerals: list[str] | None = None
    if args.minerals:
        minerals = [name.strip() for name in args.minerals.split(",") if name.strip()]

    output_dir = Path(args.output) if args.output else CACHE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if minerals:
        print(f"Fetching RELAB spectra for: {', '.join(minerals)}")
        library = build_spectral_library(target_minerals=minerals)
        print(f"Found {len(library.names)} spectra for {', '.join(minerals)}")
        print(f"Wavelength range: {float(library.wavelengths[0]):.1f} – {float(library.wavelengths[-1]):.1f} nm")
        print(f"Spectra shape: {library.spectra.shape}")
        index_path = output_dir / "index.json"
        if index_path.exists():
            index_text = index_path.read_text(encoding="utf-8")
        else:
            from .relab_fetcher import RelabIndex
            index = RelabIndex([])
            index_text = index.to_json()
            index_path.write_text(index_text, encoding="utf-8")
        print(f"Index written to {index_path}")
    else:
        entries = fetch_relab_entries()
        print(f"Indexed {len(entries)} RELAB spectra")
        mineral_classes: dict[str, int] = {}
        for e in entries:
            mineral_classes[e.mineral_class] = mineral_classes.get(e.mineral_class, 0) + 1
        for cls_name, count in sorted(mineral_classes.items()):
            print(f"  {cls_name}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


def _write_png(path: Path, data_url: str) -> None:
    prefix = "data:image/png;base64,"
    if not data_url.startswith(prefix):
        raise ValueError("Expected PNG data URL")
    path.write_bytes(base64.b64decode(data_url[len(prefix) :]))
