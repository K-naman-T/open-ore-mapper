export const CLASS_COLORS: string[] = [
  "#e6194b", "#3cb44b", "#4363d8", "#f58231",
  "#911eb4", "#42d4f4", "#f032e6", "#bfef45",
  "#fabed4", "#469990", "#dcbeff", "#9a6324",
  "#800000", "#aaffc3",
]

export function getClassColor(index: number): string {
  return CLASS_COLORS[index % CLASS_COLORS.length]
}

export function classColorMap(classes: string[]): Record<string, string> {
  const map: Record<string, string> = {}
  classes.forEach((cls, i) => {
    map[cls] = getClassColor(i)
  })
  return map
}
