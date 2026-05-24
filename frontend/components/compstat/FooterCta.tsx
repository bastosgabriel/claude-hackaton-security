"use client"

type Props = {
  selectedCount: number
  agentsAllocated: number
  agentsAvailable: number
  onExport?: () => void
  onPrioritize: () => void
}

export function FooterCta({
  selectedCount,
  agentsAllocated,
  agentsAvailable,
  onExport,
  onPrioritize,
}: Props) {
  return (
    <div className="sticky bottom-0 z-10 -mx-7 flex items-center justify-between border-t border-slate-200 bg-white px-7 py-3.5 shadow-[0_-4px_20px_rgba(15,23,42,.05)]">
      <div className="text-[13px] text-slate-600">
        <strong className="font-bold text-slate-900">{selectedCount}</strong> regiões
        selecionadas · <span>{agentsAllocated}</span> agentes alocados de{" "}
        {agentsAvailable} disponíveis
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onExport}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-transparent px-4 py-2.5 text-[13px] font-semibold text-slate-600 transition-colors hover:bg-slate-50"
        >
          Exportar relatório
        </button>
        <button
          type="button"
          onClick={onPrioritize}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-700 px-4 py-2.5 text-[13px] font-semibold text-white transition-colors hover:bg-blue-800 active:translate-y-px"
        >
          Priorizar lista
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="m9 6 6 6-6 6" />
          </svg>
        </button>
      </div>
    </div>
  )
}
