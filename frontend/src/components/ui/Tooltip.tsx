import { useState, useEffect, useRef, type ReactNode } from "react"

interface Props {
  content: string
  children: ReactNode
  delay?: number
}

export function Tooltip({ content, children, delay = 300 }: Props) {
  const [show, setShow] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={() => { timer.current = setTimeout(() => setShow(true), delay) }}
      onMouseLeave={() => { if (timer.current) clearTimeout(timer.current); setShow(false) }}
    >
      {children}
      {show && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-bg-3 text-text-primary text-xs rounded-md border border-border-default shadow-lg whitespace-nowrap animate-[tooltip-in] pointer-events-none z-50">
          {content}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px border-4 border-transparent border-t-bg-3" />
        </div>
      )}
    </div>
  )
}
