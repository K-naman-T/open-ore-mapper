export interface MatchOptions {
  classes?: string[]
  classifier?: string
  min_confidence?: number
  normalization?: string
  excluded_band_indices?: number[]
  spectral_library?: string
  tile_size?: number
}

export interface ClassStatistics {
  count: number
  percentage: number
  mean_confidence: number
  mean_abundance: number
}

export interface MatchResult {
  status: string
  model_used: string
  sensor: string
  wavelengths: number[]
  classes: string[]
  output_image: string
  confidence_image: string
  statistics: Record<string, ClassStatistics>
  warnings: string[]
  downloads: Record<string, string>
  quality_report?: object
}

export type Theme = "light" | "dark" | "system"
