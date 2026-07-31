import { useRef, useState, type DragEvent } from "react"
import { Upload, FileText } from "lucide-react"
import { cn } from "@/lib/utils"

interface UploadZoneProps {
  onFile: (f: File) => void
  file: File | null
  accept?: string
  label: string
  extensions?: string
}

export function UploadZone({ onFile, file, accept, label, extensions }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) onFile(f)
  }

  const handleChange = () => {
    const f = inputRef.current?.files?.[0]
    if (f) onFile(f)
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed p-3 text-center transition-colors",
          dragging
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-muted-foreground/50"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={handleChange}
        />
        <Upload className="h-5 w-5 text-muted-foreground" />
        <p className="text-xs font-medium">{label}</p>
        <p className="text-[10px] text-muted-foreground">click or drop</p>
      </div>
      {file ? (
        <div className="flex min-w-0 items-center gap-1.5 rounded-md bg-muted px-2 py-1">
          <FileText className="h-3 w-3 shrink-0 text-muted-foreground" />
          <span className="truncate text-[11px] font-medium">{file.name}</span>
        </div>
      ) : (
        extensions && (
          <p className="truncate px-0.5 text-[10px] text-muted-foreground">{extensions}</p>
        )
      )}
    </div>
  )
}
