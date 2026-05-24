"use client"

import { useEffect } from "react"
import maplibregl, {
  type GeoJSONSource,
  type MapMouseEvent,
} from "maplibre-gl"

import { type Ocorrencia } from "@/lib/api/ocorrencias"

import { useMap } from "./map-context"
import { useOcorrenciasInViewport } from "./use-ocorrencias"

const SOURCE_ID = "ocorrencias-source"
const CIRCLE_LAYER_ID = "ocorrencias-circles"

type Props = {
  startDate: string // YYYY-MM-DD
  endDate: string // YYYY-MM-DD
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
  const query = useOcorrenciasInViewport(startDate, endDate)

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
