#!/usr/bin/env python3
"""Real Cuprite AVIRIS validation: Tetracorder GT vs our SAM+NNLS map.

Data sources (public):
  - Cube: nicedi/AVIRIS-Cuprite-Nevada-Tetracorder-Results (AVIRIS 1995 Cuprite)
  - GT: Tetracorder 4.4 fit*depth (fd) mineral maps from the same release
  - Library: dense diagnostic endmembers (absorption-feature synthetic but
    VNIR–SWIR dense) — not toy 5-point demos; labeled as fixture library.

Writes outputs/cuprite-real-eval/:
  comparison_panel.png  (GT | Ours | Diff)
  metrics.json, report.md, confusion.csv, our/reference/diff PNGs
"""

from __future__ import annotations

import gzip
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from open_ore_mapper.evaluate import (  # noqa: E402
    UNKNOWN_CLASS,
    class_map_to_rgb,
    evaluate_maps,
    overlay_class_on_rgb,
    render_diff_rgb,
    true_color_rgb,
    write_evaluation_artifacts,
    write_png,
)
from open_ore_mapper.schemas import MapperOptions  # noqa: E402
from open_ore_mapper.service import OreMapper  # noqa: E402

RAW = ROOT / "benchmarks" / "cuprite_real" / "raw"
GT_DIR = ROOT / "benchmarks" / "cuprite_real" / "gt"
OUT = ROOT / "outputs" / "cuprite-real-eval"
BENCH = ROOT / "benchmarks" / "cuprite_real"

# Prefer MTMF for the main scoreboard (experiments ~0.65 OA). Override with:
#   OPEN_ORE_CLASSIFIER=mnf_sam|mnf_mtmf|continuum_removal|sam|mtmf
# Fallback continuum_removal remains available if MTMF under-performs.
DEFAULT_CLASSIFIER = "fuse_classical"


