"use client"

import { formatWeekRange, type Week } from "@/lib/iso-week"

type Props = {
  weeks: Week[]
  selectedKey: string
  onSelect: (key: string) => void
}

export function WeekBar({ weeks, selectedKey, onSelect }: Props) {
  const currentKey = weeks[weeks.length - 1].key

  return (
    <div className="pointer-events-auto absolute inset-x-0 bottom-0 z-10 border-t border-zinc-200 bg-white/95 backdrop-blur">
      <div className="flex items-stretch justify-center gap-1 overflow-x-auto px-3 py-2">
        {weeks.map((week) => {
          const isSelected = week.key === selectedKey
          const isCurrent = week.key === currentKey
          return (
            <button
              key={week.key}
              type="button"
              onClick={() => onSelect(week.key)}
              className={
                "flex w-24 shrink-0 flex-col items-center justify-center rounded-md border px-3 py-1.5 text-xs transition-colors " +
                (isSelected
                  ? "border-zinc-900 bg-zinc-900 text-white"
                  : "border-zinc-200 bg-white text-zinc-700 hover:border-zinc-400 hover:bg-zinc-50")
              }
            >
              <span className="font-semibold leading-tight">
                W{week.isoWeek}
                {isCurrent && (
                  <span
                    className={
                      "ml-1 rounded px-1 py-px text-[9px] font-medium " +
                      (isSelected ? "bg-white/20" : "bg-zinc-200 text-zinc-700")
                    }
                  >
                    now
                  </span>
                )}
              </span>
              <span
                className={
                  "mt-0.5 text-[10px] leading-tight " +
                  (isSelected ? "text-white/80" : "text-zinc-500")
                }
              >
                {formatWeekRange(week.start)}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
