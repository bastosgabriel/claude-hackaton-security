export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000"

// Matches backend OcorrenciaSerializer.
export type Ocorrencia = {
  id: string
  lat: number
  lng: number
  data: string // "YYYY-MM-DD"
  hora: string | null
  desc_delito: string
  aisp: number | null
  risp: number | null
  locf: string
}

export type SearchSummary = {
  total: number
  by_desc_delito: Array<{ desc_delito: string; count: number }>
  by_month: Array<{ month: string; count: number }>
  by_aisp: Array<{ aisp: number; count: number }>
}

export type SearchPagination = {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export type SearchResponse = {
  summary: SearchSummary
  pagination: SearchPagination
  results: Ocorrencia[]
}

export type SearchOcorrenciasParams = {
  /** Polygon ring as [[lat, lng], ...]. Backend auto-closes. */
  polygon: Array<[number, number]>
  /** ISO date YYYY-MM-DD */
  start_date: string
  /** ISO date YYYY-MM-DD */
  end_date: string
  page?: number
  page_size?: number
}

export async function searchOcorrencias(
  params: SearchOcorrenciasParams,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE_URL}/api/ocorrencias/search/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      page: 1,
      page_size: 500,
      ...params,
    }),
    signal,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(
      `ocorrencias/search failed: ${res.status} ${res.statusText}${
        text ? ` — ${text.slice(0, 200)}` : ""
      }`,
    )
  }
  return (await res.json()) as SearchResponse
}
