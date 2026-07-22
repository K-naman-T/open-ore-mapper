from __future__ import annotations

import io
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
import tifffile

from .preprocessing import ensure_hwc, normalize_cube, select_bands, valid_pixel_mask
from .qc import RasterQualityReport, analyze_raster_quality
from .rendering import class_map_png_data_url, confidence_png_data_url, mineral_statistics
from .sam import angles_to_strength, compute_sam_angles
from .schemas import MapperOptions, MapperResult
from .spectral_library import SpectralLibrary, load_csv_library, load_demo_library, resample_library
from .tiling import iter_tiles
from .sff import sff_classify_cube
from .unmixing import estimate_nnls_abundances
from .wavelengths import resolve_wavelengths, validate_wavelengths


UNKNOWN_CLASS = 255


def _mat_ensure_hwc(arr: np.ndarray, band_count_hint: int | None = None) -> np.ndarray:
    if band_count_hint is not None:
        return cast(np.ndarray, ensure_hwc(arr, band_count=band_count_hint))
    if arr.ndim != 3:
        raise ValueError(f"Expected a 3D raster cube, got shape {arr.shape}")
    h, w, c = arr.shape
    if h < c and w < c:
        return arr
    if h > w + c:
        return np.moveaxis(arr, 0, -1).astype(np.float32, copy=False)
    if c < h and c < w:
        return arr
    return np.moveaxis(arr, 0, -1).astype(np.float32, copy=False)


