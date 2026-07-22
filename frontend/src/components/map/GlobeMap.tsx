import { useEffect, useRef } from "react"
import maplibregl from "maplibre-gl"

interface Props {
  onMapReady?: (map: maplibregl.Map) => void
  onWebGLError?: () => void
}

export function GlobeMap({ onMapReady, onWebGLError }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const initialized = useRef(false)

  useEffect(() => {
    if (initialized.current || !container.current) return
    initialized.current = true

    const check = document.createElement("canvas")
    const gl = check.getContext("webgl") || check.getContext("webgl2")
    if (!gl) {
      onWebGLError?.()
      return
    }

    let projectionApplied = false

    const map = new maplibregl.Map({
      container: container.current,
      style: {
        version: 8,
        sources: {
          "carto-dark": {
            type: "raster",
            tiles: ["https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"],
            tileSize: 256,
            attribution:
              '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
          },
        },
        layers: [
          { id: "background", type: "background", paint: { "background-color": "#000000" } },
          { id: "carto-dark-layer", type: "raster", source: "carto-dark" },
        ],
      },
      center: [20, 0],
      zoom: 2,
      boxZoom: false,
      attributionControl: false,
    })

    const applyGlobe = () => {
      if (projectionApplied) return
      projectionApplied = true
      try { map.setProjection({ type: "globe" }) } catch (_) {}
    }

    map.on("load", () => {
      applyGlobe()
      onMapReady?.(map)
    })

    map.on("style.load", () => {
      setTimeout(applyGlobe, 100)
    })

    map.on("error", (_e) => {})

    map.addControl(new maplibregl.NavigationControl(), "bottom-right")

    return () => {
      try { map.remove() } catch (_) {}
      initialized.current = false
    }
  }, [])

  return (
    <div ref={container} className="h-full w-full">
      <div className="absolute inset-0 bg-bg-0" />
    </div>
  )
}
