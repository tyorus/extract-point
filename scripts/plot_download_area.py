#!/usr/bin/env python3
"""Plot the ERA5 download area on a Cartopy map (default: 20×20, Natuna Sea)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from download_era5 import (  # noqa: E402
    DEFAULT_GRID_POINTS,
    DEFAULT_LAT,
    DEFAULT_LON,
    GRID_SPACING_DEG,
    area_box,
    buffer_for_grid,
    grid_shape,
)

DEFAULT_OUTPUT = Path("data/download_area.png")


def grid_coords(area: list[float]) -> tuple[np.ndarray, np.ndarray]:
    """Return 1D lat/lon coordinates for grid cell centers in the download box."""
    north, west, south, east = area
    n_lat, n_lon = grid_shape(area)
    lats = south + np.arange(n_lat) * GRID_SPACING_DEG
    lons = west + np.arange(n_lon) * GRID_SPACING_DEG
    return lats, lons


def plot_area(
    *,
    lat: float,
    lon: float,
    grid_points: int,
    output: Path,
    show: bool,
) -> Path:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    buffer = buffer_for_grid(grid_points)
    area = area_box(lat, lon, buffer)
    north, west, south, east = area
    n_lat, n_lon = grid_shape(area)
    lats, lons = grid_coords(area)
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    margin = 1.5
    geo = ccrs.PlateCarree()
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(1, 1, 1, projection=geo)
    ax.set_extent(
        [west - margin, east + margin, south - margin, north + margin],
        crs=geo,
    )

    ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor="#dbeafe", zorder=0)
    ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#f5f5f4", zorder=1)
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.8, edgecolor="#44403c", zorder=2)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4, edgecolor="#78716c", linestyle=":", zorder=2)

    gl = ax.gridlines(draw_labels=True, linewidth=0.4, color="#94a3b8", alpha=0.7, linestyle="--")
    gl.top_labels = False
    gl.right_labels = False

    box_lons = [west, east, east, west, west]
    box_lats = [south, south, north, north, south]
    ax.plot(
        box_lons,
        box_lats,
        color="#2563eb",
        lw=2.2,
        transform=geo,
        zorder=4,
        label=f"CDS area ({north:.2f}°N–{south:.2f}°N, {west:.2f}°E–{east:.2f}°E)",
    )

    ax.scatter(
        lon_grid,
        lat_grid,
        s=14,
        c="#93c5fd",
        edgecolors="#1d4ed8",
        linewidths=0.35,
        transform=geo,
        zorder=5,
        label=f"ERA5 grid ({n_lat}×{n_lon} @ {GRID_SPACING_DEG}°)",
    )

    ax.scatter(
        [lon],
        [lat],
        s=160,
        c="#dc2626",
        marker="*",
        edgecolors="white",
        linewidths=0.8,
        transform=geo,
        zorder=6,
        label=f"Platform ({lat}°N, {lon}°E)",
    )

    ax.set_title("ERA5 download domain — Natuna Sea sample", fontsize=13, pad=12)
    ax.legend(loc="lower left", fontsize=8, framealpha=0.92)

    note = (
        f"Box half-width: {buffer:.2f}°  |  "
        f"Span: {north - south:.1f}° × {east - west:.1f}°  |  "
        f"{grid_points}×{grid_points} cells"
    )
    fig.text(0.5, 0.02, note, ha="center", fontsize=9, color="#374151")

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(output, dpi=150, bbox_inches="tight")
    print(f"Saved: {output}")

    if show:
        plt.show()
    else:
        plt.close(fig)

    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot ERA5 download area on a Cartopy map.")
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT)
    parser.add_argument("--lon", type=float, default=DEFAULT_LON)
    parser.add_argument("--grid", type=int, default=DEFAULT_GRID_POINTS)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--show", action="store_true", help="Open interactive window")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plot_area(
        lat=args.lat,
        lon=args.lon,
        grid_points=args.grid,
        output=args.output,
        show=args.show,
    )


if __name__ == "__main__":
    main()
