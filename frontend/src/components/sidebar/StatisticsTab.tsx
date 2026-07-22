import type { MineralStat } from "../../api/client"
import { mineralColor } from "../../lib/colors"

interface Props {
  statistics: Record<string, MineralStat>
}

export function StatisticsTab({ statistics }: Props) {
  const entries = Object.entries(statistics)
  if (!entries.length) {
    return <p className="text-sm text-text-tertiary text-center py-8">No statistics available</p>
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium text-text-secondary">
        {entries.length} minerals classified
      </p>

      {entries.map(([name, stat], i) => (
        <div
          key={name}
          className="group p-3 rounded-xl border border-border-subtle bg-bg-2 hover:bg-bg-3 transition-colors duration-150"
        >
          <div className="flex items-center gap-2.5 mb-3">
            <div
              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: mineralColor(i) }}
            />
            <span className="text-sm font-medium text-text-primary truncate">{name.replace("_demo", "")}</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Coverage</p>
              <p className="text-sm font-mono tabular-nums text-text-primary">{stat.percentage.toFixed(2)}%</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Pixels</p>
              <p className="text-sm font-mono tabular-nums text-text-primary">{stat.count.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Confidence</p>
              <p className="text-sm font-mono tabular-nums text-text-primary">{(stat.mean_confidence * 100).toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Abundance</p>
              <p className="text-sm font-mono tabular-nums text-text-primary">{(stat.mean_abundance * 100).toFixed(1)}%</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
