import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import type { MatchOptions } from "@/types"

const CLASSIFIERS = ["auto", "sam", "fuse_classical", "mtmf", "mnf_sam", "mnf_mtmf"] as const
const NORMALIZATIONS = ["none", "l2", "percentile"] as const
const STARTER_LIBRARIES = [
  { value: "", label: "None" },
  { value: "usgs_minerals", label: "USGS Minerals" },
  { value: "ecostress_veg", label: "ECOSTRESS Vegetation" },
  { value: "urban_materials", label: "Urban Materials" },
] as const

interface SettingsProps {
  options: MatchOptions
  onChange: (o: MatchOptions) => void
}

export function Settings({ options, onChange }: SettingsProps) {
  const update = (partial: Partial<MatchOptions>) => onChange({ ...options, ...partial })

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium">Settings</h3>

      <div className="space-y-2">
        <label className="text-xs text-muted-foreground">Classifier</label>
        <Select
          value={options.classifier || "auto"}
          onValueChange={(v: string | null) => update({ classifier: v ?? "auto" })}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {CLASSIFIERS.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <label className="text-xs text-muted-foreground">
          Min Confidence: {options.min_confidence ?? 0.65}
        </label>
        <Slider
          min={0}
          max={1}
          step={0.05}
          value={[options.min_confidence ?? 0.65]}
          onValueChange={(v: number | readonly number[]) => update({ min_confidence: Array.isArray(v) ? v[0] : v })}
        />
      </div>

      <div className="space-y-2">
        <label className="text-xs text-muted-foreground">Normalization</label>
        <Select
          value={options.normalization || "none"}
          onValueChange={(v: string | null) => update({ normalization: v ?? "none" })}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {NORMALIZATIONS.map((n) => (
              <SelectItem key={n} value={n}>
                {n}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <label className="text-xs text-muted-foreground">Spectral Library</label>
        <Select
          value={options.spectral_library || ""}
          onValueChange={(v: string | null) => update({ spectral_library: v || undefined })}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="None" />
          </SelectTrigger>
          <SelectContent>
            {STARTER_LIBRARIES.map((l) => (
              <SelectItem key={l.value} value={l.value}>
                {l.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
