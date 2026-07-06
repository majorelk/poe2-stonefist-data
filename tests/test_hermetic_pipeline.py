import csv
import shutil
from pathlib import Path

import stonefist_build_dataset as sbd

FIXTURE_PAIRS_DIR = Path(__file__).parent / "fixtures" / "mini_pairs"
FIXTURE_POOL_CSV = Path(__file__).parent / "fixtures" / "tiny_glove_mod_pool.csv"

WRITTEN_FILENAMES = [
    "dataset.json",
    "pair_summary.csv",
    "mod_lines.csv",
    "mapping_observations.csv",
    "mapping_candidates.csv",
    "mapping_families.csv",
    "glove_mod_coverage.csv",
    "transformed_output_only.csv",
    "capture_targets.csv",
    "base_control_summary.csv",
]


def test_build_pipeline_writes_only_inside_tmp_path(tmp_path, monkeypatch):
    """Exercise the real write_json_dataset/write_csvs functions end to end,
    but with every module-level output path redirected into tmp_path. This
    is the regression check that the build pipeline never touches
    stonefist-captures/ or stonefist-reference/ when driven by tests -
    the autouse guard_real_project_outputs fixture in conftest.py would
    fail this (and every other) test if it did.
    """
    captures_root = tmp_path / "stonefist-captures"
    reference_root = tmp_path / "stonefist-reference"
    pairs_dir = captures_root / "pairs"

    shutil.copytree(FIXTURE_PAIRS_DIR, pairs_dir)
    reference_root.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE_POOL_CSV, reference_root / "glove_mod_pool.csv")

    monkeypatch.setattr(sbd, "ROOT", captures_root)
    monkeypatch.setattr(sbd, "PAIRS_DIR", pairs_dir)
    monkeypatch.setattr(sbd, "DATASET_PATH", captures_root / "dataset.json")
    monkeypatch.setattr(sbd, "PAIR_SUMMARY_PATH", captures_root / "pair_summary.csv")
    monkeypatch.setattr(sbd, "MOD_LINES_PATH", captures_root / "mod_lines.csv")
    monkeypatch.setattr(sbd, "MAPPING_OBSERVATIONS_PATH", captures_root / "mapping_observations.csv")
    monkeypatch.setattr(sbd, "MAPPING_CANDIDATES_PATH", captures_root / "mapping_candidates.csv")
    monkeypatch.setattr(sbd, "MAPPING_FAMILIES_PATH", captures_root / "mapping_families.csv")
    monkeypatch.setattr(sbd, "GLOVE_MOD_POOL_JSON_PATH", reference_root / "glove_mod_pool.json")
    monkeypatch.setattr(sbd, "GLOVE_MOD_POOL_CSV_PATH", reference_root / "glove_mod_pool.csv")
    monkeypatch.setattr(sbd, "GLOVE_COVERAGE_PATH", captures_root / "glove_mod_coverage.csv")
    monkeypatch.setattr(sbd, "TRANSFORMED_OUTPUT_ONLY_PATH", captures_root / "transformed_output_only.csv")
    monkeypatch.setattr(sbd, "CAPTURE_TARGETS_PATH", captures_root / "capture_targets.csv")
    monkeypatch.setattr(sbd, "BASE_CONTROL_SUMMARY_PATH", captures_root / "base_control_summary.csv")

    pairs = sbd.load_pairs()
    assert len(pairs) == 1

    sbd.write_json_dataset(pairs)
    sbd.write_csvs(pairs)

    for filename in WRITTEN_FILENAMES:
        assert (captures_root / filename).exists(), f"expected {filename} to be written inside tmp_path"

    with (captures_root / "glove_mod_coverage.csv").open(encoding="utf-8", newline="") as f:
        coverage_rows = list(csv.DictReader(f))
    assert len(coverage_rows) == 1
    assert coverage_rows[0]["stat_template"] == "+# to Strength"
