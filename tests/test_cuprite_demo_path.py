"""Structural + integration checks for dumb-first-user Cuprite classical path."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_cuprite_real_validation.py"


def test_cuprite_validation_script_defaults_to_fuse_classical() -> None:
    """Product demo entry must default to unsupervised classical fuse, not ML."""
    assert SCRIPT.is_file()
    src = SCRIPT.read_text(encoding="utf-8")
    assert 'DEFAULT_CLASSIFIER = "fuse_classical"' in src
    assert "HistGB" not in src
    assert "RandomForest" not in src
    # Ensure main path uses env override then DEFAULT
    assert "OPEN_ORE_CLASSIFIER" in src
    assert "evaluate_maps" in src
    assert "comparison_panel" in src


def test_cuprite_validation_script_parses() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    assert any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in tree.body)


def test_fuse_classical_is_effective_classifier() -> None:
    from open_ore_mapper.service import OreMapper

    om = OreMapper()
    assert om._effective_classifier("fuse_classical") == "fuse_classical"
    assert om._effective_classifier("fuse") == "fuse_classical"


def test_shipped_evaluate_path_drives_oa(tmp_path: Path) -> None:
    """Drive evaluate_maps + write_evaluation_artifacts as validation script does."""
    from open_ore_mapper.evaluate import evaluate_maps, write_evaluation_artifacts

    names = ["kaolinite", "alunite"]
    h, w = 32, 32
    ref = np.zeros((h, w), dtype=np.uint8)
    ref[:, w // 2 :] = 1
    pred = ref.copy()
    # intentional mismatches
    pred[:4, :4] = 1
    pred[-4:, -4:] = 0

    metrics = evaluate_maps(pred, ref, names)
    assert metrics.n_labeled == h * w
    assert 0.0 < metrics.overall_accuracy < 1.0

    write_evaluation_artifacts(
        tmp_path,
        pred,
        ref,
        names,
        extra_metrics={
            "classifier": "fuse_classical",
            "metric_framing": "map_to_map_agreement",
            "not_field_truth": True,
        },
    )
    assert (tmp_path / "metrics.json").is_file()
    assert (tmp_path / "our_class.png").is_file()
    assert (tmp_path / "reference.png").is_file()
    assert (tmp_path / "diff.png").is_file()
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "map-to-map" in report.lower()


@pytest.mark.skipif(
    not (ROOT / "benchmarks" / "cuprite_real" / "scene.tif").is_file(),
    reason="Cuprite benchmark package not present",
)
def test_cuprite_bench_package_has_reference() -> None:
    bench = ROOT / "benchmarks" / "cuprite_real"
    for name in ("scene.tif", "reference.tif", "legend.json", "wavelengths.json"):
        assert (bench / name).is_file(), name
