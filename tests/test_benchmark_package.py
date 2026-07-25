"""Benchmark package schema + end-to-end evaluate (uses demo_fixture if present)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks" / "demo_fixture"


def _ensure_fixture() -> None:
    if (FIXTURE / "scene.tif").is_file() and (FIXTURE / "library.csv").is_file():
        return
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "build_demo_fixture.py")])


def test_fixture_schema() -> None:
    _ensure_fixture()
    legend = json.loads((FIXTURE / "legend.json").read_text(encoding="utf-8"))
    assert "class_names" in legend
    assert len(legend["class_names"]) >= 2
    options = json.loads((FIXTURE / "options.json").read_text(encoding="utf-8"))
    assert options.get("classifier") == "sam"
    assert (FIXTURE / "library.csv").is_file()
    assert (FIXTURE / "reference.tif").is_file()
    assert (FIXTURE / "wavelengths.json").is_file()


def test_run_benchmark_oa_high(tmp_path: Path) -> None:
    _ensure_fixture()
    from open_ore_mapper.benchmark import run_benchmark

    out = tmp_path / "eval"
    summary = run_benchmark(FIXTURE, out)
    assert summary["overall_accuracy"] >= 0.9
    assert (out / "metrics.json").is_file()
    assert (out / "diff.png").is_file()
    assert summary["model_used"].startswith("library_sam")


def test_real_names_without_library_fail_closed(tmp_path: Path) -> None:
    import numpy as np
    import tifffile
    from open_ore_mapper.schemas import MapperOptions
    from open_ore_mapper.service import OreMapper

    cube = np.ones((4, 4, 10), dtype=np.float32) * 0.4
    path = tmp_path / "c.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")
    with pytest.raises(ValueError, match="[Aa]uthoritative|library|unavailable"):
        OreMapper().predict_file(
            path,
            MapperOptions(
                wavelengths=list(range(400, 410)),
                sensor="manual",
                minerals=["hematite", "kaolinite"],
                spectral_library=None,
                min_confidence=0.0,
                sam_threshold_deg=180.0,
            ),
        )