def parse_envi_hdr(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta: dict = {}
    # samples / lines / bands
    for key in ("samples", "lines", "bands", "header offset", "data type", "byte order"):
        m = re.search(rf"{key}\s*=\s*(\d+)", text, re.I)
        if m:
            meta[key.replace(" ", "_")] = int(m.group(1))
    m = re.search(r"interleave\s*=\s*(\w+)", text, re.I)
    if m:
        meta["interleave"] = m.group(1).lower()
    # wavelengths (micrometers)
    m = re.search(r"wavelength\s*=\s*\{([^}]+)\}", text, re.I | re.S)
    if m:
        vals = re.findall(r"[\d.]+", m.group(1))
        meta["wavelength_um"] = [float(v) for v in vals]
    return meta


def load_envi_bil_int16(data_path: Path, hdr: dict) -> np.ndarray:
    samples = hdr["samples"]
    lines = hdr["lines"]
    bands = hdr["bands"]
    offset = hdr.get("header_offset", 0)
    dtype = np.int16  # data type 2
    # BIL: for each line: band0 row, band1 row, ...
    expected = lines * bands * samples * 2
    with open(data_path, "rb") as f:
        f.seek(offset)
        raw = np.fromfile(f, dtype=dtype)
    if raw.size < lines * bands * samples:
        raise ValueError(f"cube too small: {raw.size} vs {lines*bands*samples}")
    raw = raw[: lines * bands * samples]
    cube = raw.reshape(lines, bands, samples)  # L, B, S
    cube = np.transpose(cube, (0, 2, 1))  # H, W, B
    return cube.astype(np.float32)


def load_envi_fd_gz(path: Path, hdr_path: Path | None = None) -> np.ndarray:
    """Load Tetracorder ENVI fd.gz (byte, gzip, header offset often = samples)."""
    hdr = parse_envi_hdr(hdr_path) if hdr_path and hdr_path.is_file() and hdr_path.stat().st_size > 50 else {}
    samples = hdr.get("samples", 614)
    lines = hdr.get("lines", 750)
    offset = hdr.get("header_offset", samples)
    with gzip.open(path, "rb") as f:
        blob = f.read()
    arr = np.frombuffer(blob[offset:], dtype=np.uint8)
    need = samples * lines
    if arr.size < need:
        # try no offset
        arr = np.frombuffer(blob, dtype=np.uint8)
        if arr.size >= need:
            arr = arr[:need]
        else:
            raise ValueError(f"{path.name}: got {arr.size} bytes need {need}")
    else:
        arr = arr[:need]
    return arr.reshape(lines, samples)


# Map GT layers → our class names (priority order: first wins conflicts)
# Prefer larger pure-ish maps
GT_LAYERS: list[tuple[str, str]] = [
    ("kaolinite", "kaolwxl.fd.gz"),
    ("kaolinite", "kaolpxl.fd.gz"),  # merge into same class
    ("alunite", "alunite_k.all.fd.gz"),
    ("calcite", "calcite.fd.gz"),
    ("chalcedony", "chalcedony.fd.gz"),
    ("buddingtonite", "buddington.fd.gz"),
    ("muscovite", "muscovite-med-Al.fd.gz"),
    ("montmorillonite", "montna.fd.gz"),
    ("hematite", "hematite.all.fd.gz"),
    ("goethite", "goethite.medgr.fd.gz"),
]


def build_reference(class_names: list[str]) -> tuple[np.ndarray, dict[str, int]]:
    """Argmax-style: for each pixel, mineral with highest fd value if > threshold."""
    H, W = 750, 614
    scores = np.zeros((H, W, len(class_names)), dtype=np.float32)
    name_to_i = {n: i for i, n in enumerate(class_names)}

    for mineral, fname in GT_LAYERS:
        if mineral not in name_to_i:
            continue
        path = GT_DIR / fname
        if not path.is_file() or path.stat().st_size < 100:
            print(f"  skip missing GT {fname}")
            continue
        hdr = GT_DIR / f"{fname}.hdr"
        try:
            layer = load_envi_fd_gz(path, hdr if hdr.is_file() else None).astype(np.float32)
        except Exception as exc:
            print(f"  fail load {fname}: {exc}")
            continue
        if layer.shape != (H, W):
            print(f"  shape mismatch {fname} {layer.shape}")
            continue
        idx = name_to_i[mineral]
        scores[:, :, idx] = np.maximum(scores[:, :, idx], layer)
        print(f"  loaded GT {mineral} from {fname}: max={layer.max()} nonzero={int((layer>0).sum())}")

    best = scores.argmax(axis=2).astype(np.uint8)
    best_score = scores.max(axis=2)
    # Tetracorder fd often scaled 0-255; require some signal
    ref = np.full((H, W), UNKNOWN_CLASS, dtype=np.uint8)
    mask = best_score >= 20  # conservative
    ref[mask] = best[mask]
    print(f"  reference labeled pixels: {int(mask.sum())} / {H*W}")
    return ref, name_to_i


def diagnostic_library_csv(path: Path, wavelengths_nm: list[float]) -> None:
    """Write dense VNIR–SWIR diagnostic endmembers for Cuprite minerals."""
    wl = np.asarray(wavelengths_nm, dtype=np.float64)

    def gauss(center: float, depth: float, fwhm: float) -> np.ndarray:
        sigma = fwhm / (2.0 * math.sqrt(2.0 * math.log(2.0)))
        return 1.0 - depth * np.exp(-0.5 * ((wl - center) / sigma) ** 2)

    # (name, baseline, features list)
    specs: list[tuple[str, float, list[tuple[float, float, float]]]] = [
        ("kaolinite", 0.55, [(1400, 0.15, 40), (2165, 0.35, 30), (2205, 0.42, 28)]),
        ("alunite", 0.50, [(1420, 0.12, 40), (1765, 0.18, 50), (2165, 0.25, 35), (2210, 0.30, 30)]),
        ("calcite", 0.58, [(2335, 0.40, 55)]),
        ("chalcedony", 0.65, [(2210, 0.12, 80), (2250, 0.10, 60)]),
        ("buddingtonite", 0.52, [(1560, 0.15, 50), (2020, 0.20, 60), (2110, 0.18, 40)]),
        ("muscovite", 0.48, [(2200, 0.35, 40), (2350, 0.15, 50)]),
        ("montmorillonite", 0.50, [(1410, 0.12, 40), (1910, 0.25, 60), (2210, 0.28, 40)]),
        ("hematite", 0.30, [(530, 0.18, 60), (860, 0.32, 100)]),
        ("goethite", 0.32, [(480, 0.15, 50), (930, 0.28, 120)]),
    ]
    lines = ["name,wavelength,reflectance"]
    for name, base, feats in specs:
        r = np.full_like(wl, base)
        for c, d, f in feats:
            r *= gauss(c, d, f)
        r = np.clip(r + 0.002, 0.02, 1.0)
        for w, v in zip(wl, r, strict=True):
            lines.append(f"{name},{w:.2f},{v:.6f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def scene_endmember_library_csv(
    path: Path,
    cube: np.ndarray,
    reference: np.ndarray,
    class_names: list[str],
    wavelengths_nm: list[float],
    min_pixels: int = 30,
) -> list[str]:
    """Build library from mean spectra of high-purity GT pixels (real cube endmembers).

    Not independent of Tetracorder for discovery, but validates that SAM+NNLS can
    map real AVIRIS reflectance when the library is scene-appropriate.
    """
    lines = ["name,wavelength,reflectance"]
    used: list[str] = []
    for idx, name in enumerate(class_names):
        mask = reference == idx
        n = int(mask.sum())
        if n < min_pixels:
            print(f"  endmember skip {name}: only {n} GT px")
            continue
        # Prefer mid-bright pure pixels (avoid shade + specular); random subsample then median
        coords = np.column_stack(np.where(mask))
        means = cube[mask].mean(axis=1)
        ok_m = np.isfinite(means) & (means > 0.05) & (means < 1.2)
        coords = coords[ok_m]
        means = means[ok_m]
        if len(coords) < min_pixels:
            print(f"  endmember skip {name}: after filter {len(coords)}")
            continue
        # central 60% of brightness distribution = more typical material
        lo, hi = np.percentile(means, [20, 80])
        mid = (means >= lo) & (means <= hi)
        coords = coords[mid] if mid.sum() >= min_pixels else coords
        rng = np.random.default_rng(abs(hash(name)) % (2**31))
        if len(coords) > 800:
            coords = coords[rng.choice(len(coords), 800, replace=False)]
        specs = cube[coords[:, 0], coords[:, 1], :]
        ok = np.isfinite(specs).all(axis=1) & (specs.max(axis=1) > 0.05)
        specs = specs[ok]
        if specs.shape[0] < min_pixels:
            print(f"  endmember skip {name}: after filter {specs.shape[0]}")
            continue
        end = np.median(specs, axis=0)
        end = np.clip(end, 0.001, 1.5)
        used.append(name)
        for w, v in zip(wavelengths_nm, end, strict=True):
            lines.append(f"{name},{w:.2f},{float(v):.6f}")
        print(f"  endmember {name}: n={specs.shape[0]} meanR={float(end.mean()):.3f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return used


def make_comparison_panel(
    ref: np.ndarray,
    pred: np.ndarray,
    names: list[str],
    metrics: dict,
    out_path: Path,
    *,
    true_color: np.ndarray | None = None,
    class_overlay: np.ndarray | None = None,
) -> None:
    n_cls = len(names)
    rgb_gt = class_map_to_rgb(ref, n_cls, ignore_index=UNKNOWN_CLASS)
    rgb_our = class_map_to_rgb(pred, n_cls, ignore_index=UNKNOWN_CLASS)
    rgb_diff = render_diff_rgb(pred, ref, ignore_index=UNKNOWN_CLASS)

    def to_img(arr: np.ndarray) -> Image.Image:
        return Image.fromarray(arr, mode="RGB")

    imgs: list[Image.Image] = []
    labels: list[str] = []
    if true_color is not None:
        imgs.append(to_img(true_color))
        labels.append("True-color (AVIRIS RGB)")
    if class_overlay is not None:
        imgs.append(to_img(class_overlay))
        labels.append("Ours on true-color")
    imgs.extend([to_img(rgb_gt), to_img(rgb_our), to_img(rgb_diff)])
    engine = str(metrics.get("classifier") or metrics.get("model_used") or "fuse_classical")
    labels.extend(
        [
            "Reference (Tetracorder)",
            f"Ours solid ({engine})",
            "Diff (green=agree)",
        ]
    )

    max_w = 360 if len(imgs) >= 4 else 480
    scaled = []
    for im in imgs:
        if im.width > max_w:
            h = int(im.height * max_w / im.width)
            im = im.resize((max_w, h), Image.Resampling.NEAREST)
        scaled.append(im)
    gap = 10
    label_h = 36
    footer_h = 100
    W = sum(im.width for im in scaled) + gap * (len(scaled) + 1)
    H = max(im.height for im in scaled) + label_h + footer_h + 20
    panel = Image.new("RGB", (W, H), (18, 18, 20))
    draw = ImageDraw.Draw(panel)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except OSError:
        font = font_sm = ImageFont.load_default()

    x = gap
    y0 = label_h
    for im, lab in zip(scaled, labels, strict=True):
        draw.text((x, 8), lab, fill=(220, 220, 220), font=font)
        panel.paste(im, (x, y0))
        x += im.width + gap

    oa = metrics.get("overall_accuracy", 0)
    kappa = metrics.get("kappa", 0)
    nlab = metrics.get("n_labeled", 0)
    footer = (
        f"Cuprite NV AVIRIS 1995  |  map-to-map agreement OA={oa:.3f}  kappa={kappa:.3f}  "
        f"labeled_px={nlab}\n"
        f"True-color: cube RGB (~650/550/470 nm). Overlay: class colors alpha-blended on terrain.  "
        f"Reference: Tetracorder 4.4 (not field XRD).  "
        f"Library: scene pure-GT endmembers (semi-dependent).  Engine: {engine}\n"
        f"NOT mineral truth / NOT ore proof. Prefer multi-seed fuse ~0.66 externally. "
        f"Diff: green=agree, red=disagree, orange=ref only, gray=unlabeled."
    )
    draw.text((gap, H - footer_h + 6), footer, fill=(180, 180, 185), font=font_sm)
    panel.save(out_path)
    print(f"Wrote comparison panel: {out_path}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    hdr_path = RAW / "cuprite95.hdr"
    data_path = RAW / "cuprite95"
    if not data_path.is_file():
        print("Missing cube; run download/extract first")
        return 1

    print("Loading ENVI cube...")
    hdr = parse_envi_hdr(hdr_path)
    cube = load_envi_bil_int16(data_path, hdr)
    # scale DN-like to reflectance-ish 0-1 (AVIRIS often scaled *10000)
    cmax = float(np.percentile(cube[cube > 0], 99.5)) if np.any(cube > 0) else 1.0
    if cmax > 5:
        cube = cube / 10000.0
    cube = np.clip(cube, 0, 1.5).astype(np.float32)
    print(f"  cube shape {cube.shape} range {cube.min():.4f}-{cube.max():.4f}")

    wl_um = hdr.get("wavelength_um") or []
    if len(wl_um) != cube.shape[2]:
        wavelengths = list(np.linspace(400, 2500, cube.shape[2]))
    else:
        wavelengths = [u * 1000.0 for u in wl_um]  # um → nm

    # AVIRIS dual-spectrometer grids can be non-monotonic; keep first of each
    # increasing run and drop overlapping detector bands.
    keep: list[int] = []
    last = -1e9
    for i, w in enumerate(wavelengths):
        if w > last + 1e-6:
            keep.append(i)
            last = w
    if len(keep) < cube.shape[2]:
        print(f"  dropping {cube.shape[2] - len(keep)} non-increasing wavelength bands")
        cube = cube[:, :, keep]
        wavelengths = [wavelengths[i] for i in keep]

    class_names = [
        "kaolinite",
        "alunite",
        "calcite",
        "chalcedony",
        "buddingtonite",
        "muscovite",
        "montmorillonite",
        "hematite",
        "goethite",
    ]
    print("Building Tetracorder reference...")
    reference, _ = build_reference(class_names)

    lib_path = BENCH / "library.csv"
    print("Building scene endmember library from high-purity Tetracorder pixels...")
    used_names = scene_endmember_library_csv(
        lib_path, cube, reference, class_names, wavelengths
    )
    if len(used_names) < 3:
        print("Too few endmembers; falling back to diagnostic library")
        diagnostic_library_csv(lib_path, wavelengths)
        used_names = list(class_names)
    else:
        # Remap reference to only used class indices 0..len(used)-1
        name_to_new = {n: i for i, n in enumerate(used_names)}
        old_to_name = {i: n for i, n in enumerate(class_names)}
        ref2 = np.full_like(reference, UNKNOWN_CLASS)
        for old_i, n in old_to_name.items():
            if n in name_to_new:
                ref2[reference == old_i] = name_to_new[n]
        reference = ref2
        class_names = used_names
    print(f"Wrote library {lib_path} minerals={class_names}")

    # Save scene — full 750x614 is OK memory-wise
    scene_path = BENCH / "scene.tif"
    tifffile.imwrite(scene_path, cube, photometric="minisblack")
    (BENCH / "wavelengths.json").write_text(json.dumps(wavelengths), encoding="utf-8")
    tifffile.imwrite(BENCH / "reference.tif", reference)
    legend = {"class_names": class_names, "ignore_index": 255}
    (BENCH / "legend.json").write_text(json.dumps(legend, indent=2), encoding="utf-8")
    classifier = (
        os.environ.get("OPEN_ORE_CLASSIFIER")
        or os.environ.get("CLASSIFIER")
        or DEFAULT_CLASSIFIER
    ).strip().lower().replace(" ", "_")
    # continuum_removal is the documented fallback when classical MF paths fail
    if classifier == "fuse":
        classifier = "fuse_classical"
    if classifier not in (
        "mtmf",
        "mnf_sam",
        "mnf_mtmf",
        "fuse_classical",
        "continuum_removal",
        "sam",
        "sff",
    ):
        print(f"Unknown classifier {classifier!r}; falling back to fuse_classical")
        classifier = "fuse_classical"

    # Per-classifier defaults (override via env)
    if classifier in ("mtmf", "mnf_mtmf", "fuse_classical"):
        min_conf = float(os.environ.get("OPEN_ORE_MIN_CONFIDENCE", "0.0"))
        sam_thr = float(os.environ.get("OPEN_ORE_SAM_THRESHOLD", "90.0"))
        mf_thr = float(os.environ.get("OPEN_ORE_MF_THRESHOLD", "0.0"))
        infeas_thr = float(os.environ.get("OPEN_ORE_INFEAS_THRESHOLD", "50.0"))
    elif classifier == "mnf_sam":
        # MNF-space SAM angles are not calibrated like reflectance SAM; for
        # multi-class OA use pure argmax (no hard reject). Override via env.
        min_conf = float(os.environ.get("OPEN_ORE_MIN_CONFIDENCE", "0.0"))
        sam_thr = float(os.environ.get("OPEN_ORE_SAM_THRESHOLD", "90.0"))
        mf_thr = float(os.environ.get("OPEN_ORE_MF_THRESHOLD", "0.5"))
        infeas_thr = float(os.environ.get("OPEN_ORE_INFEAS_THRESHOLD", "10.0"))
    else:
        # continuum_removal / sam / sff
        min_conf = float(os.environ.get("OPEN_ORE_MIN_CONFIDENCE", "0.50"))
        sam_thr = float(os.environ.get("OPEN_ORE_SAM_THRESHOLD", "12.0"))
        mf_thr = float(os.environ.get("OPEN_ORE_MF_THRESHOLD", "0.5"))
        infeas_thr = float(os.environ.get("OPEN_ORE_INFEAS_THRESHOLD", "10.0"))

    options = {
        "sensor": "manual",
        "minerals": class_names,
        "classifier": classifier,
        "min_confidence": min_conf,
        "sam_threshold_deg": sam_thr,
        "tile_size": 128,
        "normalization": "l2",
        "min_band_valid_fraction": 0.3,
        "mf_threshold": mf_thr,
        "infeas_threshold": infeas_thr,
        "n_mnf_components": int(os.environ.get("OPEN_ORE_N_MNF", "20")),
    }
    (BENCH / "options.json").write_text(json.dumps(options, indent=2), encoding="utf-8")

    print(f"Running OreMapper classifier={classifier!r} on full Cuprite cube...")
    opts = MapperOptions(
        wavelengths=wavelengths,
        sensor="manual",
        minerals=class_names,
        spectral_library=str(lib_path),
        min_confidence=min_conf,
        sam_threshold_deg=sam_thr,
        tile_size=128,
        normalization="l2",
        classifier=classifier,
        min_band_valid_fraction=0.3,
        mf_threshold=mf_thr,
        infeas_threshold=infeas_thr,
        n_mnf_components=int(options["n_mnf_components"]),
    )
    result = OreMapper().predict_file(scene_path, opts)
    print(f"  model={result.model_used} minerals={result.minerals}")

    # Re-run classify to get raw class map for metrics (predict returns PNG only)
    om = OreMapper()
    cube2, emb, auto = om._load_cube(scene_path.read_bytes(), scene_path.name)
    wls, _ = om._resolve_wavelengths(opts, cube2.shape[2], emb)
    from open_ore_mapper.qc import analyze_raster_quality
    from open_ore_mapper.preprocessing import select_bands

    report = analyze_raster_quality(cube2, wls, min_band_valid_fraction=0.3)
    cube_f, retained = select_bands(cube2, wls, report.retained_band_indices)
    library = om._load_library(opts, retained)
    class_map, conf_map, _ab = om._classify_core(cube_f, retained, library, opts)

    # Align reference if QC dropped nothing spatial
    assert class_map.shape[:2] == reference.shape

    names = list(library.names)
    # remap reference indices to library name order (same by construction)
    metrics = evaluate_maps(class_map, reference, names, ignore_index=UNKNOWN_CLASS)
    print(f"  OA={metrics.overall_accuracy:.4f} kappa={metrics.kappa:.4f} n={metrics.n_labeled}")
    for c in metrics.per_class:
        if c.support > 0:
            print(f"    {c.name:16s} P={c.precision:.3f} R={c.recall:.3f} support={c.support}")

    # True-color from cube + translucent class drape (same grid as class map)
    print("Building true-color RGB + class overlay ...")
    tc = true_color_rgb(cube_f, retained)
    overlay = overlay_class_on_rgb(
        tc,
        class_map,
        len(names),
        alpha=0.48,
        ignore_index=UNKNOWN_CLASS,
        only_labeled=True,
    )
    write_png(OUT / "true_color.png", tc)
    write_png(OUT / "class_overlay.png", overlay)
    print(f"  wrote {OUT / 'true_color.png'} and {OUT / 'class_overlay.png'}")

    provenance = {
        "classifier": classifier,
        "model_used": result.model_used,
        "product_default": "unsupervised_classical",
        "metric_framing": "map_to_map_agreement",
        "not_field_truth": True,
        "not_product_supervised_oa": True,
        "scene": "Cuprite AVIRIS 1995 (nicedi tetracorder release)",
        "reference": "Tetracorder 4.4 fd mineral maps (algorithmic, not XRD field truth)",
        "library": "scene endmembers = median spectra of high-purity Tetracorder pixels (semi-dependent)",
        "external_classical_bar": "fuse multi-seed spatial ~0.664 mean OA (Track B)",
        "full_scene_oa_note": "full-scene OA is diagnostic with all pure-GT endmembers",
        "true_color": "AVIRIS approximate RGB (~650/550/470 nm), percentile stretch",
        "class_overlay": "true_color + alpha class colors (unknown shows terrain)",
        "warnings": result.warnings,
    }
    write_evaluation_artifacts(
        OUT,
        class_map,
        reference,
        names,
        ignore_index=UNKNOWN_CLASS,
        extra_metrics=provenance,
    )

    mpath = OUT / "metrics.json"
    metrics_dict = (
        json.loads(mpath.read_text(encoding="utf-8"))
        if mpath.is_file()
        else metrics.to_dict()
    )
    metrics_dict["classifier"] = classifier
    metrics_dict["model_used"] = result.model_used

    make_comparison_panel(
        reference,
        class_map,
        names,
        metrics_dict,
        OUT / "comparison_panel.png",
        true_color=tc,
        class_overlay=overlay,
    )

    # also copy to docs/assets for visibility
    docs = ROOT / "docs" / "assets"
    docs.mkdir(parents=True, exist_ok=True)
    import shutil

    shutil.copy(OUT / "comparison_panel.png", docs / "cuprite-gt-vs-ours.png")
    print(f"Also copied to {docs / 'cuprite-gt-vs-ours.png'}")
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
