import { classColorMap } from "@/lib/colors"

interface ClassLegendProps {
  classes: string[]
}

export function ClassLegend({ classes }: ClassLegendProps) {
  const colors = classColorMap(classes)

  return (
    <div className="space-y-1">
      <h4 className="text-xs font-medium text-muted-foreground">Legend</h4>
      <div className="grid grid-cols-2 gap-1">
        {classes.map((cls) => (
          <div key={cls} className="flex items-center gap-2 text-xs">
            <span
              className="inline-block h-3 w-3 rounded-sm"
              style={{ backgroundColor: colors[cls] }}
            />
            <span className="truncate">{cls}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
