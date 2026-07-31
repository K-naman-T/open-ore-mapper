interface ProgressBarProps {
  message?: string
}

export function ProgressBar({ message = "Matching..." }: ProgressBarProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-3">
        <div className="h-2 w-48 overflow-hidden rounded-full bg-muted">
          <div className="h-full w-full animate-pulse rounded-full bg-primary" />
        </div>
        <p className="animate-pulse text-sm font-medium text-muted-foreground">{message}</p>
      </div>
    </div>
  )
}
