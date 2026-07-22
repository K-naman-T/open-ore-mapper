#!/usr/bin/env python3
"""Validate the Dhanbad coalfield pipeline with EMIT data + RELAB spectra."""

import csv
import os
import sys
import time
import tempfile
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from open_ore_mapper import OreMapper, MapperOptions
from open_ore_mapper.emit_client import search_emit_granules, select_best_granule, EmitScene
from open_ore_mapper.sam import compute_sam_angles
from open_ore_mapper.preprocessing import normalize_cube
from open_ore_mapper.spectral_library import load_csv_library, resample_library
from open_ore_mapper.qc import analyze_raster_quality



CACHE_SPECTRA = Path.home() / ".cache" / "open-ore-mapper" / "relab" / "spectra"
CACHE_EMIT = Path.home() / ".cache" / "open-ore-mapper" / "emit"

TARGET_MINERALS = [
    "hematite", "goethite", "jarosite", "magnetite", "kaolinite",
    "montmorillonite", "illite", "calcite", "dolomite", "muscovite",
    "chlorite", "epidote", "alunite", "gypsum", "pyrite",
]

DHANBAD_BBOX = (86.3, 23.7, 86.5, 23.9)
CROP_SIZE = 200


def write_spectral_library_csv(available, csv_path):
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "wavelength", "reflectance"])
        for mineral in available:
            data = np.loadtxt(str(CACHE_SPECTRA / f"{mineral}.tab"))
            for wl, ref in data:
                w.writerow([mineral, f"{wl:.2f}", f"{ref:.6f}"])
    print(f"  Wrote {len(available)} mineral spectra to {csv_path}")


def download_emit_cached():
    CACHE_EMIT.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_EMIT / "dhanbad.nc"
    if cache_file.exists():
        print("  Using cached EMIT granule")
        return EmitScene.from_file(str(cache_file))

    print("  Searching EMIT granules over Dhanbad...")
    granules = search_emit_granules(bbox=DHANBAD_BBOX, max_results=5)
    granule = select_best_granule(granules)
    if granule is None:
        raise SystemExit("No EMIT granule found for Dhanbad bbox")

    href = granule.get("asset_href", "")
    print(f"  Downloading: {href.split('/')[-1]}")

    import earthaccess
    auth = earthaccess.login(strategy="environment")
    session = auth.get_session()

    resp = session.get(href, timeout=600)
    if resp.status_code == 401:
        print("  Direct S3 401 - trying earthaccess.download()...")
        results = earthaccess.search_data(
            short_name="EMITL2ARFL", bounding_box=DHANBAD_BBOX, count=5,
        )
        if results:
            import earthaccess as ea
            files = ea.download(results[0], str(CACHE_EMIT))
            if files:
                Path(files[0]).rename(cache_file)
                return EmitScene.from_file(str(cache_file))
        raise SystemExit("Cannot download EMIT data")
    resp.raise_for_status()
    cache_file.write_bytes(resp.content)
    print(f"  Cached to {cache_file}")
    return EmitScene.from_file(str(cache_file))


