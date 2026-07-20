import io
import json

import numpy as np
import tifffile
from fastapi.testclient import TestClient

from open_ore_mapper.api import app
from open_ore_mapper.schemas import DEFAULT_DEMO_MINERALS


client = TestClient(app)


def test_health_returns_healthy() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_minerals_returns_default_demo_minerals() -> None:
    response = client.get("/v1/minerals")
    assert response.status_code == 200
    assert response.json() == {"minerals": DEFAULT_DEMO_MINERALS}


def test_predict_accepts_synthetic_tiff() -> None:
    response = client.post(
        "/v1/predict",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={
            "options": json.dumps(
                {
                    "minerals": ["hematite_demo", "goethite_demo"],
                    "min_confidence": 0.0,
                    "sam_threshold_deg": 180.0,
                }
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_invalid_mineral_returns_400() -> None:
    response = client.post(
        "/v1/predict",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={"options": json.dumps({"minerals": ["unobtainium_demo"]})},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


def test_empty_file_returns_400() -> None:
    response = client.post(
        "/v1/predict",
        files={"file": ("empty.tif", b"", "image/tiff")},
        data={"options": "{}"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


def test_qc_raster_returns_quality_report() -> None:
    response = client.post(
        "/v1/qc/raster",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={"options": json.dumps({"sensor": "cubert_ultris_s5"})},
    )
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "band_count" in data


def test_qc_raster_empty_file_returns_400() -> None:
    response = client.post(
        "/v1/qc/raster",
        files={"file": ("empty.tif", b"", "image/tiff")},
        data={"options": "{}"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


def test_qc_raster_with_excluded_band_indices() -> None:
    response = client.post(
        "/v1/qc/raster",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={
            "options": json.dumps({
                "sensor": "cubert_ultris_s5",
                "excluded_band_indices": [0, 5, 10],
            })
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert 0 in data["excluded_band_indices"]
    assert 5 in data["excluded_band_indices"]
    assert 10 in data["excluded_band_indices"]


def test_qc_raster_all_bands_excluded_returns_fail() -> None:
    response = client.post(
        "/v1/qc/raster",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={
            "options": json.dumps({
                "sensor": "cubert_ultris_s5",
                "excluded_band_indices": list(range(51)),
            })
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "fail"
    assert data["valid_pixel_fraction"] == 0.0


def test_predict_returns_quality_report_with_excluded_band_indices() -> None:
    response = client.post(
        "/v1/predict",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={
            "options": json.dumps(
                {
                    "minerals": ["hematite_demo", "goethite_demo"],
                    "min_confidence": 0.0,
                    "sam_threshold_deg": 180.0,
                    "excluded_band_indices": [0, 1],
                }
            )
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "quality_report" in data
    qr = data["quality_report"]
    assert "excluded_band_indices" in qr
    assert 0 in qr["excluded_band_indices"]
    assert 1 in qr["excluded_band_indices"]


def test_qc_raster_rejects_non_integer_excluded_band_indices_float() -> None:
    response = client.post(
        "/v1/qc/raster",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={
            "options": json.dumps({
                "sensor": "cubert_ultris_s5",
                "excluded_band_indices": [1.9],
            })
        },
    )
    assert response.status_code == 400
    assert "integers" in response.json()["error"]["message"].lower()


def test_qc_raster_rejects_non_integer_excluded_band_indices_str() -> None:
    response = client.post(
        "/v1/qc/raster",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={
            "options": json.dumps({
                "sensor": "cubert_ultris_s5",
                "excluded_band_indices": ["1"],
            })
        },
    )
    assert response.status_code == 400
    assert "integers" in response.json()["error"]["message"].lower()


def test_qc_raster_rejects_non_integer_excluded_band_indices_bool() -> None:
    response = client.post(
        "/v1/qc/raster",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={
            "options": json.dumps({
                "sensor": "cubert_ultris_s5",
                "excluded_band_indices": [True],
            })
        },
    )
    assert response.status_code == 400
    assert "integers" in response.json()["error"]["message"].lower()


def test_predict_rejects_non_integer_excluded_band_indices() -> None:
    response = client.post(
        "/v1/predict",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={
            "options": json.dumps({
                "minerals": ["hematite_demo"],
                "excluded_band_indices": [1.9],
            })
        },
    )
    assert response.status_code == 400
    assert "integers" in response.json()["error"]["message"].lower()


# -- Web app UI tests -----------------------------------------------------------


def test_get_index_returns_html() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    body = response.text
    assert "Open Ore Mapper" in body
    assert "/v1/qc/raster" in body
    assert "/v1/predict" in body
    assert "spectral similarity" in body.lower()


def test_get_app_js_returns_javascript() -> None:
    response = client.get("/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_app_js_references_statistics_fields() -> None:
    response = client.get("/app.js")
    body = response.text
    assert "mean_confidence" in body
    assert "mean_abundance" in body
    assert "percentage" in body


def test_app_js_references_image_fields() -> None:
    response = client.get("/app.js")
    body = response.text
    assert "output_image" in body
    assert "confidence_image" in body
    assert "top_abundance_image" in body
    assert "Class map" in body
    assert "Confidence" in body
    assert "Top abundance" in body


def test_get_styles_css_returns_css() -> None:
    response = client.get("/styles.css")
    assert response.status_code == 200
    assert "css" in response.headers["content-type"]


def test_qc_raster_malformed_options_returns_400() -> None:
    response = client.post(
        "/v1/qc/raster",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={"options": "not-json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


def test_predict_malformed_options_returns_400() -> None:
    response = client.post(
        "/v1/predict",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={"options": "not-json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


def test_predict_response_structure() -> None:
    response = client.post(
        "/v1/predict",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={
            "options": json.dumps(
                {
                    "minerals": ["hematite_demo", "goethite_demo"],
                    "min_confidence": 0.0,
                    "sam_threshold_deg": 180.0,
                }
            )
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "quality_report" in data
    assert "statistics" in data
    assert "warnings" in data
    assert "output_image" in data
    assert data["output_image"].startswith("data:image/png")
    assert "confidence_image" in data
    assert data["confidence_image"].startswith("data:image/png")
    assert "top_abundance_image" in data
    assert data["top_abundance_image"].startswith("data:image/png")


def test_upload_exceeds_limit() -> None:
    import open_ore_mapper.api as api

    saved_limit = api._MAX_UPLOAD_BYTES
    api._MAX_UPLOAD_BYTES = 10
    try:
        response = client.post(
            "/v1/qc/raster",
            files={"file": ("small.tif", b"\x00" * 100, "image/tiff")},
            data={"options": "{}"},
        )
        assert response.status_code == 400
        message = response.json()["error"]["message"]
        assert "exceeds" in message.lower()
    finally:
        api._MAX_UPLOAD_BYTES = saved_limit


def test_api_rejects_server_side_spectral_library_path() -> None:
    response = client.post(
        "/v1/predict",
        files={"file": ("synthetic.tif", _synthetic_tiff_bytes(), "image/tiff")},
        data={"options": json.dumps({"spectral_library": "/etc/passwd"})},
    )

    assert response.status_code == 400
    assert "not supported" in response.json()["error"]["message"]


def _synthetic_tiff_bytes() -> bytes:
    buffer = io.BytesIO()
    cube = np.ones((4, 4, 51), dtype=np.float32) * 0.5
    tifffile.imwrite(buffer, cube, photometric="minisblack")
    return buffer.getvalue()
