import { useState } from "react"
import { Button } from "../ui/Button"
import { useToast } from "../ui/Toast"
import { useParams } from "react-router-dom"

export function ExportTab() {
  const { uuid } = useParams<{ uuid: string }>()
  const { toast } = useToast()
  const [copied, setCopied] = useState(false)

  const shareUrl = `${window.location.origin}/maps/${uuid}`

  const handleCopy = async () => {
    await navigator.clipboard.writeText(shareUrl)
    setCopied(true)
    toast("Link copied to clipboard", "success")
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownloadPNG = () => {
    if (!uuid) return
    const link = document.createElement("a")
    link.href = `/api/v1/predict/preview.png?uuid=${uuid}`
    link.download = `mineral-map-${uuid}.png`
    link.click()
    toast("Downloading PNG...", "info")
  }

  const handleDownloadGeoTIFF = () => {
    if (!uuid) return
    const link = document.createElement("a")
    link.href = `/api/v1/predict/export?uuid=${uuid}&format=geotiff`
    link.download = `mineral-map-${uuid}.tif`
    link.click()
    toast("Downloading GeoTIFF...", "info")
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <p className="text-xs font-medium text-text-secondary">Share</p>
        <div className="flex items-center gap-2">
          <input
            readOnly
            value={shareUrl}
            className="flex-1 h-9 px-3 text-xs bg-bg-2 border border-border-default rounded-lg text-text-secondary font-mono truncate"
            onClick={(e) => (e.target as HTMLInputElement).select()}
          />
          <Button variant="secondary" size="sm" onClick={handleCopy}>
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>
      </div>

      <div className="border-t border-border-subtle pt-4 space-y-2">
        <p className="text-xs font-medium text-text-secondary">Download</p>
        <Button variant="secondary" onClick={handleDownloadPNG} className="w-full">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M7.5 12l4.5 4.5m0 0l4.5-4.5m-4.5 4.5V3" />
          </svg>
          Download PNG
        </Button>
        <Button variant="secondary" onClick={handleDownloadGeoTIFF} className="w-full">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M7.5 12l4.5 4.5m0 0l4.5-4.5m-4.5 4.5V3" />
          </svg>
          Download GeoTIFF
        </Button>
      </div>
    </div>
  )
}
