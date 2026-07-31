import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Moon, Sun } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { UploadZone } from "@/components/upload-zone"
import { Settings } from "@/components/settings"
import { MatchButton } from "@/components/match-button"
import { ProgressBar } from "@/components/progress-bar"
import { useTheme } from "@/components/theme-provider"
import { uploadAndMatch, getStarterLibraries } from "@/lib/api"
import type { MatchOptions, MatchResult } from "@/types"

export function HomePage() {
  const { theme, setTheme } = useTheme()
  const navigate = useNavigate()

  const [cubeFile, setCubeFile] = useState<File | null>(null)
  const [libraryFile, setLibraryFile] = useState<File | null>(null)
  const [options, setOptions] = useState<MatchOptions>({
    classifier: "auto",
    min_confidence: 0.65,
    normalization: "none",
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canMatch = !!cubeFile && (!!libraryFile || !!options.spectral_library || !!options.classes?.length)

  const handleMatch = async () => {
    if (!cubeFile) return
    setLoading(true)
    setError(null)
    try {
      const result: MatchResult = await uploadAndMatch(cubeFile, libraryFile, options)
      navigate(`/result/${encodeURIComponent(result.model_used)}`, { state: { result } })
    } catch (e) {
      setError(e instanceof Error ? e.message : "Match failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-dvh flex-col">
      {loading && <ProgressBar message="Matching..." />}

      <header className="flex h-12 flex-shrink-0 items-center justify-between px-4">
        <h1 className="text-lg font-bold tracking-tight">Spectral</h1>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </header>

      {error && (
        <div className="mx-4 mb-2 flex-shrink-0 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {error}
        </div>
      )}

      <main className="flex min-h-0 flex-1 gap-4 overflow-hidden p-3 pt-1">
        <section className="flex h-full min-w-0 flex-1 flex-col overflow-y-auto rounded-xl border border-border/60 bg-card p-3">
          <h2 className="mb-2 flex-shrink-0 text-xs font-medium text-muted-foreground">
            Upload Cube
          </h2>
          <UploadZone
            label="Drop cube file"
            accept=".tif,.tiff,.h5,.hdf5,.envi,.dat,.img,.bsq,.bil,.bip"
            extensions="tif/tiff · h5/hdf5 · envi · dat · img"
            onFile={setCubeFile}
            file={cubeFile}
          />
        </section>

        <section className="flex h-full min-w-0 flex-1 flex-col overflow-y-auto rounded-xl border border-border/60 bg-card p-3">
          <h2 className="mb-2 flex-shrink-0 text-xs font-medium text-muted-foreground">
            Spectral Library
          </h2>
          <UploadZone
            label="Upload library CSV"
            accept=".csv"
            extensions="csv"
            onFile={setLibraryFile}
            file={libraryFile}
          />
          <div className="my-2 flex items-center gap-2 text-[10px] font-medium tracking-wider text-muted-foreground uppercase">
            <span className="h-px flex-1 bg-border" />
            or
            <span className="h-px flex-1 bg-border" />
          </div>
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-muted-foreground">Starter Library</label>
            <Select
              value={options.spectral_library || ""}
              onValueChange={(v: string | null) =>
                setOptions((o) => ({ ...o, spectral_library: v || undefined }))
              }
            >
              <SelectTrigger size="sm" className="w-full">
                <SelectValue placeholder="None" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">None</SelectItem>
                {getStarterLibraries().map((l) => (
                  <SelectItem key={l.value} value={l.value}>
                    {l.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </section>

        <section className="flex h-full min-w-0 flex-1 flex-col overflow-y-auto rounded-xl border border-border/60 bg-card p-3">
          <h2 className="mb-2 flex-shrink-0 text-xs font-medium text-muted-foreground">
            Match Settings
          </h2>
          <Settings options={options} onChange={setOptions} />
        </section>
      </main>

      <footer className="flex-shrink-0 p-3 pt-1">
        <MatchButton disabled={!canMatch} loading={loading} onClick={handleMatch} />
      </footer>
    </div>
  )
}
