import { API_BASE_URL } from "./ocorrencias"

export type AreaForcaScore = {
  fid: number
  nome_subar: string
  area_km2: number
  geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon
  occurrence_count: number
  weighted_count: number
  density: number
  ocorrencia_score: number
  denuncia_count: number
  denuncia_density: number
  denuncia_score: number
  camera_count: number
  camera_density: number
  camera_score: number
  score: number
  score_raw: number
  by_desc_delito: Array<{ desc_delito: string; count: number }>
  by_year: Array<{ year: number; count: number }>
}

export type AreasForcaScoresResponse = {
  date_range: { start_date: string; end_date: string }
  weights: Record<string, number>
  component_weights: Record<string, number>
  results: AreaForcaScore[]
}

export async function fetchAreasForcaScores(
  startDate: string,
  endDate: string,
  signal?: AbortSignal,
): Promise<AreasForcaScoresResponse> {
  const url = `${API_BASE_URL}/api/areas-forca/scores/?start_date=${encodeURIComponent(
    startDate,
  )}&end_date=${encodeURIComponent(endDate)}`
  const res = await fetch(url, { signal })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(
      `areas-forca/scores failed: ${res.status} ${res.statusText}${
        text ? ` — ${text.slice(0, 200)}` : ""
      }`,
    )
  }
  return (await res.json()) as AreasForcaScoresResponse
}
