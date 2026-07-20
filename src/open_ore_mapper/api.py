from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from .schemas import DEFAULT_DEMO_MINERALS, MapperOptions
from .service import OreMapper

_MAX_UPLOAD_BYTES = 100 * 1024 * 1024
_CHUNK_SIZE = 64 * 1024


app = FastAPI(title="Open Ore Mapper", version="0.1.0")

_STATIC = Path(__file__).with_name("static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@app.get("/app.js")
def app_js() -> FileResponse:
    return FileResponse(_STATIC / "app.js")


@app.get("/styles.css")
def styles_css() -> FileResponse:
    return FileResponse(_STATIC / "styles.css")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/v1/minerals")
def minerals() -> dict[str, list[str]]:
    return {"minerals": list(DEFAULT_DEMO_MINERALS)}


async def _read_upload(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(_CHUNK_SIZE):
        total += len(chunk)
        if total > _MAX_UPLOAD_BYTES:
            raise ValueError("Uploaded file exceeds 100 MiB limit")
        chunks.append(chunk)
    return b"".join(chunks)


@app.post("/v1/qc/raster", response_model=None)
async def qc_raster(
    file: UploadFile = File(...),
    options: str = Form("{}"),
) -> dict[str, Any] | JSONResponse:
    try:
        file_bytes = await _read_upload(file)
    except ValueError as exc:
        return _bad_request(str(exc))
    if not file_bytes:
        return _bad_request("Uploaded file is empty")
    try:
        mapper_options = _parse_options(options)
        mapper = OreMapper()
        report = mapper.quality_bytes(file_bytes, file.filename or "upload.tif", mapper_options)
        return mapper.to_quality_response(report)
    except ValueError as exc:
        return _bad_request(str(exc))


@app.post("/v1/predict", response_model=None)
async def predict(
    file: UploadFile = File(...),
    options: str = Form("{}"),
) -> dict[str, Any] | JSONResponse:
    try:
        file_bytes = await _read_upload(file)
    except ValueError as exc:
        return _bad_request(str(exc))
    if not file_bytes:
        return _bad_request("Uploaded file is empty")

    try:
        mapper_options = _parse_options(options)
        mapper = OreMapper()
        result = mapper.predict_bytes(file_bytes, file.filename or "upload.tif", mapper_options)
        return mapper.to_response(result)
    except ValueError as exc:
        return _bad_request(str(exc))


def _parse_options(options_text: str) -> MapperOptions:
    try:
        raw = json.loads(options_text or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("options must be valid JSON") from exc
    if not isinstance(raw, dict):
        raise ValueError("options must be a JSON object")

    wavelengths = _optional_float_list(raw.get("wavelengths"), "wavelengths")
    minerals = _string_list(raw.get("minerals", DEFAULT_DEMO_MINERALS), "minerals")
    if raw.get("spectral_library") is not None:
        raise ValueError(
            "API spectral_library paths are not supported; use the CLI --library option or a future multipart library upload"
        )

    excluded: list[int] = []
    if "excluded_band_indices" in raw:
        val = raw["excluded_band_indices"]
        if not isinstance(val, list):
            raise ValueError("excluded_band_indices must be a list of integers")
        for i, item in enumerate(val):
            if isinstance(item, bool) or not isinstance(item, int):
                raise ValueError("excluded_band_indices must contain only integers")
        excluded = list(val)

    return MapperOptions(
        wavelengths=wavelengths,
        sensor=str(raw.get("sensor", "cubert_ultris_s5")),
        minerals=minerals,
        spectral_library=None,
        sam_threshold_deg=float(raw.get("sam_threshold_deg", 12.0)),
        min_confidence=float(raw.get("min_confidence", 0.65)),
        tile_size=int(raw.get("tile_size", 128)),
        normalization=str(raw.get("normalization", "l2")),
        excluded_band_indices=excluded,
        min_band_valid_fraction=float(raw.get("min_band_valid_fraction", 0.5)),
    )


def _string_list(value: Any, field_name: str) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise ValueError(f"{field_name} must be a list of strings")


def _optional_float_list(value: Any, field_name: str) -> list[float] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of numbers")
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must contain only numbers") from exc


def _bad_request(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "BAD_REQUEST", "message": message}},
    )
