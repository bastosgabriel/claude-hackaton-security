export function TopBar() {
  return (
    <header className="flex items-center justify-between border-b border-slate-800 bg-[#0a1729] px-7 py-3.5 text-white">
      <div className="flex items-center gap-3">
        <img
          src="/prefeitura-rio.svg"
          alt="Prefeitura do Rio"
          className="h-8 w-auto"
        />
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
            CompStat Rio
          </div>
          <div className="text-[15px] font-bold tracking-tight">
            Diagnóstico Territorial
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3.5">
        <div className="flex w-[280px] items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-[13px] text-slate-300">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="opacity-60"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            placeholder="Buscar região, AP ou batalhão…"
            className="flex-1 border-0 bg-transparent text-white outline-none placeholder:text-slate-400"
          />
        </div>
        <div className="flex items-center gap-2.5 rounded-full bg-white/5 py-1 pl-1 pr-3 text-[13px]">
          <div className="grid h-7 w-7 place-items-center rounded-full bg-blue-700 text-xs font-bold">
            MN
          </div>
          <span>Maria N. · Analista</span>
        </div>
      </div>
    </header>
  );
}
