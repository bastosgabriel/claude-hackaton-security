"use client"

import { useCallback, useRef, useState } from "react"
import { usePathname, useSearchParams } from "next/navigation"
import type { Map as MaplibreMap } from "maplibre-gl"

import { INITIAL_CENTER, INITIAL_ZOOM } from "@/lib/map-config"

export type InitialView = {
  center: [number, number]
  zoom: number
}

export function useViewportUrl(): {
  initialView: InitialView
  writeViewportToUrl: (map: MaplibreMap) => void
} {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const pathnameRef = useRef(pathname)
  pathnameRef.current = pathname

  const [initialView] = useState<InitialView>(() => {
    const lat = parseFloat(searchParams.get("lat") ?? "")
    const lng = parseFloat(searchParams.get("lng") ?? "")
    const z = parseFloat(searchParams.get("z") ?? "")
    return {
      center:
        Number.isFinite(lat) && Number.isFinite(lng)
          ? [lng, lat]
          : INITIAL_CENTER,
      zoom: Number.isFinite(z) ? z : INITIAL_ZOOM,
    }
  })

  const writeViewportToUrl = useCallback((map: MaplibreMap) => {
    const center = map.getCenter()
    const params = new URLSearchParams(window.location.search)
    params.set("lat", center.lat.toFixed(5))
    params.set("lng", center.lng.toFixed(5))
    params.set("z", map.getZoom().toFixed(2))
    const url = `${pathnameRef.current}?${params.toString()}`
    window.history.replaceState(window.history.state, "", url)
  }, [])

  return { initialView, writeViewportToUrl }
}
