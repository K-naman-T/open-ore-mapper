import type { MatchResult } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ClassLegend } from "@/components/class-legend"

interface ResultViewProps {
  result: MatchResult
}

export function ResultView({ result }: ResultViewProps) {
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Classified Map</CardTitle>
          </CardHeader>
          <CardContent>
            <img
              src={result.output_image}
              alt="Classified map"
              className="w-full rounded-lg"
            />
          </CardContent>
        </Card>

        {result.confidence_image && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Confidence Map</CardTitle>
            </CardHeader>
            <CardContent>
              <img
                src={result.confidence_image}
                alt="Confidence map"
                className="w-full rounded-lg"
              />
            </CardContent>
          </Card>
        )}
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Statistics</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-xs text-muted-foreground">
              Model: <span className="font-medium text-foreground">{result.model_used}</span>
              <br />
              Sensor: <span className="font-medium text-foreground">{result.sensor}</span>
              <br />
              Classes: <span className="font-medium text-foreground">{result.classes.length}</span>
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
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
