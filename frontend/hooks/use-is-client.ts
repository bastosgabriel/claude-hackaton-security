"use client"

import { useEffect, useState } from "react"

/**
 * Returns `false` on the server (and during the first client render that
 * hydrates the server HTML) and flips to `true` after mount. Use to gate
 * content that depends on browser-only state (`window`, `Date.now()`,
 * locale-sensitive `Intl` output) and would otherwise cause hydration
 * mismatches.
 */
export function useIsClient(): boolean {
  const [isClient, setIsClient] = useState(false)
  useEffect(() => {
    setIsClient(true)
  }, [])
  return isClient
}
