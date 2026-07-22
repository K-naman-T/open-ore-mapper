import { useState, useEffect } from "react"

interface Props {
  value: string[]
  onChange: (minerals: string[]) => void
}

export function MineralSelector({ value, onChange }: Props) {
  const [all, setAll] = useState<string[]>([])
  const [search, setSearch] = useState("")

  useEffect(() => {
    fetch("/api/v1/minerals")
      .then((r) => r.json())
      .then((d) => setAll(d.minerals ?? d ?? []))
      .catch(() => {})
  }, [])

  const filtered = search ? all.filter((m) => m.toLowerCase().includes(search.toLowerCase())) : all

  const toggle = (mineral: string) => {
    if (value.includes(mineral)) onChange(value.filter((m) => m !== mineral))
    else onChange([...value, mineral])
  }

  const selectAll = () => onChange(filtered.length > 0 ? filtered : all)
  const clear = () => onChange([])

  if (!all.length) return null

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wider text-text-tertiary">
          Minerals ({value.length} selected)
        </p>
        <div className="flex gap-2">
          <button onClick={selectAll} className="text-xs text-text-secondary hover:text-text-primary transition-colors">All</button>
          <button onClick={clear} className="text-xs text-text-secondary hover:text-text-primary transition-colors">Clear</button>
        </div>
      </div>

      <input
        type="text"
        placeholder="Search minerals..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full h-9 px-3 text-sm bg-bg-2 border border-border-default rounded-lg text-text-primary
          placeholder:text-text-tertiary focus:border-border-strong focus:outline-none transition-colors duration-150"
      />

      <div className="max-h-48 overflow-y-auto rounded-lg border border-border-subtle bg-bg-1">
        {filtered.map((m) => (
          <label
            key={m}
            className={`flex items-center gap-3 px-3 py-2 cursor-pointer transition-colors duration-100 hover:bg-bg-2
              ${value.includes(m) ? "bg-accent/5" : ""}`}
          >
            <div className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all duration-150
              ${value.includes(m) ? "bg-accent border-accent" : "border-border-default"}`}
            >
              {value.includes(m) && (
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <span className={`text-sm transition-colors ${value.includes(m) ? "text-text-primary font-medium" : "text-text-secondary"}`}>
              {m}
            </span>
          </label>
        ))}
      </div>
    </div>
  )
}
