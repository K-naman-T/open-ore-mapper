import { ProgressBar } from "../ui/ProgressBar"

interface Props {
  progress: number
  message: string
}

export function ProcessingOverlay({ progress, message }: Props) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-bg-0/80 backdrop-blur-sm">
      <div className="bg-bg-1 border border-border-default rounded-2xl shadow-lg p-8 w-80 space-y-5">
        <div className="flex items-center gap-3">
          <svg className="w-5 h-5 text-accent animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeDasharray="31.4 31.4" strokeLinecap="round" className="opacity-30" />
            <path d="M12 2A10 10 0 112 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <p className="text-sm font-medium text-text-primary">{message}</p>
        </div>
        <ProgressBar percent={progress} />
        <p className="text-xs text-text-tertiary tabular-nums font-mono">{progress.toFixed(0)}% complete</p>
      </div>
    </div>
  )
}
