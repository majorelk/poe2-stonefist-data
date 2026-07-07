from __future__ import annotations

import csv
import json

from stonefist_dataset.explicit_mods import parse_explicit_modifier_blocks
from stonefist_dataset.item_text import join_stats_for_csv, normalise_stat_template
from stonefist_dataset import paths


def load_glove_mod_pool() -> list[dict[str, str]]:
    def normalize_row(row: dict[str, object]) -> dict[str, str] | None:
        raw_stat_text = str(row.get("stat_text", "") or "").strip()
        stat_template = str(row.get("stat_template", "") or "").strip() or normalise_stat_template(raw_stat_text)
        if not raw_stat_text and not stat_template:
            return None

        return {
            "source_url": str(row.get("source_url", "") or "").strip(),
            "glove_class": str(row.get("glove_class", "") or "").strip(),
            "pool_type": str(row.get("pool_type", "") or "").strip(),
            "modifier_kind": str(row.get("modifier_kind", "") or "").strip(),
            "modifier_name": str(row.get("modifier_name", "") or "").strip(),
            "tier": str(row.get("tier", "") or "").strip(),
            "min_item_level": str(row.get("min_item_level", "") or "").strip(),
            "tags": str(row.get("tags", "") or "").strip(),
            "stat_text": raw_stat_text,
            "stat_template": stat_template,
        }

    if paths.GLOVE_MOD_POOL_JSON_PATH.exists():
        try:
            data = json.loads(paths.GLOVE_MOD_POOL_JSON_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        if not isinstance(data, list):
            return []

        entries: list[dict[str, str]] = []
        for raw_row in data:
            if not isinstance(raw_row, dict):
                continue
            entry = normalize_row(raw_row)
            if entry:
                entries.append(entry)

        return entries

    if paths.GLOVE_MOD_POOL_CSV_PATH.exists():
        entries = []
        with paths.GLOVE_MOD_POOL_CSV_PATH.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = normalize_row(row)
                if entry:
                    entries.append(entry)
        return entries

    return []


def build_capture_targets(coverage_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    targets: list[dict[str, object]] = []

    for row in coverage_rows:
        status = row["coverage_status"]
        pool_types = [p.strip() for p in str(row["pool_types"]).split(",") if p.strip()]
        isolated_sample_count = int(row["isolated_sample_count"] or 0)

        if status == "missing_input_sample" and "explicit" in pool_types:
            priority = 1
            reason = "Missing explicit input sample"
            suggested_action = "Find and capture this modifier as an input glove mod, ideally isolated on a magic item."
        elif status == "likely_mapping" and isolated_sample_count == 0:
            priority = 2
            reason = "Likely mapping needs isolated confirmation"
            suggested_action = "Capture an isolated sample to confirm this likely mapping."
        elif status == "corruption_only_missing":
            priority = 3
            reason = "Missing corruption-only sample"
            suggested_action = "Capture if available, lower priority because it requires corrupted/enchantment data."
        elif status == "confirmed_mapping":
            priority = 4
            reason = "Confirmed mapping"
            suggested_action = "No immediate action."
        else:
            continue

        targets.append(
            {
                "priority": priority,
                "reason": reason,
                "stat_template": row["stat_template"],
                "modifier_names": row["modifier_names"],
                "glove_classes": row["glove_classes"],
                "pool_types": row["pool_types"],
                "current_status": status,
                "isolated_sample_count": row["isolated_sample_count"],
                "likely_sample_count": row["likely_sample_count"],
                "sample_ids": row["sample_ids"],
                "suggested_action": suggested_action,
            }
        )

    targets.sort(key=lambda t: (t["priority"], t["current_status"], t["stat_template"]))
    return targets


def write_capture_targets_csv(rows: list[dict[str, object]]) -> None:
    with paths.CAPTURE_TARGETS_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(
            [
                "priority",
                "reason",
                "stat_template",
                "modifier_names",
                "glove_classes",
                "pool_types",
                "current_status",
                "isolated_sample_count",
                "likely_sample_count",
                "sample_ids",
                "suggested_action",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row["priority"],
                    row["reason"],
                    row["stat_template"],
                    row["modifier_names"],
                    row["glove_classes"],
                    row["pool_types"],
                    row["current_status"],
                    row["isolated_sample_count"],
                    row["likely_sample_count"],
                    row["sample_ids"],
                    row["suggested_action"],
                ]
            )


def compute_coverage_rows(
    pairs: list[dict],
    family_summaries: list[dict[str, object]],
    reference_entries: list[dict[str, str]],
) -> list[dict[str, object]]:
    pool_by_template: dict[str, dict[str, object]] = {}
    for entry in reference_entries:
        tmpl = entry.get("stat_template", "")
        if not tmpl:
            continue

        group = pool_by_template.setdefault(
            tmpl,
            {
                "modifier_names": set(),
                "glove_classes": set(),
                "pool_types": set(),
                "source_urls": set(),
            },
        )
        group["modifier_names"].add(entry.get("modifier_name", "") or "")
        group["glove_classes"].add(entry.get("glove_class", ""))
        group["pool_types"].add(entry.get("pool_type", ""))
        group["source_urls"].add(entry.get("source_url", ""))

    before_obs: dict[str, set[str]] = {}
    after_obs: dict[str, set[str]] = {}

    for p in pairs:
        for block in parse_explicit_modifier_blocks(p["before_text"]):
            tmpl = normalise_stat_template(join_stats_for_csv(block["stat_lines"]))
            if not tmpl:
                continue
            before_obs.setdefault(tmpl, set()).add(p["test_id"])

        for block in parse_explicit_modifier_blocks(p["after_text"]):
            tmpl = normalise_stat_template(join_stats_for_csv(block["stat_lines"]))
            if not tmpl:
                continue
            after_obs.setdefault(tmpl, set()).add(p["test_id"])

    family_by_before: dict[str, dict[str, object]] = {}
    for family in family_summaries:
        before_tmpl = family.get("before_stat_template", "")
        if not before_tmpl:
            continue
        entry = family_by_before.setdefault(
            before_tmpl,
            {
                "has_mapping_family": False,
                "confirmed_family": False,
                "likely_family": False,
                "isolated_sample_count": 0,
                "likely_sample_count": 0,
                "sample_ids": set(),
            },
        )
        entry["has_mapping_family"] = True
        if family.get("confidence_summary") == "confirmed_family":
            entry["confirmed_family"] = True
        elif family.get("confidence_summary") == "likely_family":
            entry["likely_family"] = True
        entry["isolated_sample_count"] += int(family.get("isolated_sample_count", 0) or 0)
        entry["likely_sample_count"] += int(family.get("likely_sample_count", 0) or 0)
        ids = family.get("sample_ids", "")
        if ids:
            entry["sample_ids"].update(ids.split("|"))

    coverage_rows: list[dict[str, object]] = []
    for tmpl, data in pool_by_template.items():
        modifier_names = sorted({name for name in data["modifier_names"] if name})
        glove_classes = sorted({cls for cls in data["glove_classes"] if cls})
        pool_types = sorted({ptype for ptype in data["pool_types"] if ptype})
        seen_before = tmpl in before_obs
        seen_after = tmpl in after_obs
        family_info = family_by_before.get(
            tmpl,
            {
                "has_mapping_family": False,
                "confirmed_family": False,
                "likely_family": False,
                "isolated_sample_count": 0,
                "likely_sample_count": 0,
                "sample_ids": set(),
            },
        )
        sample_ids = set(family_info["sample_ids"]) | before_obs.get(tmpl, set())

        if family_info["confirmed_family"]:
            coverage_status = "confirmed_mapping"
        elif family_info["likely_family"]:
            coverage_status = "likely_mapping"
        elif seen_before:
            coverage_status = "captured_unmapped"
        elif "corrupted_enchantment" in pool_types:
            coverage_status = "corruption_only_missing"
        else:
            coverage_status = "missing_input_sample"

        coverage_rows.append(
            {
                "stat_template": tmpl,
                "modifier_names": ", ".join(modifier_names),
                "glove_classes": ", ".join(glove_classes),
                "pool_types": ", ".join(pool_types),
                "seen_as_before_input": str(seen_before),
                "seen_as_after_output": str(seen_after),
                "has_mapping_family": str(family_info["has_mapping_family"]),
                "confirmed_family": str(family_info["confirmed_family"]),
                "likely_family": str(family_info["likely_family"]),
                "isolated_sample_count": family_info["isolated_sample_count"],
                "likely_sample_count": family_info["likely_sample_count"],
                "sample_ids": "|".join(sorted(sample_ids)),
                "coverage_status": coverage_status,
            }
        )

    return coverage_rows


def write_glove_coverage_files(
    pairs: list[dict],
    observations: list[dict[str, object]],
    family_summaries: list[dict[str, object]],
    reference_entries: list[dict[str, str]],
) -> None:
    coverage_rows = compute_coverage_rows(pairs, family_summaries, reference_entries)

    pool_templates: set[str] = {
        entry.get("stat_template", "") for entry in reference_entries if entry.get("stat_template", "")
    }

    after_obs: dict[str, set[str]] = {}
    after_examples: dict[str, str] = {}

    for p in pairs:
        for block in parse_explicit_modifier_blocks(p["after_text"]):
            tmpl = normalise_stat_template(join_stats_for_csv(block["stat_lines"]))
            if not tmpl:
                continue
            after_obs.setdefault(tmpl, set()).add(p["test_id"])
            after_examples.setdefault(tmpl, join_stats_for_csv(block["stat_lines"]))

    if not reference_entries:
        print("No glove modifier reference pool found; coverage outputs are header-only.")
        with paths.GLOVE_COVERAGE_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(
                [
                    "stat_template",
                    "modifier_names",
                    "glove_classes",
                    "pool_types",
                    "seen_as_before_input",
                    "seen_as_after_output",
                    "has_mapping_family",
                    "confirmed_family",
                    "likely_family",
                    "isolated_sample_count",
                    "likely_sample_count",
                    "sample_ids",
                    "coverage_status",
                ]
            )

        with paths.TRANSFORMED_OUTPUT_ONLY_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(
                [
                    "after_stat_template",
                    "example_after_stats",
                    "sample_count",
                    "sample_ids",
                ]
            )

        write_capture_targets_csv([])
        return

    output_only_rows: list[dict[str, object]] = []
    for tmpl, sample_ids in after_obs.items():
        if tmpl not in pool_templates:
            output_only_rows.append(
                {
                    "after_stat_template": tmpl,
                    "example_after_stats": after_examples.get(tmpl, ""),
                    "sample_count": len(sample_ids),
                    "sample_ids": "|".join(sorted(sample_ids)),
                }
            )

    with paths.GLOVE_COVERAGE_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(
            [
                "stat_template",
                "modifier_names",
                "glove_classes",
                "pool_types",
                "seen_as_before_input",
                "seen_as_after_output",
                "has_mapping_family",
                "confirmed_family",
                "likely_family",
                "isolated_sample_count",
                "likely_sample_count",
                "sample_ids",
                "coverage_status",
            ]
        )
        for row in coverage_rows:
            writer.writerow(
                [
                    row["stat_template"],
                    row["modifier_names"],
                    row["glove_classes"],
                    row["pool_types"],
                    row["seen_as_before_input"],
                    row["seen_as_after_output"],
                    row["has_mapping_family"],
                    row["confirmed_family"],
                    row["likely_family"],
                    row["isolated_sample_count"],
                    row["likely_sample_count"],
                    row["sample_ids"],
                    row["coverage_status"],
                ]
            )

    with paths.TRANSFORMED_OUTPUT_ONLY_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(
            [
                "after_stat_template",
                "example_after_stats",
                "sample_count",
                "sample_ids",
            ]
        )
        for row in output_only_rows:
            writer.writerow(
                [
                    row["after_stat_template"],
                    row["example_after_stats"],
                    row["sample_count"],
                    row["sample_ids"],
                ]
            )

    write_capture_targets_csv(build_capture_targets(coverage_rows))
