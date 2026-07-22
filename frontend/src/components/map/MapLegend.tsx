import { mineralColor } from "../../lib/colors"

interface Props {
  minerals: string[]
}

export function MapLegend({ minerals }: Props) {
  if (!minerals.length) return null

  return (
    <div className="bg-bg-1/95 backdrop-blur-sm border border-border-default rounded-xl shadow-lg p-3 space-y-1.5 max-h-64 overflow-y-auto">
      <p className="text-[10px] uppercase tracking-wider text-text-tertiary mb-1">Legend</p>
      {minerals.map((m, i) => (
        <div key={m} className="flex items-center gap-2">
          <div
            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
            style={{ backgroundColor: mineralColor(i) }}
          />
          <span className="text-xs text-text-secondary truncate max-w-[140px]">{m.replace("_demo", "")}</span>
        </div>
      ))}
    </div>
  )
}