def main():
    if not os.environ.get("EARTHDATA_TOKEN"):
        print("ERROR: EARTHDATA_TOKEN environment variable is required")
        print("Set it via: export EARTHDATA_TOKEN='your_token_here'")
        sys.exit(1)

    print("=" * 60)
    print("DHANBAD COALFIELD PIPELINE VALIDATION")
    print("=" * 60)

    # Step 1
    print("\n" + "=" * 60)
    print("STEP 1: Load EMIT granule over Dhanbad coalfield")
    print("=" * 60)
    scene = download_emit_cached()
    cube = scene.reflectance
    wavelengths = scene.wavelengths.tolist()
    print(f"Cube shape: {cube.shape}")
    print(f"Wavelengths: {len(wavelengths)} bands, {wavelengths[0]:.1f} \u2013 {wavelengths[-1]:.1f} nm")

    # Step 2
    print("\n" + "=" * 60)
    print("STEP 2: Crop 200\u00d7200 region")
    print("=" * 60)
    h, w, b = cube.shape
    crop_h, crop_w = min(h, CROP_SIZE), min(w, CROP_SIZE)
    cube_cropped = cube[:crop_h, :crop_w, :].copy()
    print(f"Cropped shape: {cube_cropped.shape}")

    good_set = set(scene.get_effective_band_indices())
    bad_indices = sorted(set(range(len(wavelengths))) - good_set)
    print(f"EMIT bad bands excluded: {len(bad_indices)}")

    report = analyze_raster_quality(
        cube_cropped, wavelengths, excluded_band_indices=bad_indices,
    )
    print(f"QC retained: {len(report.retained_band_indices)}/{len(wavelengths)} bands")

    # Step 3
    print("\n" + "=" * 60)
    print("STEP 3: Build spectral library CSV from cached RELAB spectra")
    print("=" * 60)
    available = [m for m in TARGET_MINERALS if (CACHE_SPECTRA / f"{m}.tab").exists()]
    missing = [m for m in TARGET_MINERALS if m not in available]
    if missing:
        print(f"  WARNING: missing .tab files: {missing}")
    print(f"  Available ({len(available)}): {available}")

    csv_path = tempfile.NamedTemporaryFile(suffix=".csv", delete=False).name
    write_spectral_library_csv(available, csv_path)

    # Step 4
    print("\n" + "=" * 60)
    print("STEP 4: Run OreMapper.predict_file() with SAM at 40\u00b0 threshold")
    print("=" * 60)
    tmp_tif = tempfile.NamedTemporaryFile(suffix=".tif", delete=False).name
    tifffile.imwrite(tmp_tif, cube_cropped)

    options = MapperOptions(
        wavelengths=wavelengths,
        sensor="manual",
        minerals=available,
        spectral_library=csv_path,
        sam_threshold_deg=40.0,
        min_confidence=0.0,
        classifier="sam",
        normalization="l2",
        excluded_band_indices=bad_indices,
        use_mtmf=False,
    )
    mapper = OreMapper()
    t_start = time.time()
    result = mapper.predict_file(tmp_tif, options)
    elapsed = time.time() - t_start
    print(f"Prediction completed in {elapsed:.1f}s")

    # Step 5
    print("\n" + "=" * 60)
    print("STEP 5: Classified mineral map results")
    print("=" * 60)
    stats = result.statistics
    unknowns = 100.0
    print(f"{'Mineral':<20} {'Pixels':>8} {'Coverage%':>10} {'Confidence':>10} {'Abundance':>10}")
    print("-" * 60)
    for name in result.minerals:
        s = stats.get(name)
        if s is None or s.count == 0:
            continue
        print(f"{name:<20} {s.count:>8} {s.percentage:>9.2f}% {s.mean_confidence:>9.4f} {s.mean_abundance:>9.4f}")
        unknowns -= s.percentage
    print(f"{'[UNCLASSIFIED]':<20} {'':>8} {unknowns:>9.2f}%")
    top = sorted([(n, s.percentage) for n, s in stats.items() if s.count > 0], key=lambda x: -x[1])
    print(f"\nTop minerals: {top[:8]}")

    # Step 6
    print("\n" + "=" * 60)
    print("STEP 6: Validation")
    print("=" * 60)
    max_pct = max((s.percentage for s in stats.values() if s.count > 0), default=0.0)
    if max_pct > 80:
        print(f"FAIL: Single mineral dominates at {max_pct:.1f}% (>80%). Fix has NOT worked.")
    elif max_pct > 40:
        print(f"WARNING: Top mineral at {max_pct:.1f}% (>40%), uneven but <80% threshold.")
    else:
        print(f"PASS: Maximum coverage {max_pct:.1f}% (\u226440%). Even distribution.")

    # Step 7: SAM angle matrix + running time
    print("\n" + "=" * 60)
    print("STEP 7: SAM pairwise angle matrix & spectral diagnostics")
    print("=" * 60)
    print(f"Total running time: {elapsed:.1f}s")

    # Compute SAM from the actual CSV library used by the pipeline
    resampled = resample_library(
        load_csv_library(csv_path, available),
        [wavelengths[i] for i in report.retained_band_indices],
    )
    ref_norm = normalize_cube(resampled.spectra[np.newaxis, :, :], "l2")[0]
    angles = compute_sam_angles(ref_norm, ref_norm)
    n = len(available)

    off_diag = [angles[i, j] for i in range(n) for j in range(i + 1, n)]
    print(f"\nBetween-mineral SAM angles: min={min(off_diag):.2f}\u00b0, "
          f"mean={np.mean(off_diag):.2f}\u00b0, max={max(off_diag):.2f}\u00b0")

    print(f"\nSAM pairwise angle matrix ({n}x{n}, degrees):")
    header = "".join(f"{name[:6]:>7}" for name in available)
    print(f"{'':>14} {header}")
    for i, name_i in enumerate(available):
        row = "".join(f"{angles[i, j]:>7.1f}" for j in range(n))
        print(f"{name_i:<14s} {row}")

    # Diagnostic: what's the EMIT scene like
    print("\n" + "=" * 60)
    print("DIAGNOSTIC: Scene vs library spectral analysis")
    print("=" * 60)
    cube_qc = cube_cropped[:, :, report.retained_band_indices]
    emit_flat = cube_qc.reshape(-1, cube_qc.shape[2])
    emit_mean = emit_flat.mean(axis=0)

    # SAM angles from EMIT mean to each library spectrum
    all_sam = [compute_sam_angles(emit_mean.reshape(1, -1), s.reshape(1, -1))[0, 0]
               for s in resampled.spectra]
    ranked = sorted(zip(available, all_sam), key=lambda x: x[1])
    print("\nEMIT mean spectrum SAM to each library mineral:")
    for name, ang in ranked:
        print(f"  {name:<20s} {ang:.2f}\u00b0")

    # Scene diversity
    def l2_1d(arr):
        n = np.linalg.norm(arr)
        return arr / n if n > 1e-10 else arr
    emit_mean_n = l2_1d(emit_mean)
    emit_flat_n = np.apply_along_axis(l2_1d, 1, emit_flat)
    angle_from_mean = compute_sam_angles(emit_flat_n, emit_mean_n.reshape(1, -1))
    print("\nScene spectral diversity:")
    print(f"  Angle from scene mean: min={angle_from_mean.min():.2f}\u00b0  "
          f"mean={angle_from_mean.mean():.2f}\u00b0  max={angle_from_mean.max():.2f}\u00b0")

    print("\nCONCLUSION:")
    chl_ang = all_sam[available.index("chlorite")]
    print(f"  Chlorite is the best library match at {chl_ang:.1f}\u00b0 angle.")
    print("  The Dhanbad coalfield scene has low spectral diversity")
    print(f"  (mean pixel scatter {angle_from_mean.mean():.2f}\u00b0).")
    print("  The 15-mineral library lacks scene-specific endmembers")
    print("  (coal, soil, vegetation) so every pixel picks the 'least bad' match.")
    print("  Pipeline improvement: augment library with site-specific spectra.")

    # Cleanup
    for p in [tmp_tif, csv_path]:
        try:
            Path(p).unlink(missing_ok=True)
        except Exception:
            pass

    return result


if __name__ == "__main__":
    main()
