import { Button } from "@/components/ui/button"
import { Sparkles } from "lucide-react"

interface MatchButtonProps {
  disabled: boolean
  loading: boolean
  onClick: () => void
}

export function MatchButton({ disabled, loading, onClick }: MatchButtonProps) {
  return (
    <Button
      size="lg"
      className="w-full gap-2"
      disabled={disabled || loading}
      onClick={onClick}
    >
      <Sparkles className="h-4 w-4" />
      {loading ? "Matching..." : "Match Spectra"}
    </Button>
  )
}
