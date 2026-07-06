# Stonefist Tool

A small toolchain for capturing, building, and reporting Way of the Stonefist item transformation pairs, and for cross-referencing transformed gloves against a PoE2DB glove modifier reference pool.

## Files

- `stonefist_capture.py` - captures clipboard `before`/`after` item text and saves raw evidence under `stonefist-captures/pairs/`.
- `stonefist_import_poe2db_mods.py` - imports the glove modifier reference pool from local PoE2DB page snapshots (or `--fetch` to download them) into `stonefist-reference/glove_mod_pool.csv` / `.json`. Never runs automatically.
- `stonefist_build_dataset.py` - parses raw pairs and the reference pool into `stonefist-captures/dataset.json`, `pair_summary.csv`, `mod_lines.csv`, `mapping_observations.csv`, `mapping_candidates.csv`, `mapping_families.csv`, `glove_mod_coverage.csv`, `transformed_output_only.csv`, and `capture_targets.csv`.
- `stonefist_report.py` - reads the generated dataset/CSVs and writes `stonefist-captures/report.html`.

## Workflow

1. Capture raw item pairs:

```powershell
uv run --python 3.12 python stonefist_capture.py
```

2. (Optional, one-off) Populate the glove modifier reference pool. Save PoE2DB page snapshots into `stonefist-reference/raw-poe2db/` (see its README), or pass `--fetch` to download them automatically:

```powershell
uv run --python 3.12 python stonefist_import_poe2db_mods.py
```

3. Build the dataset:

```powershell
uv run --python 3.12 python stonefist_build_dataset.py
```

4. Generate the report:

```powershell
uv run --python 3.12 python stonefist_report.py
```

## Notes

- Raw evidence is stored in `stonefist-captures/pairs/` and is never modified by any other step.
- Exact duplicate detection is supported in the dataset pipeline and is included in both `pair_summary.csv` and the generated report.
- Explicit modifier blocks are matched before/after primarily by modifier name (falling back to order only when names are ambiguous); treat mappings as provisional until confirmed by an isolated sample.
- The build and report scripts never fetch from PoE2DB - importing the reference pool is a separate, explicit step.
- `capture_targets.csv` ranks reference modifiers by what's still worth capturing (missing input samples, likely mappings needing isolation, corruption-only gaps, confirmed mappings) and is surfaced in the report's "Capture targets" section.
- `stonefist_report.py` filters on category, UID status, and duplicate status.
