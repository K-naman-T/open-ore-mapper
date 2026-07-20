from __future__ import annotations

import json
import os
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PublicScene:
    id: str
    name: str
    url: str
    source_page: str
    sensor: str
    note: str


CATALOG: list[PublicScene] = [
    PublicScene(
        id="salinas_a_corrected",
        name="Salinas-A Corrected",
        url="https://www.ehu.eus/ccwintco/uploads/1/1a/SalinasA_corrected.mat",
        source_page="https://www.ehu.eus/ccwintco/index.php/Hyperspectral_Remote_Sensing_Scenes",
        sensor="aviris",
        note=(
            "Real public airborne hyperspectral imagery from AVIRIS over Salinas Valley, CA. "
            "This is an agricultural/vegetation scene, not a mineral ore scene. "
            "Spatial extent is 83 x 86 pixels, 204 bands in the distributed corrected file."
        ),
    ),
    PublicScene(
        id="indian_pines_corrected",
        name="Indian Pines Corrected",
        url="https://www.ehu.eus/ccwintco/uploads/6/67/Indian_pines_corrected.mat",
        source_page="https://www.ehu.eus/ccwintco/index.php/Hyperspectral_Remote_Sensing_Scenes",
        sensor="aviris",
        note=(
            "Real public airborne hyperspectral imagery from AVIRIS over Indian Pines test site, IN. "
            "Agricultural/land-cover scene, not a mineral ore scene. 145 x 145 pixels, 200 bands in the distributed corrected file."
        ),
    ),
    PublicScene(
        id="cuprite_aviris",
        name="Cuprite AVIRIS Reflectance",
        url="https://www.ehu.eus/ccwintco/uploads/7/7d/Cuprite_f970619t01p02_r02_sc03.a.rfl.mat",
        source_page="https://www.ehu.eus/ccwintco/index.php/Hyperspectral_Remote_Sensing_Scenes",
        sensor="aviris",
        note=(
            "Mineral-relevant AVIRIS reflectance scene over Cuprite, NV – a well-known "
            "hydrothermal alteration mineral site. Large file (~100 MB); download may be slow. "
            "224 bands, 350 x 350 pixels."
        ),
    ),
]


def get_scene(scene_id: str) -> PublicScene:
    for scene in CATALOG:
        if scene.id == scene_id:
            return scene
    valid = ", ".join(s.id for s in CATALOG)
    raise ValueError(f"Unknown scene '{scene_id}'. Valid scene IDs: {valid}")


def scene_catalog_as_json() -> str:
    data: list[dict[str, Any]] = []
    for scene in CATALOG:
        data.append(
            {
                "id": scene.id,
                "name": scene.name,
                "url": scene.url,
                "source_page": scene.source_page,
                "sensor": scene.sensor,
                "note": scene.note,
            }
        )
    return json.dumps(data, indent=2)


def download_scene(
    scene_id: str,
    output_dir: str | Path,
    source_url: str | None = None,
) -> Path:
    scene = get_scene(scene_id)
    url = source_url or scene.url
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    dest = out / os.path.basename(url)
    print(f"Downloading {scene.name} from {url} ...")
    with urllib.request.urlopen(url) as response:  # noqa: S310
        with open(dest, "wb") as f:
            shutil.copyfileobj(response, f)
    print(f"Saved to {dest}")
    return dest
