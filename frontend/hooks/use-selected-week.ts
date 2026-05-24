"use client"

import { useCallback } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"

import type { Week } from "@/lib/iso-week"

export function useSelectedWeek(weeks: Week[]): {
  selectedKey: string
  selectWeek: (key: string) => void
} {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const defaultKey = weeks[weeks.length - 1].key
  const urlWeek = searchParams.get("week")
  const selectedKey =
    urlWeek && weeks.some((w) => w.key === urlWeek) ? urlWeek : defaultKey

  const selectWeek = useCallback(
    (key: string) => {
      const params = new URLSearchParams(window.location.search)
      params.set("week", key)
      router.replace(`${pathname}?${params.toString()}`, { scroll: false })
    },
    [pathname, router],
  )

  return { selectedKey, selectWeek }
}
