import type { RegionLevel } from "@/lib/api/regions"

export const LEVEL_COLOR: Record<RegionLevel, string> = {
  critico: "#dc2626",
  alto: "#ea580c",
  medio: "#ca8a04",
  baixo: "#16a34a",
}

export const LEVEL_LABEL: Record<RegionLevel, string> = {
  critico: "Crítico",
  alto: "Alto",
  medio: "Médio",
  baixo: "Baixo",
}
