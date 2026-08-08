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

interface SettingsProps {
  options: MatchOptions
  onChange: (o: MatchOptions) => void
}

export function Settings({ options, onChange }: SettingsProps) {
  const update = (partial: Partial<MatchOptions>) => onChange({ ...options, ...partial })

  return (
    <div className="flex flex-col gap-2.5">
      <div className="space-y-1">
        <label className="text-[11px] font-medium text-muted-foreground">Classifier</label>
        <Select
          value={options.classifier || "auto"}
          onValueChange={(v: string | null) => update({ classifier: v ?? "auto" })}
        >
          <SelectTrigger size="sm" className="w-full">
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

      <div className="space-y-1">
        <label className="text-[11px] font-medium text-muted-foreground">
          Min Confidence: {(options.min_confidence ?? 0.65).toFixed(2)}
        </label>
        <Slider
          min={0}
          max={1}
          step={0.05}
          value={[options.min_confidence ?? 0.65]}
          onValueChange={(v: number | readonly number[]) =>
            update({ min_confidence: Array.isArray(v) ? v[0] : v })
          }
        />
      </div>

      <div className="space-y-1">
        <label className="text-[11px] font-medium text-muted-foreground">Normalization</label>
        <Select
          value={options.normalization || "none"}
          onValueChange={(v: string | null) => update({ normalization: v ?? "none" })}
        >
          <SelectTrigger size="sm" className="w-full">
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
    </div>
  )
}
