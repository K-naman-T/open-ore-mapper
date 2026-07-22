import { useState, useCallback, useRef, type DragEvent } from "react"

interface Props {
  onFile: (file: File) => void
}

export function DropZone({ onFile }: Props) {
  const [dragOver, setDragOver] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback((file: File) => {
    setFileName(file.name)
    onFile(file)
  }, [onFile])

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }, [handleFile])

  const handleDragOver = (e: DragEvent) => { e.preventDefault(); setDragOver(true) }
  const handleDragLeave = () => setDragOver(false)

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={`
        relative w-full rounded-2xl border-2 border-dashed cursor-pointer
        transition-all duration-200 ease-out select-none
        flex flex-col items-center justify-center gap-3
        ${dragOver
          ? "border-accent bg-accent/5 scale-[1.01]"
          : fileName
            ? "border-green/30 bg-green/[0.03]"
            : "border-border-default bg-bg-1 hover:border-border-strong hover:bg-bg-2"
        }
        ${fileName ? "py-6" : "py-16"}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".tif,.tiff,.h5,.hdf5,.nc,.mat"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
      />

      <div className={`rounded-full p-4 transition-colors duration-200 ${fileName ? "bg-green/10" : "bg-bg-2"} ${dragOver ? "bg-accent/10" : ""}`}>
        {fileName ? (
          <svg className="w-8 h-8 text-green" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        ) : (
          <svg className={`w-8 h-8 transition-colors duration-200 ${dragOver ? "text-accent" : "text-text-tertiary"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
        )}
      </div>

      {fileName ? (
        <div className="text-center space-y-0.5">
          <p className="text-sm font-medium text-text-primary">{fileName}</p>
          <p className="text-xs text-text-tertiary">Click or drop to replace</p>
        </div>
      ) : (
        <div className="text-center space-y-1">
          <p className="text-sm font-medium text-text-primary">
            Drop your hyperspectral file
          </p>
          <p className="text-xs text-text-tertiary">
            TIFF, HDF5, NetCDF, or MATLAB (.mat) &mdash; up to 500 MB
          </p>
        </div>
      )}
    </div>
  )
}
