import { useEffect, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { ArrowLeft, Download, Moon, Sun } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ResultView } from "@/components/result-view"
import { useTheme } from "@/components/theme-provider"
import type { MatchResult } from "@/types"

const STORAGE_KEY = "spectral:last-result"

function loadPersistedResult(): MatchResult | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as MatchResult) : null
  } catch {
    return null
  }
}

export function ResultPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { theme, setTheme } = useTheme()
  const stateResult = (location.state as { result: MatchResult })?.result
  const [result, setResult] = useState<MatchResult | null>(stateResult ?? loadPersistedResult())

  // Persist so a refresh or direct link to /result/:id still shows the result.
  useEffect(() => {
    if (stateResult) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(stateResult))
      } catch {
        // storage may be unavailable (private mode); the in-memory result still works
      }
      setResult(stateResult)
    }
  }, [stateResult])

  if (!result) {
    return (
      <div className="flex h-dvh items-center justify-center">
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
  const isGeoTiff = !!result.downloads?.geotiff

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex h-12 flex-shrink-0 items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/")} aria-label="Back to home">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-lg font-bold tracking-tight">Results</h1>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden text-xs text-muted-foreground sm:inline">
            {result.model_used}
          </span>
          {downloadUrl && (
            <a href={downloadUrl} download title={isGeoTiff ? "Download GeoTIFF" : "Download PNG"}>
              <Button variant="ghost" size="icon" aria-label="Download result">
                <Download className="h-4 w-4" />
              </Button>
            </a>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </header>

      <ResultView result={result} />
    </div>
  )
}
