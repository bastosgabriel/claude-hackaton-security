"use client"

import { useEffect, useRef, useState } from "react"
import maplibregl, { type Map as MaplibreMap } from "maplibre-gl"
import "maplibre-gl/dist/maplibre-gl.css"

import { MAP_STYLE_URL } from "@/lib/map-config"
import type { InitialView } from "@/hooks/use-viewport-url"

import { MapContext } from "./map-context"

type Props = {
  initialView: InitialView
  onMoveEnd?: (map: MaplibreMap) => void
  children?: React.ReactNode
}

export function MapCanvas({ initialView, onMoveEnd, children }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [map, setMap] = useState<MaplibreMap | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    let alive = true
    const instance = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE_URL,
      center: initialView.center,
      zoom: initialView.zoom,
    })

    instance.on("load", () => {
      if (alive) setMap(instance)
    })

    return () => {
      alive = false
      setMap(null)
      instance.remove()
    }
  }, [initialView])

  useEffect(() => {
    if (!map || !onMoveEnd) return
    const handler = () => onMoveEnd(map)
    handler() // emit once after the map is ready
    map.on("moveend", handler)
    return () => {
      map.off("moveend", handler)
    }
  }, [map, onMoveEnd])

  return (
    <>
      <div ref={containerRef} className="h-full w-full" />
      {map && <MapContext.Provider value={map}>{children}</MapContext.Provider>}
    </>
  )
}