class OreMapper:
    def predict_file(self, path: str | Path, options: MapperOptions | None = None) -> MapperResult:
        file_path = Path(path)
        return self.predict_bytes(file_path.read_bytes(), file_path.name, options or MapperOptions())

    def predict_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        options: MapperOptions | None = None,
    ) -> MapperResult:
        selected_options = options or MapperOptions()
        if not selected_options.minerals:
            raise ValueError("At least one mineral is required")

        band_count_hint = (
            len(selected_options.wavelengths) if selected_options.wavelengths is not None else None
        )
        cube, embedded_wavelengths, auto_excluded = self._load_cube(
            file_bytes, filename, band_count_hint=band_count_hint
        )
        wavelengths, sensor = self._resolve_wavelengths(
            selected_options, cube.shape[2], embedded_wavelengths
        )

        if not selected_options.excluded_band_indices and auto_excluded:
            selected_options = replace(selected_options, excluded_band_indices=auto_excluded)

        return self.predict_cube(cube, wavelengths, selected_options, sensor)

    def predict_cube(
        self,
        cube: NDArray[np.floating[Any]],
        wavelengths: list[float],
        options: MapperOptions | None = None,
        sensor: str = "manual",
    ) -> MapperResult:
        selected_options = options or MapperOptions()

        report = analyze_raster_quality(
            cube,
            wavelengths,
            excluded_band_indices=selected_options.excluded_band_indices or None,
            min_band_valid_fraction=selected_options.min_band_valid_fraction,
        )
        if len(report.retained_band_indices) < 2:
            raise ValueError(
                "At least two usable spectral bands are required after QC"
            )

        cube, retained_wls = select_bands(cube, wavelengths, report.retained_band_indices)
        library = self._load_library(selected_options, retained_wls)
        class_map, confidence_map, abundance_cube = self._classify_core(
            cube, retained_wls, library, selected_options
        )

        top_abundance = np.max(abundance_cube, axis=2)
        all_warnings = self._coverage_warnings(retained_wls) + report.warnings
        return MapperResult(
            status="success",
            model_used=f"library_{selected_options.classifier}_nnls_v1",
            sensor=sensor,
            wavelengths=retained_wls,
            minerals=library.names,
            output_image=class_map_png_data_url(class_map, library.names),
            confidence_image=confidence_png_data_url(confidence_map),
            top_abundance_image=confidence_png_data_url(top_abundance),
            statistics=mineral_statistics(class_map, confidence_map, abundance_cube, library.names),
            warnings=all_warnings,
            downloads={},
            quality_report=report,
        )

    def _classify_core(
        self,
        cube: NDArray[np.floating[Any]],
        wavelengths: list[float],
        library: SpectralLibrary,
        options: MapperOptions,
    ) -> tuple[NDArray[np.uint8], NDArray[np.float32], NDArray[np.float32]]:
        valid_mask = valid_pixel_mask(cube)
        normalized_cube = normalize_cube(cube, options.normalization)
        ref_spectra = normalize_cube(library.spectra[np.newaxis, :, :], options.normalization)[0]
        abundance_cube_input = normalize_cube(cube, "none")
        abundance_refs = normalize_cube(library.spectra[np.newaxis, :, :], "none")[0]

        use_sff = options.classifier == "sff"

        wavelengths_np = np.array(wavelengths, dtype=np.float32)
        height, width, _bands = normalized_cube.shape
        mineral_count = len(library.names)
        class_map = np.full((height, width), UNKNOWN_CLASS, dtype=np.uint8)
        confidence_map = np.zeros((height, width), dtype=np.float32)
        abundance_cube = np.zeros((height, width, mineral_count), dtype=np.float32)

        if use_sff:
            class_map, confidence_map = sff_classify_cube(
                normalized_cube, wavelengths_np, mineral_names=library.names
            )

        if not use_sff:
            for row0, row1, col0, col1 in iter_tiles(height, width, options.tile_size):
                tile = normalized_cube[row0:row1, col0:col1, :]
                abundance_tile = abundance_cube_input[row0:row1, col0:col1, :]
                tile_valid = valid_mask[row0:row1, col0:col1]
                flat = tile.reshape(-1, tile.shape[2])
                abundance_flat = abundance_tile.reshape(-1, abundance_tile.shape[2])
                flat_valid = tile_valid.reshape(-1)
                if not np.any(flat_valid):
                    continue

                valid_pixels = flat[flat_valid]
                abundance_pixels = abundance_flat[flat_valid]
                angles = compute_sam_angles(valid_pixels, ref_spectra)
                strength = angles_to_strength(angles)
                abundances = estimate_nnls_abundances(abundance_pixels, abundance_refs)
                combined = 0.6 * strength + 0.4 * abundances
                best_idx = np.argmax(combined, axis=1).astype(np.uint8)
                best_conf = np.max(combined, axis=1).astype(np.float32)
                best_angle = np.min(angles, axis=1).astype(np.float32)
                accepted = (best_conf >= options.min_confidence) & (
                    best_angle <= options.sam_threshold_deg
                )

                tile_classes = np.full(flat_valid.shape, UNKNOWN_CLASS, dtype=np.uint8)
                tile_conf = np.zeros(flat_valid.shape, dtype=np.float32)
                tile_abund = np.zeros((flat_valid.shape[0], mineral_count), dtype=np.float32)
                valid_positions = np.where(flat_valid)[0]
                tile_classes[valid_positions[accepted]] = best_idx[accepted]
                tile_conf[valid_positions] = best_conf
                tile_abund[valid_positions] = abundances

                class_map[row0:row1, col0:col1] = tile_classes.reshape(row1 - row0, col1 - col0)
                confidence_map[row0:row1, col0:col1] = tile_conf.reshape(row1 - row0, col1 - col0)
                abundance_cube[row0:row1, col0:col1, :] = tile_abund.reshape(
                    row1 - row0,
                    col1 - col0,
                    mineral_count,
                )

        return class_map, confidence_map, abundance_cube

    def to_response(self, result: MapperResult) -> dict[str, Any]:
        response = asdict(result)
        response["statistics"] = {name: asdict(stats) for name, stats in result.statistics.items()}
        return response

    def _load_cube(
        self, file_bytes: bytes, filename: str, band_count_hint: int | None = None
    ) -> tuple[NDArray[np.float32], list[float] | None, list[int] | None]:
        lower = filename.lower()
        if lower.endswith((".tif", ".tiff")):
            return ensure_hwc(tifffile.imread(io.BytesIO(file_bytes))), None, None
        if lower.endswith(".mat"):
            import scipy.io

            mat = scipy.io.loadmat(io.BytesIO(file_bytes))
            known_keys = {
                "cube", "data", "hsi", "image", "scene",
                "salinasA_corrected", "SalinasA_corrected",
                "indian_pines_corrected",
            }
            def _pick_cube(arrays: list[np.ndarray]) -> np.ndarray:
                if len(arrays) == 1:
                    return arrays[0]
                hwc_scores = []
                for a in arrays:
                    s = a.shape
                    score = 0
                    if s[2] < s[0] and s[2] < s[1]:
                        score += 10
                    if s[0] > s[2] and s[1] > s[2]:
                        score += 5
                    hwc_scores.append((score, a.shape[0] * a.shape[1], a))
                hwc_scores.sort(key=lambda x: (-x[0], -x[1]))
                return hwc_scores[0][2]

            candidates: list[np.ndarray] = []
            for key in sorted(mat.keys()):
                if key.startswith("__"):
                    continue
                arr = mat[key]
                if (
                    hasattr(arr, "ndim")
                    and arr.ndim == 3
                    and (
                        np.issubdtype(arr.dtype, np.floating)
                        or np.issubdtype(arr.dtype, np.integer)
                    )
                ):
                    arr_float = np.asarray(arr, dtype=np.float32)
                    if key in known_keys:
                        candidates.insert(0, arr_float)
                    else:
                        candidates.append(arr_float)
            if not candidates:
                raise ValueError(
                    f"No 3D numeric array found in .mat file (keys: {[k for k in mat.keys() if not k.startswith('__')]})"
                )
            selected = _pick_cube(candidates)
            return _mat_ensure_hwc(selected, band_count_hint=band_count_hint), None, None
        if lower.endswith((".h5", ".hdf5", ".nc")):
            import h5py

            with h5py.File(io.BytesIO(file_bytes), "r", driver="fileobj") as h5:
                embedded_wavelengths: list[float] | None = None
                auto_excluded_indices: list[int] | None = None

                if "wavelengths" in h5:
                    wl_data = h5["wavelengths"][:]
                    embedded_wavelengths = [float(v) for v in wl_data]

                if embedded_wavelengths is None and "sensor_band_parameters" in h5:
                    sgrp = h5["sensor_band_parameters"]
                    if "wavelengths" in sgrp:
                        wl_data = sgrp["wavelengths"][:]
                        embedded_wavelengths = [float(v) for v in wl_data]

                if "sensor_band_parameters" in h5:
                    sgrp = h5["sensor_band_parameters"]
                    if "good_wavelengths" in sgrp:
                        gw = np.asarray(sgrp["good_wavelengths"][:])
                        if gw.ndim == 1:
                            auto_excluded_indices = [int(i) for i in range(len(gw)) if gw[i] == 0]

                for key in ["hdr", "cube", "data", "image", "hsi", "HSI", "reflectance"]:
                    if key in h5:
                        cube = ensure_hwc(
                            h5[key][:],
                            band_count=len(embedded_wavelengths) if embedded_wavelengths else None,
                        )
                        return cube, embedded_wavelengths, auto_excluded_indices
                keys = list(h5.keys())
                if not keys:
                    raise ValueError("HDF5 input does not contain any datasets")
                cube = ensure_hwc(
                    h5[keys[0]][:],
                    band_count=len(embedded_wavelengths) if embedded_wavelengths else None,
                )
                return cube, embedded_wavelengths, auto_excluded_indices
        raise ValueError("Supported inputs are .tif, .tiff, .h5, .hdf5, .nc, and .mat")

    def _resolve_wavelengths(
        self,
        options: MapperOptions,
        expected_bands: int,
        embedded_wavelengths: list[float] | None = None,
    ) -> tuple[list[float], str]:
        if options.wavelengths is not None:
            return validate_wavelengths(options.wavelengths, expected_bands), "manual"
        if embedded_wavelengths is not None:
            return validate_wavelengths(embedded_wavelengths, expected_bands), "embedded_hdf5"
        return resolve_wavelengths(None, options.sensor, expected_bands)

    def _load_library(self, options: MapperOptions, wavelengths: list[float]) -> SpectralLibrary:
        if options.spectral_library is not None:
            library = load_csv_library(options.spectral_library, options.minerals)
            return resample_library(library, wavelengths)

        if any(m.endswith("_demo") for m in options.minerals):
            library = load_demo_library(options.minerals)
            return resample_library(library, wavelengths)

        try:
            from .relab_fetcher import build_spectral_library as build_relab

            target_wl = np.asarray(wavelengths, dtype=np.float32)
            library = build_relab(options.minerals, target_wl)
            if library.spectra.shape[0] > 0:
                return library
        except Exception:
            pass

        raise ValueError(
            "Authoritative spectra are unavailable. "
            "Your mineral names do not include '_demo' suffixes, so synthetic demo spectra "
            "cannot be used in their place. "
            "Provide a user CSV via --library or fetch an authoritative RELAB corpus "
            "via `open-ore-mapper fetch-library`."
        )

    def quality_file(
        self, path: str | Path, options: MapperOptions | None = None
    ) -> RasterQualityReport:
        file_path = Path(path)
        return self.quality_bytes(file_path.read_bytes(), file_path.name, options)

    def quality_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        options: MapperOptions | None = None,
    ) -> RasterQualityReport:
        selected_options = options or MapperOptions()
        band_count_hint = (
            len(selected_options.wavelengths) if selected_options.wavelengths is not None else None
        )
        cube, embedded_wavelengths, auto_excluded = self._load_cube(
            file_bytes, filename, band_count_hint=band_count_hint
        )
        wavelengths, _sensor = self._resolve_wavelengths(
            selected_options, cube.shape[2], embedded_wavelengths
        )

        excluded_band_indices = selected_options.excluded_band_indices
        if not excluded_band_indices and auto_excluded:
            excluded_band_indices = auto_excluded

        return analyze_raster_quality(
            cube,
            wavelengths,
            excluded_band_indices=excluded_band_indices,
            min_band_valid_fraction=selected_options.min_band_valid_fraction,
        )

    @staticmethod
    def to_quality_response(report: RasterQualityReport) -> dict[str, Any]:
        return asdict(report)

    def _coverage_warnings(self, wavelengths: list[float]) -> list[str]:
        if max(wavelengths) < 1000.0:
            return [
                "Input does not include SWIR bands; clay, carbonate, and many alteration minerals cannot be mapped reliably"
            ]
        return []
