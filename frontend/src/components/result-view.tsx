import type { MatchResult } from "@/types"
import { ClassLegend } from "@/components/class-legend"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface ResultViewProps {
  result: MatchResult
}

export function ResultView({ result }: ResultViewProps) {
  const hasConfidence = !!result.confidence_image

  return (
    <main className="flex min-h-0 flex-1 gap-4 overflow-hidden p-3 pt-1">
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-border/60 bg-card p-3">
        <Tabs defaultValue="classified" className="flex h-full min-h-0 flex-col gap-2">
          <TabsList className="flex-shrink-0 self-start">
            <TabsTrigger value="classified">Classified Map</TabsTrigger>
            {hasConfidence && <TabsTrigger value="confidence">Confidence</TabsTrigger>}
          </TabsList>
          <TabsContent
            value="classified"
            className="flex min-h-0 flex-1 items-center justify-center overflow-auto"
          >
            <img
              src={result.output_image}
              alt="Classified map"
              className="max-h-full max-w-full rounded-lg object-contain"
            />
          </TabsContent>
          {hasConfidence && (
            <TabsContent
              value="confidence"
              className="flex min-h-0 flex-1 items-center justify-center overflow-auto"
            >
              <img
                src={result.confidence_image}
                alt="Confidence map"
                className="max-h-full max-w-full rounded-lg object-contain"
              />
            </TabsContent>
          )}
        </Tabs>
      </div>

      <aside className="flex w-80 flex-shrink-0 flex-col gap-3 overflow-y-auto rounded-xl border border-border/60 bg-card p-3">
        <div className="space-y-0.5 text-xs text-muted-foreground">
          <p>
            Model: <span className="font-medium text-foreground">{result.model_used}</span>
          </p>
          <p>
            Sensor: <span className="font-medium text-foreground">{result.sensor}</span>
          </p>
          <p>
            Classes: <span className="font-medium text-foreground">{result.classes.length}</span>
          </p>
        </div>

        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted-foreground">
              <th className="pb-1 text-left font-medium">Class</th>
              <th className="pb-1 text-right font-medium">Pixels</th>
              <th className="pb-1 text-right font-medium">%</th>
              <th className="pb-1 text-right font-medium">Conf.</th>
            </tr>
          </thead>
          <tbody>
            {result.classes.map((cls) => {
              const s = result.statistics[cls]
              return (
                <tr key={cls} className="border-t border-border">
                  <td className="py-1">{cls}</td>
                  <td className="py-1 text-right">{s?.count ?? "-"}</td>
                  <td className="py-1 text-right">
                    {s?.percentage != null ? `${s.percentage.toFixed(1)}%` : "-"}
                  </td>
                  <td className="py-1 text-right">
                    {s?.mean_confidence != null ? s.mean_confidence.toFixed(3) : "-"}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        <ClassLegend classes={result.classes} />
      </aside>
    </main>
  )
}
