"use client"

import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import maplibregl, {
  type GeoJSONSource,
  type LngLatBounds,
  type MapMouseEvent,
} from "maplibre-gl"

import {
  searchOcorrencias,
  type Ocorrencia,
  type SearchResponse,
} from "@/lib/api/ocorrencias"

import { useMap } from "./map-context"

const SOURCE_ID = "ocorrencias-source"
const CIRCLE_LAYER_ID = "ocorrencias-circles"

type Props = {
  startDate: string // YYYY-MM-DD
  endDate: string // YYYY-MM-DD
}

function boundsToPolygon(bounds: LngLatBounds): Array<[number, number]> {
  const sw = bounds.getSouthWest()
  const ne = bounds.getNorthEast()
  // [lat, lng] per backend convention. Backend auto-closes the ring.
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

function toGeoJSON(results: Ocorrencia[]): GeoJSON.FeatureCollection<
  GeoJSON.Point,
  { id: string; desc: string; data: string; aisp: number | null }
> {
  return {
    type: "FeatureCollection",
    features: results.map((o) => ({
      type: "Feature",
      properties: { id: o.id, desc: o.desc_delito, data: o.data, aisp: o.aisp },
      geometry: { type: "Point", coordinates: [o.lng, o.lat] },
    })),
  }
}

export function OcorrenciasLayer({ startDate, endDate }: Props) {
  const map = useMap()

  // Track bounds in state so query key changes on each moveend.
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

  const query = useQuery<SearchResponse>({
    queryKey: ["ocorrencias", polygon, startDate, endDate],
    enabled: !!polygon,
    queryFn: ({ signal }) =>
      searchOcorrencias(
        { polygon: polygon!, start_date: startDate, end_date: endDate },
        signal,
      ),
  })

  // Push the latest results into the map source.
  useEffect(() => {
    const data = toGeoJSON(query.data?.results ?? [])
    const source = map.getSource(SOURCE_ID) as GeoJSONSource | undefined
    if (source) {
      source.setData(data)
      return
    }
    map.addSource(SOURCE_ID, { type: "geojson", data })
    map.addLayer({
      id: CIRCLE_LAYER_ID,
      type: "circle",
      source: SOURCE_ID,
      paint: {
        "circle-radius": [
          "interpolate",
          ["linear"],
          ["zoom"],
          10, 2.5,
          14, 4,
          17, 7,
        ],
        "circle-color": "#0ea5e9",
        "circle-opacity": 0.75,
        "circle-stroke-width": 1,
        "circle-stroke-color": "#ffffff",
      },
    })
  }, [map, query.data])

  // Click → popup with crime description.
  useEffect(() => {
    const onClick = (e: MapMouseEvent & { features?: GeoJSON.Feature[] }) => {
      const feature = e.features?.[0]
      if (!feature) return
      const props = feature.properties as
        | { desc?: string; data?: string; aisp?: number | null }
        | null
      new maplibregl.Popup({ closeButton: true })
        .setLngLat(e.lngLat)
        .setHTML(
          `<div style="font:600 12px/1.3 var(--font-sans),system-ui;color:#111">
            ${props?.desc ?? "Ocorrência"}
          </div>
          <div style="font:500 11px/1.3 var(--font-sans),system-ui;color:#475569;margin-top:2px">
            ${props?.data ?? ""}${props?.aisp ? ` · AISP ${props.aisp}` : ""}
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
    map.on("click", CIRCLE_LAYER_ID, onClick)
    map.on("mouseenter", CIRCLE_LAYER_ID, onEnter)
    map.on("mouseleave", CIRCLE_LAYER_ID, onLeave)
    return () => {
      map.off("click", CIRCLE_LAYER_ID, onClick)
      map.off("mouseenter", CIRCLE_LAYER_ID, onEnter)
      map.off("mouseleave", CIRCLE_LAYER_ID, onLeave)
    }
  }, [map])

  // Tear down source/layer on unmount.
  useEffect(() => {
    return () => {
      try {
        if (map.getLayer(CIRCLE_LAYER_ID)) map.removeLayer(CIRCLE_LAYER_ID)
        if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID)
      } catch {
        // Map was already removed (style is gone). Nothing to clean up.
      }
    }
  }, [map])

  return null
}
