from __future__ import annotations

import csv
import json
from datetime import datetime

from stonefist_dataset.augment_controls import compute_augment_socket_rows, write_augment_socket_summary_csv
from stonefist_dataset.base_controls import compute_base_control_rows, write_base_control_summary_csv
from stonefist_dataset.mapping import write_mapping_csvs
from stonefist_dataset.pairs import load_pairs
from stonefist_dataset import paths


def write_json_dataset(pairs: list[dict]) -> None:
    dataset = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "pair_count": len(pairs),
        "pairs": pairs,
    }

    paths.DATASET_PATH.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csvs(pairs: list[dict]) -> None:
    with paths.PAIR_SUMMARY_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(
            [
                "test_id",
                "category",
                "before_item_class",
                "before_rarity",
                "before_name",
                "before_base",
                "before_item_level",
                "before_unique_id",
                "after_item_class",
                "after_rarity",
                "after_name",
                "after_base",
                "after_item_level",
                "after_unique_id",
                "character_level",
                "captured_at",
                "capture_version",
                "pair_hash",
                "before_hash",
                "after_hash",
                "uid_status",
                "is_exact_duplicate",
                "duplicate_of",
                "duplicate_group_size",
                "before_explicit_count",
                "after_explicit_count",
                "before_path",
                "after_path",
            ]
        )

        for p in pairs:
            writer.writerow(
                [
                    p["test_id"],
                    p["category"],
                    p["before_item_class"],
                    p["before_rarity"],
                    p["before_name"],
                    p["before_base"],
                    p["before_item_level"],
                    p["before_unique_id"],
                    p["after_item_class"],
                    p["after_rarity"],
                    p["after_name"],
                    p["after_base"],
                    p["after_item_level"],
                    p["after_unique_id"],
                    p["character_level"],
                    p["captured_at"],
                    p["capture_version"],
                    p["pair_hash"],
                    p["before_hash"],
                    p["after_hash"],
                    p["uid_status"],
                    str(p["is_exact_duplicate"]),
                    p["duplicate_of"],
                    p["duplicate_group_size"],
                    p["before_explicit_count"],
                    p["after_explicit_count"],
                    p["before_path"],
                    p["after_path"],
                ]
            )

    with paths.MOD_LINES_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["test_id", "category", "side", "line_number", "mod_line"])

        for p in pairs:
            for i, line in enumerate(p["before_lines"], start=1):
                writer.writerow([p["test_id"], p["category"], "before", i, line])

            for i, line in enumerate(p["after_lines"], start=1):
                writer.writerow([p["test_id"], p["category"], "after", i, line])

    write_mapping_csvs(pairs)
    write_base_control_summary_csv(compute_base_control_rows(pairs))
    write_augment_socket_summary_csv(compute_augment_socket_rows(pairs))


def main() -> None:
    pairs = load_pairs()

    if not pairs:
        raise SystemExit("No before/after pairs found in stonefist-captures/pairs")

    write_json_dataset(pairs)
    write_csvs(pairs)

    duplicate_count = sum(1 for p in pairs if p.get("is_exact_duplicate"))
    print(f"Loaded {len(pairs)} pairs.")
    print(f"Exact duplicates: {duplicate_count}.")
    print(f"Wrote: {paths.DATASET_PATH}")
    print(f"Wrote: {paths.PAIR_SUMMARY_PATH}")
    print(f"Wrote: {paths.MOD_LINES_PATH}")
