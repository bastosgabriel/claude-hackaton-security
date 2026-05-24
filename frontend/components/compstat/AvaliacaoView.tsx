"use client"

import { useCallback, useEffect, useState } from "react"
import type { Map as MaplibreMap } from "maplibre-gl"

import { AreasLayer } from "@/components/map/AreasLayer"
import { H3Layer } from "@/components/map/H3Layer"
import { MapCanvas } from "@/components/map/MapCanvas"
import { useMap } from "@/components/map/map-context"
import { OcorrenciasLayer } from "@/components/map/OcorrenciasLayer"
import { INITIAL_CENTER, INITIAL_ZOOM } from "@/lib/map-config"

const SNAPSHOT_VIEW = { center: INITIAL_CENTER, zoom: INITIAL_ZOOM }

type MapLayer = "h3" | "areas"

const MAP_LAYERS: { key: MapLayer; label: string }[] = [
  { key: "h3", label: "Ocorrências" },
  { key: "areas", label: "Áreas da FM" },
]

type Delta = {
  label: string
  value: string
  trend: "up" | "down"
  positive: boolean
  prev: string
}

const DELTAS: Delta[] = [
  { label: "Roubos a transeunte", value: "−28%", trend: "down", positive: true, prev: "42 → 30 ocorrências" },
  { label: "Disque Denúncia", value: "−41%", trend: "down", positive: true, prev: "18 → 11 denúncias" },
  { label: "Tempo médio resposta", value: "−12%", trend: "down", positive: true, prev: "8'24\" → 7'24\"" },
  { label: "Cobertura territorial", value: "+19%", trend: "up", positive: true, prev: "62% → 74%" },
]

const CHECKLIST: { label: string; by: string; done: boolean }[] = [
  { label: "Reforço de patrulhamento a pé (24 agentes)", by: "14 mai", done: true },
  { label: "Reparo de iluminação · R. do Lavradio", by: "15 mai", done: true },
  { label: "Poda de vegetação · Arcos da Lapa", by: "16 mai", done: true },
  { label: "Operação integrada PM + GM (sex/sáb)", by: "17–18 mai", done: true },
  { label: "Remoção de obstrução visual (containers)", by: "pendente", done: false },
]

const TIMELINE: { date: string; text: React.ReactNode }[] = [
  { date: "13 MAI 08h", text: <><strong className="text-slate-900">Priorização aprovada</strong> · score inicial 92</> },
  { date: "14 MAI 06h", text: <><strong className="text-slate-900">Reforço deslocado</strong> · 24 agentes · base R. Riachuelo</> },
  { date: "17 MAI 22h", text: <><strong className="text-slate-900">Operação noturna</strong> · 3 prisões em flagrante</> },
  { date: "19 MAI 23h", text: <><strong className="text-slate-900">Semana encerrada</strong> · score atual 64 (−28)</> },
]

