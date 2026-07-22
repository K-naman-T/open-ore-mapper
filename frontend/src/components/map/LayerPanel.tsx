import { useState } from "react"

interface Props {
  showClassified: boolean
  showConfidence: boolean
  showAbundance: boolean
  onToggleClassified: () => void
  onToggleConfidence: () => void
  onToggleAbundance: () => void
  minerals: string[]
}

export function LayerPanel({
  showClassified,
  showConfidence,
  showAbundance,
  onToggleClassified,
  onToggleConfidence,
  onToggleAbundance,
  minerals,
}: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="h-9 px-3 bg-bg-1/95 backdrop-blur-sm border border-border-default rounded-lg shadow-lg
          text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-bg-2 transition-all duration-150
          flex items-center gap-2"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
        </svg>
        Layers
      </button>

      {open && (
        <div className="absolute bottom-full mb-2 left-0 bg-bg-1/95 backdrop-blur-sm border border-border-default rounded-xl shadow-lg p-3 w-56 space-y-2 animate-[tooltip-in]">
          <label className="flex items-center justify-between cursor-pointer group">
            <span className="text-xs text-text-secondary group-hover:text-text-primary transition-colors">Classified map</span>
            <div
              onClick={onToggleClassified}
              className={`w-9 h-5 rounded-full transition-colors duration-200 relative ${showClassified ? "bg-accent" : "bg-bg-3"}`}
            >
              <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${showClassified ? "translate-x-[18px]" : "translate-x-0.5"}`} />
            </div>
          </label>

          <label className="flex items-center justify-between cursor-pointer group">
            <span className="text-xs text-text-secondary group-hover:text-text-primary transition-colors">Confidence</span>
            <div
              onClick={onToggleConfidence}
              className={`w-9 h-5 rounded-full transition-colors duration-200 relative ${showConfidence ? "bg-accent" : "bg-bg-3"}`}
            >
              <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${showConfidence ? "translate-x-[18px]" : "translate-x-0.5"}`} />
            </div>
          </label>

          <label className="flex items-center justify-between cursor-pointer group">
            <span className="text-xs text-text-secondary group-hover:text-text-primary transition-colors">Top abundance</span>
            <div
              onClick={onToggleAbundance}
              className={`w-9 h-5 rounded-full transition-colors duration-200 relative ${showAbundance ? "bg-accent" : "bg-bg-3"}`}
            >
              <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${showAbundance ? "translate-x-[18px]" : "translate-x-0.5"}`} />
            </div>
          </label>

          {minerals.length > 0 && (
            <>
              <div className="border-t border-border-subtle pt-2 mt-1">
                <p className="text-[10px] uppercase tracking-wider text-text-tertiary mb-1">{minerals.length} minerals</p>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
