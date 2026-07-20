import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import scipy.io  # type: ignore[import-untyped]
import tifffile


def test_cli_help_contains_predict() -> None:
    completed = subprocess.run(
        [_cli_command(), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "predict" in completed.stdout


def test_cli_predict_creates_result_json(tmp_path: Path) -> None:
    scene = _write_synthetic_scene(tmp_path)
    output_dir = tmp_path / "outputs" / "test"

    completed = subprocess.run(
        [
            _cli_command(),
            "predict",
            str(scene),
            "--sensor",
            "cubert_ultris_s5",
            "--minerals",
            "hematite_demo,goethite_demo",
            "--output-dir",
            str(output_dir),
            "--min-confidence",
            "0",
            "--sam-threshold-deg",
            "180",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "success"
    assert (output_dir / "class_map.png").exists()
    assert (output_dir / "confidence.png").exists()
    assert (output_dir / "top_abundance.png").exists()


def test_cli_invalid_mineral_exits_nonzero(tmp_path: Path) -> None:
    scene = _write_synthetic_scene(tmp_path)
    output_dir = tmp_path / "outputs" / "bad"

    completed = subprocess.run(
        [
            _cli_command(),
            "predict",
            str(scene),
            "--minerals",
            "unobtainium_demo",
            "--output-dir",
            str(output_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "Unknown minerals" in completed.stderr


def test_cli_qc_raster_writes_json_report(tmp_path: Path) -> None:
    scene = _write_synthetic_scene(tmp_path)
    completed = subprocess.run(
        [_cli_command(), "qc-raster", str(scene), "--sensor", "cubert_ultris_s5"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert "status" in report
    assert "band_count" in report


def test_cli_qc_raster_with_wavelengths_file(tmp_path: Path) -> None:
    scene = _write_synthetic_scene(tmp_path)
    wl_path = tmp_path / "wavelengths.json"
    wl_path.write_text(
        json.dumps([round(450.0 + i * 8.0, 1) for i in range(51)]),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [_cli_command(), "qc-raster", str(scene), "--wavelengths", str(wl_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert "status" in report
    assert "band_count" in report


def test_cli_qc_raster_with_output_flag(tmp_path: Path) -> None:
    scene = _write_synthetic_scene(tmp_path)
    qc_path = tmp_path / "qc_report.json"
    completed = subprocess.run(
        [
            _cli_command(),
            "qc-raster",
            str(scene),
            "--sensor",
            "cubert_ultris_s5",
            "--output",
            str(qc_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert qc_path.exists()
    assert "Wrote quality report to" in completed.stdout
    report = json.loads(qc_path.read_text(encoding="utf-8"))
    assert "status" in report
    assert "band_count" in report


def test_cli_qc_raster_exclude_bands(tmp_path: Path) -> None:
    scene = _write_synthetic_scene(tmp_path)
    completed = subprocess.run(
        [
            _cli_command(),
            "qc-raster",
            str(scene),
            "--sensor",
            "cubert_ultris_s5",
            "--exclude-bands",
            "0,10,20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["excluded_band_indices"] == [0, 10, 20]


def test_cli_predict_confidence_differs_from_top_abundance(tmp_path: Path) -> None:
    cube = np.ones((4, 4, 51), dtype=np.float32) * 0.5
    cube[:2, :2, :] = 0.1
    scene = tmp_path / "non_uniform.tif"
    tifffile.imwrite(scene, cube, photometric="minisblack")
    output_dir = tmp_path / "outputs"
    completed = subprocess.run(
        [
            _cli_command(),
            "predict",
            str(scene),
            "--sensor",
            "cubert_ultris_s5",
            "--minerals",
            "hematite_demo,goethite_demo",
            "--output-dir",
            str(output_dir),
            "--min-confidence",
            "0",
            "--sam-threshold-deg",
            "180",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    conf_bytes = (output_dir / "confidence.png").read_bytes()
    top_bytes = (output_dir / "top_abundance.png").read_bytes()
    assert conf_bytes != top_bytes


def test_cli_qc_raster_all_bands_excluded_fails(tmp_path: Path) -> None:
    scene = _write_synthetic_scene(tmp_path)
    completed = subprocess.run(
        [
            _cli_command(),
            "qc-raster",
            str(scene),
            "--sensor",
            "cubert_ultris_s5",
            "--exclude-bands",
            ",".join(str(i) for i in range(51)),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["status"] == "fail"
    assert report["valid_pixel_fraction"] == 0.0


def test_cli_predict_writes_quality_report(tmp_path: Path) -> None:
    scene = _write_synthetic_scene(tmp_path)
    output_dir = tmp_path / "outputs" / "test"
    completed = subprocess.run(
        [
            _cli_command(),
            "predict",
            str(scene),
            "--sensor",
            "cubert_ultris_s5",
            "--minerals",
            "hematite_demo,goethite_demo",
            "--output-dir",
            str(output_dir),
            "--min-confidence",
            "0",
            "--sam-threshold-deg",
            "180",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    qc_path = output_dir / "quality_report.json"
    assert qc_path.exists()
    report = json.loads(qc_path.read_text(encoding="utf-8"))
    assert "status" in report
    assert "band_count" in report


def test_cli_list_scenes_includes_known_scenes() -> None:
    completed = subprocess.run(
        [_cli_command(), "list-scenes"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    scenes = json.loads(completed.stdout)
    scene_ids = [s["id"] for s in scenes]
    assert "salinas_a_corrected" in scene_ids
    assert "cuprite_aviris" in scene_ids


def test_cli_download_scene_unknown_id_fails() -> None:
    completed = subprocess.run(
        [_cli_command(), "download-scene", "nonexistent_scene", "--output-dir", "/tmp"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "Unknown scene" in completed.stderr


def test_cli_download_scene_salinas_local(tmp_path: Path) -> None:
    cube = np.ones((4, 4, 3), dtype=np.float32) * 0.5
    mat_bytes = io.BytesIO()
    scipy.io.savemat(mat_bytes, {"salinas_a_corrected": cube})
    local_url = tmp_path / "SalinasA_corrected.mat"
    local_url.write_bytes(mat_bytes.getvalue())

    completed = subprocess.run(
        [
            _cli_command(),
            "download-scene",
            "salinas_a_corrected",
            "--output-dir",
            str(tmp_path),
            "--source-url",
            local_url.as_uri(),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert local_url.name in completed.stdout


def _write_synthetic_scene(tmp_path: Path) -> Path:
    cube = np.ones((4, 4, 51), dtype=np.float32) * 0.5
    scene = tmp_path / "synthetic.tif"
    tifffile.imwrite(scene, cube, photometric="minisblack")
    return scene


def _cli_command() -> str:
    return shutil.which("open-ore-mapper") or str(Path(sys.executable).with_name("open-ore-mapper"))
