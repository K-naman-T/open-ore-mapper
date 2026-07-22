import json
import logging
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Union

from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile, Body, Path as FAPath
from fastapi.responses import FileResponse, JSONResponse, Response

import numpy as np

from .schemas import (
    DEFAULT_DEMO_MINERALS,
    DEFAULT_REAL_MINERALS,
    MapperOptions,
    validate_bbox,
)
from .service import OreMapper
from .store import (
    get_connection,
    create_bbox_job,
    update_job_progress,
    fail_job,
    complete_job,
    fetch_job_public,
    fetch_map_result,
    store_result,
    mark_nonterminal_jobs_interrupted,
)

logger = logging.getLogger(__name__)

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
        report = mapper.quality_bytes(
            file_bytes, file.filename or "upload.tif", mapper_options
        )
        return mapper.to_quality_response(report)
    except ValueError as exc:
        return _bad_request(str(exc))


@app.post("/v1/predict", response_model=None)
async def predict(
    file: UploadFile = File(...),
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
        mapper = OreMapper()
        result = mapper.predict_bytes(
            file_bytes, file.filename or "upload.tif", mapper_options
        )
        response = mapper.to_response(result)
        response["map_uuid"] = predict_id
        return response
    except ValueError as exc:
        return _bad_request(str(exc))


@app.post("/v1/predict/bbox", response_model=None)
async def predict_bbox(
    body: dict[str, Any] = Body(...),
    background_tasks: BackgroundTasks = None,
) -> Union[dict[str, Any], JSONResponse]:
    try:
        bbox_raw = body.get("bbox")
        if not bbox_raw or not isinstance(bbox_raw, dict):
            return _bad_request(
                "bbox must be a JSON object with west/south/east/north"
            )

        bbox = validate_bbox(bbox_raw)
        mapper_options = _parse_options(json.dumps(body))

        conn = get_connection()
        job_id = create_bbox_job(conn, bbox, body)

        background_tasks.add_task(
            _run_bbox_pipeline,
            job_id=job_id,
            bbox=bbox,
            options=mapper_options,
        )

        return JSONResponse(
            status_code=202,
            content=fetch_job_public(conn, job_id),
        )
    except ValueError as exc:
        return _bad_request(str(exc))


@app.get("/v1/maps/{map_uuid}", response_model=None)
async def get_map(map_uuid: str) -> dict[str, Any] | JSONResponse:
    conn = get_connection()
    job = fetch_job_public(conn, map_uuid)
    if job is None or job["status"] != "complete":
        return _not_found("map not found or not yet complete")
    result = fetch_map_result(conn, map_uuid)
    if result is None:
        return _not_found("map result not found")
    return result


@app.get("/v1/maps/{map_uuid}/tiles/{z}/{x}/{y}.png")
async def get_tile(
    map_uuid: str,
    z: int = FAPath(ge=0),
    x: int = FAPath(ge=0),
    y: int = FAPath(ge=0),
) -> Response:
    from .tileserver import get_tile_path

    path = get_tile_path(map_uuid, z, x, y)
    if path is None:
        return JSONResponse(status_code=404, content={"error": "tile not found"})
    return FileResponse(path, media_type="image/png")


@app.get("/v1/jobs/{job_id}", response_model=None)
async def get_job(job_id: str) -> dict[str, Any] | JSONResponse:
    conn = get_connection()
    job = fetch_job_public(conn, job_id)
    if job is None:
        return _not_found("job not found")
    return job


@app.on_event("startup")
async def startup() -> None:
    conn = get_connection()
    mark_nonterminal_jobs_interrupted(conn)
    logger.info("Startup complete: marked interrupted jobs as failed")


def _run_bbox_pipeline(
    job_id: str,
    bbox: dict[str, float],
    options: MapperOptions,
) -> None:
    conn = get_connection()
    try:
        update_job_progress(
            conn, job_id, "searching", progress=10, message="Searching EMIT granules"
        )

        from .emit_client import EmitError, EmitScene, search_emit_granules, select_best_granule

        granules = search_emit_granules(
            bbox=(bbox["west"], bbox["south"], bbox["east"], bbox["north"]),
            cloud_max=10.0,
            max_results=3,
        )
        if not granules:
            msg = "No EMIT granules found for the requested bounding box"
            logger.error("%s: %s", job_id, msg)
            fail_job(conn, job_id, error=msg)
            return

        best = select_best_granule(granules, cloud_max=10.0)
        if best is None:
            msg = (
                "No suitable EMIT granule found (all exceed cloud cover threshold)"
            )
            logger.error("%s: %s", job_id, msg)
            fail_job(conn, job_id, error=msg)
            return

        update_job_progress(
            conn,
            job_id,
            "downloading",
            progress=30,
            message="Downloading selected granule",
        )

        scene = EmitScene.from_granule(best)

        update_job_progress(
            conn,
            job_id,
            "processing",
            progress=50,
            message="Orthorectifying scene",
        )

        wavelengths_list = scene.wavelengths.tolist()

        auto_excluded: list[int] | None = None
        if scene.good_wavelengths is not None:
            gw = np.asarray(scene.good_wavelengths)
            auto_excluded = [int(i) for i in range(len(gw)) if not gw[i]]

        tiles = list(scene.orthorectify(tile_size=options.tile_size))
        if not tiles:
            msg = "No orthorectified tiles produced from the granule"
            logger.error("%s: %s", job_id, msg)
            fail_job(conn, job_id, error=msg)
            return

        total_tiles = len(tiles)
        update_job_progress(
            conn,
            job_id,
            "processing",
            progress=50,
            message=f"Classifying tile 1/{total_tiles}",
        )

        excluded = list(options.excluded_band_indices)
        if not excluded and auto_excluded is not None:
            excluded = auto_excluded

        first_tile = tiles[0][4]
        from .qc import analyze_raster_quality

        report = analyze_raster_quality(
            first_tile,
            wavelengths_list,
            excluded_band_indices=excluded or None,
            min_band_valid_fraction=0.0,
        )
        if len(report.retained_band_indices) < 2:
            msg = "Fewer than 2 usable bands in EMIT scene after QC"
            logger.error("%s: %s", job_id, msg)
            fail_job(conn, job_id, error=msg)
            return

        retained_bands = report.retained_band_indices
        retained_wls = [wavelengths_list[i] for i in retained_bands]

        mapper = OreMapper()
        library = mapper._load_library(options, retained_wls)

        o_h, o_w = scene.glt_x.shape
        n_minerals = len(library.names)
        full_class = np.full((o_h, o_w), 255, dtype=np.uint8)
        full_conf = np.zeros((o_h, o_w), dtype=np.float32)
        full_abund = np.zeros((o_h, o_w, n_minerals), dtype=np.float32)
        classified_any = False

        for tile_idx, (y0, y1, x0, x1, tile_data) in enumerate(tiles):
            progress = 50 + int(40 * (tile_idx + 1) / total_tiles)
            if tile_idx == 0:
                msg = f"Classifying tile 1/{total_tiles}"
            else:
                msg = f"Classifying tile {tile_idx + 1}/{total_tiles}"
            update_job_progress(conn, job_id, "processing", progress=progress, message=msg)

            tile_bands = tile_data[:, :, retained_bands].astype(np.float32, copy=False)
            cm, cf, ab = mapper._classify_core(
                tile_bands, retained_wls, library, options
            )

            th, tw = y1 - y0, x1 - x0
            full_class[y0:y1, x0:x1] = cm[:th, :tw]
            full_conf[y0:y1, x0:x1] = cf[:th, :tw]
            full_abund[y0:y1, x0:x1] = ab[:th, :tw]

            if np.any(cm != 255):
                classified_any = True

        if not classified_any:
            msg = "No valid classified pixels in any orthorectified tile"
            logger.error("%s: %s", job_id, msg)
            fail_job(conn, job_id, error=msg)
            return

        update_job_progress(conn, job_id, "processing", progress=92, message="Rendering map")
        top_abundance = np.max(full_abund, axis=2)

        from .rendering import class_map_png_data_url, confidence_png_data_url, mineral_statistics

        map_stats = mineral_statistics(full_class, full_conf, full_abund, library.names)
        response = {
            "status": "success",
            "model_used": f"library_{options.classifier}_nnls_v1",
            "sensor": "emit",
            "wavelengths": retained_wls,
            "minerals": library.names,
            "output_image": class_map_png_data_url(full_class, library.names),
            "confidence_image": confidence_png_data_url(full_conf),
            "top_abundance_image": confidence_png_data_url(top_abundance),
            "statistics": {name: asdict(stats) for name, stats in map_stats.items()},
            "warnings": [],
            "downloads": {},
            "provenance": {
                "source": "emit",
                "granule_id": best.get("id", ""),
                "requested_bbox": bbox,
                "processed_bounds": (
                    f"Orthorectified scene of shape ({o_h}, {o_w}) pixels; "
                    "exact WGS84 georeferencing not yet available from GLT metadata"
                ),
                "processed_tile_count": total_tiles,
                "selected_minerals": library.names,
                "classifier": options.classifier,
                "wavelength_count": len(retained_wls),
            },
        }

        store_result(conn, job_id, response)
        complete_job(conn, job_id, map_uuid=job_id)

    except EmitError as exc:
        logger.error("Bbox pipeline failed for job %s: %s", job_id, exc)
        try:
            fail_job(conn, job_id, error=str(exc))
        except Exception:
            pass
    except Exception:
        logger.exception("Bbox pipeline failed for job %s", job_id)
        try:
            fail_job(conn, job_id, error="Pipeline error")
        except Exception:
            pass


def _parse_options(options_text: str) -> MapperOptions:
    try:
        raw = json.loads(options_text or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("options must be valid JSON") from exc
    if not isinstance(raw, dict):
        raise ValueError("options must be a JSON object")

    wavelengths = _optional_float_list(raw.get("wavelengths"), "wavelengths")
    minerals = _string_list(raw.get("minerals", DEFAULT_REAL_MINERALS), "minerals")
    if "minerals" in raw and any(m.endswith("_demo") for m in minerals):
        missing = [
            m for m in minerals if m.endswith("_demo") and m not in DEFAULT_DEMO_MINERALS
        ]
        if missing:
            raise ValueError(f"Unknown demo minerals: {missing}")
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
        classifier=str(raw.get("classifier", "continuum_removal")),
        use_ace=bool(raw.get("use_ace", False)),
        unmixing=str(raw.get("unmixing", "auto")),
        vegetation_mask=bool(raw.get("vegetation_mask", False)),
        ndvi_threshold=float(raw.get("ndvi_threshold", 0.3)),
        topographic_correct=bool(raw.get("topographic_correct", False)),
        dem_type=str(raw.get("dem_type", "COP30")),
        solar_azimuth=raw.get("solar_azimuth"),
        solar_elevation=raw.get("solar_elevation"),
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


def _not_found(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "NOT_FOUND", "message": message}},
    )
