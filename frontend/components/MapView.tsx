"use client"

import { useMemo } from "react";

import { buildWeeks } from "@/lib/iso-week"
import { WEEK_COUNT } from "@/lib/map-config"
import { useIsClient } from "@/hooks/use-is-client";
import { useSelectedWeek } from "@/hooks/use-selected-week"
import { useViewportUrl } from "@/hooks/use-viewport-url"

import { AreasLayer } from "@/components/map/AreasLayer"
import { H3Layer } from "@/components/map/H3Layer"
import { MapCanvas } from "@/components/map/MapCanvas"
import { WeekBar } from "@/components/map/WeekBar"

export function MapView() {
  const isClient = useIsClient();
  const { initialView, writeViewportToUrl } = useViewportUrl()
  const weeks = useMemo(() => buildWeeks(new Date(), WEEK_COUNT), [])
  const { selectedKey, selectWeek } = useSelectedWeek(weeks)

  return (
    <div className="relative h-screen w-full">
      <MapCanvas initialView={initialView} onMoveEnd={writeViewportToUrl}>
        <H3Layer />
        <AreasLayer />
      </MapCanvas>
      {isClient && (
        <WeekBar
          weeks={weeks}
          selectedKey={selectedKey}
          onSelect={selectWeek}
        />
      )}
    </div>
  );
}
