"use client"

import { useEffect, useRef, useState } from "react"

import { AreasLayer } from "@/components/map/AreasLayer"
import { H3Layer } from "@/components/map/H3Layer"
import { MapCanvas } from "@/components/map/MapCanvas"
import { OcorrenciasLayer } from "@/components/map/OcorrenciasLayer"
import type { Region } from "@/lib/api/regions"
import { INITIAL_CENTER, INITIAL_ZOOM } from "@/lib/map-config"

import { RegionList } from "./RegionList"

type MapLayer = "h3" | "areas" | "pontos"

const MAP_LAYERS: { key: MapLayer; label: string }[] = [
  { key: "h3", label: "Ocorrências" },
  { key: "areas", label: "Áreas da FM" },
  { key: "pontos", label: "Pontos" },
]

const MAP_INITIAL_VIEW = { center: INITIAL_CENTER, zoom: INITIAL_ZOOM }

type Props = {
  regions: Region[]
  isLoading: boolean
  selected: ReadonlySet<number>
  onToggleSelect: (id: number) => void
  /** Date window for the ocorrencias query, YYYY-MM-DD. */
  startDate: string
  endDate: string
}

export function DiagnosticoView({
  regions,
  isLoading,
  selected,
  onToggleSelect,
  startDate,
  endDate,
}: Props) {
  const [activeLayers, setActiveLayers] = useState<ReadonlySet<MapLayer>>(
    () => new Set<MapLayer>(["h3", "areas"]),
  )
  const [openId, setOpenId] = useState<number | null>(null)
  const autoOpened = useRef(false)

  // Auto-open the top-ranked region the first time data arrives. After the
  // user closes it, leave it closed — don't re-open on refetch.
  useEffect(() => {
    if (autoOpened.current) return
    if (regions.length === 0) return
    autoOpened.current = true
    setOpenId(regions[0].id)
  }, [regions])

  const toggleLayer = (key: MapLayer) => {
    setActiveLayers((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_460px]">
      {/* Map card */}
      <div className="flex min-h-[560px] flex-col rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4.5 py-3.5">
          <div>
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 20 3 17V4l6 3m0 13 6-3m-6 3V7m6 10 6 3V7l-6-3m0 13V4m0 0L9 7" />
              </svg>
              Mapa de risco · 27 mai – 2 jun
            </div>
            <div className="mt-0.5 text-[12px] text-slate-600">
              Polígonos de áreas de força · clique para detalhar
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            {MAP_LAYERS.map(({ key, label }) => {
              const active = activeLayers.has(key)
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => toggleLayer(key)}
                  aria-pressed={active}
                  className={
                    "rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-colors " +
                    (active
                      ? "border-[#0a1729] bg-[#0a1729] text-white"
                      : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100")
                  }
                >
                  {label}
                </button>
              )
            })}
          </div>
        </div>
        <div className="relative flex-1 overflow-hidden rounded-b-2xl bg-gradient-to-b from-blue-50 to-blue-100">
          <div className="absolute left-3.5 top-3.5 z-10 flex items-center gap-1.5 rounded-lg bg-slate-900/85 px-2.5 py-1.5 text-[11px] font-semibold text-white">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="12" r="6" />
            </svg>
            Projeção 27 mai – 2 jun
          </div>
          <MapCanvas initialView={MAP_INITIAL_VIEW}>
            {activeLayers.has("h3") && (
              <H3Layer startDate={startDate} endDate={endDate} />
            )}
            {activeLayers.has("areas") && (
              <AreasLayer startDate={startDate} endDate={endDate} />
            )}
            {activeLayers.has("pontos") && (
              <OcorrenciasLayer startDate={startDate} endDate={endDate} />
            )}
          </MapCanvas>
          <div className="absolute bottom-3.5 left-3.5 z-10 flex flex-col gap-1.5 rounded-xl border border-slate-200 bg-white/95 px-3 py-2.5 text-[11px] shadow-sm backdrop-blur">
            <div className="mb-0.5 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
              Score preditivo
            </div>
            <LegendRow color="#dc2626" label="Crítico (85–100)" />
            <LegendRow color="#ea580c" label="Alto (70–84)" />
            <LegendRow color="#ca8a04" label="Médio (50–69)" />
            <LegendRow color="#16a34a" label="Baixo (0–49)" />
          </div>
        </div>
      </div>

      {/* Ranking list */}
      <RegionList
        regions={regions}
        isLoading={isLoading}
        selected={selected}
        openId={openId}
        onToggleOpen={(id) => setOpenId((cur) => (cur === id ? null : id))}
        onToggleSelect={onToggleSelect}
      />
    </div>
  )
}

function LegendRow({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="h-3.5 w-3.5 rounded border border-black/10"
        style={{ background: color }}
      />
      {label}
    </div>
  )
}
