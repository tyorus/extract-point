# ERA5 sample data

`data/era5_sample.nc` is a **pre-sliced file committed to the repo** so Colab and local runs work without a CDS account.

The notebook opening line (*"You downloaded ERA5. It's 2.3 GB"*) describes the **naive mistake** people make with full global downloads — not this file.

## Sample file spec

| Setting | Value |
|---------|-------|
| Location | 4°N, 108°E (Natuna Sea platform) |
| Grid | 20 × 20 points at 0.5° (~9.5° × 9.5° box) |
| Time | 2020–2024 (5 years), hourly |
| Variables | swh, tp, u10, v10 |
| Size | ~270 MB uncompressed (~60 CDS jobs) |

CDS enforces a **per-request cost limit**. The download script fetches **one month at a time** and merges the result.

Open in the notebook:

```python
import xarray as xr
ds = xr.open_dataset("../data/era5_sample.nc")
ts = ds["swh"].sel(latitude=4.0, longitude=108.0, method="nearest")
```

## Regenerate the sample (maintainers)

One-time CDS setup:

1. Register at [Copernicus CDS](https://cds.climate.copernicus.eu/)
2. Accept the [ERA5 single levels license](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels)
3. Create `~/.cdsapirc`:

```yaml
url: https://cds.climate.copernicus.eu/api
key: YOUR_UID:YOUR_API_KEY
```

```bash
pip install -r requirements.txt
python3 scripts/download_era5.py   # 5 yr, 20×20 grid → 60 monthly jobs
```

Commit the updated `data/era5_sample.nc` if you change the slice. Files over 100 MB need [Git LFS](https://git-lfs.com/).

## Custom local downloads

```bash
python3 scripts/download_era5.py --years 1 --grid 10 --end-year 2020
python3 scripts/download_era5.py --year 2020 --month 01 --grid 5
```

## Variables

- **swh** — significant wave height (m)
- **tp** — peak wave period (s)
- **u10 / v10** — 10 m wind components (m/s)
