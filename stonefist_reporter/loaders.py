from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path("stonefist-captures")
DATASET_PATH = ROOT / "dataset.json"
MAPPING_CANDIDATES_PATH = ROOT / "mapping_candidates.csv"
MAPPING_FAMILIES_PATH = ROOT / "mapping_families.csv"
GLOVE_COVERAGE_PATH = ROOT / "glove_mod_coverage.csv"
TRANSFORMED_OUTPUT_ONLY_PATH = ROOT / "transformed_output_only.csv"
CAPTURE_TARGETS_PATH = ROOT / "capture_targets.csv"
BASE_CONTROL_SUMMARY_PATH = ROOT / "base_control_summary.csv"
AUGMENT_SOCKET_SUMMARY_PATH = ROOT / "augment_socket_summary.csv"
REPORT_PATH = ROOT / "report.html"


def load_dataset() -> list[dict]:
    if not DATASET_PATH.exists():
        raise SystemExit(f"Could not find {DATASET_PATH}")

    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "pairs" not in data:
        raise SystemExit(f"Invalid dataset format in {DATASET_PATH}")

    return data["pairs"]


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def load_mapping_candidates() -> list[dict[str, str]]:
    return _load_csv(MAPPING_CANDIDATES_PATH)


def load_mapping_families() -> list[dict[str, str]]:
    return _load_csv(MAPPING_FAMILIES_PATH)


def load_glove_coverage() -> list[dict[str, str]]:
    return _load_csv(GLOVE_COVERAGE_PATH)


def load_transformed_output_only() -> list[dict[str, str]]:
    return _load_csv(TRANSFORMED_OUTPUT_ONLY_PATH)


def load_capture_targets() -> list[dict[str, str]]:
    return _load_csv(CAPTURE_TARGETS_PATH)


def load_base_control_summary() -> list[dict[str, str]]:
    return _load_csv(BASE_CONTROL_SUMMARY_PATH)


def load_augment_socket_summary() -> list[dict[str, str]]:
    return _load_csv(AUGMENT_SOCKET_SUMMARY_PATH)
