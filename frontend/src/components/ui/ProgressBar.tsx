interface Props {
  percent: number
  shimmer?: boolean
  className?: string
}

export function ProgressBar({ percent, shimmer = true, className = "" }: Props) {
  const pct = Math.min(100, Math.max(0, percent))

  return (
    <div className={`w-full h-1.5 bg-bg-2 rounded-full overflow-hidden ${className}`}>
      <div
        className="h-full rounded-full bg-accent transition-all duration-300 ease-out relative"
        style={{ width: `${pct}%` }}
      >
        {shimmer && pct > 0 && pct < 100 && (
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background: "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%)",
              backgroundSize: "200% 100%",
              animation: "progress-shimmer 1.5s cubic-bezier(0.4, 0, 0.2, 1) infinite",
            }}
          />
        )}
      </div>
    </div>
  )
}
