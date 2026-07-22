import { useState } from "react"

interface Props {
  sensor: string
  onChange: (opts: Record<string, unknown>) => void
}

export function AdvancedOptions({ sensor, onChange }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [classifier, setClassifier] = useState("continuum_removal")
  const [threshold, setThreshold] = useState(0.65)
  const [angle, setAngle] = useState(12)
  const [tileSize, setTileSize] = useState(128)
  const [vegMask, setVegMask] = useState(false)
  const [useACE, setUseACE] = useState(false)
  const [excludeBands, setExcludeBands] = useState("")

  const emit = () => {
    onChange({
      classifier,
      min_confidence: threshold,
      sam_threshold_deg: angle,
      tile_size: tileSize,
      vegetation_mask: vegMask,
      use_ace: useACE,
      excluded_band_indices: excludeBands ? excludeBands.split(",").map(Number).filter(n => !isNaN(n)) : [],
    })
  }

  return (
    <div className="space-y-3">
      <button
        onClick={() => { setExpanded(!expanded); if (!expanded) emit() }}
        className="flex items-center gap-2 text-xs font-medium text-text-tertiary hover:text-text-secondary transition-colors"
      >
        <svg className={`w-3 h-3 transition-transform duration-200 ${expanded ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        Advanced options
      </button>

      {expanded && (
        <div className="space-y-4 p-4 rounded-xl bg-bg-2 border border-border-subtle">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs uppercase tracking-wider text-text-tertiary">Classifier</label>
              <select
                value={classifier}
                onChange={(e) => { setClassifier(e.target.value); emit() }}
                className="w-full h-9 px-2 text-xs bg-bg-1 border border-border-default rounded-lg text-text-primary"
              >
                <option value="continuum_removal">Continuum Removal</option>
                <option value="sam">SAM (Angle)</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs uppercase tracking-wider text-text-tertiary">Min Confidence</label>
              <input
                type="number" step="0.05" min="0" max="1" value={threshold}
                onChange={(e) => { setThreshold(+e.target.value); emit() }}
                className="w-full h-9 px-2 text-xs bg-bg-1 border border-border-default rounded-lg text-text-primary font-mono"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs uppercase tracking-wider text-text-tertiary">SAM Angle (&deg;)</label>
              <input
                type="number" step="1" min="1" max="90" value={angle}
                onChange={(e) => { setAngle(+e.target.value); emit() }}
                className="w-full h-9 px-2 text-xs bg-bg-1 border border-border-default rounded-lg text-text-primary font-mono"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs uppercase tracking-wider text-text-tertiary">Tile Size</label>
              <select
                value={tileSize}
                onChange={(e) => { setTileSize(+e.target.value); emit() }}
                className="w-full h-9 px-2 text-xs bg-bg-1 border border-border-default rounded-lg text-text-primary"
              >
                <option value="64">64</option>
                <option value="128">128</option>
                <option value="256">256</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <div
                onClick={() => { setVegMask(!vegMask); emit() }}
                className={`w-9 h-5 rounded-full transition-colors duration-200 relative ${vegMask ? "bg-green" : "bg-bg-3"}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${vegMask ? "translate-x-[18px]" : "translate-x-0.5"}`} />
              </div>
              <span className="text-xs text-text-secondary">Vegetation mask</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <div
                onClick={() => { setUseACE(!useACE); emit() }}
                className={`w-9 h-5 rounded-full transition-colors duration-200 relative ${useACE ? "bg-accent" : "bg-bg-3"}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${useACE ? "translate-x-[18px]" : "translate-x-0.5"}`} />
              </div>
              <span className="text-xs text-text-secondary">ACE detection</span>
            </label>
          </div>

          <div className="space-y-1">
            <label className="text-xs uppercase tracking-wider text-text-tertiary">Exclude band indices (comma separated)</label>
            <input
              type="text" value={excludeBands}
              onChange={(e) => { setExcludeBands(e.target.value); emit() }}
              placeholder="e.g. 0, 42, 200"
              className="w-full h-9 px-3 text-xs bg-bg-1 border border-border-default rounded-lg text-text-primary font-mono"
            />
          </div>
        </div>
      )}
    </div>
  )
}
