"use client"

type Props = {
  show: boolean
  message: string
}

export function Toast({ show, message }: Props) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={
        "fixed bottom-24 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2.5 rounded-xl bg-[#0a1729] px-4 py-3 text-[13px] font-semibold text-white shadow-lg transition-all duration-300 " +
        (show
          ? "translate-y-0 opacity-100"
          : "pointer-events-none translate-y-5 opacity-0")
      }
    >
      <span className="grid h-5 w-5 place-items-center rounded-full bg-green-600">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3">
          <path d="m5 12 5 5L20 7" />
        </svg>
      </span>
      <span>{message}</span>
    </div>
  )
}
