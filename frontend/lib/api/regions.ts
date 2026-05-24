import { API_BASE_URL } from "./ocorrencias"

export type RegionLevel = "critico" | "alto" | "medio" | "baixo"

export type RegionCriterionKey =
  | "roubos_7d"
  | "disque_denuncia"
  | "fatores_ambientais"
  | "relints_ativos"
  | "historico_4s"

export type RegionCriterion = {
  key: RegionCriterionKey
  label: string
  value: string
  pct: number
  level: RegionLevel
}

export type RegionActionKind = "amb" | "pol" | "int"

export type RegionAction = {
  kind: RegionActionKind
  title: string
  desc: string
  agents: number
  cost_label: string
}

export type Region = {
  id: number
  name: string
  aisp: string
  score: number
  level: RegionLevel
  roubos: number
  denuncias: number
  ambiente: number
  criteria: RegionCriterion[]
  narrative: string
  actions: RegionAction[]
}

export type RegionsResponse = {
  date_range: { start_date: string; end_date: string }
  results: Region[]
}

export async function fetchRegions(
  startDate: string,
  endDate: string,
  signal?: AbortSignal,
): Promise<RegionsResponse> {
  const url = `${API_BASE_URL}/api/regions/?start_date=${encodeURIComponent(
    startDate,
  )}&end_date=${encodeURIComponent(endDate)}`
  const res = await fetch(url, { signal })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(
      `regions failed: ${res.status} ${res.statusText}${
        text ? ` — ${text.slice(0, 200)}` : ""
      }`,
    )
  }
  return (await res.json()) as RegionsResponse
}
