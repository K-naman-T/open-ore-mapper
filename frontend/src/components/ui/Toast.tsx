import { type ReactNode, useState, useEffect, useCallback, createContext, useContext } from "react"

interface Toast {
  id: number
  message: string
  type: "success" | "error" | "info"
  exiting: boolean
}

interface ToastCtx {
  toast: (message: string, type?: "success" | "error" | "info") => void
}

const ctx = createContext<ToastCtx>({ toast: () => {} })
export const useToast = () => useContext(ctx)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  let nextId = 0

  const toast = useCallback((message: string, type: "success" | "error" | "info" = "info") => {
    const id = nextId++
    setToasts((prev) => [...prev, { id, message, type, exiting: false }])
    setTimeout(() => {
      setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)))
      setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 300)
    }, 4000)
  }, [])

  return (
    <ctx.Provider value={{ toast }}>
      {children}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto px-4 py-3 rounded-lg border border-border-default shadow-lg text-sm font-medium
              ${t.type === "success" ? "bg-green/10 border-green/30 text-green" : ""}
              ${t.type === "error" ? "bg-red/10 border-red/30 text-red" : ""}
              ${t.type === "info" ? "bg-bg-2 border-border-strong text-text-primary" : ""}
              ${t.exiting ? "animate-[toast-in_300ms_ease-out_reverse_forwards]" : "animate-[toast-in]"}
            `}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ctx.Provider>
  )
}
