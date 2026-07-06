import hashlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Real project outputs that no test may ever modify. Tests must redirect
# module-level paths (via monkeypatch) to tmp_path instead of writing here.
_CAPTURES_DIR = REPO_ROOT / "stonefist-captures"
_REFERENCE_DIR = REPO_ROOT / "stonefist-reference"

PROTECTED_FILES = [
    _CAPTURES_DIR / "dataset.json",
    _CAPTURES_DIR / "report.html",
    _CAPTURES_DIR / "pair_summary.csv",
    _CAPTURES_DIR / "mod_lines.csv",
    _CAPTURES_DIR / "mapping_observations.csv",
    _CAPTURES_DIR / "mapping_candidates.csv",
    _CAPTURES_DIR / "mapping_families.csv",
    _CAPTURES_DIR / "glove_mod_coverage.csv",
    _CAPTURES_DIR / "transformed_output_only.csv",
    _CAPTURES_DIR / "capture_targets.csv",
    _REFERENCE_DIR / "glove_mod_pool.csv",
    _REFERENCE_DIR / "glove_mod_pool.json",
]

PROTECTED_DIRS = [
    _CAPTURES_DIR / "pairs",
    _CAPTURES_DIR / "raw",
]


def _snapshot_protected_paths() -> dict[str, str]:
    snapshot: dict[str, str] = {}

    for path in PROTECTED_FILES:
        if path.exists():
            snapshot[str(path)] = hashlib.sha1(path.read_bytes()).hexdigest()

    for directory in PROTECTED_DIRS:
        if not directory.exists():
            continue
        for file_path in sorted(directory.rglob("*")):
            if file_path.is_file():
                snapshot[str(file_path)] = hashlib.sha1(file_path.read_bytes()).hexdigest()

    return snapshot


@pytest.fixture(autouse=True)
def guard_real_project_outputs():
    """Fail any test that writes to real generated outputs or raw pair data.

    Tests must redirect module-level path constants to tmp_path via
    monkeypatch rather than touching stonefist-captures/ or
    stonefist-reference/ directly.
    """
    before = _snapshot_protected_paths()
    yield
    after = _snapshot_protected_paths()
    assert before == after, (
        "A test modified real project output files or raw pair data. "
        "Tests must only write to tmp_path (use monkeypatch to redirect "
        "module-level paths in stonefist_build_dataset.py / stonefist_reporter/loaders.py)."
    )
