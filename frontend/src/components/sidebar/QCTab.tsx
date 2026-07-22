import type { QCReport } from "../../api/client"

interface Props {
  report?: QCReport
}

export function QCTab({ report }: Props) {
  if (!report) {
    return <p className="text-sm text-text-tertiary text-center py-8">No QC data available</p>
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-xl border border-border-subtle bg-bg-2">
          <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Status</p>
          <p className={`text-sm font-semibold mt-0.5 ${
            report.status === "pass" ? "text-green" : report.status === "warn" ? "text-amber" : "text-red"
          }`}>
            {report.status.toUpperCase()}
          </p>
        </div>
        <div className="p-3 rounded-xl border border-border-subtle bg-bg-2">
          <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Valid pixels</p>
          <p className="text-sm font-mono tabular-nums text-text-primary mt-0.5">
            {(report.valid_pixel_fraction * 100).toFixed(1)}%
          </p>
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-text-secondary">Bands</p>
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2.5 rounded-lg border border-border-subtle bg-bg-2">
            <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Total</p>
            <p className="text-sm font-mono text-text-primary">{report.band_count}</p>
          </div>
          <div className="p-2.5 rounded-lg border border-green/20 bg-green/5">
            <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Retained</p>
            <p className="text-sm font-mono text-green">{report.retained_band_indices.length}</p>
          </div>
          {report.excluded_band_indices.length > 0 && (
            <div className="p-2.5 rounded-lg border border-red/20 bg-red/5 col-span-2">
              <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Excluded</p>
              <p className="text-sm font-mono text-red mt-0.5">
                {report.excluded_band_indices.length} bands: {report.excluded_band_indices.join(", ")}
              </p>
            </div>
          )}
        </div>
      </div>

      {report.warnings.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-amber">Warnings</p>
          {report.warnings.map((w, i) => (
            <div key={i} className="p-2.5 rounded-lg border border-amber/10 bg-amber/5">
              <p className="text-xs text-amber leading-relaxed">{w}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
