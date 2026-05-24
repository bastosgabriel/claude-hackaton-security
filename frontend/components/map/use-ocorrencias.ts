"use client"

import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import type { LngLatBounds } from "maplibre-gl"

import { searchOcorrencias, type SearchResponse } from "@/lib/api/ocorrencias"

import { useMap } from "./map-context"

function boundsToPolygon(bounds: LngLatBounds): Array<[number, number]> {
  const sw = bounds.getSouthWest()
  const ne = bounds.getNorthEast()
  return [
    [sw.lat, sw.lng],
    [ne.lat, sw.lng],
    [ne.lat, ne.lng],
    [sw.lat, ne.lng],
  ]
}

function roundPolygon(
  polygon: Array<[number, number]>,
  precision = 4,
): Array<[number, number]> {
  const factor = 10 ** precision
  return polygon.map(([lat, lng]) => [
    Math.round(lat * factor) / factor,
    Math.round(lng * factor) / factor,
  ])
}

export function useOcorrenciasInViewport(startDate: string, endDate: string) {
  const map = useMap()

  const [polygon, setPolygon] = useState<Array<[number, number]> | null>(() => {
    const b = map.getBounds()
    return b ? roundPolygon(boundsToPolygon(b)) : null
  })

  useEffect(() => {
    const update = () => {
      const b = map.getBounds()
      if (!b) return
      setPolygon(roundPolygon(boundsToPolygon(b)))
    }
    update()
    map.on("moveend", update)
    return () => {
      map.off("moveend", update)
    }
  }, [map])

  return useQuery<SearchResponse>({
    queryKey: ["ocorrencias", polygon, startDate, endDate],
    enabled: !!polygon,
    queryFn: ({ signal }) =>
      searchOcorrencias(
        { polygon: polygon!, start_date: startDate, end_date: endDate },
        signal,
      ),
  })
}
