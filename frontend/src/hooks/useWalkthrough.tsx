import { useState, useEffect, useCallback, useRef, type ReactNode } from "react"

export interface WalkthroughStep {
  target: string        // CSS selector for the element to spotlight
  title: string         // step title
  content: string       // instruction text
  placement?: "bottom" | "top" | "right" | "left"  // where tooltip appears relative to target
}

interface Props {
  steps: WalkthroughStep[]
  onComplete?: () => void
  onSkip?: () => void
}

export function useWalkthrough(steps: WalkthroughStep[]) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null)
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null)
  const observer = useRef<ResizeObserver | null>(null)

  const start = useCallback(() => setActiveIndex(0), [])
  const next = useCallback(() => {
    setActiveIndex((i) => {
      if (i === null || i >= steps.length - 1) return null
      return i + 1
    })
  }, [steps.length])
  const prev = useCallback(() => {
    setActiveIndex((i) => {
      if (i === null || i <= 0) return null
      return i - 1
    })
  }, [])
  const stop = useCallback(() => setActiveIndex(null), [])

  const active = activeIndex !== null
  const step = activeIndex !== null ? steps[activeIndex] : null
  const isLast = activeIndex === steps.length - 1
  const isFirst = activeIndex === 0

  useEffect(() => {
    if (!step) {
      setTargetRect(null)
      return
    }

    const measure = () => {
      const el = document.querySelector(step.target)
      if (el) {
        const r = el.getBoundingClientRect()
        const cx = r.left + r.width / 2
        const cy = r.top + r.height / 2
        const pad = 8
        setTargetRect(new DOMRect(r.left - pad, r.top - pad, r.width + pad * 2, r.height + pad * 2))
      }
    }

    measure()
    const timer = setInterval(measure, 200)
    observer.current = new ResizeObserver(measure)
    const el = document.querySelector(step.target)
    if (el) observer.current.observe(el)

    return () => {
      clearInterval(timer)
      observer.current?.disconnect()
    }
  }, [step])

  return { active, step, targetRect, activeIndex, isLast, isFirst, steps, start, next, prev, stop } as const
}

export function Spotlight({ targetRect }: { targetRect: DOMRect | null }) {
  if (!targetRect) return null

  const r = targetRect
  const pad = 4
  const clipPath = `path('M0,0 H${window.innerWidth} V${window.innerHeight} H0 Z M${r.x - pad},${r.y - pad} h${r.width + pad * 2} v${r.height + pad * 2} h${-(r.width + pad * 2)} Z')`

  return (
    <div
      className="fixed inset-0 z-40 pointer-events-none"
      style={{
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        clipPath,
      }}
    />
  )
}

export function WalkthroughTooltip({
  step,
  targetRect,
  isLast,
  isFirst,
  stepIndex,
  totalSteps,
  onNext,
  onPrev,
  onSkip,
  onComplete,
}: {
  step: WalkthroughStep
  targetRect: DOMRect | null
  isLast: boolean
  isFirst: boolean
  stepIndex: number
  totalSteps: number
  onNext: () => void
  onPrev: () => void
  onSkip: () => void
  onComplete: () => void
}) {
  if (!targetRect) return null

  const r = targetRect
  const placement = step.placement ?? "bottom"

  let left = r.left + r.width / 2
  let top = r.bottom + 16

  if (placement === "top") {
    top = r.top - 16
    left = r.left + r.width / 2
  } else if (placement === "right") {
    left = r.right + 16
    top = r.top + r.height / 2
  } else if (placement === "left") {
    left = r.left - 16
    top = r.top + r.height / 2
  }

  return (
    <div
      className="fixed z-50 animate-[fade-in_200ms_ease-out]"
      style={{
        left: `${Math.max(16, Math.min(left, window.innerWidth - 352))}px`,
        top: `${Math.max(16, Math.min(top, window.innerHeight - 200))}px`,
        transform: placement === "right" ? "translateY(-50%)" : placement === "left" ? "translate(-100%, -50%)" : placement === "top" ? "translate(-50%, -100%)" : "translateX(-50%)",
      }}
    >
      <div className="bg-bg-1 border border-border-default rounded-xl shadow-2xl p-5 w-80 space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
            {stepIndex + 1} of {totalSteps}
          </span>
          <button
            onClick={onSkip}
            className="text-xs text-text-tertiary hover:text-text-secondary transition-colors"
          >
            Skip
          </button>
        </div>

        <div className="space-y-1.5">
          <h3 className="text-sm font-semibold text-text-primary">{step.title}</h3>
          <p className="text-xs text-text-secondary leading-relaxed">{step.content}</p>
        </div>

        <div className="flex items-center justify-between pt-1">
          <button
            onClick={onPrev}
            disabled={isFirst}
            className="text-xs text-text-tertiary hover:text-text-secondary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Back
          </button>

          <div className="flex gap-1.5">
            {Array.from({ length: totalSteps }).map((_, i) => (
              <div
                key={i}
                className={`w-1.5 h-1.5 rounded-full transition-all duration-200 ${
                  i === stepIndex ? "bg-accent w-4" : "bg-bg-3"
                }`}
              />
            ))}
          </div>

          {isLast ? (
            <button
              onClick={onComplete}
              className="text-xs font-medium text-accent hover:brightness-110 transition-colors"
            >
              Got it
            </button>
          ) : (
            <button
              onClick={onNext}
              className="text-xs font-medium text-accent hover:brightness-110 transition-colors"
            >
              Next
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
