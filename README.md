# Stonefist Tool

A small toolchain for capturing, building, and reporting Way of the Stonefist item transformation pairs.

## Files

- `stonefist_capture.py` - captures clipboard `before`/`after` item text and saves raw evidence under `stonefist-captures/pairs/`.
- `stonefist_build_dataset.py` - parses raw pairs into `stonefist-captures/dataset.json`, `stonefist-captures/pair_summary.csv`, and `stonefist-captures/mod_lines.csv`.
- `stonefist_report.py` - reads `dataset.json` and writes `stonefist-captures/report.html`.

## Workflow

1. Capture raw item pairs:

```powershell
uv run --python 3.12 python stonefist_capture.py
```

2. Build the dataset:

```powershell
uv run --python 3.12 python stonefist_build_dataset.py
```

3. Generate the report:

```powershell
uv run --python 3.12 python stonefist_report.py
```

## Notes

- Raw evidence is stored in `stonefist-captures/pairs/` and is not modified by the build or report steps.
- Exact duplicate detection is supported in the dataset pipeline and is included in both `pair_summary.csv` and the generated report.
- `stonefist_report.py` filters on category, UID status, and duplicate status.
