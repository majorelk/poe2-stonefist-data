# Stonefist Tool

A small toolchain for capturing, building, and reporting Way of the Stonefist item transformation pairs, and for cross-referencing transformed gloves against a PoE2DB glove modifier reference pool.

## Files

- `stonefist_capture.py` - captures clipboard `before`/`after` item text and saves raw evidence under `stonefist-captures/pairs/`.
- `stonefist_import_poe2db_mods.py` - imports the glove modifier reference pool from local PoE2DB page snapshots, or with `--fetch` to download them, into `stonefist-reference/glove_mod_pool.csv` and `stonefist-reference/glove_mod_pool.json`. Never runs automatically.
- `stonefist_build_dataset.py` - parses raw pairs and the reference pool into `stonefist-captures/dataset.json`, `pair_summary.csv`, `mod_lines.csv`, `mapping_observations.csv`, `mapping_candidates.csv`, `mapping_families.csv`, `glove_mod_coverage.csv`, `transformed_output_only.csv`, and `capture_targets.csv`.
- `stonefist_report.py` - reads the generated dataset and CSVs, then writes `stonefist-captures/report.html`.

## Workflow

1. Capture raw item pairs:

```bash
uv run --python 3.12 python stonefist_capture.py
```

2. Optional, one-off: populate the glove modifier reference pool. Save PoE2DB page snapshots into `stonefist-reference/raw-poe2db/`, see its README, or pass `--fetch` to download them automatically:

```bash
uv run --python 3.12 python stonefist_import_poe2db_mods.py
```

3. Build the dataset:

```bash
uv run --python 3.12 python stonefist_build_dataset.py
```

4. Generate the report:

```bash
uv run --python 3.12 python stonefist_report.py
```

## Reference source

The glove modifier reference pool is imported from local snapshots of the PoE2DB glove modifier pages:

- https://poe2db.tw/us/Gloves_str#ModifiersCalc
- https://poe2db.tw/us/Gloves_dex#ModifiersCalc
- https://poe2db.tw/us/Gloves_int#ModifiersCalc
- https://poe2db.tw/us/Gloves_str_dex#ModifiersCalc
- https://poe2db.tw/us/Gloves_str_int#ModifiersCalc
- https://poe2db.tw/us/Gloves_dex_int#ModifiersCalc

Snapshots are stored under `stonefist-reference/raw-poe2db/`.

The importer reads those local snapshots by default and writes:

- `stonefist-reference/glove_mod_pool.csv`
- `stonefist-reference/glove_mod_pool.json`

The importer may be run with `--fetch` to refresh snapshots from PoE2DB, but fetching is never performed by the build or report scripts.

## Generated outputs

The build step produces derived data under `stonefist-captures/`:

- `dataset.json` - parsed pair data used by the report.
- `pair_summary.csv` - one row per before/after pair.
- `mod_lines.csv` - extracted modifier/stat lines.
- `mapping_observations.csv` - raw explicit modifier mapping observations.
- `mapping_candidates.csv` - provisional explicit modifier mapping candidates.
- `mapping_families.csv` - normalised before/after stat-family mappings.
- `glove_mod_coverage.csv` - comparison between the PoE2DB glove modifier pool and captured Stonefist data.
- `transformed_output_only.csv` - Stonefist output stat templates not present in the loaded glove modifier reference pool.
- `capture_targets.csv` - prioritised list of modifiers worth hunting or isolating next.
- `report.html` - static human-readable report.

## Reading the report

`stonefist-captures/report.html` is a static tabbed report generated from the captured item pairs and the loaded glove modifier reference pool.

### Overview

Shows high-level dataset counts, including total pairs, transformed pairs, unique samples, UID status, duplicate count, capture target priority counts, and glove modifier coverage counts.

Use this tab as a quick sanity check after rebuilding the dataset.

### Capture Targets

Shows what is still worth capturing or isolating next.

Priority meanings:

