import { useState, useCallback, useRef, useEffect, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { useToast } from "../components/ui/Toast"
import { uploadAndPredict } from "../api/client"
import { GlobeMap } from "../components/map/GlobeMap"
import { DrawBbox, type Bbox } from "../components/map/DrawBbox"
import { SettingsPanel } from "../components/map/SettingsPanel"
import { useWalkthrough, Spotlight, WalkthroughTooltip } from "../hooks/useWalkthrough"
import type maplibregl from "maplibre-gl"

const WALKTHROUGH_KEY = "oom-walkthrough-done"

export function Home() {
  const navigate = useNavigate()
  const { toast } = useToast()

  const [map, setMap] = useState<maplibregl.Map | null>(null)
  const [webglErr, setWebglErr] = useState(false)
  const [panelOpen, setPanelOpen] = useState(false)

  const [sensor, setSensor] = useState("EMIT")
  const [minerals, setMinerals] = useState(["hematite", "goethite", "jarosite", "magnetite", "limonite", "ferrihydrite"])
  const [classifier, setClassifier] = useState("Continuum Removal")
  const [confidence, setConfidence] = useState(0.85)
  const [ace, setAce] = useState(true)
  const [vegMask, setVegMask] = useState(true)

  const [file, setFile] = useState<File | null>(null)
  const [bbox, setBbox] = useState<Bbox | null>(null)

  const [processing, setProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const progressRef = useRef(0)

  const canMap = (!!bbox || !!file) && minerals.length > 0

  const handleMapMinerals = useCallback(async () => {
    if (!minerals.length) { toast("Select at least one mineral", "error"); return }
    setProcessing(true)
    setProgress(0)
    progressRef.current = 0
    const sim = setInterval(() => {
      const next = Math.min(progressRef.current + Math.random() * 8, 90)
      progressRef.current = next
      setProgress(next)
    }, 300)

    try {
      const options = {
        minerals,
        sensor: sensor.toLowerCase().replace(" ", "_"),
        classifier: classifier.toLowerCase().replace(" ", "_"),
        min_confidence: confidence,
        use_ace: ace,
        vegetation_mask: vegMask,
      }
      const result = file
        ? await uploadAndPredict(file, options)
        : await fetch("/api/v1/predict/bbox", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...options, bbox }),
          }).then((r) => {
            if (!r.ok) return r.json().then((b) => { throw new Error(b.detail ?? "Prediction failed") })
            return r.json()
          })

      clearInterval(sim)
      setProgress(100)
      const uuid = result.map_uuid ?? crypto.randomUUID()
      sessionStorage.setItem(`map-${uuid}`, JSON.stringify(result))
      if (bbox) sessionStorage.setItem(`bbox-${uuid}`, JSON.stringify(bbox))
      setTimeout(() => {
        setProcessing(false)
        setBbox(null)
        navigate(`/maps/${uuid}`)
      }, 400)
    } catch (err) {
      clearInterval(sim)
      setProcessing(false)
      toast(err instanceof Error ? err.message : "Processing failed", "error")
    }
  }, [file, bbox, minerals, sensor, classifier, confidence, ace, vegMask, toast, navigate])

  const closePanel = () => setPanelOpen(false)

  // ── Walkthrough ──
  const steps = useMemo(() => [
    { target: "[data-wt=\"globe\"]", title: "The Globe", placement: "bottom" as const,
      content: "Pan and zoom to explore. This is a WebGL globe with a dark basemap." },
    { target: "[data-wt=\"cue\"]", title: "Select an Area", placement: "top" as const,
      content: "Hold Shift and click-drag to draw a bounding box. This tells us where to search for minerals." },
    { target: "[data-wt=\"settings\"]", title: "Configure", placement: "left" as const,
      content: "Click the gear to open settings. Pick your sensor, target minerals, and classifier." },
    { target: "[data-wt=\"map-btn\"]", title: "Map Minerals", placement: "left" as const,
      content: "Once you've drawn a bbox or uploaded a file, hit Map Minerals. We'll search NASA's EMIT archive and run spectral matching." },
  ], [])

  const dismissed = sessionStorage.getItem(WALKTHROUGH_KEY) === "1"
  const { active, step, targetRect, isLast, isFirst, activeIndex, start, next, prev, stop } = useWalkthrough(steps)

  useEffect(() => {
    if (!dismissed && map && !bbox && !active) {
      const t = setTimeout(start, 2500)
      return () => clearTimeout(t)
    }
  }, [dismissed, map, bbox, active, start])

  const handleSkip = useCallback(() => { sessionStorage.setItem(WALKTHROUGH_KEY, "1"); stop() }, [stop])
  const handleDone = useCallback(() => { sessionStorage.setItem(WALKTHROUGH_KEY, "1"); stop() }, [stop])

  if (webglErr) {
    return (
      <div className="h-screen flex items-center justify-center bg-bg-0">
        <div className="text-center space-y-3">
          <p className="text-text-primary font-medium">WebGL not available</p>
          <p className="text-xs text-text-tertiary">Your browser does not support WebGL, which is required for the globe view.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen w-screen overflow-hidden bg-bg-0 relative">
      {/* Map */}
      <div data-wt="globe" className="absolute inset-0">
        <GlobeMap onMapReady={setMap} onWebGLError={() => setWebglErr(true)} />
      </div>
      {map && (
        <DrawBbox map={map} bbox={bbox}
          onBboxChange={(b) => { setBbox(b); if (b) setPanelOpen(true) }} />
      )}

      {/* Logo */}
      <div className="absolute top-4 left-4 z-10 pointer-events-none">
        <h1 className="text-sm font-semibold text-text-primary/80 tracking-tight select-none">
          Open Ore Mapper
        </h1>
      </div>

      {/* Shift-drag cue */}
      {!bbox && !panelOpen && (
        <div data-wt="cue" className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 pointer-events-none animate-[fade-in_400ms_ease-out]">
          <div className="bg-bg-1/80 backdrop-blur-sm border border-border-default rounded-lg px-4 py-2 shadow-lg">
            <p className="text-xs text-text-tertiary whitespace-nowrap">
              <kbd className="keycap">Shift</kbd>
              {" + drag to select an area of interest"}
            </p>
          </div>
        </div>
      )}

      {/* Gear button */}
      <button data-wt="settings"
        onClick={() => setPanelOpen(true)}
        className="absolute top-4 right-4 z-20 w-9 h-9 flex items-center justify-center bg-bg-1/90 backdrop-blur-sm border border-border-default rounded-xl shadow-lg hover:bg-bg-2 transition-colors"
      >
        <svg className="w-4 h-4 text-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 15a3 3 0 100-6 3 3 0 000 6z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
        </svg>
      </button>

      {/* Quick "Map" button when bbox is selected but panel is closed */}
      {bbox && !panelOpen && canMap && (
        <div className="absolute bottom-24 left-1/2 -translate-x-1/2 z-20 animate-[fade-in_200ms_ease-out]">
          <button
            data-wt="map-btn"
            onClick={handleMapMinerals}
            className="h-10 px-5 bg-text-primary text-bg-0 text-sm font-medium rounded-xl shadow-xl
              hover:brightness-90 active:scale-[0.98] transition-all duration-150"
          >
            Map Minerals
          </button>
        </div>
      )}

      {/* Settings panel */}
      <SettingsPanel
        open={panelOpen} onClose={closePanel}
        sensor={sensor} onSensorChange={setSensor}
        minerals={minerals} onMineralsChange={setMinerals}
        classifier={classifier} onClassifierChange={setClassifier}
        confidence={confidence} onConfidenceChange={setConfidence}
        ace={ace} onAceChange={setAce}
        vegMask={vegMask} onVegMaskChange={setVegMask}
        file={file} onFileChange={setFile}
        bbox={bbox}
        onMapMinerals={handleMapMinerals}
        processing={processing}
        canMap={canMap}
        dataWt="map-btn"
      />

      {/* Processing overlay */}
      {processing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg-0/80 backdrop-blur-sm">
          <div className="bg-bg-1 border border-border-default rounded-2xl shadow-lg p-6 w-72 space-y-4">
            <div className="flex items-center gap-3">
              <svg className="w-5 h-5 text-accent animate-spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeDasharray="31.4 31.4" className="opacity-30" />
                <path d="M12 2A10 10 0 112 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <p className="text-sm font-medium text-text-primary">Processing…</p>
            </div>
            <div className="w-full h-1.5 bg-bg-3 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-accent transition-all duration-300 ease-out" style={{ width: `${progress}%` }} />
            </div>
            <p className="text-xs text-text-tertiary font-mono tabular-nums">{progress.toFixed(0)}%</p>
          </div>
        </div>
      )}

      {/* ── Walkthrough overlay ── */}
      {active && step && (
        <>
          <Spotlight targetRect={targetRect} />
          <WalkthroughTooltip
            step={step}
            targetRect={targetRect}
            isLast={isLast}
            isFirst={isFirst}
            stepIndex={activeIndex ?? 0}
            totalSteps={steps.length}
            onNext={next}
            onPrev={prev}
            onSkip={handleSkip}
            onComplete={handleDone}
          />
        </>
      )}
    </div>
  )
}
