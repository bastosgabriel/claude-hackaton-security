"use client"

import { useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import maplibregl, {
  type GeoJSONSource,
  type MapMouseEvent,
} from "maplibre-gl"

import {
  fetchAreasForcaScores,
  type AreaForcaScore,
  type AreasForcaScoresResponse,
} from "@/lib/api/areas-forca"

import { useMap } from "./map-context"

const SOURCE_ID = "areas-forca-source"
const FILL_LAYER_ID = "areas-forca-fill"
const LINE_LAYER_ID = "areas-forca-line"

type Props = {
  startDate: string // YYYY-MM-DD
  endDate: string // YYYY-MM-DD
}

type AreaProperties = {
  fid: number
  nome_subar: string
  score: number
  occurrence_count: number
}

// Relative ramp: stretches green→yellow→orange→red across whatever score
// range the current response actually contains, so the lowest area is always
// fully green and the highest fully red even when scores cluster.
function relativeColorExpression(scores: number[]): unknown[] {
  if (scores.length === 0) {
    return ["literal", "#16a34a"]
  }
  const min = Math.min(...scores)
  const max = Math.max(...scores)
  const range = max - min
  if (range === 0) {
    // All polygons share the same score — paint them the middle band.
    return ["literal", "#ca8a04"]
  }
  return [
    "interpolate",
    ["linear"],
    ["coalesce", ["get", "score"], min],
    min,                      "#16a34a",
    min + range * 0.33,       "#ca8a04",
    min + range * 0.66,       "#ea580c",
    max,                      "#dc2626",
  ]
}

function toGeoJSON(
  results: AreaForcaScore[],
): GeoJSON.FeatureCollection<GeoJSON.Polygon | GeoJSON.MultiPolygon, AreaProperties> {
  return {
    type: "FeatureCollection",
    features: results.map((r) => ({
      type: "Feature",
      properties: {
        fid: r.fid,
        nome_subar: r.nome_subar,
        score: r.score,
        occurrence_count: r.occurrence_count,
      },
      geometry: r.geometry,
    })),
  }
}

export function AreasLayer({ startDate, endDate }: Props) {
  const map = useMap()
  const query = useQuery<AreasForcaScoresResponse>({
    queryKey: ["areas-forca-scores", startDate, endDate],
    queryFn: ({ signal }) => fetchAreasForcaScores(startDate, endDate, signal),
  })
  const results = query.data?.results

  useEffect(() => {
    if (!results) return
    const data = toGeoJSON(results)
    const color = relativeColorExpression(results.map((r) => r.score))
    const source = map.getSource(SOURCE_ID) as GeoJSONSource | undefined
    if (source) {
      source.setData(data)
      if (map.getLayer(FILL_LAYER_ID)) {
        map.setPaintProperty(FILL_LAYER_ID, "fill-color", color)
      }
      return
    }
    map.addSource(SOURCE_ID, { type: "geojson", data })
    map.addLayer({
      id: FILL_LAYER_ID,
      type: "fill",
      source: SOURCE_ID,
      paint: {
        "fill-color": color,
        "fill-opacity": 0.45,
      },
    })
    map.addLayer({
      id: LINE_LAYER_ID,
      type: "line",
      source: SOURCE_ID,
      paint: {
        "line-color": "#0f172a",
        "line-width": 1.5,
        "line-opacity": 0.55,
      },
    })
  }, [map, results])

  useEffect(() => {
    const onClick = (e: MapMouseEvent & { features?: GeoJSON.Feature[] }) => {
      const feature = e.features?.[0]
      if (!feature) return
      const props = feature.properties as AreaProperties | null
      const name = props?.nome_subar ?? "Área"
      const score = props?.score != null ? Math.round(props.score) : "—"
      const count = props?.occurrence_count ?? 0
      new maplibregl.Popup({ closeButton: true })
        .setLngLat(e.lngLat)
        .setHTML(
          `<div style="font:600 13px/1.3 var(--font-sans),system-ui;color:#111">${name}</div>
          <div style="font:500 11px/1.3 var(--font-sans),system-ui;color:#475569;margin-top:2px">
            Score ${score} · ${count} ocorrências
          </div>`,
        )
        .addTo(map)
    }
    const onEnter = () => {
      map.getCanvas().style.cursor = "pointer"
    }
    const onLeave = () => {
      map.getCanvas().style.cursor = ""
    }
    map.on("click", FILL_LAYER_ID, onClick)
    map.on("mouseenter", FILL_LAYER_ID, onEnter)
    map.on("mouseleave", FILL_LAYER_ID, onLeave)
    return () => {
      map.off("click", FILL_LAYER_ID, onClick)
      map.off("mouseenter", FILL_LAYER_ID, onEnter)
      map.off("mouseleave", FILL_LAYER_ID, onLeave)
    }
  }, [map])

  useEffect(() => {
    return () => {
      try {
        if (map.getLayer(LINE_LAYER_ID)) map.removeLayer(LINE_LAYER_ID)
        if (map.getLayer(FILL_LAYER_ID)) map.removeLayer(FILL_LAYER_ID)
        if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID)
      } catch {
        // Map was already removed (style is gone). Nothing to clean up.
      }
    }
  }, [map])

  return null
}
