"use client"

import { useState } from "react"

import type { Region, RegionLevel } from "@/lib/api/regions"

import { RegionItem } from "./RegionItem"

type Filter = "todas" | "critico" | "alto"

type Props = {
  regions: Region[]
  isLoading: boolean
  selected: ReadonlySet<number>
  openId: number | null
  onToggleOpen: (id: number) => void
  onToggleSelect: (id: number) => void
}

const FILTER_LEVELS: Record<Filter, RegionLevel[] | null> = {
  todas: null,
  critico: ["critico"],
  alto: ["alto"],
}

export function RegionList({
  regions,
  isLoading,
  selected,
  openId,
  onToggleOpen,
  onToggleSelect,
}: Props) {
  const [filter, setFilter] = useState<Filter>("todas")

  const visibleLevels = FILTER_LEVELS[filter]
  const filtered = visibleLevels
    ? regions.filter((r) => visibleLevels.includes(r.level))
    : regions

  return (
    <div className="flex max-h-[80vh] flex-col rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-4.5 py-3.5">
        <div>
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 6h18M3 12h18M3 18h12" />
            </svg>
            Ranking de prioridade
          </div>
          <div className="mt-0.5 text-[12px] text-slate-600">
            {regions.length} regiões · ordenadas por score
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between border-b border-slate-200 px-4.5 py-2.5 text-[12px] text-slate-600">
        <span>
          <strong className="font-bold text-slate-900">{selected.size}</strong> regiões selecionadas
        </span>
        <div className="flex items-center gap-1.5">
          {(Object.keys(FILTER_LEVELS) as Filter[]).map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setFilter(key)}
              className={
                "rounded-full border px-2.5 py-1 text-[11px] font-semibold capitalize transition-colors " +
                (filter === key
                  ? "border-[#0a1729] bg-[#0a1729] text-white"
                  : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100")
              }
            >
              {key === "todas" ? "Todas" : key === "critico" ? "Crítico" : "Alto"}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-y-auto p-2">
        {isLoading && regions.length === 0 && (
          <div className="px-4 py-8 text-center text-[12.5px] text-slate-500">
            Carregando regiões…
          </div>
        )}
        {!isLoading &&
          filtered.map((region) => (
            <RegionItem
              key={region.id}
              region={region}
              rank={regions.indexOf(region) + 1}
              isOpen={openId === region.id}
              isSelected={selected.has(region.id)}
              onToggleOpen={onToggleOpen}
              onToggleSelect={onToggleSelect}
            />
          ))}
        {!isLoading && filtered.length === 0 && (
          <div className="px-4 py-8 text-center text-[12.5px] text-slate-500">
            Nenhuma região no filtro selecionado.
          </div>
        )}
      </div>
    </div>
  )
}
