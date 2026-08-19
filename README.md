# Point Extraction

## Project Structure

```bash
extract-point/
│
├── README.md                  ← repo landing page + quick start
├── LICENSE                    ← MIT
├── requirements.txt           ← pinned versions
├── notebooks/
│   └── extract_point.ipynb    ← THE main Colab notebook
│
├── data/
│   └── README.md              ← instructions to download ERA5 slice
│   └── era5_sample.nc         ← pre-sliced <10MB dummy file
│
├── src/
│   └── extract_utils.py       ← reusable functions (importable)
│
└── benchmarks/
    └── benchmark_results.png  ← pre-generated comparison chart
    └── benchmark.py           ← reproducible benchmark script
```