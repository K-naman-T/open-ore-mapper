import { useEffect, useRef, useCallback } from "react"
import type maplibregl from "maplibre-gl"

export interface Bbox {
  west: number
  south: number
  east: number
  north: number
}

interface Props {
  map: maplibregl.Map
  bbox: Bbox | null
  onBboxChange: (bbox: Bbox | null) => void
  onDrawingChange?: (drawing: boolean) => void
}

const LAYER_FILL = "bbox-fill"
const LAYER_OUTLINE = "bbox-outline"
const SOURCE = "bbox-rect"

function ensureLayers(map: maplibregl.Map) {
  if (!map.getSource(SOURCE)) {
    map.addSource(SOURCE, {
      type: "geojson",
      data: { type: "Feature", geometry: { type: "Polygon", coordinates: [[]] }, properties: {} },
    })
    map.addLayer({
      id: LAYER_FILL,
      type: "fill",
      source: SOURCE,
      paint: { "fill-color": "#006efe", "fill-opacity": 0.15 },
    })
    map.addLayer({
      id: LAYER_OUTLINE,
      type: "line",
      source: SOURCE,
      paint: { "line-color": "#006efe", "line-width": 2 },
    })
  }
}

export function DrawBbox({ map, bbox, onBboxChange, onDrawingChange }: Props) {
  const drawing = useRef(false)
  const start = useRef<{ lng: number; lat: number } | null>(null)

  const setRect = useCallback(
    (sw: [number, number], ne: [number, number]) => {
      const coords = [
        [sw[0], sw[1]],
        [ne[0], sw[1]],
        [ne[0], ne[1]],
        [sw[0], ne[1]],
        [sw[0], sw[1]],
      ]
      const src = map.getSource(SOURCE) as maplibregl.GeoJSONSource | undefined
      if (src) {
        src.setData({
          type: "Feature",
          geometry: { type: "Polygon", coordinates: [coords] },
          properties: {},
        })
      }
    },
    [map],
  )

  const clearRect = useCallback(() => {
    const src = map.getSource(SOURCE) as maplibregl.GeoJSONSource | undefined
    if (src) {
      src.setData({
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [[]] },
        properties: {},
      })
    }
  }, [map])

  useEffect(() => {
    ensureLayers(map)

    // Track Shift key globally to toggle dragPan
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Shift" && !e.repeat) {
        map.dragPan.disable()
      }
    }
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.key === "Shift") {
        map.dragPan.enable()
      }
    }
    window.addEventListener("keydown", onKeyDown)
    window.addEventListener("keyup", onKeyUp)

    const onDown = (e: maplibregl.MapMouseEvent & { originalEvent: MouseEvent }) => {
      if (!e.originalEvent.shiftKey) return
      e.originalEvent.preventDefault()
      e.originalEvent.stopPropagation()
      drawing.current = true
      start.current = e.lngLat
      onDrawingChange?.(true)
    }

    const onMove = (e: maplibregl.MapMouseEvent) => {
      if (!drawing.current || !start.current) return
      setRect(
        [start.current.lng, start.current.lat],
        [e.lngLat.lng, e.lngLat.lat],
      )
    }

    const onUp = (e: maplibregl.MapMouseEvent & { originalEvent: MouseEvent }) => {
      if (!drawing.current || !start.current) return
      drawing.current = false
      map.dragPan.enable()
      onDrawingChange?.(false)

      const src = map.getSource(SOURCE) as maplibregl.GeoJSONSource
      if (!src) return

      const data = (src as any)._data
      if (!data || !data.geometry || data.geometry.type !== "Polygon") return
      const coords = (data.geometry as any).coordinates[0] as number[][]
      if (!coords || !coords.length) return

      const lngs = coords.map((c: number[]) => c[0])
      const lats = coords.map((c: number[]) => c[1])
      onBboxChange({
        west: Math.min(...lngs),
        south: Math.min(...lats),
        east: Math.max(...lngs),
        north: Math.max(...lats),
      })
      start.current = null

      // Re-disable if Shift still held
      if (e.originalEvent.shiftKey) {
        map.dragPan.disable()
      }
    }

    const onClick = (e: maplibregl.MapMouseEvent) => {
      const features = map.queryRenderedFeatures(e.point, { layers: [LAYER_FILL, LAYER_OUTLINE] })
      if (features.length > 0) {
        clearRect()
        onBboxChange(null)
      }
    }

    map.on("mousedown", onDown)
    map.on("mousemove", onMove)
    map.on("mouseup", onUp)
    map.on("click", onClick)

    return () => {
      map.dragPan.enable()
      window.removeEventListener("keydown", onKeyDown)
      window.removeEventListener("keyup", onKeyUp)
      map.off("mousedown", onDown)
      map.off("mousemove", onMove)
      map.off("mouseup", onUp)
      map.off("click", onClick)
    }
  }, [map])

  useEffect(() => {
    if (!bbox) {
      clearRect()
    }
  }, [bbox])

  return null
}