export function AvaliacaoView() {
  const [activeLayers, setActiveLayers] = useState<ReadonlySet<MapLayer>>(
    () => new Set<MapLayer>(["h3", "areas"]),
  )
  const [showPoints, setShowPoints] = useState(false)

  const toggleLayer = (key: MapLayer) => {
    setActiveLayers((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  // Mirror pan/zoom across all snapshot maps. Each MapCanvas registers its
  // instance on mount; when the user drags or zooms one of them, the others
  // jump to the same view. The `originalEvent` check skips programmatic moves
  // (the ones we trigger here) so the sync doesn't loop.
  const [maps, setMaps] = useState<MaplibreMap[]>([])
  const registerMap = useCallback((m: MaplibreMap) => {
    setMaps((cur) => (cur.includes(m) ? cur : [...cur, m]))
    return () => setMaps((cur) => cur.filter((x) => x !== m))
  }, [])

  useEffect(() => {
    if (maps.length < 2) return
    const cleanups: Array<() => void> = []
    for (const src of maps) {
      const onMove = (e: { originalEvent?: unknown }) => {
        if (!e.originalEvent) return
        const c = src.getCenter()
        const z = src.getZoom()
        for (const m of maps) {
          if (m === src) continue
          m.jumpTo({ center: [c.lng, c.lat], zoom: z })
        }
      }
      src.on("move", onMove)
      cleanups.push(() => src.off("move", onMove))
    }
    return () => cleanups.forEach((c) => c())
  }, [maps])

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_420px]">
      {/* Filter bar + stacked before/after maps */}
      <div className="grid h-[560px] grid-rows-[auto_1fr_1fr] gap-3.5">
        <div className="flex flex-wrap items-center justify-end gap-1.5 rounded-2xl border border-slate-200 bg-white px-4.5 py-2 shadow-sm">
          <label className="mr-1.5 flex cursor-pointer items-center gap-1.5 text-[11px] font-semibold text-slate-600">
            <input
              type="checkbox"
              checked={showPoints}
              onChange={(e) => setShowPoints(e.target.checked)}
              className="h-3.5 w-3.5 cursor-pointer accent-[#0a1729]"
            />
            Pontos
          </label>
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
        <SnapshotPanel
          stampClass="bg-orange-700/90"
          stampLabel="Antes · jan–dez 2023 · Snapshot"
          startDate="2023-01-01"
          endDate="2023-12-31"
          activeLayers={activeLayers}
          showPoints={showPoints}
          registerMap={registerMap}
        />
        <SnapshotPanel
          stampClass="bg-red-600/90"
          stampLabel="● Atual · jan–dez 2024 · Real time"
          startDate="2024-01-01"
          endDate="2024-12-31"
          activeLayers={activeLayers}
          showPoints={showPoints}
          registerMap={registerMap}
        />
      </div>

      {/* Acompanhamento panel */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4.5 shadow-sm">
        <div className="mb-1.5 flex items-center justify-between">
          <div>
            <div className="text-[15px] font-bold text-slate-900">Acompanhamento</div>
            <div className="mt-0.5 text-[12px] text-slate-600">
              Lapa-Centro · AISP 5 · semana 13–19 mai
            </div>
          </div>
          <div className="rounded-full bg-green-100 px-2.5 py-1 text-[12px] font-bold text-green-700">
            ✓ Melhora
          </div>
        </div>

        <SectionTitle>Resultados</SectionTitle>
        <div className="grid grid-cols-2 gap-2.5">
          {DELTAS.map((d) => (
            <div
              key={d.label}
              className="rounded-xl border border-slate-200 bg-slate-50 p-3"
            >
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                {d.label}
              </div>
              <div className="mt-1 flex items-baseline gap-1.5">
                <span
                  className={
                    "font-mono text-2xl font-bold " +
                    (d.positive ? "text-green-600" : "text-red-600")
                  }
                >
                  {d.value}
                </span>
                <span
                  className={
                    "text-sm font-bold " +
                    (d.positive ? "text-green-600" : "text-red-600")
                  }
                >
                  {d.trend === "up" ? "↑" : "↓"}
                </span>
              </div>
              <div className="mt-1 text-[11px] text-slate-400">{d.prev}</div>
            </div>
          ))}
        </div>

        <SectionTitle>Ações executadas</SectionTitle>
        <div className="flex flex-col gap-2">
          {CHECKLIST.map((c) => (
            <div
              key={c.label}
              className="flex items-center gap-2.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-[12.5px]"
            >
              <div
                className={
                  "grid h-[18px] w-[18px] flex-shrink-0 place-items-center rounded-md border-[1.5px] " +
                  (c.done
                    ? "border-green-600 bg-green-600"
                    : "border-slate-300 bg-white")
                }
              >
                {c.done && (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                    <path d="m5 12 5 5L20 7" />
                  </svg>
                )}
              </div>
              <span
                className={
                  "flex-1 " + (c.done ? "text-slate-600 line-through" : "text-slate-900")
                }
              >
                {c.label}
              </span>
              <span className="text-[11px] text-slate-400">{c.by}</span>
            </div>
          ))}
        </div>

        <div className="mt-3.5 border-t border-slate-200 pt-3.5">
          <SectionTitle>Marcos da semana</SectionTitle>
          <div className="flex flex-col">
            {TIMELINE.map((t, i) => (
              <div
                key={t.date}
                className={
                  "grid grid-cols-[80px_1fr] items-center gap-3 py-2 text-[12.5px] " +
                  (i < TIMELINE.length - 1 ? "border-b border-dashed border-slate-200" : "")
                }
              >
                <span className="font-mono text-[11px] font-semibold text-slate-400">
                  {t.date}
                </span>
                <div className="text-slate-600">{t.text}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function SnapshotPanel({
  stampClass,
  stampLabel,
  startDate,
  endDate,
  activeLayers,
  showPoints,
  registerMap,
}: {
  stampClass: string
  stampLabel: string
  startDate: string
  endDate: string
  activeLayers: ReadonlySet<MapLayer>
  showPoints: boolean
  registerMap: (m: MaplibreMap) => void | (() => void)
}) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-b from-blue-50 to-blue-100">
      <MapCanvas initialView={SNAPSHOT_VIEW}>
        <MapRegister registerMap={registerMap} />
        {activeLayers.has("h3") && (
          <H3Layer startDate={startDate} endDate={endDate} />
        )}
        {activeLayers.has("areas") && (
          <AreasLayer startDate={startDate} endDate={endDate} />
        )}
        {showPoints && (
          <OcorrenciasLayer startDate={startDate} endDate={endDate} />
        )}
      </MapCanvas>
      <div
        className={
          "pointer-events-none absolute left-2.5 top-2.5 z-10 rounded-md px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-white " +
          stampClass
        }
      >
        {stampLabel}
      </div>
    </div>
  )
}

function MapRegister({
  registerMap,
}: {
  registerMap: (m: MaplibreMap) => void | (() => void)
}) {
  const map = useMap()
  useEffect(() => {
    const cleanup = registerMap(map)
    return typeof cleanup === "function" ? cleanup : undefined
  }, [map, registerMap])
  return null
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-2 mt-3.5 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-400">
      {children}
    </div>
  )
}
