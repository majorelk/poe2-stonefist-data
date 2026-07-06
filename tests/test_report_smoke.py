from pathlib import Path

import stonefist_build_dataset as sbd
import stonefist_report as sr

FIXTURE_PAIRS_DIR = Path(__file__).parent / "fixtures" / "mini_pairs"

TAB_LABELS = [
    "Overview",
    "Capture Targets",
    "Mapping Families",
    "Modifier Coverage",
    "Output Only",
    "Pair Explorer",
    "Raw Evidence",
]


def test_report_html_contains_all_tabs(tmp_path, monkeypatch):
    monkeypatch.setattr(sbd, "PAIRS_DIR", FIXTURE_PAIRS_DIR)
    pairs = sbd.load_pairs()
    assert len(pairs) == 1

    # Point the CSV loaders at an empty directory so the report renders
    # against a minimal dataset rather than the real generated CSVs.
    monkeypatch.setattr(sr, "MAPPING_FAMILIES_PATH", tmp_path / "mapping_families.csv")
    monkeypatch.setattr(sr, "MAPPING_CANDIDATES_PATH", tmp_path / "mapping_candidates.csv")
    monkeypatch.setattr(sr, "GLOVE_COVERAGE_PATH", tmp_path / "glove_mod_coverage.csv")
    monkeypatch.setattr(sr, "TRANSFORMED_OUTPUT_ONLY_PATH", tmp_path / "transformed_output_only.csv")
    monkeypatch.setattr(sr, "CAPTURE_TARGETS_PATH", tmp_path / "capture_targets.csv")

    html = sr.render_html(pairs)

    for label in TAB_LABELS:
        assert label in html
