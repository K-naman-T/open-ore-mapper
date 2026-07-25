import { useEffect, useState, useRef } from "react"
import { useParams } from "react-router-dom"
import maplibregl from "maplibre-gl"
import { GlobeMap } from "../components/map/GlobeMap"
import { MapLegend } from "../components/map/MapLegend"
import { StatisticsTab } from "../components/sidebar/StatisticsTab"
import { QCTab } from "../components/sidebar/QCTab"
import { ExportTab } from "../components/sidebar/ExportTab"
import type { MapResult } from "../api/client"

export function MapViewPage() {
  const { uuid } = useParams<{ uuid: string }>()
  const [result, setResult] = useState<MapResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [activeTab, setActiveTab] = useState<"score" | "stats" | "qc" | "export">("stats")
  const [showOverlay, setShowOverlay] = useState(true)
  const [scoreLayer, setScoreLayer] = useState<"ours" | "reference" | "diff">("ours")
  const mapRef = useRef<maplibregl.Map | null>(null)

  const scorecard = result?.scorecard
  const hasScorecard = !!(scorecard && typeof scorecard.overall_accuracy === "number")

  useEffect(() => {
    if (!uuid) return
    const cached = sessionStorage.getItem(`map-${uuid}`)
    if (cached) {
      const parsed = JSON.parse(cached) as MapResult
      setResult(parsed)
      if (parsed.scorecard && typeof parsed.scorecard.overall_accuracy === "number") {
        setActiveTab("score")
      }
      setLoading(false)
      return
    }
    fetch(`/api/v1/maps/${uuid}`)
      .then((r) => r.json())
      .then((data) => { setResult(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [uuid])

  // Scorecard image for demo fixture (no geo bbox required)
  const scoreImageSrc =
    hasScorecard && scorecard
      ? scoreLayer === "reference"
        ? scorecard.reference_image || result?.top_abundance_image
        : scoreLayer === "diff"
          ? scorecard.diff_image || result?.confidence_image
          : scorecard.our_image || result?.output_image
      : null

  // Render classified mineral map as MapLibre image overlay
  useEffect(() => {
    const map = mapRef.current
    if (!map || !result) return

    const bbox = JSON.parse(sessionStorage.getItem(`bbox-${uuid}`) || "null")
    if (!bbox) return

    // Convert base64 data URL to Blob URL
    const img = new Image()
    img.onload = () => {
      try { map.removeLayer("mineral-overlay") } catch (_) {}
      try { map.removeSource("mineral-overlay") } catch (_) {}

      map.addSource("mineral-overlay", {
        type: "image",
        url: img.src,
        coordinates: [
          [bbox.west, bbox.north],
          [bbox.east, bbox.north],
          [bbox.east, bbox.south],
          [bbox.west, bbox.south],
        ],
      })
      map.addLayer({
        id: "mineral-overlay",
        type: "raster",
        source: "mineral-overlay",
        paint: {
          "raster-opacity": showOverlay ? 0.85 : 0,
          "raster-resampling": "nearest",
        },
      })
      map.fitBounds(
        [[bbox.west, bbox.south], [bbox.east, bbox.north]],
        { padding: 80, duration: 1000 }
      )
    }
    img.src = result.output_image

    return () => {
      try { map.removeLayer("mineral-overlay") } catch (_) {}
      try { map.removeSource("mineral-overlay") } catch (_) {}
    }
  }, [result, uuid, showOverlay])

  if (loading) {
    return (
      <div className="flex h-screen bg-bg-0 items-center justify-center">
        <div className="text-center space-y-3">
          <svg className="w-8 h-8 mx-auto text-accent animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" className="opacity-30" />
            <path d="M12 2A10 10 0 112 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <p className="text-sm text-text-secondary">Loading mineral map…</p>
        </div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="flex h-screen bg-bg-0 items-center justify-center">
        <div className="text-center space-y-4 max-w-xs">
          <div className="w-12 h-12 mx-auto rounded-full bg-bg-2 flex items-center justify-center">
            <svg className="w-6 h-6 text-text-tertiary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-text-primary">Map not found</p>
          <p className="text-xs text-text-tertiary leading-relaxed">This map may have expired or the URL is incorrect.</p>
          <a href="/" className="inline-flex h-9 px-4 items-center text-xs font-medium bg-text-primary text-bg-0 rounded-lg hover:brightness-90 active:scale-[0.98] transition-all duration-150">
            Back to globe
          </a>
        </div>
      </div>
    )
  }

  const tabs = (hasScorecard
    ? (["score", "stats", "qc", "export"] as const)
    : (["stats", "qc", "export"] as const))

  return (
    <div className="h-screen flex bg-bg-0 overflow-hidden">
      {/* Map / scorecard image area */}
      <div className="flex-1 relative">
        {hasScorecard && scoreImageSrc ? (
          <div className="absolute inset-0 flex flex-col bg-bg-0">
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex gap-1 bg-bg-1/90 backdrop-blur-sm border border-border-default rounded-xl p-1 shadow-lg">
              {(["ours", "reference", "diff"] as const).map((layer) => (
                <button
                  key={layer}
                  type="button"
                  onClick={() => setScoreLayer(layer)}
                  className={`h-8 px-3 text-xs font-medium rounded-lg capitalize transition-colors ${
                    scoreLayer === layer
                      ? "bg-accent/15 text-accent"
                      : "text-text-secondary hover:text-text-primary"
                  }`}
                >
                  {layer === "ours" ? "Ours" : layer === "reference" ? "Reference" : "Diff"}
                </button>
              ))}
            </div>
            <div className="flex-1 flex items-center justify-center p-8 pt-16">
              <img
                src={scoreImageSrc}
                alt={`Scorecard ${scoreLayer}`}
                className="max-w-full max-h-full object-contain rounded-lg border border-border-default shadow-lg bg-bg-2"
                style={{ imageRendering: "pixelated" }}
              />
            </div>
          </div>
        ) : (
          <GlobeMap onMapReady={(m) => { mapRef.current = m }} onWebGLError={() => {}} />
        )}

        {/* Top-right: visibility toggle */}
        <div className="absolute top-4 right-4 z-20 flex gap-1">
          {!hasScorecard && (
            <button
              onClick={() => setShowOverlay(!showOverlay)}
              className={`h-9 px-3 text-xs font-medium rounded-xl border shadow-lg transition-all duration-150 ${
                showOverlay
                  ? "bg-accent/10 border-accent/20 text-accent"
                  : "bg-bg-1/90 border-border-default text-text-secondary hover:text-text-primary"
              }`}>
              {showOverlay ? "Minerals visible" : "Show minerals"}
            </button>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-9 h-9 flex items-center justify-center bg-bg-1/90 backdrop-blur-sm border border-border-default rounded-xl shadow-lg hover:bg-bg-2 transition-colors">
            <svg className="w-4 h-4 text-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
        </div>

        {/* Bottom-left: legend */}
        <div className="absolute bottom-4 left-4 z-20">
          <MapLegend minerals={result.minerals} />
        </div>

        {/* Back to globe button */}
        <a href="/" className="absolute top-4 left-4 z-20 h-9 px-3 flex items-center gap-1.5 bg-bg-1/90 backdrop-blur-sm border border-border-default rounded-xl shadow-lg text-xs text-text-secondary hover:text-text-primary transition-colors">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Back
        </a>
      </div>

      {/* Sidebar */}
      <div className={`border-l border-border-default bg-bg-1 transition-all duration-300 ease-out flex flex-col overflow-hidden ${sidebarOpen ? "w-80" : "w-0 border-l-0"}`}>
        <div className="flex-1 overflow-y-auto">
          <div className="px-5 py-4 border-b border-border-subtle space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-text-primary">
                {hasScorecard ? "Scorecard" : "Mineral Map"}
              </h2>
              <button onClick={() => setSidebarOpen(false)} className="text-text-tertiary hover:text-text-primary transition-colors">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex items-center gap-2 text-xs text-text-tertiary">
              <span className="bg-bg-2 px-2 py-0.5 rounded font-mono">{result.sensor}</span>
              <span>{result.wavelengths.length} bands</span>
            </div>
          </div>

          <div className="flex border-b border-border-subtle">
            {tabs.map((t) => (
              <button key={t} onClick={() => setActiveTab(t)}
                className={`flex-1 h-10 text-xs font-medium uppercase tracking-wider transition-all duration-200 border-b-2 ${
                  activeTab === t ? "text-text-primary border-accent" : "text-text-tertiary border-transparent hover:text-text-secondary"
                }`}>
                {t === "score" ? "Score" : t === "stats" ? "Statistics" : t === "qc" ? "QC" : "Export"}
              </button>
            ))}
          </div>

          <div className="p-5">
            {activeTab === "score" && scorecard && (
              <div className="space-y-4" data-testid="scorecard-panel">
                <div className="rounded-xl border border-border-default bg-bg-2/50 p-4 text-center">
                  <p className="text-[10px] uppercase tracking-wider text-text-tertiary mb-1">
                    Map-to-map agreement
                  </p>
                  <p className="text-3xl font-semibold text-accent tabular-nums">
                    {(Number(scorecard.overall_accuracy) * 100).toFixed(1)}%
                  </p>
                  <p className="text-xs text-text-secondary mt-1">
                    kappa {Number(scorecard.kappa ?? 0).toFixed(3)}
                    {scorecard.n_labeled != null ? ` · ${scorecard.n_labeled} labeled px` : ""}
                  </p>
                  <p className="text-[10px] text-text-tertiary mt-2 leading-snug px-1">
                    Agreement with reference labels — not field mineral truth, not ore grade.
                  </p>
                </div>
                <ul className="space-y-2">
                  {(scorecard.per_class ?? []).map((row) => (
                    <li key={row.name} className="flex items-center justify-between text-xs gap-2">
                      <span className="text-text-primary font-medium capitalize truncate">{row.name}</span>
                      <span className="text-text-tertiary tabular-nums shrink-0">
                        P {(row.precision * 100).toFixed(0)}% · R {(row.recall * 100).toFixed(0)}%
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="text-[10px] text-text-tertiary leading-relaxed">
                  Product maps use unsupervised classical spectral matching (library / fuse).
                  Fixture demos use planted reference labels. Supervised research OA (e.g. RF/HistGB)
                  is not product accuracy.
                </p>
                {result.warnings?.length > 0 && (
                  <ul className="text-[10px] text-text-tertiary space-y-1 list-disc pl-4">
                    {result.warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            {activeTab === "stats" && <StatisticsTab statistics={result.statistics} />}
            {activeTab === "qc" && <QCTab report={result.quality_report} />}
            {activeTab === "export" && <ExportTab />}
          </div>
        </div>

        <div className="px-5 py-3 border-t border-border-subtle">
          <p className="text-[10px] text-text-tertiary font-mono truncate">{result.model_used}</p>
        </div>
      </div>
    </div>
  )
}
