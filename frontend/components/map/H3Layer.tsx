"use client"

import { useEffect } from "react"
import type { GeoJSONSource } from "maplibre-gl"

import { buildHexGeoJSON, zoomToResolution } from "@/lib/h3-grid"

import { useMap } from "./map-context"

const SOURCE_ID = "h3-hex-source"
const FILL_LAYER_ID = "h3-hex-fill"
const LINE_LAYER_ID = "h3-hex-line"

export function H3Layer() {
  const map = useMap()

  useEffect(() => {
    const refresh = () => {
      const resolution = zoomToResolution(map.getZoom())
      const data = buildHexGeoJSON(map, resolution)
      const source = map.getSource(SOURCE_ID) as GeoJSONSource | undefined
      if (source) {
        source.setData(data)
        return
      }
      map.addSource(SOURCE_ID, { type: "geojson", data })
      map.addLayer({
        id: FILL_LAYER_ID,
        type: "fill",
        source: SOURCE_ID,
        paint: {
          "fill-color": "#7c3aed",
          "fill-opacity": 0.18,
        },
      })
      map.addLayer({
        id: LINE_LAYER_ID,
        type: "line",
        source: SOURCE_ID,
        paint: {
          "line-color": "#5b21b6",
          "line-width": 1,
        },
      })
    }

    refresh()
    map.on("moveend", refresh)

    return () => {
      map.off("moveend", refresh)
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
