import type { MatchOptions, MatchResult } from "@/types"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

export async function uploadAndMatch(
  cubeFile: File,
  libraryFile: File | null,
  options: MatchOptions,
): Promise<MatchResult> {
  const form = new FormData()
  form.append("cube_file", cubeFile)
  if (libraryFile) form.append("library_file", libraryFile)
  if (options.classifier) form.append("classifier", options.classifier)
  if (options.min_confidence !== undefined)
    form.append("min_confidence", String(options.min_confidence))
  if (options.normalization) form.append("normalization", options.normalization)
  if (options.excluded_band_indices && options.excluded_band_indices.length > 0)
    form.append("excluded_band_indices", options.excluded_band_indices.join(","))
  if (options.spectral_library) form.append("spectral_library", options.spectral_library)
  if (options.tile_size) form.append("tile_size", String(options.tile_size))

  const res = await fetch(`${API_BASE}/v1/match`, { method: "POST", body: form })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Match failed (${res.status}): ${err}`)
  }
  return res.json()
}

export async function getClasses(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/v1/classes`)
  if (!res.ok) throw new Error(`Failed to fetch classes (${res.status})`)
  return res.json()
}

export async function healthCheck(): Promise<void> {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) throw new Error(`Health check failed (${res.status})`)
}
