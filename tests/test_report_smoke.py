import shutil
from pathlib import Path

import stonefist_build_dataset as sbd
from stonefist_reporter import loaders
from stonefist_reporter.render import render_html

FIXTURE_PAIRS_DIR = Path(__file__).parent / "fixtures" / "mini_pairs"

TAB_LABELS = [
    "Overview",
    "Capture Targets",
    "Mapping Families",
    "Modifier Coverage",
    "Output Only",
    "Base Controls",
    "Pair Explorer",
    "Raw Evidence",
]


def test_report_html_contains_all_tabs(tmp_path, monkeypatch):
    # Copy the fixture pair into tmp_path rather than pointing PAIRS_DIR
    # straight at tests/fixtures, keeping test I/O entirely inside tmp_path.
    pairs_dir = tmp_path / "pairs"
    shutil.copytree(FIXTURE_PAIRS_DIR, pairs_dir)

    monkeypatch.setattr(sbd, "PAIRS_DIR", pairs_dir)
    pairs = sbd.load_pairs()
    assert len(pairs) == 1

    # Point the CSV loaders at an empty directory so the report renders
    # against a minimal dataset rather than the real generated CSVs.
    monkeypatch.setattr(loaders, "MAPPING_FAMILIES_PATH", tmp_path / "mapping_families.csv")
    monkeypatch.setattr(loaders, "MAPPING_CANDIDATES_PATH", tmp_path / "mapping_candidates.csv")
    monkeypatch.setattr(loaders, "GLOVE_COVERAGE_PATH", tmp_path / "glove_mod_coverage.csv")
    monkeypatch.setattr(loaders, "TRANSFORMED_OUTPUT_ONLY_PATH", tmp_path / "transformed_output_only.csv")
    monkeypatch.setattr(loaders, "CAPTURE_TARGETS_PATH", tmp_path / "capture_targets.csv")
    monkeypatch.setattr(loaders, "BASE_CONTROL_SUMMARY_PATH", tmp_path / "base_control_summary.csv")

    html = render_html(pairs)

    for label in TAB_LABELS:
        assert label in html
