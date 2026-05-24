"""Visualize and summarize the `sh_area_forca` shapefile.

Loads the municipal "áreas de força" polygons, prints each one in a
structured form (matching it to its intelligence report in `relints/`),
plots them on a map, and prints an aggregate summary.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt

DATA_DIR = Path(__file__).parent / "data"
SHP_PATH = DATA_DIR / "sh_area_forca" / "areas_forca_municipal.shp"
RELINTS_DIR = DATA_DIR / "relints"
OUTPUT_MAP = Path(__file__).parent / "areas_forca_map.png"


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def match_relint(area_name: str, relint_files: list[Path]) -> Path | None:
    tokens = [t for t in slugify(area_name).split("_") if len(t) >= 3]
    threshold = 2 if len(tokens) >= 3 else 1
    best, best_score = None, 0
    for f in relint_files:
        fslug = slugify(f.stem)
        score = sum(1 for t in tokens if t in fslug)
        if score > best_score:
            best, best_score = f, score
    return best if best_score >= threshold else None


def format_bbox(bounds: tuple[float, float, float, float]) -> str:
    minx, miny, maxx, maxy = bounds
    return f"lon [{minx:.5f}, {maxx:.5f}]  lat [{miny:.5f}, {maxy:.5f}]"


def main() -> None:
    gdf = gpd.read_file(SHP_PATH)
    # Project to a metric CRS (UTM 23S, EPSG:31983) for area in km².
    gdf_m = gdf.to_crs(epsg=31983)
    gdf = gdf.assign(
        area_km2=gdf_m.area / 1_000_000,
        perimeter_km=gdf_m.length / 1_000,
        centroid=gdf_m.centroid.to_crs(epsg=4326),
    )

    relint_files = sorted(RELINTS_DIR.glob("*.docx"))

    print("=" * 78)
    print(f"ÁREAS DE FORÇA MUNICIPAL — {SHP_PATH.relative_to(DATA_DIR.parent)}")
    print("=" * 78)
    print(f"CRS: {gdf.crs} | Records: {len(gdf)} | Geometry: {gdf.geom_type.iloc[0]}")
    print(f"Schema: {[c for c in gdf.columns if c != 'geometry']}")
    print()

    for i, row in gdf.sort_values("fid").reset_index(drop=True).iterrows():
        relint = match_relint(row["nome_subar"], relint_files)
        c = row["centroid"]
        print(f"[{i + 1}] fid={int(row['fid']):>2}  {row['nome_subar']}")
        print(f"     area       : {row['area_km2']:.3f} km²")
        print(f"     perimeter  : {row['perimeter_km']:.3f} km")
        print(f"     centroid   : ({c.y:.5f}, {c.x:.5f})")
        print(f"     bbox       : {format_bbox(row.geometry.bounds)}")
        print(f"     relint     : {relint.name if relint else '— (no match)'}")
        print()

    areas = gdf["area_km2"]
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"Total areas       : {len(gdf)}")
    print(f"Total coverage    : {areas.sum():.3f} km²")
    print(f"Mean area         : {areas.mean():.3f} km²")
    print(f"Median area       : {areas.median():.3f} km²")
    print(f"Min / Max area    : {areas.min():.3f} / {areas.max():.3f} km²")
    print(f"Overall bbox      : {format_bbox(tuple(gdf.total_bounds))}")
    print(f"Largest area      : {gdf.loc[areas.idxmax(), 'nome_subar']}")
    print(f"Smallest area     : {gdf.loc[areas.idxmin(), 'nome_subar']}")
    print(f"Relint files found: {len(relint_files)}")
    matched = sum(1 for _, r in gdf.iterrows() if match_relint(r["nome_subar"], relint_files))
    print(f"Areas matched RI  : {matched}/{len(gdf)}")
    print()

    fig, ax = plt.subplots(figsize=(11, 9))
    gdf.plot(ax=ax, edgecolor="#b22222", facecolor="#ffcccc", alpha=0.6, linewidth=1.5)
    for _, row in gdf.iterrows():
        c = row["centroid"]
        label = row["nome_subar"]
        if len(label) > 32:
            label = label[:30] + "…"
        ax.annotate(
            f"fid {int(row['fid'])}\n{label}",
            xy=(c.x, c.y),
            ha="center",
            va="center",
            fontsize=7,
            color="#222",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#888", alpha=0.85),
        )
    ax.set_title("Áreas de Força Municipal — Rio de Janeiro", fontsize=13)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, linestyle=":", alpha=0.4)
    fig.tight_layout()
    fig.savefig(OUTPUT_MAP, dpi=140)
    print(f"Map saved to: {OUTPUT_MAP.relative_to(Path(__file__).parent)}")


if __name__ == "__main__":
    main()
