"use client"

import { useEffect } from "react"
import maplibregl, { type MapMouseEvent } from "maplibre-gl"

import { AREAS_GEOJSON_URL } from "@/lib/map-config"

import { useMap } from "./map-context"

const SOURCE_ID = "areas-forca-source"
const FILL_LAYER_ID = "areas-forca-fill"
const LINE_LAYER_ID = "areas-forca-line"

type AreasProperties = { fid: number; nome_subar: string }
type AreasFeatureCollection = GeoJSON.FeatureCollection<
  GeoJSON.Polygon,
  AreasProperties
>

export function AreasLayer() {
  const map = useMap()

  useEffect(() => {
    let alive = true

    const onClick = (e: MapMouseEvent & { features?: GeoJSON.Feature[] }) => {
      const feature = e.features?.[0]
      if (!feature) return
      const name =
        (feature.properties as AreasProperties | null)?.nome_subar ?? "Área"
      new maplibregl.Popup({ closeButton: true })
        .setLngLat(e.lngLat)
        .setHTML(
          `<div style="font:600 13px/1.3 var(--font-sans),system-ui;color:#111">${name}</div>`,
        )
        .addTo(map)
    }
    const onEnter = () => {
      map.getCanvas().style.cursor = "pointer"
    }
    const onLeave = () => {
      map.getCanvas().style.cursor = ""
    }

    const load = async () => {
      try {
        const res = await fetch(AREAS_GEOJSON_URL)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const geojson = (await res.json()) as AreasFeatureCollection
        if (!alive || map.getSource(SOURCE_ID)) return
        map.addSource(SOURCE_ID, { type: "geojson", data: geojson })
        map.addLayer({
          id: FILL_LAYER_ID,
          type: "fill",
          source: SOURCE_ID,
          paint: {
            "fill-color": "#ef4444",
            "fill-opacity": 0.35,
          },
        })
        map.addLayer({
          id: LINE_LAYER_ID,
          type: "line",
          source: SOURCE_ID,
          paint: {
            "line-color": "#7f1d1d",
            "line-width": 3.5,
          },
        });
        map.on("click", FILL_LAYER_ID, onClick)
        map.on("mouseenter", FILL_LAYER_ID, onEnter)
        map.on("mouseleave", FILL_LAYER_ID, onLeave)
      } catch (err) {
        console.error("Failed to load áreas de força:", err)
      }
    }

    load()

    return () => {
      alive = false
      map.off("click", FILL_LAYER_ID, onClick)
      map.off("mouseenter", FILL_LAYER_ID, onEnter)
      map.off("mouseleave", FILL_LAYER_ID, onLeave)
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
