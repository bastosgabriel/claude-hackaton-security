import * as h3 from "h3-js"
import type { Map as MaplibreMap } from "maplibre-gl"

export const MIN_RES = 8
export const MAX_RES = 10
export const MAX_CELLS = 5000

export type HexFeatureCollection = GeoJSON.FeatureCollection<
  GeoJSON.Polygon,
  { h3: string }
>

export function zoomToResolution(zoom: number): number {
  const res = Math.round(zoom) - 5
  return Math.max(MIN_RES, Math.min(MAX_RES, res))
}

export function buildHexGeoJSON(
  map: MaplibreMap,
  resolution: number,
): HexFeatureCollection {
  const bounds = map.getBounds()
  if (!bounds) {
    return { type: "FeatureCollection", features: [] }
  }

  const sw = bounds.getSouthWest()
  const ne = bounds.getNorthEast()
  const viewportPolygon: [number, number][] = [
    [sw.lat, sw.lng],
    [ne.lat, sw.lng],
    [ne.lat, ne.lng],
    [sw.lat, ne.lng],
    [sw.lat, sw.lng],
  ]

  let cells: string[] = []
  try {
    cells = h3.polygonToCells(viewportPolygon, resolution)
  } catch {
    cells = []
  }

  if (cells.length === 0) {
    const center = map.getCenter()
    cells = [h3.latLngToCell(center.lat, center.lng, resolution)]
  }

  if (cells.length > MAX_CELLS) {
    cells = cells.slice(0, MAX_CELLS)
  }

  const features: HexFeatureCollection["features"] = cells.map((cell) => {
    const boundary = h3.cellToBoundary(cell, true) as [number, number][]
    boundary.push(boundary[0])
    return {
      type: "Feature",
      properties: { h3: cell },
      geometry: {
        type: "Polygon",
        coordinates: [boundary],
      },
    }
  })

  return { type: "FeatureCollection", features }
}
