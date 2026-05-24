"use client"

import {
  LEVEL_LABEL,
  type Region,
  type RegionActionIcon,
  type RegionLevel,
} from "@/lib/compstat/regions"

type Props = {
  region: Region
  rank: number
  isOpen: boolean
  isSelected: boolean
  onToggleOpen: (id: string) => void
  onToggleSelect: (id: string) => void
}

const SCORE_NUM_CLASS: Record<RegionLevel, string> = {
  critico: "text-red-600",
  alto: "text-orange-600",
  medio: "text-yellow-700",
  baixo: "text-green-600",
}

const SCORE_LABEL_CLASS: Record<RegionLevel, string> = {
  critico: "bg-red-100 text-red-700",
  alto: "bg-orange-100 text-orange-700",
  medio: "bg-yellow-100 text-yellow-800",
  baixo: "bg-green-100 text-green-700",
}

const RANK_CLASS: Record<number, string> = {
  1: "bg-red-600 text-white border-red-600",
  2: "bg-orange-500 text-white border-orange-500",
  3: "bg-orange-500 text-white border-orange-500",
}

const ACTION_ICO_CLASS: Record<RegionActionIcon, string> = {
  amb: "bg-green-100 text-green-700",
  pol: "bg-blue-100 text-blue-700",
  int: "bg-yellow-100 text-yellow-700",
}

export function RegionItem({
  region,
  rank,
  isOpen,
  isSelected,
  onToggleOpen,
  onToggleSelect,
}: Props) {
  return (
    <div
      className={
        "mb-2 overflow-hidden rounded-xl border bg-white transition-all " +
        (isOpen
          ? "border-blue-700 shadow-[0_0_0_3px_rgba(29,78,216,.08)]"
          : "border-slate-200 hover:border-slate-300")
      }
    >
      <button
        type="button"
        onClick={() => onToggleOpen(region.id)}
        className="grid w-full cursor-pointer grid-cols-[34px_1fr_auto] items-center gap-3 px-3.5 py-3 text-left"
      >
        <div
          className={
            "grid h-7 w-7 place-items-center rounded-lg border text-[13px] font-bold " +
            (RANK_CLASS[rank] ?? "border-slate-200 bg-slate-50 text-slate-600")
          }
        >
          {rank}
        </div>
        <div>
          <div className="text-sm font-semibold text-slate-900">{region.name}</div>
          <div className="mt-0.5 flex flex-wrap gap-2.5 text-[12px] text-slate-600">
            <span>{region.aisp}</span>
            <span>•</span>
            <span>{region.roubos} roubos</span>
            <span>•</span>
            <span>{region.denuncias} denúncias</span>
          </div>
        </div>
        <div className="flex min-w-[64px] flex-col items-end gap-0.5">
          <span className={"font-mono text-lg font-bold leading-none " + SCORE_NUM_CLASS[region.level]}>
            {region.score}
          </span>
          <span
            className={
              "rounded px-1.5 py-px text-[10px] font-semibold uppercase tracking-wider " +
              SCORE_LABEL_CLASS[region.level]
            }
          >
            {LEVEL_LABEL[region.level]}
          </span>
        </div>
      </button>

      {isOpen && (
        <div className="border-t border-slate-200 bg-slate-50 px-3.5 pb-3.5">
          <SectionTitle>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4M12 16h.01" />
            </svg>
            Por que esse score?
          </SectionTitle>
          <div
            className="rounded-lg border border-slate-200 bg-white px-3.5 py-3 text-[12.5px] leading-relaxed text-slate-600 [&_strong]:font-semibold [&_strong]:text-slate-900"
            dangerouslySetInnerHTML={{ __html: region.narrative }}
          />

          <SectionTitle>Critérios ({region.criteria.length})</SectionTitle>
          <div className="flex flex-col gap-2">
            {region.criteria.map((c) => (
              <div
                key={c.label}
                className="grid grid-cols-[1fr_80px_38px] items-center gap-2.5 text-[12.5px]"
              >
                <div className="flex items-center gap-2 text-slate-900">
                  <span className="grid h-[22px] w-[22px] place-items-center rounded-md border border-slate-200 bg-white">
                    {c.icon}
                  </span>
                  {c.label}
                </div>
                <div className="h-1.5 overflow-hidden rounded-full border border-slate-200 bg-white">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${c.pct}%`, background: c.color }}
                  />
                </div>
                <div className="text-right font-mono text-[12px] font-bold text-slate-600">
                  {c.val}
                </div>
              </div>
            ))}
          </div>

          <SectionTitle>Ações sugeridas ({region.actions.length})</SectionTitle>
          <div className="flex flex-col gap-1.5">
            {region.actions.map((a) => (
              <div
                key={a.title}
                className="flex items-start gap-2.5 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-[12.5px]"
              >
                <div
                  className={
                    "grid h-7 w-7 flex-shrink-0 place-items-center rounded-md text-base " +
                    ACTION_ICO_CLASS[a.ico]
                  }
                >
                  {a.icon}
                </div>
                <div className="flex-1 text-slate-900">
                  <strong className="mb-0.5 block font-semibold">{a.title}</strong>
                  <span className="text-slate-600">{a.desc}</span>
                </div>
                <div className="whitespace-nowrap text-right text-[11px] font-semibold text-slate-400">
                  {a.cost}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-3.5 flex gap-2">
            <button
              type="button"
              className="rounded-lg border border-slate-200 px-3 py-2 text-[12px] font-semibold text-slate-600 hover:bg-slate-100"
            >
              Análise histórica
            </button>
            <button
              type="button"
              className="rounded-lg border border-slate-200 px-3 py-2 text-[12px] font-semibold text-slate-600 hover:bg-slate-100"
            >
              Ver RELINTs
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onToggleSelect(region.id)
              }}
              className={
                "ml-auto rounded-lg px-3 py-2 text-[12px] font-semibold transition-colors " +
                (isSelected
                  ? "border border-slate-200 bg-white text-slate-600 hover:bg-slate-100"
                  : "bg-blue-700 text-white hover:bg-blue-800")
              }
            >
              {isSelected ? "✓ Selecionada" : "Selecionar"}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-2 mt-3.5 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-400">
      {children}
    </div>
  )
}
