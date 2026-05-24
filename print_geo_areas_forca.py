"""Dump the raw geospatial content of `sh_area_forca/areas_forca_municipal.shp`.

Prints each feature's geometry (polygon ring coordinates + counts), then a
summary of the layer (CRS, feature count, geometry types, vertex stats,
bounding box, total area in km²).
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon

SHP_PATH = Path(__file__).parent / "data" / "sh_area_forca" / "areas_forca_municipal.shp"
MAX_COORDS_PREVIEW = 4  # how many coordinates from each ring to print


def fmt_coord(c: tuple[float, float]) -> str:
    return f"({c[0]:.6f}, {c[1]:.6f})"


def preview_ring(coords: list[tuple[float, float]]) -> str:
    if len(coords) <= MAX_COORDS_PREVIEW * 2:
        return ", ".join(fmt_coord(c) for c in coords)
    head = ", ".join(fmt_coord(c) for c in coords[:MAX_COORDS_PREVIEW])
    tail = ", ".join(fmt_coord(c) for c in coords[-MAX_COORDS_PREVIEW:])
    return f"{head}, … [{len(coords) - 2 * MAX_COORDS_PREVIEW} more], {tail}"


def print_polygon(poly: Polygon, indent: str = "    ") -> int:
    ext = list(poly.exterior.coords)
    print(f"{indent}exterior ring: {len(ext)} vertices")
    print(f"{indent}  coords: {preview_ring(ext)}")
    total = len(ext)
    for j, interior in enumerate(poly.interiors):
        ring = list(interior.coords)
        total += len(ring)
        print(f"{indent}interior #{j}: {len(ring)} vertices")
        print(f"{indent}  coords: {preview_ring(ring)}")
    return total


def main() -> None:
    gdf = gpd.read_file(SHP_PATH)
    gdf_m = gdf.to_crs(epsg=31983)  # SIRGAS 2000 / UTM 23S → metric area

    print("=" * 78)
    print(f"FILE  : {SHP_PATH}")
    print(f"CRS   : {gdf.crs}")
    print(f"COUNT : {len(gdf)} feature(s)")
    print(f"GTYPES: {gdf.geom_type.value_counts().to_dict()}")
    print(f"COLS  : {[c for c in gdf.columns if c != 'geometry']}")
    print("=" * 78)

    vertex_counts: list[int] = []
    for i, row in gdf.sort_values("fid").reset_index(drop=True).iterrows():
        geom = row.geometry
        area_km2 = gdf_m.geometry.iloc[gdf.index[i]].area / 1_000_000 if False else (
            gdf_m.to_crs(epsg=31983).geometry.iloc[i].area / 1_000_000
        )
        # simpler: recompute from gdf_m aligned by index
        area_km2 = gdf_m.geometry.iloc[i].area / 1_000_000
        print(f"\n[Feature {i + 1}] fid={int(row['fid'])}")
        print(f"  nome_subar : {row['nome_subar']}")
        print(f"  geom_type  : {geom.geom_type}")
        print(f"  is_valid   : {geom.is_valid}")
        print(f"  bounds     : {tuple(round(v, 6) for v in geom.bounds)}")
        print(f"  area       : {area_km2:.4f} km²")
        if isinstance(geom, MultiPolygon):
            print(f"  parts      : {len(geom.geoms)}")
            v = 0
            for k, part in enumerate(geom.geoms):
                print(f"  Polygon part #{k}:")
                v += print_polygon(part, indent="      ")
        elif isinstance(geom, Polygon):
            v = print_polygon(geom)
        else:
            v = 0
            print(f"  (unhandled geometry: {geom.geom_type})")
        print(f"  total vertices: {v}")
        vertex_counts.append(v)

    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    minx, miny, maxx, maxy = gdf.total_bounds
    total_area = (gdf_m.area.sum()) / 1_000_000
    print(f"Features          : {len(gdf)}")
    geom_types = set(gdf.geom_type.unique())
    print(f"Geometry types    : {sorted(geom_types)}")
    polygon_count = int((gdf.geom_type == "Polygon").sum())
    multipoly_count = int((gdf.geom_type == "MultiPolygon").sum())
    print(f"Polygons detected : {polygon_count}")
    print(f"MultiPolygons     : {multipoly_count}")
    print(f"Total vertices    : {sum(vertex_counts)}")
    print(
        f"Vertices per feat : min={min(vertex_counts)} "
        f"max={max(vertex_counts)} mean={sum(vertex_counts) / len(vertex_counts):.1f}"
    )
    print(f"Overall bbox      : lon [{minx:.6f}, {maxx:.6f}]  lat [{miny:.6f}, {maxy:.6f}]")
    print(f"Total area        : {total_area:.4f} km²")
    print(f"All geometries valid: {bool(gdf.is_valid.all())}")

    print("\nPOLYGON VISIBILITY CHECK:")
    if polygon_count == len(gdf) and gdf.is_valid.all():
        print(f"  ✓ Yes — {polygon_count} valid Polygon geometries are present and readable.")
    else:
        print("  ✗ Issue detected: not all features are valid polygons.")


if __name__ == "__main__":
    main()
