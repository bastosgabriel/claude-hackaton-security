"use client"

export type WeekView = "avaliacao" | "atual" | "prereuniao"

export type WeekTab = {
  view: WeekView
  label: string
  range: string
  status: React.ReactNode
}

type Props = {
  tabs: WeekTab[]
  selected: WeekView
  onSelect: (view: WeekView) => void
}

export function WeekTabs({ tabs, selected, onSelect }: Props) {
  return (
    <div className="mb-5 grid grid-cols-3 gap-3">
      {tabs.map((tab) => {
        const isActive = tab.view === selected
        return (
          <button
            key={tab.view}
            type="button"
            onClick={() => onSelect(tab.view)}
            className={
              "relative flex flex-col gap-1.5 overflow-hidden rounded-2xl border px-4 py-3.5 text-left transition-all " +
              (isActive
                ? "border-blue-700 shadow-[0_0_0_3px_rgba(29,78,216,.12)]"
                : "border-slate-200 hover:border-slate-300")
            }
          >
            {isActive && (
              <span className="absolute left-0 top-0 bottom-0 w-[3px] bg-blue-700" />
            )}
            <span
              className={
                "text-[11px] font-bold uppercase tracking-[0.14em] " +
                (isActive ? "text-blue-700" : "text-slate-400")
              }
            >
              {tab.label}
            </span>
            <span className="text-[15px] font-bold text-slate-900">{tab.range}</span>
            <span className="flex items-center gap-1.5 text-[12px] text-slate-600">
              {tab.status}
            </span>
          </button>
        )
      })}
    </div>
  )
}