- `P1` - missing explicit input sample. The modifier exists in the glove reference pool, but has not been captured as a Stonefist input yet.
- `P2` - likely mapping needs isolated confirmation. The mapping has evidence, usually from multi-mod items, but still needs a clean isolated sample.
- `P3` - corruption-only missing. The modifier appears only in corrupted/enchantment reference data and has not been captured.
- `P4` - confirmed mapping. No immediate action needed.

For normal data collection, prioritise `P1` first, then `P2`.

### Mapping Families

Groups observed before/after transformations by normalised stat text.

This is the main tab for understanding what Stonefist appears to do to each modifier family.

### Modifier Coverage

Compares the PoE2DB glove modifier reference pool against the currently captured Stonefist data.

Use this tab to see which reference modifier families are confirmed, likely, missing, or corruption-only.

### Output Only

Shows stat templates that appear after Stonefist transformation but are not present in the loaded glove reference pool.

These are not directly targetable as glove input mods unless they also appear in the reference pool.

### Pair Explorer

Shows each captured before/after pair.

Use this tab to inspect individual evidence, including item name, base, item level, rarity, explicit count, parsed stats, parsed modifier blocks, raw item text, and capture metadata.

### Raw Evidence

Raw before/after item text is not duplicated in this tab. It remains available inside each `Pair Explorer` row under the collapsed `Raw item text` section.

## Capture workflow

Recommended loop:

1. Open `stonefist-captures/report.html`.
2. Go to `Capture Targets`.
3. Filter for `P1`.
4. Find or craft a glove with one of those missing input modifiers.
5. Prefer isolated magic items where possible.
6. Capture the before/after pair with `stonefist_capture.py`.
7. Rebuild the dataset with `stonefist_build_dataset.py`.
8. Regenerate the report with `stonefist_report.py`.
9. Check whether the target moved from `missing_input_sample` or `likely_mapping` into confirmed coverage.

For confirmation quality, prefer:

- one explicit modifier on a magic item
- two explicit modifiers only if the modifier names are unambiguous
- rare multi-mod items only as provisional evidence

Raw captured evidence under `stonefist-captures/pairs/` should not be edited manually.

## Evidence model

The toolchain separates raw evidence from derived outputs.

Raw evidence:

- `stonefist-captures/pairs/*/before.txt`
- `stonefist-captures/pairs/*/after.txt`
- `stonefist-captures/pairs/*/meta.json`

Derived outputs:

- `dataset.json`
- generated CSV files
- `report.html`

The raw pair folders are the source of truth. The dataset, CSV files, and report can be regenerated from them.

## Data interpretation

Mappings are evidence-based, not assumed final truth.

- `confirmed_mapping` means the mapping has at least one isolated sample.
- `likely_mapping` means the mapping is supported by captured data but still needs isolated confirmation.
- `missing_input_sample` means the modifier exists in the loaded glove reference pool but has not yet been captured as a Stonefist input.
- `corruption_only_missing` means the modifier is present only in the corrupted/enchantment reference pool and has not yet been captured.
- `transformed_output_only` means the stat appears after Stonefist transformation but is not present in the loaded glove input reference pool.

## Notes

- Raw evidence is stored in `stonefist-captures/pairs/` and is never modified by any other step.
- Exact duplicate detection is supported in the dataset pipeline and is included in both `pair_summary.csv` and the generated report.
- Explicit modifier blocks are matched before/after primarily by modifier name, falling back to order only when names are ambiguous. Treat mappings as provisional until confirmed by an isolated sample.
- The build and report scripts never fetch from PoE2DB. Importing the reference pool is a separate, explicit step.
- `capture_targets.csv` ranks reference modifiers by what is still worth capturing, including missing input samples, likely mappings needing isolation, corruption-only gaps, and confirmed mappings. It is surfaced in the report's `Capture Targets` section.
- `stonefist_report.py` includes filters for report tabs such as priority, coverage status, pair search, category, UID status, and duplicate status.
