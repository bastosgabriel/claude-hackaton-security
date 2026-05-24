# reggaethon

A Next.js + TypeScript + Tailwind + shadcn/ui + MapLibre GL + OpenStreetMap + H3 starter that renders interactive H3 hexagonal grid polygons over a map.

## Stack

- **Next.js** (App Router) + **React 19** + **TypeScript**
- **Tailwind CSS v4**
- **shadcn/ui** (base-ui primitives) — `Slider` for the resolution control
- **maplibre-gl** for the map (open-source mapbox-gl fork)
- **OpenStreetMap** raster tiles (no token required)
- **h3-js** for hexagonal grid math

## Getting started

```bash
pnpm install
pnpm dev
```

Open http://localhost:3000 — no API keys needed.

## What you'll see

A MapLibre GL map served by OpenStreetMap raster tiles, centered on San Francisco, with a translucent layer of H3 hexagons covering the current viewport. Pan or zoom and the hexagons recompute. Use the slider in the top-left to change the H3 resolution (0–10).

## Key files

- `app/page.tsx` — renders the map component.
- `components/MapView.tsx` — MapLibre setup with the inline OSM style, viewport → H3 cell computation, GeoJSON layer.
- `components/ui/slider.tsx` — shadcn `Slider` (base-ui under the hood).

## A note on OSM tiles

This demo points directly at `tile.openstreetmap.org`, which is fine for development but [not allowed for production / high-volume usage](https://operations.osmfoundation.org/policies/tiles/). For production, switch to a hosted tile provider (Stadia, MapTiler, Protomaps, Cloudflare, etc.) or self-host.
