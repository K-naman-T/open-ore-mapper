"""Dispatch tests for classical spectral classifiers (mtmf, mnf_sam, mnf_mtmf)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import tifffile

from open_ore_mapper.schemas import MapperOptions
from open_ore_mapper.service import OreMapper, UNKNOWN_CLASS


def _write_library_csv(path: Path, names: list[str], wavelengths: list[float]) -> None:
    lines = ["name,wavelength,reflectance"]
    for i, name in enumerate(names):
        for j, wl in enumerate(wavelengths):
            # Distinct spectral shapes per mineral
            refl = 0.3 + 0.1 * i + 0.2 * np.sin(0.01 * wl * (i + 1) + j * 0.1)
            lines.append(f"{name},{wl},{refl:.6f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _synthetic_scene(
    tmp_path: Path,
    height: int = 12,
    width: int = 12,
    n_bands: int = 16,
) -> tuple[Path, Path, list[float], list[str]]:
    wavelengths = [400.0 + i * 50.0 for i in range(n_bands)]
    names = ["hematite", "goethite", "kaolinite"]
    lib_path = tmp_path / "library.csv"
    _write_library_csv(lib_path, names, wavelengths)

    rng = np.random.default_rng(0)
    # Build library spectra the same way for embedding
    refs = []
    for i, _name in enumerate(names):
        refl = np.array(
            [
                0.3 + 0.1 * i + 0.2 * np.sin(0.01 * wl * (i + 1) + j * 0.1)
                for j, wl in enumerate(wavelengths)
            ],
            dtype=np.float32,
        )
        refs.append(refl)
    refs_a = np.stack(refs, axis=0)

    cube = 0.05 * rng.normal(size=(height, width, n_bands)).astype(np.float32)
    # Plant pure endmember patches
    cube[1:4, 1:4, :] = refs_a[0]
    cube[1:4, 5:8, :] = refs_a[1]
    cube[6:9, 3:7, :] = refs_a[2]
    cube = np.clip(cube, 0.01, None).astype(np.float32)

    scene = tmp_path / "scene.tif"
    tifffile.imwrite(scene, cube, photometric="minisblack")
    return scene, lib_path, wavelengths, names


def test_classifier_fuse_classical_model_used(tmp_path: Path) -> None:
    scene, lib, wls, names = _synthetic_scene(tmp_path)
    result = OreMapper().predict_file(
        scene,
        MapperOptions(
            wavelengths=wls,
            sensor="manual",
            minerals=names,
            spectral_library=str(lib),
            classifier="fuse_classical",
            n_mnf_components=8,
            min_band_valid_fraction=0.0,
            min_confidence=0.0,
            sam_threshold_deg=90.0,
        ),
    )
    assert result.status == "success"
    assert result.model_used == "library_fuse_classical_v1"
    assert set(result.minerals) == set(names)


def test_classifier_mtmf_model_used(tmp_path: Path) -> None:
    scene, lib, wls, names = _synthetic_scene(tmp_path)
    result = OreMapper().predict_file(
        scene,
        MapperOptions(
            wavelengths=wls,
            sensor="manual",
            minerals=names,
            spectral_library=str(lib),
            classifier="mtmf",
            mf_threshold=0.05,
            infeas_threshold=50.0,
            min_band_valid_fraction=0.0,
        ),
    )
    assert result.status == "success"
    assert result.model_used == "library_mtmf_v1"
    assert result.minerals == names


def test_classifier_mnf_sam_model_used(tmp_path: Path) -> None:
    scene, lib, wls, names = _synthetic_scene(tmp_path)
    result = OreMapper().predict_file(
        scene,
        MapperOptions(
            wavelengths=wls,
            sensor="manual",
            minerals=names,
            spectral_library=str(lib),
            classifier="mnf_sam",
            n_mnf_components=8,
            min_confidence=0.0,
            sam_threshold_deg=90.0,
            min_band_valid_fraction=0.0,
        ),
    )
    assert result.status == "success"
    assert result.model_used == "library_mnf_sam_nnls_v1"


def test_classifier_mnf_mtmf_model_used(tmp_path: Path) -> None:
    scene, lib, wls, names = _synthetic_scene(tmp_path)
    result = OreMapper().predict_file(
        scene,
        MapperOptions(
            wavelengths=wls,
            sensor="manual",
            minerals=names,
            spectral_library=str(lib),
            classifier="mnf_mtmf",
            n_mnf_components=8,
            mf_threshold=0.0,
            infeas_threshold=1e6,
            min_band_valid_fraction=0.0,
        ),
    )
    assert result.status == "success"
    assert result.model_used == "library_mnf_mtmf_v1"


def test_classify_core_mtmf_assigns_known_pixels(tmp_path: Path) -> None:
    scene, lib, wls, names = _synthetic_scene(tmp_path, height=10, width=10, n_bands=20)
    om = OreMapper()
    opts = MapperOptions(
        wavelengths=wls,
        sensor="manual",
        minerals=names,
        spectral_library=str(lib),
        classifier="mtmf",
        mf_threshold=0.1,
        infeas_threshold=100.0,
        min_band_valid_fraction=0.0,
    )
    cube, emb, _ = om._load_cube(scene.read_bytes(), scene.name)
    wls2, _ = om._resolve_wavelengths(opts, cube.shape[2], emb)
    library = om._load_library(opts, wls2)
    class_map, conf, abund = om._classify_core(cube, wls2, library, opts)

    assert class_map.shape == cube.shape[:2]
    assert conf.shape == cube.shape[:2]
    assert abund.shape == (cube.shape[0], cube.shape[1], len(names))
    # At least some pixels classified (not all unknown)
    labeled = class_map != UNKNOWN_CLASS
    assert np.any(labeled), "MTMF should label pure endmember patches"


def test_classify_core_mnf_sam_no_crash(tmp_path: Path) -> None:
    scene, lib, wls, names = _synthetic_scene(tmp_path)
    om = OreMapper()
    opts = MapperOptions(
        wavelengths=wls,
        sensor="manual",
        minerals=names,
        spectral_library=str(lib),
        classifier="mnf_sam",
        n_mnf_components=6,
        min_confidence=0.0,
        sam_threshold_deg=180.0,
        min_band_valid_fraction=0.0,
    )
    cube, emb, _ = om._load_cube(scene.read_bytes(), scene.name)
    wls2, _ = om._resolve_wavelengths(opts, cube.shape[2], emb)
    library = om._load_library(opts, wls2)
    class_map, conf, abund = om._classify_core(cube, wls2, library, opts)
    assert class_map.dtype == np.uint8
    assert conf.dtype == np.float32
    assert abund.shape[2] == len(names)
    assert np.all(np.isfinite(conf))


def test_effective_classifier_aliases() -> None:
    assert OreMapper._effective_classifier("MTMF") == "mtmf"
    assert OreMapper._effective_classifier("mnf_sam") == "mnf_sam"
    assert OreMapper._effective_classifier("mnf_mtmf") == "mnf_mtmf"
    assert OreMapper._effective_classifier("cr_sam") == "continuum_removal"
    assert OreMapper._effective_classifier("sam", use_mtmf=True) == "mtmf"
    assert OreMapper._effective_classifier("unknown_thing") == "sam"
    assert OreMapper._effective_classifier("continuum_removal") == "continuum_removal"
