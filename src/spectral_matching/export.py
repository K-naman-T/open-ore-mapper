from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
import tifffile


def export_geotiff(
    path: str | Path,
    class_map: NDArray[np.uint8],
    confidence_map: NDArray[np.float32],
    classes: list[str],
    source_path: str | Path | None = None,
) -> Path:
    dest = Path(path)

    extratags: list[tuple[int, str, int, object, bool]] = []
    if source_path is not None:
        src = Path(source_path)
        if src.suffix.lower() in (".tif", ".tiff"):
            with tifffile.TiffFile(str(src)) as src_tif:
                page = src_tif.pages[0]
                for code in (33550, 33922, 34264, 34735, 34736, 34737):
                    if code in page.tags:
                        tag = page.tags[code]
                        extratags.append((code, tag.dtype, tag.count, tag.value, True))

    class_names_json = json.dumps(classes)
    with tifffile.TiffWriter(str(dest)) as tif:
        tif.write(
            class_map,
            description="class_id",
            extratags=extratags or None,
        )
        tif.write(
            confidence_map,
            description="confidence",
            metadata={"CLASS_NAMES": class_names_json},
        )

    return dest
