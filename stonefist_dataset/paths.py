from __future__ import annotations

from pathlib import Path

ROOT = Path("stonefist-captures")
PAIRS_DIR = ROOT / "pairs"
DATASET_PATH = ROOT / "dataset.json"
PAIR_SUMMARY_PATH = ROOT / "pair_summary.csv"
MOD_LINES_PATH = ROOT / "mod_lines.csv"
MAPPING_OBSERVATIONS_PATH = ROOT / "mapping_observations.csv"
MAPPING_CANDIDATES_PATH = ROOT / "mapping_candidates.csv"
MAPPING_FAMILIES_PATH = ROOT / "mapping_families.csv"
GLOVE_MOD_POOL_JSON_PATH = Path("stonefist-reference") / "glove_mod_pool.json"
GLOVE_MOD_POOL_CSV_PATH = Path("stonefist-reference") / "glove_mod_pool.csv"
GLOVE_COVERAGE_PATH = ROOT / "glove_mod_coverage.csv"
TRANSFORMED_OUTPUT_ONLY_PATH = ROOT / "transformed_output_only.csv"
CAPTURE_TARGETS_PATH = ROOT / "capture_targets.csv"
BASE_CONTROL_SUMMARY_PATH = ROOT / "base_control_summary.csv"
AUGMENT_SOCKET_SUMMARY_PATH = ROOT / "augment_socket_summary.csv"


BASE_CONTROL_FIELDNAMES = [
    "sample_id",
    "character_level",
    "before_name",
    "before_base_type",
    "before_defence_family",
    "before_armour",
    "before_evasion",
    "before_energy_shield",
    "after_evasion",
    "after_energy_shield",
    "evasion_per_level",
    "energy_shield_per_level",
    "after_implicit_templates",
    "notes",
]


AUGMENT_SOCKET_FIELDNAMES = [
    "sample_id",
    "character_level",
    "before_rarity",
    "before_name",
    "before_base_type",
    "after_name",
    "after_base_type",
    "before_socket_count",
    "after_socket_count",
    "before_socket_lines",
    "after_socket_lines",
    "before_augment_lines",
    "after_augment_lines",
    "augment_family",
    "socketed_augment_source",
    "socket_behaviour",
    "augment_line_behaviour",
    "before_usable_for_capture_character",
    "after_usable_for_capture_character",
    "after_stats_ignored_for_capture_character",
    "usability_behaviour_for_capture_character",
    "augment_effect_status_for_capture_character",
    "notes",
]
