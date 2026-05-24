"use client"

import { createContext, useContext } from "react"
import type { Map as MaplibreMap } from "maplibre-gl"

export const MapContext = createContext<MaplibreMap | null>(null)

export function useMap(): MaplibreMap {
  const map = useContext(MapContext)
  if (!map) {
    throw new Error("useMap must be used inside <MapCanvas>")
  }
  return map
}
