import { Suspense } from "react"

import { CompStat } from "@/components/compstat/CompStat"

export default function Home() {
  return (
    <Suspense fallback={null}>
      <CompStat />
    </Suspense>
  )
}
