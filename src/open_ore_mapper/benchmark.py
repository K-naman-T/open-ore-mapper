"""Run predict + evaluate against a benchmark package directory."""

from __future__ import annotations

import base64
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import tifffile

from .evaluate import (
    UNKNOWN_CLASS,
    rasterize_rois,
    write_evaluation_artifacts,
)
from .preprocessing import select_bands
from .qc import analyze_raster_quality
from .schemas import MapperOptions
from .service import OreMapper


def load_benchmark_options(bench_dir: Path) -> MapperOptions:
    raw: dict[str, Any] = {}
    opt_path = bench_dir / "options.json"
    if opt_path.is_file():
        raw = json.loads(opt_path.read_text(encoding="utf-8"))
    legend = json.loads((bench_dir / "legend.json").read_text(encoding="utf-8"))
    minerals = list(raw.get("minerals") or legend.get("class_names") or [])
    wavelengths = None
    wl_path = bench_dir / "wavelengths.json"
    if wl_path.is_file():
        wavelengths = [float(x) for x in json.loads(wl_path.read_text(encoding="utf-8"))]
    library = bench_dir / "library.csv"
    if not library.is_file():
        raise FileNotFoundError(f"Missing library.csv in {bench_dir}")
    return MapperOptions(
        wavelengths=wavelengths,
        sensor=str(raw.get("sensor", "manual")),
        minerals=minerals,
        spectral_library=str(library),
        sam_threshold_deg=float(raw.get("sam_threshold_deg", 25.0)),
        min_confidence=float(raw.get("min_confidence", 0.0)),
        tile_size=int(raw.get("tile_size", 32)),
        normalization=str(raw.get("normalization", "l2")),
        classifier=str(raw.get("classifier", "sam")),
        use_ace=False,
        vegetation_mask=False,
        use_mtmf=bool(raw.get("use_mtmf", False)),
        mf_threshold=float(raw.get("mf_threshold", 0.5)),
        infeas_threshold=float(raw.get("infeas_threshold", 10.0)),
        n_mnf_components=int(raw.get("n_mnf_components", 20)),
        min_band_valid_fraction=float(raw.get("min_band_valid_fraction", 0.0)),
    )


def load_reference(bench_dir: Path, height: int, width: int, class_names: list[str]) -> np.ndarray:
    legend = json.loads((bench_dir / "legend.json").read_text(encoding="utf-8"))
    ignore = int(legend.get("ignore_index", UNKNOWN_CLASS))
    ref_path = bench_dir / "reference.tif"
    if ref_path.is_file():
        ref = np.asarray(tifffile.imread(ref_path))
        if ref.ndim == 3:
            ref = ref[:, :, 0]
        if ref.shape != (height, width):
            raise ValueError(f"reference shape {ref.shape} != predicted {(height, width)}")
        return ref.astype(np.uint8)
    rois_path = bench_dir / "rois.json"
    if rois_path.is_file():
        rois = json.loads(rois_path.read_text(encoding="utf-8"))
        name_to_index = {n: i for i, n in enumerate(class_names)}
        return rasterize_rois(height, width, rois, name_to_index, ignore_index=ignore)
    raise FileNotFoundError(f"Need reference.tif or rois.json in {bench_dir}")


def run_benchmark(
    bench_dir: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Predict scene in package, evaluate vs reference, write scorecard artifacts."""
    bench = Path(bench_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    scene = bench / "scene.tif"
    if not scene.is_file():
        # allow .tiff
        alts = list(bench.glob("scene.tif*"))
        if not alts:
            raise FileNotFoundError(f"No scene.tif in {bench}")
        scene = alts[0]

    options = load_benchmark_options(bench)
    om = OreMapper()
    result = om.predict_file(scene, options)

    cube, emb, auto_ex = om._load_cube(scene.read_bytes(), scene.name)
    wls, sensor = om._resolve_wavelengths(options, cube.shape[2], emb)
    if not options.excluded_band_indices and auto_ex:
        options = replace(options, excluded_band_indices=auto_ex)

    report = analyze_raster_quality(
        cube,
        wls,
        excluded_band_indices=options.excluded_band_indices or None,
        min_band_valid_fraction=options.min_band_valid_fraction,
    )
    cube_f, retained = select_bands(cube, wls, report.retained_band_indices)
    library = om._load_library(options, retained)
    class_map, _conf_map, _abund = om._classify_core(cube_f, retained, library, options)

    class_names = list(library.names)
    reference = load_reference(bench, class_map.shape[0], class_map.shape[1], class_names)

    eval_result = write_evaluation_artifacts(
        out,
        class_map,
        reference,
        class_names,
        ignore_index=UNKNOWN_CLASS,
        extra_metrics={
            "benchmark": str(bench),
            "model_used": result.model_used,
            "sensor": sensor,
            "classifier": options.classifier,
            "library": options.spectral_library,
            "wavelengths_used": len(retained),
            "minerals": class_names,
            "warnings": result.warnings,
        },
    )

    _write_png_data_url(out / "prediction_class.png", result.output_image)
    _write_png_data_url(out / "prediction_confidence.png", result.confidence_image)

    summary = eval_result.to_dict()
    summary["model_used"] = result.model_used
    summary["benchmark"] = str(bench)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _write_png_data_url(path: Path, data_url: str) -> None:
    prefix = "data:image/png;base64,"
    if not data_url.startswith(prefix):
        raise ValueError("Expected PNG data URL")
    path.write_bytes(base64.b64decode(data_url[len(prefix) :]))
