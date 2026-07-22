import { useRef } from "react"
import { mineralColor } from "../../lib/colors"
import type { Bbox } from "./DrawBbox"

const ALL_MINERALS = [
  "hematite",
  "goethite",
  "jarosite",
  "magnetite",
  "limonite",
  "ferrihydrite",
]

const SENSORS = ["EMIT", "Cubert", "Custom"]

const CLASSIFIERS = ["Continuum Removal", "SAM"]

interface Props {
  open: boolean
  onClose: () => void
  sensor: string
  onSensorChange: (v: string) => void
  minerals: string[]
  onMineralsChange: (v: string[]) => void
  classifier: string
  onClassifierChange: (v: string) => void
  confidence: number
  onConfidenceChange: (v: number) => void
  ace: boolean
  onAceChange: (v: boolean) => void
  vegMask: boolean
  onVegMaskChange: (v: boolean) => void
  file: File | null
  onFileChange: (v: File | null) => void
  bbox: Bbox | null
  onMapMinerals: () => void
  processing: boolean
  canMap: boolean
  dataWt?: string
}

export function SettingsPanel({
  open,
  onClose,
  sensor,
  onSensorChange,
  minerals,
  onMineralsChange,
  classifier,
  onClassifierChange,
  confidence,
  onConfidenceChange,
  ace,
  onAceChange,
  vegMask,
  onVegMaskChange,
  file,
  onFileChange,
  bbox,
  onMapMinerals,
  processing,
  canMap,
  dataWt,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  const toggle = (m: string) => {
    onMineralsChange(
      minerals.includes(m)
        ? minerals.filter((x) => x !== m)
        : [...minerals, m],
    )
  }

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-30" onClick={onClose} />
      )}

      <div
        className={`fixed top-0 right-0 z-40 h-full w-80 bg-bg-1/95 backdrop-blur-xl border-l border-border-default shadow-2xl
          transition-transform duration-300 ease-out flex flex-col
          ${open ? "translate-x-0" : "translate-x-full"}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 h-14 border-b border-border-subtle shrink-0">
          <h2 className="text-sm font-semibold text-text-primary">Settings</h2>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg text-text-tertiary hover:text-text-primary hover:bg-bg-2 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5 text-sm">
          {/* Sensor */}
          <section>
            <label className="text-xs font-medium text-text-secondary mb-2 block">Sensor</label>
            <div className="flex gap-1">
              {SENSORS.map((s) => (
                <button
                  key={s}
                  onClick={() => onSensorChange(s)}
                  className={`flex-1 h-8 text-xs font-medium rounded-lg transition-all duration-150 ${
                    sensor === s
                      ? "bg-accent/10 text-accent border border-accent/20"
                      : "bg-bg-0 text-text-tertiary border border-border-subtle hover:border-border-strong"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </section>

          {/* Classifier */}
          <section>
            <label className="text-xs font-medium text-text-secondary mb-2 block">Classifier</label>
            <div className="flex gap-1">
              {CLASSIFIERS.map((c) => (
                <button
                  key={c}
                  onClick={() => onClassifierChange(c)}
                  className={`flex-1 h-8 text-xs font-medium rounded-lg transition-all duration-150 ${
                    classifier === c
                      ? "bg-accent/10 text-accent border border-accent/20"
                      : "bg-bg-0 text-text-tertiary border border-border-subtle hover:border-border-strong"
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </section>

          {/* Minerals */}
          <section>
            <label className="text-xs font-medium text-text-secondary mb-2 block">Minerals</label>
            <div className="flex flex-wrap gap-1.5">
              {ALL_MINERALS.map((m, i) => (
                <button
                  key={m}
                  onClick={() => toggle(m)}
                  className={`inline-flex items-center gap-1.5 h-7 px-2.5 rounded-lg text-xs font-medium transition-all duration-150 ${
                    minerals.includes(m)
                      ? "bg-accent/10 text-accent border border-accent/20"
                      : "bg-bg-0 text-text-tertiary border border-border-subtle hover:border-border-strong"
                  }`}
                >
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: mineralColor(i) }} />
                  {m}
                </button>
              ))}
            </div>
          </section>

          {/* Confidence */}
          <section>
            <label className="text-xs font-medium text-text-secondary mb-2 block">
              Confidence: <span className="text-text-primary font-mono">{confidence.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min={0.5}
              max={1.0}
              step={0.01}
              value={confidence}
              onChange={(e) => onConfidenceChange(+e.target.value)}
              className="w-full h-1.5 bg-bg-3 rounded-full appearance-none cursor-pointer accent-accent
                [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5
                [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent [&::-webkit-slider-thumb]:shadow-md"
            />
          </section>

          {/* Toggles */}
          <section className="space-y-2">
            <label className="flex items-center justify-between cursor-pointer group">
              <span className="text-xs text-text-secondary group-hover:text-text-primary transition-colors">ACE Detection</span>
              <div
                onClick={() => onAceChange(!ace)}
                className={`w-9 h-5 rounded-full transition-colors duration-200 relative ${ace ? "bg-accent" : "bg-bg-3"}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${ace ? "translate-x-[18px]" : "translate-x-0.5"}`} />
              </div>
            </label>
            <label className="flex items-center justify-between cursor-pointer group">
              <span className="text-xs text-text-secondary group-hover:text-text-primary transition-colors">Vegetation Mask</span>
              <div
                onClick={() => onVegMaskChange(!vegMask)}
                className={`w-9 h-5 rounded-full transition-colors duration-200 relative ${vegMask ? "bg-accent" : "bg-bg-3"}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${vegMask ? "translate-x-[18px]" : "translate-x-0.5"}`} />
              </div>
            </label>
          </section>

          {/* File upload */}
          <section>
            <label className="text-xs font-medium text-text-secondary mb-2 block">Or upload a file</label>
            <div
              onClick={() => inputRef.current?.click()}
              className="w-full h-16 rounded-xl border-2 border-dashed border-border-default bg-bg-0
                flex items-center justify-center gap-2 cursor-pointer hover:border-border-strong hover:bg-bg-2 transition-all duration-150"
            >
              <input
                ref={inputRef}
                type="file"
                accept=".tif,.tiff,.h5,.hdf5,.nc,.mat"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) onFileChange(f)
                }}
              />
              <svg className="w-4 h-4 text-text-tertiary shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
              {file ? (
                <span className="text-xs text-accent font-medium truncate max-w-[180px]">{file.name}</span>
              ) : (
                <span className="text-xs text-text-tertiary">.tif, .h5, .mat</span>
              )}
              {file && (
                <button
                  onClick={(e) => { e.stopPropagation(); onFileChange(null); if (inputRef.current) inputRef.current.value = "" }}
                  className="ml-auto mr-1 text-text-tertiary hover:text-text-primary"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </section>

          {/* Bbox display */}
          {bbox && (
            <section>
              <label className="text-xs font-medium text-text-secondary mb-2 block">Selected AOI</label>
              <div className="grid grid-cols-2 gap-1">
                {[
                  { label: "W", value: bbox.west.toFixed(4) },
                  { label: "S", value: bbox.south.toFixed(4) },
                  { label: "E", value: bbox.east.toFixed(4) },
                  { label: "N", value: bbox.north.toFixed(4) },
                ].map(({ label, value }) => (
                  <div
                    key={label}
                    className="h-7 px-2 bg-bg-0 border border-border-subtle rounded-lg flex items-center gap-1.5"
                  >
                    <span className="text-[10px] font-mono text-text-tertiary">{label}</span>
                    <span className="text-xs font-mono text-text-primary truncate">{value}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-border-subtle shrink-0">
          <button
            data-wt={dataWt}
            onClick={onMapMinerals}
            disabled={!canMap || processing}
            className="w-full h-10 bg-text-primary text-bg-0 text-sm font-medium rounded-xl
              hover:brightness-90 active:scale-[0.98] transition-all duration-150
              disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {processing ? "Processing…" : "Map Minerals"}
          </button>
        </div>
      </div>
    </>
  )
}
