import { useRef, useState, type DragEvent } from "react"
import { Upload } from "lucide-react"

interface UploadZoneProps {
  onFile: (f: File) => void
  file: File | null
  accept?: string
  label: string
}

export function UploadZone({ onFile, file, accept, label }: UploadZoneProps) {
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
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
        dragging
          ? "border-primary bg-primary/5"
          : "border-muted-foreground/25 hover:border-muted-foreground/50"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={handleChange}
      />
      <Upload className="mb-2 h-8 w-8 text-muted-foreground" />
      {file ? (
        <p className="text-sm font-medium">{file.name}</p>
      ) : (
        <>
          <p className="text-sm font-medium">{label}</p>
          <p className="text-xs text-muted-foreground">or click to browse</p>
        </>
      )}
    </div>
  )
}
