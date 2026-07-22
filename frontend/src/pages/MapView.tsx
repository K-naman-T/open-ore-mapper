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
  const [activeTab, setActiveTab] = useState<"stats" | "qc" | "export">("stats")
  const [showOverlay, setShowOverlay] = useState(true)
  const mapRef = useRef<maplibregl.Map | null>(null)

  useEffect(() => {
    if (!uuid) return
    const cached = sessionStorage.getItem(`map-${uuid}`)
    if (cached) {
      setResult(JSON.parse(cached))
      setLoading(false)
      return
    }
    fetch(`/api/v1/maps/${uuid}`)
      .then((r) => r.json())
      .then((data) => { setResult(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [uuid])

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

  return (
    <div className="h-screen flex bg-bg-0 overflow-hidden">
      {/* Map area */}
      <div className="flex-1 relative">
        <GlobeMap onMapReady={(m) => { mapRef.current = m }} onWebGLError={() => {}} />

        {/* Top-right: visibility toggle */}
        <div className="absolute top-4 right-4 z-20 flex gap-1">
          <button
            onClick={() => setShowOverlay(!showOverlay)}
            className={`h-9 px-3 text-xs font-medium rounded-xl border shadow-lg transition-all duration-150 ${
              showOverlay
                ? "bg-accent/10 border-accent/20 text-accent"
                : "bg-bg-1/90 border-border-default text-text-secondary hover:text-text-primary"
            }`}>
            {showOverlay ? "Minerals visible" : "Show minerals"}
          </button>
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
              <h2 className="text-sm font-semibold text-text-primary">Mineral Map</h2>
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
            {(["stats", "qc", "export"] as const).map((t) => (
              <button key={t} onClick={() => setActiveTab(t)}
                className={`flex-1 h-10 text-xs font-medium uppercase tracking-wider transition-all duration-200 border-b-2 ${
                  activeTab === t ? "text-text-primary border-accent" : "text-text-tertiary border-transparent hover:text-text-secondary"
                }`}>
                {t === "stats" ? "Statistics" : t === "qc" ? "QC" : "Export"}
              </button>
            ))}
          </div>

          <div className="p-5">
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
