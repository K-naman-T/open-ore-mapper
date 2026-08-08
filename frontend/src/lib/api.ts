import type { MatchOptions, MatchResult } from "@/types"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

export interface StarterLibrary {
  value: string
  label: string
}

export const STARTER_LIBRARIES: StarterLibrary[] = [
  { value: "usgs_minerals", label: "USGS Minerals" },
  { value: "ecostress_veg", label: "ECOSTRESS Vegetation" },
  { value: "urban_materials", label: "Urban Materials" },
  { value: "usgs_minerals_real", label: "USGS Minerals (real)" },
  { value: "ecostress_veg_real", label: "ECOSTRESS Vegetation (real)" },
  { value: "relab_minerals", label: "RELAB Minerals" },
]

export function getStarterLibraries(): StarterLibrary[] {
  return STARTER_LIBRARIES
}

export async function uploadAndMatch(
  cubeFile: File,
  libraryFile: File | null,
  options: MatchOptions,
): Promise<MatchResult> {
  const form = new FormData()
  form.append("file", cubeFile)
  if (libraryFile) form.append("library", libraryFile)

  const payload: Record<string, unknown> = {}
  if (options.classes?.length) payload.classes = options.classes
  if (options.classifier) payload.classifier = options.classifier
  if (options.min_confidence !== undefined)
    payload.min_confidence = options.min_confidence
  if (options.normalization) payload.normalization = options.normalization
  if (options.excluded_band_indices?.length)
    payload.excluded_band_indices = options.excluded_band_indices
  if (options.spectral_library) payload.spectral_library = options.spectral_library
  if (options.tile_size !== undefined) payload.tile_size = options.tile_size
  form.append("options", JSON.stringify(payload))

  const res = await fetch(`${API_BASE}/v1/match`, { method: "POST", body: form })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Match failed (${res.status}): ${err}`)
  }
  return res.json()
}
