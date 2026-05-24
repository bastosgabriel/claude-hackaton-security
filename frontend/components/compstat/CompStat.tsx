"use client"

import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"

import { useIsClient } from "@/hooks/use-is-client"
import { fetchRegions, type RegionsResponse } from "@/lib/api/regions"

import { AvaliacaoView } from "./AvaliacaoView"
import { DiagnosticoView } from "./DiagnosticoView"
import { FooterCta } from "./FooterCta"
import { PageHeader } from "./PageHeader"
import { Toast } from "./Toast"
import { TopBar } from "./TopBar"
import { WeekTabs, type WeekTab, type WeekView } from "./WeekTabs"

const TABS: WeekTab[] = [
  {
    view: "avaliacao",
    label: "Avaliação",
    range: "13 – 19 mai",
    status: (
      <>
        <Tag className="bg-cyan-100 text-cyan-700">● Avaliação</Tag>
        <span>· 6 ações executadas</span>
      </>
    ),
  },
  {
    view: "prereuniao",
    label: "Pré-reunião",
    range: "27 mai – 2 jun",
    status: (
      <>
        <Tag className="bg-blue-100 text-blue-700">● Diagnóstico</Tag>
        <span>· pronto para priorização</span>
      </>
    ),
  },
]

const START_DATE = "2020-01-01"
const END_DATE = "2026-01-01"

export function CompStat() {
  const isClient = useIsClient()
  const [view, setView] = useState<WeekView>("avaliacao")
  const [selected, setSelected] = useState<ReadonlySet<number>>(() => new Set())
  const [toastShown, setToastShown] = useState(false)

  const regionsQuery = useQuery<RegionsResponse>({
    queryKey: ["regions", START_DATE, END_DATE],
    queryFn: ({ signal }) => fetchRegions(START_DATE, END_DATE, signal),
  })
  const regions = regionsQuery.data?.results ?? []

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const agentsAllocated = useMemo(
    () =>
      regions
        .filter((r) => selected.has(r.id))
        .reduce(
          (sum, r) => sum + r.actions.reduce((s, a) => s + a.agents, 0),
          0,
        ),
    [regions, selected],
  )

  const handlePrioritize = () => {
    if (selected.size === 0 && regions.length > 0) {
      setSelected(new Set(regions.slice(0, 3).map((r) => r.id)))
    }
    setToastShown(true)
    window.setTimeout(() => setToastShown(false), 2400)
    window.setTimeout(() => setView("avaliacao"), 1200)
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <TopBar />
      <main className="px-7 pb-20 pt-6">
        <PageHeader />
        {isClient && (
          <WeekTabs tabs={TABS} selected={view} onSelect={setView} />
        )}

        {view === "prereuniao" && (
          <DiagnosticoView
            regions={regions}
            isLoading={regionsQuery.isLoading}
            selected={selected}
            onToggleSelect={toggleSelect}
            startDate={START_DATE}
            endDate={END_DATE}
          />
        )}
        {view === "avaliacao" && <AvaliacaoView />}

        {view === "prereuniao" && (
          <FooterCta
            selectedCount={selected.size}
            agentsAllocated={agentsAllocated}
            agentsAvailable={600}
            onPrioritize={handlePrioritize}
          />
        )}
      </main>
      <Toast
        show={toastShown}
        message="Priorização confirmada · acompanhe em Semana atual"
      />
    </div>
  );
}

function Tag({
  className,
  children,
}: {
  className?: string
  children: React.ReactNode
}) {
  return (
    <span
      className={
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-semibold " +
        (className ?? "")
      }
    >
      {children}
    </span>
  )
}
