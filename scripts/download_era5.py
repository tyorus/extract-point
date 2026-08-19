#!/usr/bin/env python3
"""
Regenerate the repo sample ERA5 file via the Copernicus Climate Data Store (CDS).

The committed sample (data/era5_sample.nc) is a small slice for GitHub + Colab.
The notebook's "2.3 GB" scenario is illustrative — CDS rejects oversized single requests
("cost limits exceeded"). Full-year downloads are split into one CDS job per month.

Setup (one time):
  1. Register at https://cds.climate.copernicus.eu/
  2. Accept the ERA5 license on the dataset page
  3. Create ~/.cdsapirc:
       url: https://cds.climate.copernicus.eu/api
       key: <UID>:<API-KEY>

Usage:
  python3 scripts/download_era5.py
  python3 scripts/download_era5.py --year 2020 --month 01 --grid 5
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

DATASET = "reanalysis-era5-single-levels"

VARIABLES = {
    "significant_height_of_combined_wind_waves_and_swell": "swh",
    "peak_wave_period": "tp",
    "10m_u_component_of_wind": "u10",
    "10m_v_component_of_wind": "v10",
}

DEFAULT_LAT = 4.0
DEFAULT_LON = 108.0
DEFAULT_YEARS = 5
DEFAULT_END_YEAR = 2024
DEFAULT_MONTH = "all"  # all months per year
DEFAULT_GRID_POINTS = 20  # 20 × 20 cells at 0.5° resolution
DEFAULT_OUTPUT = Path("data/era5_sample.nc")

# CDS rejects most large selections; keep custom downloads under this unless --force
MAX_ESTIMATE_GB = 1.0

GRID_SPACING_DEG = 0.5
BYTES_PER_VALUE = 4
HOURS_PER_MONTH = 744  # upper bound for sizing


def cdsapirc_path() -> Path:
    return Path.home() / ".cdsapirc"


def check_credentials() -> None:
    path = cdsapirc_path()
    if not path.is_file():
        sys.exit(
            f"Missing CDS credentials at {path}\n\n"
            "Create the file with:\n"
            "  url: https://cds.climate.copernicus.eu/api\n"
            "  key: <UID>:<API-KEY>\n\n"
            "Get your key from: https://cds.climate.copernicus.eu/user\n"
            "Accept the ERA5 license at:\n"
            "  https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels"
        )


def buffer_for_grid(n_points: int) -> float:
    """Half-width (degrees) for an n×n grid at ERA5 wave resolution (0.5°)."""
    return (n_points - 1) * GRID_SPACING_DEG / 2


def area_box(lat: float, lon: float, buffer_deg: float) -> list[float]:
    """Return CDS area as [North, West, South, East]."""
    return [
        lat + buffer_deg,
        lon - buffer_deg,
        lat - buffer_deg,
        lon + buffer_deg,
    ]


def grid_shape(area: list[float]) -> tuple[int, int]:
    north, west, south, east = area
    n_lat = int(round((north - south) / GRID_SPACING_DEG)) + 1
    n_lon = int(round((east - west) / GRID_SPACING_DEG)) + 1
    return n_lat, n_lon


def estimate_size_bytes(*, n_months: int, area: list[float]) -> int:
    n_lat, n_lon = grid_shape(area)
    n_time = n_months * HOURS_PER_MONTH
    return n_time * n_lat * n_lon * len(VARIABLES) * BYTES_PER_VALUE


def format_size(num_bytes: int | float) -> str:
    mb = num_bytes / (1024 * 1024)
    if mb < 1024:
        return f"~{mb:.2f} MB" if mb < 10 else f"~{mb:.1f} MB"
    return f"~{mb / 1024:.2f} GB"


def all_days() -> list[str]:
    return [f"{day:02d}" for day in range(1, 32)]


def all_hours() -> list[str]:
    return [f"{hour:02d}:00" for hour in range(24)]


def month_list(start: int = 1, end: int = 12) -> list[str]:
    return [f"{m:02d}" for m in range(start, end + 1)]


def year_range(end_year: int, count: int) -> list[str]:
    start = end_year - count + 1
    return [str(y) for y in range(start, end_year + 1)]


def month_jobs(years: list[str], months: list[str]) -> list[tuple[str, str]]:
    return [(year, month) for year in years for month in months]


def build_request(
    *,
    lat: float,
    lon: float,
    buffer_deg: float,
    years: list[str],
    months: list[str],
) -> dict:
    return {
        "product_type": "reanalysis",
        "variable": list(VARIABLES.keys()),
        "year": years,
        "month": months,
        "day": all_days(),
        "time": all_hours(),
        "area": area_box(lat, lon, buffer_deg),
        "format": "netcdf",
    }


def normalize_dataset(ds_or_path):
    """Rename variables/dims so the notebook can open the file directly."""
    import xarray as xr

    if isinstance(ds_or_path, Path):
        ds = xr.open_dataset(ds_or_path)
        in_place = True
    else:
        ds = ds_or_path
        in_place = False

    rename_vars = {
        cds_name: short_name
        for cds_name, short_name in VARIABLES.items()
        if cds_name in ds.data_vars
    }
    if rename_vars:
        ds = ds.rename(rename_vars)

    if "valid_time" in ds.dims:
        ds = ds.rename({"valid_time": "time"})

    if in_place:
        ds.to_netcdf(ds_or_path)
        ds.close()
    return ds


def retrieve_month(
    client,
    *,
    lat: float,
    lon: float,
    buffer_deg: float,
    year: str,
    month: str,
    target: Path,
) -> None:
    request = build_request(
        lat=lat,
        lon=lon,
        buffer_deg=buffer_deg,
        years=[year],
        months=[month],
    )
    client.retrieve(DATASET, request, str(target))


def download(
    output: Path,
    *,
    lat: float,
    lon: float,
    buffer_deg: float,
    years: list[str],
    months: list[str],
    normalize: bool,
    force: bool,
) -> None:
    import cdsapi
    import xarray as xr

    area = area_box(lat, lon, buffer_deg)
    jobs = month_jobs(years, months)
    n_jobs = len(jobs)
    est_bytes = estimate_size_bytes(n_months=n_jobs, area=area)
    est_gb = est_bytes / (1024**3)

    if est_gb > MAX_ESTIMATE_GB and not force:
        sys.exit(
            f"Estimated selection size {format_size(est_bytes)} exceeds {MAX_ESTIMATE_GB} GB.\n"
            "CDS will likely reject this request (cost limits exceeded).\n"
            "Use a smaller --grid / --years range, or pass --force to try anyway.\n"
            "The repo sample is meant to stay small — see data/README.md."
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    n_lat, n_lon = grid_shape(area)

    print(f"Requesting ERA5 from CDS → {output}")
    print(f"  area (N/W/S/E): {area}")
    print(f"  years: {years[0]}–{years[-1]} ({len(years)} yr)" if len(years) > 1 else f"  year: {years[0]}")
    print(f"  grid: ~{n_lat} × {n_lon} points, {n_jobs} month(s) hourly")
    print(f"  estimated size: {format_size(est_bytes)} (uncompressed float32)")
    print(f"  fetching {n_jobs} separate CDS jobs (one per month — avoids cost-limit rejection)")
    print("  (CDS queues each job; allow several minutes per month.)")

    client = cdsapi.Client()
    tmp_dir = output.parent / f".{output.stem}_parts"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    part_paths: list[Path] = []

    try:
        for i, (year, month) in enumerate(jobs, start=1):
            part = tmp_dir / f"{year}_{month}.nc"
            print(f"  [{i}/{n_jobs}] downloading {year}-{month} …")
            retrieve_month(
                client,
                lat=lat,
                lon=lon,
                buffer_deg=buffer_deg,
                year=year,
                month=month,
                target=part,
            )
            part_paths.append(part)

        print("  merging monthly files …")
        datasets = [xr.open_dataset(p) for p in part_paths]
        time_dim = "valid_time" if "valid_time" in datasets[0].dims else "time"
        merged = xr.concat(datasets, dim=time_dim)
        for ds in datasets:
            ds.close()

        if normalize:
            merged = normalize_dataset(merged)

        merged.to_netcdf(output)
        merged.close()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"Done: {output} ({format_size(output.stat().st_size)} on disk)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate data/era5_sample.nc for the extract-point tutorial.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output NetCDF path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT, help="Target latitude (°N)")
    parser.add_argument("--lon", type=float, default=DEFAULT_LON, help="Target longitude (°E)")
    parser.add_argument(
        "--grid",
        type=int,
        default=DEFAULT_GRID_POINTS,
        help=f"Grid points per axis at 0.5° (default: {DEFAULT_GRID_POINTS} → 20×20)",
    )
    parser.add_argument(
        "--buffer",
        type=float,
        default=None,
        dest="buffer_deg",
        help="Half-width of box in degrees (overrides --grid)",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=DEFAULT_YEARS,
        help=f"Number of years ending at --end-year (default: {DEFAULT_YEARS})",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=DEFAULT_END_YEAR,
        help=f"Last year in range (default: {DEFAULT_END_YEAR})",
    )
    parser.add_argument(
        "--year",
        type=str,
        default=None,
        help="Single year only (overrides --years / --end-year)",
    )
    parser.add_argument(
        "--month",
        type=str,
        default=DEFAULT_MONTH,
        help="Month MM, or 'all' for every month (default: all)",
    )
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Skip renaming variables to swh/tp/u10/v10",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Submit even if estimated size exceeds CDS-friendly limit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    check_credentials()

    months = month_list() if args.month == "all" else [args.month.zfill(2)]
    buffer_deg = args.buffer_deg if args.buffer_deg is not None else buffer_for_grid(args.grid)

    if args.year:
        years = [args.year]
    else:
        years = year_range(args.end_year, args.years)

    download(
        args.output,
        lat=args.lat,
        lon=args.lon,
        buffer_deg=buffer_deg,
        years=years,
        months=months,
        normalize=not args.no_normalize,
        force=args.force,
    )


if __name__ == "__main__":
    main()
