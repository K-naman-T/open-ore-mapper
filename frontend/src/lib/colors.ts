export const MINERAL_COLORS: Record<string, string> = {
  default: "#B13824",
}

export const CLASS_COLORS = [
  "#B13824",
  "#D67527",
  "#E7B239",
  "#52545B",
  "#885C30",
  "#C2864F",
  "#79562D",
  "#4E7E99",
  "#4E9974",
  "#775CA3",
  "#B54D7A",
  "#6C6F3D",
  "#2D7B8C",
  "#8C4E6B",
  "#5A7A4A",
  "#A5682A",
]

export function mineralColor(index: number): string {
  return CLASS_COLORS[index % CLASS_COLORS.length]
}

export function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
