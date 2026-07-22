from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .continuum_removal import AbsorptionFeature, extract_absorption_features, hull_quotient
from .mineral_features import DiagnosticFeature, all_mineral_names, lookup_mineral


@dataclass
class SffResult:
    mineral: str
    score: float
    matched_features: list[str]
    reason: str


_POSITION_TOLERANCE = 20.0
_MIN_SCORE = 0.3


def _score_diagnostic(
    diag: DiagnosticFeature,
    extracted: list[AbsorptionFeature],
) -> tuple[float, str | None]:
    best = 0.0
    best_match: AbsorptionFeature | None = None
    for ef in extracted:
        diff = abs(ef.position - diag.position_nm)
        if diff > _POSITION_TOLERANCE:
            continue
        pos_score = np.exp(-0.5 * (diff / 15.0) ** 2)
        if ef.depth < diag.depth_min:
            depth_score = ef.depth / diag.depth_min if diag.depth_min > 0 else 0.0
        elif ef.depth > diag.depth_max:
            depth_score = diag.depth_max / ef.depth if ef.depth > 0 else 0.0
        else:
            depth_score = 1.0
        depth_score = min(depth_score, 1.0)
        score = float(pos_score * depth_score)
        if score > best:
            best = score
            best_match = ef
    if best_match is None:
        return 0.0, None
    name = f"{diag.assignment} @ {diag.position_nm:.0f}nm"
    return best, name


def _discrimination_penalty(
    mineral: str,
    raw_score: float,
    features: list[AbsorptionFeature],
) -> tuple[float, list[str]]:
    penalties: list[str] = []
    score = raw_score
    pos_set = {f.position for f in features}
    depth_map = {f.position: f.depth for f in features}

    def has_near(pos: float, tol: float = 20.0) -> bool:
        return any(abs(p - pos) <= tol for p in pos_set)

    def max_depth_near(pos: float, tol: float = 20.0) -> float:
        depths = [d for p, d in depth_map.items() if abs(p - pos) <= tol]
        return max(depths) if depths else 0.0

    if mineral == "kaolinite":
        if has_near(1480) and has_near(1760):
            score *= 0.3
            penalties.append("1480+1760nm present (suggests alunite)")

    if mineral == "dickite":
        if has_near(2160, tol=15):
            score *= 0.4
            penalties.append("2160nm shoulder present (suggests kaolinite)")

    if mineral == "alunite":
        if not (has_near(1480) and has_near(1760)):
            score *= 0.3
            penalties.append("missing 1480+1760nm SO4 (suggests kaolinite)")

    if mineral == "calcite":
        if has_near(2320, tol=10.0) and not has_near(2340, tol=10.0):
            score *= 0.3
            penalties.append("2320nm without 2340nm (suggests dolomite)")

    if mineral == "dolomite":
        if has_near(2340, tol=10.0) and not has_near(2320, tol=10.0):
            score *= 0.3
            penalties.append("2340nm without 2320nm (suggests calcite)")

    if mineral == "illite":
        if max_depth_near(1900) > 0.08:
            score *= 0.5
            penalties.append("strong 1900nm water (suggests montmorillonite)")

    if mineral == "montmorillonite":
        if max_depth_near(1900) < 0.08:
            score *= 0.3
            penalties.append("weak 1900nm water (suggests illite)")

    if mineral == "hematite":
        if has_near(930, tol=15.0):
            score *= 0.3
            penalties.append("930nm present (suggests goethite)")

    if mineral == "goethite":
        if has_near(860, tol=15.0):
            score *= 0.3
            penalties.append("860nm present (suggests hematite)")

    return score, penalties


def sff_classify_details(
    wavelengths: NDArray[np.float32],
    continuum_removed: NDArray[np.float32],
    mineral_names: list[str] | None = None,
) -> SffResult | None:
    if mineral_names is None:
        mineral_names = all_mineral_names()

    features = extract_absorption_features(wavelengths, continuum_removed, min_depth=0.02)
    if not features:
        return None

    best_result: SffResult | None = None

    for name in mineral_names:
        profile = lookup_mineral(name)
        if profile is None or not profile.features:
            continue

        total_score = 0.0
        matched_names: list[str] = []

        for diag in profile.features:
            score, feat_name = _score_diagnostic(diag, features)
            if score > 0.3:
                total_score += score
                if feat_name:
                    matched_names.append(feat_name)

        raw = total_score / len(profile.features)
        adj, penalties = _discrimination_penalty(name, raw, features)

        if adj < _MIN_SCORE:
            continue

        parts: list[str] = []
        if matched_names:
            parts.append(f"matched {len(matched_names)}/{len(profile.features)} features")
        if penalties:
            parts.extend(penalties)
        parts.append(f"score={adj:.3f}")

        result = SffResult(
            mineral=profile.name,
            score=float(adj),
            matched_features=matched_names,
            reason="; ".join(parts),
        )

        if best_result is None or adj > best_result.score:
            best_result = result

    if best_result is not None and best_result.score >= _MIN_SCORE:
        return best_result
    return None


def sff_classify(
    wavelengths: NDArray[np.float32],
    continuum_removed: NDArray[np.float32],
    mineral_names: list[str] | None = None,
) -> str | None:
    result = sff_classify_details(wavelengths, continuum_removed, mineral_names)
    return result.mineral if result is not None else None


def sff_classify_cube(
    cube: NDArray[np.float32],
    wavelengths: NDArray[np.float32],
    mineral_names: list[str] | None = None,
) -> tuple[NDArray[np.uint8], NDArray[np.float32]]:
    H, W, B = cube.shape
    if mineral_names is None:
        mineral_names = all_mineral_names()

    class_map: NDArray[np.uint8] = np.zeros((H, W), dtype=np.uint8)
    confidence: NDArray[np.float32] = np.zeros((H, W), dtype=np.float32)

    for h in range(H):
        for w in range(W):
            cr = hull_quotient(wavelengths, cube[h, w, :])
            result = sff_classify_details(wavelengths, cr, mineral_names)
            if result is not None:
                try:
                    class_map[h, w] = np.uint8(mineral_names.index(result.mineral) + 1)
                except ValueError:
                    class_map[h, w] = 0
                confidence[h, w] = result.score

    return class_map, confidence
