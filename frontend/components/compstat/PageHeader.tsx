export function PageHeader() {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="mb-1 text-[12px] font-medium uppercase tracking-[0.12em] text-slate-400">
          Painel · Análise semanal
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Diagnóstico Semanal
        </h1>
      </div>
      <div className="flex items-center gap-2.5 text-[13px] text-slate-600">
        <Pill>
          <Dot color="bg-green-600" /> 22 AISP integradas
        </Pill>
        <Pill>
          <Dot color="bg-red-500" pulse /> Dados atualizados há 4 min
        </Pill>
        <Pill>600 agentes disponíveis</Pill>
      </div>
    </div>
  )
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <div className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[12px] font-semibold text-slate-600">
      {children}
    </div>
  )
}

function Dot({ color, pulse }: { color: string; pulse?: boolean }) {
  return (
    <span
      className={
        "inline-block h-1.5 w-1.5 rounded-full " +
        color +
        (pulse ? " animate-pulse ring-2 ring-red-500/20" : "")
      }
    />
  )
}
