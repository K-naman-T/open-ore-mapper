import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Moon, Sun } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { UploadZone } from "@/components/upload-zone"
import { Settings } from "@/components/settings"
import { MatchButton } from "@/components/match-button"
import { ProgressBar } from "@/components/progress-bar"
import { useTheme } from "@/components/theme-provider"
import { uploadAndMatch } from "@/lib/api"
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
    <div className="mx-auto max-w-3xl space-y-6 p-4 pb-16 sm:p-6">
      {loading && <ProgressBar />}

      <header className="flex items-center justify-between">
        <h1 className="text-xl font-bold tracking-tight">Spectral</h1>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Upload Hyperspectral Cube</CardTitle>
        </CardHeader>
        <CardContent>
          <UploadZone
            label="Drop cube file here"
            accept=".tif,.tiff,.h5,.hdf5,.envi,.dat,.img,.bsq,.bil,.bip"
            onFile={setCubeFile}
            file={cubeFile}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Spectral Library</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <UploadZone
            label="Upload spectral library CSV"
            accept=".csv"
            onFile={setLibraryFile}
            file={libraryFile}
          />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <Settings options={options} onChange={setOptions} />
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <MatchButton disabled={!canMatch} loading={loading} onClick={handleMatch} />
    </div>
  )
}
