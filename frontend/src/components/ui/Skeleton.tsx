export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`rounded-md bg-border-subtle ${className}`}
      style={{
        background: "linear-gradient(90deg, var(--color-bg-2) 25%, var(--color-bg-3) 50%, var(--color-bg-2) 75%)",
        backgroundSize: "200% 100%",
        animation: "shimmer 1.5s cubic-bezier(0.4, 0, 0.2, 1) infinite",
      }}
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="bg-bg-1 border border-border-subtle rounded-xl p-5 space-y-3">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-8 w-32" />
      <Skeleton className="h-3 w-16" />
    </div>
  )
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      <Skeleton className="h-8 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  )
}
