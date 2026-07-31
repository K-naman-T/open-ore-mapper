import json
import logging
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .library import load_csv_bytes, load_csv_library
from .schemas import MatchOptions
from .engine import SpectralMatcher


logger = logging.getLogger(__name__)

_MAX_UPLOAD_BYTES = 100 * 1024 * 1024
_CHUNK_SIZE = 64 * 1024

_STARTER_LIBRARY_MAP: dict[str, str] = {
    "usgs_minerals": "usgs_minerals.csv",
    "ecostress_veg": "ecostress_veg.csv",
    "urban_materials": "urban_materials.csv",
    "usgs_minerals_real": "real/usgs_minerals.csv",
    "ecostress_veg_real": "real/ecostress_veg.csv",
    "relab_minerals": "real/relab_minerals.csv",
}


app = FastAPI(title="Spectral", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/v1/classes")
def classes() -> dict[str, list[str]]:
    return {"classes": [
        "hematite", "goethite", "jarosite", "kaolinite", "montmorillonite",
        "illite", "calcite", "dolomite", "muscovite", "chlorite",
        "epidote", "alunite", "gypsum",
    ]}


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
        mapper = SpectralMatcher()
        report = mapper.quality_bytes(
            file_bytes, file.filename or "upload.tif", mapper_options
        )
        return mapper.to_quality_response(report)
    except ValueError as exc:
        return _bad_request(str(exc))


@app.post("/v1/match", response_model=None)
async def match(
    file: UploadFile = File(...),
    library: UploadFile = File(None),
    options: str = Form("{}"),
) -> dict[str, Any] | JSONResponse:
    predict_id = uuid.uuid4().hex[:12]
    try:
        file_bytes = await _read_upload(file)
    except ValueError as exc:
        return _bad_request(str(exc))
    if not file_bytes:
        return _bad_request("Uploaded file is empty")
    try:
        mapper_options = _parse_options(options)

        if not mapper_options.classes and mapper_options.spectral_library is not None:
            lib_obj = load_csv_library(mapper_options.spectral_library, None)
            mapper_options = replace(mapper_options, classes=lib_obj.names)

        if library is not None and library.filename:
            lib_bytes = await _read_upload(library)
            if lib_bytes:
                lib_obj = load_csv_bytes(lib_bytes)
                mapper_options = replace(
                    mapper_options,
                    classes=lib_obj.names,
                    spectral_library=None,
                    spectral_library_bytes=lib_bytes,
                )

        mapper = SpectralMatcher()
        result = mapper.predict_bytes(
            file_bytes, file.filename or "upload.tif", mapper_options
        )
        response = mapper.to_response(result)
        response["map_uuid"] = predict_id
        return response
    except ValueError as exc:
        return _bad_request(str(exc))


def _parse_options(options_text: str) -> MatchOptions:
    try:
        raw = json.loads(options_text or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("options must be valid JSON") from exc
    if not isinstance(raw, dict):
        raise ValueError("options must be a JSON object")

    wavelengths = _optional_float_list(raw.get("wavelengths"), "wavelengths")
    classes = _string_list(raw.get("classes", []), "classes")

    spectral_library: str | None = None
    if raw.get("spectral_library") is not None:
        spectral_library = _resolve_spectral_library(str(raw["spectral_library"]))

    excluded: list[int] = []
    if "excluded_band_indices" in raw:
        val = raw["excluded_band_indices"]
        if not isinstance(val, list):
            raise ValueError("excluded_band_indices must be a list of integers")
        for i, item in enumerate(val):
            if isinstance(item, bool) or not isinstance(item, int):
                raise ValueError("excluded_band_indices must contain only integers")
        excluded = list(val)

    return MatchOptions(
        wavelengths=wavelengths,
        sensor=str(raw.get("sensor", "aviris")),
        classes=classes if classes else [],
        spectral_library=spectral_library,
        sam_threshold_deg=float(raw.get("sam_threshold_deg", 12.0)),
        min_confidence=float(raw.get("min_confidence", 0.65)),
        tile_size=int(raw.get("tile_size", 128)),
        normalization=str(raw.get("normalization", "l2")),
        excluded_band_indices=excluded,
        min_band_valid_fraction=float(raw.get("min_band_valid_fraction", 0.5)),
        classifier=str(raw.get("classifier", "auto")),
        use_mtmf=bool(raw.get("use_mtmf", False)),
        mf_threshold=float(raw.get("mf_threshold", 0.5)),
        infeas_threshold=float(raw.get("infeas_threshold", 10.0)),
        n_mnf_components=int(raw.get("n_mnf_components", 20)),
    )


def _resolve_starter_library(name: str) -> str | None:
    """Map a starter library name to its CSV path, or None if unknown."""
    relative = _STARTER_LIBRARY_MAP.get(name.strip())
    if relative is None:
        return None
    return str(Path(__file__).resolve().parents[2] / "data" / "starter_libraries" / relative)


def _resolve_spectral_library(value: str) -> str:
    """Resolve a spectral_library option to a loadable path.

    Bare names (no path separators, no .csv suffix) are matched against the
    bundled starter libraries; anything with a .csv suffix is treated as a
    relative path.
    """
    value = value.strip()
    if not value:
        return value
    looks_like_starter_name = (
        "/" not in value and "\\" not in value and not value.endswith(".csv")
    )
    if looks_like_starter_name:
        resolved = _resolve_starter_library(value)
        if resolved is None:
            known = ", ".join(sorted(_STARTER_LIBRARY_MAP))
            raise ValueError(
                f"Unknown spectral library '{value}'. Known starter libraries: {known}"
            )
        return resolved
    return value


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
