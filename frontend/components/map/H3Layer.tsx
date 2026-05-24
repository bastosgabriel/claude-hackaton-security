"use client"

import { useEffect } from "react"
import * as h3 from "h3-js";
import type { GeoJSONSource } from "maplibre-gl"

import { buildHexGeoJSON, zoomToResolution } from "@/lib/h3-grid"

import { useMap } from "./map-context"
import { useOcorrenciasInViewport } from "./use-ocorrencias";

const SOURCE_ID = "h3-hex-source"
const FILL_LAYER_ID = "h3-hex-fill"
const LINE_LAYER_ID = "h3-hex-line"

type Props = {
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
};

// Absolute count thresholds: same color means the same number of points,
// regardless of viewport / zoom.
const COUNT_COLOR: unknown[] = [
  "step",
  ["coalesce", ["get", "count"], 0],
  "rgba(0,0,0,0)",
  1, "#16a34a",
  5, "#ca8a04",
  15, "#ea580c",
  30, "#dc2626",
];

export function H3Layer({ startDate, endDate }: Props) {
  const map = useMap();
  const query = useOcorrenciasInViewport(startDate, endDate);
  const results = query.data?.results;

  useEffect(() => {
    const refresh = () => {
      const resolution = zoomToResolution(map.getZoom());
      const data = buildHexGeoJSON(map, resolution);

      const counts = new Map<string, number>();
      if (results) {
        for (const o of results) {
          const cell = h3.latLngToCell(o.lat, o.lng, resolution);
          counts.set(cell, (counts.get(cell) ?? 0) + 1);
        }
      }
      for (const f of data.features) {
        const c = counts.get(f.properties.h3) ?? 0;
        (f.properties as { h3: string; count: number }).count = c;
      }

      const source = map.getSource(SOURCE_ID) as GeoJSONSource | undefined;
      if (source) {
        source.setData(data);
        return;
      }
      map.addSource(SOURCE_ID, { type: "geojson", data });
      map.addLayer({
        id: FILL_LAYER_ID,
        type: "fill",
        source: SOURCE_ID,
        paint: {
          "fill-color": COUNT_COLOR,
          "fill-opacity": 0.3,
        },
      });
      map.addLayer({
        id: LINE_LAYER_ID,
        type: "line",
        source: SOURCE_ID,
        paint: {
          "line-color": "#0f172a",
          "line-width": 0.5,
          "line-opacity": 0.35,
        },
      });
    };

    refresh();
    map.on("moveend", refresh);

    return () => {
      map.off("moveend", refresh);
    };
  }, [map, results]);

  useEffect(() => {
    return () => {
      try {
        if (map.getLayer(LINE_LAYER_ID)) map.removeLayer(LINE_LAYER_ID);
        if (map.getLayer(FILL_LAYER_ID)) map.removeLayer(FILL_LAYER_ID);
        if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
      } catch {
        // Map was already removed (style is gone). Nothing to clean up.
      }
    };
  }, [map]);

  return null;
}
