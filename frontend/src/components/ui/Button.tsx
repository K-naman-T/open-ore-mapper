import { type ButtonHTMLAttributes, type ReactNode, useState } from "react"

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger"
  size?: "sm" | "md" | "lg"
  loading?: boolean
  icon?: ReactNode
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  children,
  className = "",
  disabled,
  ...props
}: Props) {
  const [pressed, setPressed] = useState(false)

  const base =
    "inline-flex items-center justify-center gap-2 font-medium rounded-lg cursor-pointer select-none transition-all duration-150 ease-out focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-40 disabled:cursor-not-allowed"

  const variants: Record<string, string> = {
    primary: "bg-text-primary text-bg-0 hover:brightness-90",
    secondary: "bg-bg-2 text-text-primary border border-border-default hover:bg-bg-3",
    ghost: "text-text-secondary hover:bg-bg-2 hover:text-text-primary",
    danger: "bg-red text-white hover:brightness-90",
  }

  const sizes: Record<string, string> = {
    sm: "text-xs h-8 px-3 rounded-md",
    md: "text-sm h-10 px-4 rounded-lg",
    lg: "text-sm h-12 px-6 rounded-xl",
  }

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      style={pressed ? { transform: "scale(0.98)" } : undefined}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : icon ? (
        <span className="w-4 h-4 flex items-center">{icon}</span>
      ) : null}
      {children}
    </button>
  )
}
