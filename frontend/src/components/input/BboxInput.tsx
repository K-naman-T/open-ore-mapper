import { useState } from "react"

interface Props {
  onSubmit: (params: { north: number; south: number; east: number; west: number; sensor: string }) => void
}

export function BboxInput({ onSubmit }: Props) {
  const [west, setWest] = useState("-115.5")
  const [south, setSouth] = useState("36.5")
  const [east, setEast] = useState("-114.5")
  const [north, setNorth] = useState("37.5")
  const [sensor, setSensor] = useState("emit")

  const handleSubmit = () => {
    onSubmit({ north: +north, south: +south, east: +east, west: +west, sensor })
  }

  const inputClass =
    "w-full h-10 px-3 text-sm bg-bg-2 border border-border-default rounded-lg text-text-primary font-mono tabular-nums placeholder:text-text-tertiary focus:border-border-strong focus:outline-none transition-colors duration-150"

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs font-medium uppercase tracking-wider text-text-tertiary">North</label>
          <input type="number" step="0.1" value={north} onChange={(e) => setNorth(e.target.value)} className={inputClass} placeholder="37.5" />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium uppercase tracking-wider text-text-tertiary">South</label>
          <input type="number" step="0.1" value={south} onChange={(e) => setSouth(e.target.value)} className={inputClass} placeholder="36.5" />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium uppercase tracking-wider text-text-tertiary">West</label>
          <input type="number" step="0.1" value={west} onChange={(e) => setWest(e.target.value)} className={inputClass} placeholder="-115.5" />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium uppercase tracking-wider text-text-tertiary">East</label>
          <input type="number" step="0.1" value={east} onChange={(e) => setEast(e.target.value)} className={inputClass} placeholder="-114.5" />
        </div>
      </div>

      <div className="space-y-1">
        <label className="text-xs font-medium uppercase tracking-wider text-text-tertiary">Sensor</label>
        <select
          value={sensor}
          onChange={(e) => setSensor(e.target.value)}
          className="w-full h-10 px-3 text-sm bg-bg-2 border border-border-default rounded-lg text-text-primary focus:border-border-strong focus:outline-none transition-colors duration-150 appearance-none cursor-pointer"
          style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%236D6D7A' stroke-width='1.5'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19.5 8.25l-7.5 7.5-7.5-7.5'/%3E%3C/svg%3E")`, backgroundPosition: "right 12px center", backgroundRepeat: "no-repeat", backgroundSize: "16px" }}
        >
          <option value="emit">EMIT (NASA, 60m, 285 bands)</option>
          <option value="cubert_ultris_s5">Cubert Ultris S5 (VNIR, 51 bands)</option>
          <option value="manual">Custom wavelengths</option>
        </select>
      </div>

      <button
        onClick={handleSubmit}
        className="w-full h-11 bg-text-primary text-bg-0 font-medium text-sm rounded-xl hover:brightness-90 active:scale-[0.98] transition-all duration-150 ease-out flex items-center justify-center gap-2"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
        Search & Map
      </button>
    </div>
  )
}
