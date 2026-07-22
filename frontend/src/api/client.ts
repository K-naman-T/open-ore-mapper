const API_BASE = import.meta.env.VITE_API_URL ?? "/api"

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...opts?.headers },
    ...opts,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? `Request failed: ${res.status}`)
  }
  return res.json()
}

export interface JobStatus {
  job_id: string
  status: "queued" | "processing" | "complete" | "failed"
  progress: number
}

export interface MapResult {
  map_uuid: string
  status: string
  model_used: string
  sensor: string
  wavelengths: number[]
  minerals: string[]
  output_image: string
  confidence_image: string
  top_abundance_image: string
  statistics: Record<string, MineralStat>
  warnings: string[]
  quality_report: QCReport
}

export interface MineralStat {
  count: number
  percentage: number
  mean_confidence: number
  mean_abundance: number
}

export interface QCReport {
  status: string
  shape: [number, number, number]
  band_count: number
  retained_band_indices: number[]
  excluded_band_indices: number[]
  valid_pixel_fraction: number
  warnings: string[]
}

export async function uploadAndPredict(
  file: File,
  options: Record<string, unknown>,
): Promise<MapResult> {
  const form = new FormData()
  form.append("file", file)
  form.append("options", JSON.stringify(options))
  const res = await fetch(`${API_BASE}/v1/predict`, { method: "POST", body: form })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? `Upload failed: ${res.status}`)
  }
  const data = await res.json()
  if (!data.map_uuid) {
    data.map_uuid = crypto.randomUUID?.() ?? Date.now().toString(36)
  }
  return data as MapResult
}

export async function getMinerals(): Promise<string[]> {
  const data = await request<{ minerals: string[] }>("/v1/minerals")
  return data.minerals
}

export async function healthCheck(): Promise<boolean> {
  return request<{ status: string }>("/health").then(() => true).catch(() => false)
}
