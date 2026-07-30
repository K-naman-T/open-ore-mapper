import { useLocation, useNavigate } from "react-router-dom"
import { ArrowLeft, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ResultView } from "@/components/result-view"
import { useTheme } from "@/components/theme-provider"
import { Moon, Sun } from "lucide-react"
import type { MatchResult } from "@/types"

export function ResultPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { theme, setTheme } = useTheme()
  const result = (location.state as { result: MatchResult })?.result

  if (!result) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">No result data available.</p>
          <Button variant="link" onClick={() => navigate("/")}>
            Go home
          </Button>
        </div>
      </div>
    )
  }

  const downloadUrl = result.downloads?.geotiff || result.output_image

  return (
    <div className="mx-auto max-w-6xl p-4 pb-16 sm:p-6">
      <header className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-xl font-bold tracking-tight">Results</h1>
        </div>
        <div className="flex items-center gap-2">
          <a href={downloadUrl} download>
            <Button variant="ghost" size="icon">
              <Download className="h-5 w-5" />
            </Button>
          </a>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>
        </div>
      </header>

      <ResultView result={result} />
    </div>
  )
}
