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
from .cr_sam import classify_cube_cr_sam
from .mnf import apply_mnf, mnf_data_mean, mnf_transform
from .mtmf import mtmf
from .sff import sff_classify_cube
from .unmixing import estimate_nnls_abundances
from .wavelengths import resolve_wavelengths, validate_wavelengths


UNKNOWN_CLASS = 255

# Classifiers fully implemented in _classify_core (not remapped to SAM).
_IMPLEMENTED_CLASSIFIERS = frozenset(
    {
        "sam",
        "sff",
        "continuum_removal",
        "cr_sam",
        "mtmf",
        "mnf_sam",
        "mnf_mtmf",
        "fuse",
        "fuse_classical",
    }
)


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
        effective = self._effective_classifier(
            selected_options.classifier, use_mtmf=selected_options.use_mtmf
        )
        requested = (selected_options.classifier or "sam").strip().lower().replace(" ", "_")
        if selected_options.use_mtmf and requested not in ("mtmf", "mnf_mtmf"):
            all_warnings.append("use_mtmf=True selected MTMF path")
        if effective != requested and not (
            selected_options.use_mtmf and effective == "mtmf"
        ):
            if requested not in _IMPLEMENTED_CLASSIFIERS and requested != "cr_sam":
                all_warnings.append(
                    f"classifier={selected_options.classifier!r} is not implemented; "
                    f"ran {effective!r} instead"
                )
        model_tag = self._model_tag(effective)
        return MapperResult(
            status="success",
            model_used=f"library_{model_tag}_v1",
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

        effective = self._effective_classifier(options.classifier, use_mtmf=options.use_mtmf)

        wavelengths_np = np.array(wavelengths, dtype=np.float32)
        height, width, _bands = normalized_cube.shape
        mineral_count = len(library.names)
        class_map = np.full((height, width), UNKNOWN_CLASS, dtype=np.uint8)
        confidence_map = np.zeros((height, width), dtype=np.float32)
        abundance_cube = np.zeros((height, width, mineral_count), dtype=np.float32)

        if options.use_ace:
            raise ValueError(
                "use_ace=True is not wired into the classification pipeline; "
                "disable ACE or wait for a supported release"
            )
        if options.vegetation_mask:
            raise ValueError(
                "vegetation_mask=True is not wired into the classification pipeline; "
                "disable vegetation_mask or wait for a supported release"
            )

        if effective == "sff":
            class_map, confidence_map = sff_classify_cube(
                normalized_cube, wavelengths_np, mineral_names=library.names
            )
        elif effective == "continuum_removal":
            # Continuum-removed + VNIR/SWIR hierarchical SAM (CPU classical)
            class_map, confidence_map = classify_cube_cr_sam(
                abundance_cube_input,  # raw reflectance (not L2) for CR
                abundance_refs,
                wavelengths_np,
                library.names,
                valid_mask,
                tile_size=options.tile_size,
                sam_threshold_deg=options.sam_threshold_deg,
                min_strength=options.min_confidence,
            )
            self._fill_nnls_abundances(
                abundance_cube,
                abundance_cube_input,
                abundance_refs,
                valid_mask,
                mineral_count,
                options.tile_size,
            )
        elif effective == "mtmf":
            class_map, confidence_map, abundance_cube = self._classify_mtmf(
                abundance_cube_input,
                abundance_refs,
                valid_mask,
                options,
                mineral_count,
            )
        elif effective == "mnf_sam":
            class_map, confidence_map, abundance_cube = self._classify_mnf_sam(
                abundance_cube_input,
                abundance_refs,
                valid_mask,
                options,
                mineral_count,
            )
        elif effective == "mnf_mtmf":
            class_map, confidence_map, abundance_cube = self._classify_mnf_mtmf(
                abundance_cube_input,
                abundance_refs,
                valid_mask,
                options,
                mineral_count,
            )
        elif effective in ("fuse", "fuse_classical"):
            class_map, confidence_map, abundance_cube = self._classify_fuse_classical(
                abundance_cube_input,
                abundance_refs,
                wavelengths_np,
                library.names,
                valid_mask,
                options,
                mineral_count,
            )
        else:
            # Default: SAM + NNLS
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

    @staticmethod
    def _fill_nnls_abundances(
        abundance_cube: NDArray[np.float32],
        cube: NDArray[np.floating[Any]],
        refs: NDArray[np.floating[Any]],
        valid_mask: NDArray[np.bool_],
        mineral_count: int,
        tile_size: int,
    ) -> None:
        height, width, _ = cube.shape
        for row0, row1, col0, col1 in iter_tiles(height, width, tile_size):
            abundance_tile = cube[row0:row1, col0:col1, :]
            tile_valid = valid_mask[row0:row1, col0:col1]
            abundance_flat = abundance_tile.reshape(-1, abundance_tile.shape[2])
            flat_valid = tile_valid.reshape(-1)
            if not np.any(flat_valid):
                continue
            abundances = estimate_nnls_abundances(abundance_flat[flat_valid], refs)
            tile_abund = np.zeros((flat_valid.shape[0], mineral_count), dtype=np.float32)
            tile_abund[np.where(flat_valid)[0]] = abundances
            abundance_cube[row0:row1, col0:col1, :] = tile_abund.reshape(
                row1 - row0, col1 - col0, mineral_count
            )

    @staticmethod
    def _classify_mtmf(
        cube: NDArray[np.floating[Any]],
        refs: NDArray[np.floating[Any]],
        valid_mask: NDArray[np.bool_],
        options: MapperOptions,
        mineral_count: int,
    ) -> tuple[NDArray[np.uint8], NDArray[np.float32], NDArray[np.float32]]:
        """Mixture-Tuned Matched Filter multi-class assignment.

        For each pixel, pick argmax MF among library targets; accept only if
        MF >= mf_threshold and infeasibility <= infeas_threshold; else unknown 255.
        Confidence = clipped MF of the winner. Abundances = non-negative MF scores
        renormalized per pixel (soft estimate; not physical unmixing).
        """
        h, w, _b = cube.shape
        cube_f = np.asarray(cube, dtype=np.float32)
        refs_f = np.asarray(refs, dtype=np.float32)
        mf, infeas = mtmf(cube_f, refs_f, valid_mask=valid_mask)

        class_map = np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8)
        confidence_map = np.zeros((h, w), dtype=np.float32)
        abundance_cube = np.zeros((h, w, mineral_count), dtype=np.float32)

        best_idx = np.argmax(mf, axis=2).astype(np.uint8)
        best_mf = np.max(mf, axis=2).astype(np.float32)
        # Gather infeas of the winning class
        ii, jj = np.indices((h, w))
        best_infeas = infeas[ii, jj, best_idx]

        accepted = (
            valid_mask
            & (best_mf >= options.mf_threshold)
            & (best_infeas <= options.infeas_threshold)
        )
        class_map[accepted] = best_idx[accepted]
        confidence_map[valid_mask] = np.clip(best_mf[valid_mask], 0.0, 1.0)

        # Soft abundances from max(MF, 0)
        soft = np.maximum(mf, 0.0).astype(np.float32)
        totals = np.sum(soft, axis=2, keepdims=True)
        totals = np.maximum(totals, 1e-10)
        abundance_cube = soft / totals
        abundance_cube[~valid_mask] = 0.0
        return class_map, confidence_map, abundance_cube

    @staticmethod
    def _classify_mnf_sam(
        cube: NDArray[np.floating[Any]],
        refs: NDArray[np.floating[Any]],
        valid_mask: NDArray[np.bool_],
        options: MapperOptions,
        mineral_count: int,
    ) -> tuple[NDArray[np.uint8], NDArray[np.float32], NDArray[np.float32]]:
        """MNF-whiten cube + library, then SAM angles with light NNLS on original spectra.

        MNF reduces noise dimensions before spectral angle matching; NNLS abundances
        are estimated in the original reflectance space for reporting.
        """
        h, w, _b = cube.shape
        cube_f = np.asarray(cube, dtype=np.float32)
        refs_f = np.asarray(refs, dtype=np.float32)
        n_comp = max(1, int(options.n_mnf_components))

        mnf_cube, tmat = mnf_transform(cube_f, valid_mask, n_components=n_comp)
        mu = mnf_data_mean(cube_f, valid_mask)
        refs_mnf = apply_mnf(refs_f, tmat, data_mean=mu)

        class_map = np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8)
        confidence_map = np.zeros((h, w), dtype=np.float32)
        abundance_cube = np.zeros((h, w, mineral_count), dtype=np.float32)

        for row0, row1, col0, col1 in iter_tiles(h, w, options.tile_size):
            tile = mnf_cube[row0:row1, col0:col1, :]
            abundance_tile = cube_f[row0:row1, col0:col1, :]
            tile_valid = valid_mask[row0:row1, col0:col1]
            flat = tile.reshape(-1, tile.shape[2])
            abundance_flat = abundance_tile.reshape(-1, abundance_tile.shape[2])
            flat_valid = tile_valid.reshape(-1)
            if not np.any(flat_valid):
                continue

            valid_pixels = flat[flat_valid]
            abundance_pixels = abundance_flat[flat_valid]
            angles = compute_sam_angles(valid_pixels, refs_mnf)
            strength = angles_to_strength(angles)
            abundances = estimate_nnls_abundances(abundance_pixels, refs_f)
            # Light blend: primarily SAM in MNF space
            combined = 0.75 * strength + 0.25 * abundances
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
                row1 - row0, col1 - col0, mineral_count
            )

        return class_map, confidence_map, abundance_cube

    @staticmethod
    def _classify_mnf_mtmf(
        cube: NDArray[np.floating[Any]],
        refs: NDArray[np.floating[Any]],
        valid_mask: NDArray[np.bool_],
        options: MapperOptions,
        mineral_count: int,
    ) -> tuple[NDArray[np.uint8], NDArray[np.float32], NDArray[np.float32]]:
        """Fused path: MNF transform of cube + library, then MTMF in reduced space.

        Noise-whitened low-dimensional MTMF keeps covariance estimation stable
        when B is large relative to the number of background samples. Assignment
        rules match :meth:`_classify_mtmf` (MF / infeasibility thresholds).
        """
        cube_f = np.asarray(cube, dtype=np.float32)
        refs_f = np.asarray(refs, dtype=np.float32)
        n_comp = max(1, int(options.n_mnf_components))

        mnf_cube, tmat = mnf_transform(cube_f, valid_mask, n_components=n_comp)
        mu = mnf_data_mean(cube_f, valid_mask)
        refs_mnf = apply_mnf(refs_f, tmat, data_mean=mu)

        return OreMapper._classify_mtmf(
            mnf_cube, refs_mnf, valid_mask, options, mineral_count
        )

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

    @staticmethod
    def _effective_classifier(classifier: str, use_mtmf: bool = False) -> str:
        """Map requested classifier to what the pipeline actually runs."""
        name = (classifier or "sam").strip().lower().replace(" ", "_")
        if name == "cr_sam":
            name = "continuum_removal"
        if use_mtmf and name not in ("mtmf", "mnf_mtmf", "mnf_sam"):
            # Legacy flag: force MTMF when classifier is still the default SAM path
            return "mtmf"
        if name in (
            "sam",
            "sff",
            "continuum_removal",
            "mtmf",
            "mnf_sam",
            "mnf_mtmf",
            "fuse",
            "fuse_classical",
        ):
            return "fuse_classical" if name == "fuse" else name
        return "sam"

    @staticmethod
    def _model_tag(effective: str) -> str:
        """Honest model_used fragment for the classifier that actually ran."""
        if effective in (
            "sff",
            "continuum_removal",
            "mtmf",
            "mnf_mtmf",
            "fuse_classical",
        ):
            return effective
        if effective == "mnf_sam":
            return "mnf_sam_nnls"
        return f"{effective}_nnls"

    @staticmethod
    def _classify_fuse_classical(
        cube: NDArray[np.floating[Any]],
        refs: NDArray[np.floating[Any]],
        wavelengths: NDArray[np.floating[Any]],
        mineral_names: list[str],
        valid_mask: NDArray[np.bool_],
        options: MapperOptions,
        mineral_count: int,
    ) -> tuple[NDArray[np.uint8], NDArray[np.float32], NDArray[np.float32]]:
        """Soft fusion of MTMF + CR-region SAM + MNF-SAM (CPU classical ensemble).

        Default weights (from Cuprite grid search maximizing labeled OA):
        0.7 * MTMF + 0.2 * CR-SAM + 0.1 * MNF-SAM, then argmax over minerals.
        Always assigns on valid pixels (no unknown gate) for multi-class OA.
        """
        h, w, _b = cube.shape
        cube_f = np.asarray(cube, dtype=np.float32)
        refs_f = np.asarray(refs, dtype=np.float32)
        k = mineral_count

        # --- MTMF soft scores ---
        mf, _infeas = mtmf(cube_f, refs_f, valid_mask=valid_mask)
        # Scale MF by 99th percentile of valid pixels for [0,1]-ish scores
        valid_mf = mf[valid_mask]
        scale = float(np.percentile(valid_mf, 99)) if valid_mf.size else 1.0
        scale = max(scale, 1e-6)
        mf_soft = np.clip(mf / scale, 0.0, 1.0).astype(np.float32)

        # --- CR-SAM soft scores (always-assign) ---
        cr_cls, cr_conf = classify_cube_cr_sam(
            cube_f,
            refs_f,
            wavelengths,
            mineral_names,
            valid_mask,
            tile_size=options.tile_size,
            sam_threshold_deg=90.0,
            min_strength=0.0,
        )
        cr_soft = np.zeros((h, w, k), dtype=np.float32)
        for j in range(k):
            m = cr_cls == j
            cr_soft[..., j] = np.where(m, cr_conf, 0.0)

        # --- MNF-SAM soft scores ---
        n_comp = max(1, int(options.n_mnf_components))
        mnf_cube, tmat = mnf_transform(cube_f, valid_mask, n_components=n_comp)
        mu = mnf_data_mean(cube_f, valid_mask)
        refs_mnf = apply_mnf(refs_f, tmat, data_mean=mu)
        mnf_soft = np.zeros((h, w, k), dtype=np.float32)
        for row0, row1, col0, col1 in iter_tiles(h, w, options.tile_size):
            tile = mnf_cube[row0:row1, col0:col1, :]
            tile_valid = valid_mask[row0:row1, col0:col1]
            flat = tile.reshape(-1, tile.shape[2])
            flat_valid = tile_valid.reshape(-1)
            if not np.any(flat_valid):
                continue
            angles = compute_sam_angles(flat[flat_valid], refs_mnf)
            strength = angles_to_strength(angles)
            out = np.zeros((flat_valid.shape[0], k), dtype=np.float32)
            out[np.where(flat_valid)[0]] = strength
            mnf_soft[row0:row1, col0:col1, :] = out.reshape(
                row1 - row0, col1 - col0, k
            )

        # Default fusion weights (Cuprite-tuned); could be options later
        w_mt, w_cr, w_mn = 0.7, 0.2, 0.1
        fused = w_mt * mf_soft + w_cr * cr_soft + w_mn * mnf_soft
        class_map = np.argmax(fused, axis=2).astype(np.uint8)
        confidence_map = np.max(fused, axis=2).astype(np.float32)
        class_map[~valid_mask] = UNKNOWN_CLASS
        confidence_map[~valid_mask] = 0.0

        # Soft abundances from fused scores
        totals = np.sum(np.maximum(fused, 0.0), axis=2, keepdims=True)
        totals = np.maximum(totals, 1e-10)
        abundance_cube = (np.maximum(fused, 0.0) / totals).astype(np.float32)
        abundance_cube[~valid_mask] = 0.0
        return class_map, confidence_map, abundance_cube

    def _load_library(self, options: MapperOptions, wavelengths: list[float]) -> SpectralLibrary:
        if options.spectral_library is not None:
            library = load_csv_library(options.spectral_library, options.minerals)
            return resample_library(library, wavelengths)

        demo_names = [m for m in options.minerals if m.endswith("_demo")]
        real_names = [m for m in options.minerals if not m.endswith("_demo")]
        if demo_names and real_names:
            raise ValueError(
                "Cannot mix demo minerals (*_demo) with real mineral names in one run. "
                "Use only demo names for plumbing tests, or provide --library / spectral_library "
                "for real minerals."
            )
        if demo_names and not real_names:
            library = load_demo_library(options.minerals)
            return resample_library(library, wavelengths)

        # Real mineral names: require explicit CSV. Do not silently use demo curves or
        # cache files that may be synthetic Gaussians labeled as RELAB.
        raise ValueError(
            "Authoritative spectra unavailable for real mineral names without a library CSV. "
            "Provide spectral_library / --library pointing at dense VNIR–SWIR spectra "
            "(e.g. benchmarks/demo_fixture/library.csv or a USGS-derived CSV). "
            "Toy *_demo minerals are only for software plumbing tests."
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
