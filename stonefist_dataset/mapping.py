from __future__ import annotations

import csv

from stonefist_dataset.coverage import load_glove_mod_pool, write_glove_coverage_files
from stonefist_dataset.explicit_mods import parse_explicit_modifier_blocks
from stonefist_dataset.item_text import join_stats_for_csv, normalise_stat_template
from stonefist_dataset import paths


def build_mapping_observations(pairs: list[dict]) -> list[dict[str, object]]:
    observations: list[dict[str, object]] = []

    for p in pairs:
        before_blocks = parse_explicit_modifier_blocks(p["before_text"])
        after_blocks = parse_explicit_modifier_blocks(p["after_text"])
        before_count = len(before_blocks)
        after_count = len(after_blocks)
        exact_duplicate = bool(p["is_exact_duplicate"])

        def make_observation(before_index: int, after_index: int, confidence: str, match_method: str) -> dict[str, object]:
            before_stats = join_stats_for_csv(before_blocks[before_index]["stat_lines"])
            after_stats = join_stats_for_csv(after_blocks[after_index]["stat_lines"])
            return {
                "test_id": p["test_id"],
                "character_level": p["character_level"],
                "category": p["category"],
                "confidence": confidence,
                "match_method": match_method,
                "before_block_index": before_blocks[before_index]["block_index"],
                "before_modifier_kind": before_blocks[before_index]["modifier_kind"],
                "before_modifier_name": before_blocks[before_index]["modifier_name"],
                "before_tier": before_blocks[before_index]["tier"],
                "before_header": before_blocks[before_index]["header_line"],
                "before_stats": before_stats,
                "before_stat_template": normalise_stat_template(before_stats),
                "after_block_index": after_blocks[after_index]["block_index"],
                "after_modifier_kind": after_blocks[after_index]["modifier_kind"],
                "after_modifier_name": after_blocks[after_index]["modifier_name"],
                "after_tier": after_blocks[after_index]["tier"],
                "after_header": after_blocks[after_index]["header_line"],
                "after_stats": after_stats,
                "after_stat_template": normalise_stat_template(after_stats),
                "is_exact_duplicate": exact_duplicate,
                "duplicate_of": p["duplicate_of"],
            }

        if before_count == 0 or after_count == 0:
            confidence = "duplicate_observation" if exact_duplicate else "ambiguous_count_mismatch"
            match_method = "duplicate" if exact_duplicate else "unmatched"
            for index in range(min(before_count, after_count)):
                observations.append(
                    make_observation(index, index, confidence, match_method)
                )
            continue

        before_name_counts: dict[str, int] = {}
        after_name_counts: dict[str, int] = {}
        for block in before_blocks:
            before_name_counts[block["modifier_name"]] = before_name_counts.get(block["modifier_name"], 0) + 1
        for block in after_blocks:
            after_name_counts[block["modifier_name"]] = after_name_counts.get(block["modifier_name"], 0) + 1

        matched_before = set()
        matched_after = set()

        unique_names = []
        for index, block in enumerate(before_blocks):
            name = block["modifier_name"]
            if before_name_counts.get(name, 0) == 1 and after_name_counts.get(name, 0) == 1:
                unique_names.append(name)

        for name in unique_names:
            before_index = next(i for i, block in enumerate(before_blocks) if block["modifier_name"] == name and i not in matched_before)
            after_index = next(i for i, block in enumerate(after_blocks) if block["modifier_name"] == name and i not in matched_after)
            if exact_duplicate:
                confidence = "duplicate_observation"
                match_method = "duplicate"
            elif before_count == 1 and after_count == 1:
                confidence = "confirmed_isolated"
                match_method = "isolated"
            else:
                confidence = "likely_by_name"
                match_method = "modifier_name"
            observations.append(make_observation(before_index, after_index, confidence, match_method))
            matched_before.add(before_index)
            matched_after.add(after_index)

        remaining_before = [i for i in range(before_count) if i not in matched_before]
        remaining_after = [i for i in range(after_count) if i not in matched_after]

        if remaining_before and remaining_after:
            safe_order_fallback = (
                len(remaining_before) == len(remaining_after)
                and all(before_name_counts[before_blocks[i]["modifier_name"]] == 1 for i in remaining_before)
                and all(after_name_counts[after_blocks[i]["modifier_name"]] == 1 for i in remaining_after)
            )

            if safe_order_fallback:
                for before_index, after_index in zip(remaining_before, remaining_after):
                    if exact_duplicate:
                        confidence = "duplicate_observation"
                        match_method = "duplicate"
                    else:
                        confidence = "likely_by_order_fallback"
                        match_method = "order_fallback"
                    observations.append(make_observation(before_index, after_index, confidence, match_method))
            else:
                for before_index, after_index in zip(remaining_before, remaining_after):
                    if exact_duplicate:
                        confidence = "duplicate_observation"
                        match_method = "duplicate"
                    else:
                        confidence = "ambiguous_unmatched"
                        match_method = "unmatched"
                    observations.append(make_observation(before_index, after_index, confidence, match_method))

    return observations


def summarize_mapping_candidates(observations: list[dict]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str, str], dict[str, object]] = {}

    for obs in observations:
        key = (
            obs["before_modifier_name"],
            obs["before_stats"],
            obs["after_modifier_name"],
            obs["after_stats"],
        )

        if key not in groups:
            groups[key] = {
                "before_modifier_name": obs["before_modifier_name"],
                "before_stats": obs["before_stats"],
                "after_modifier_name": obs["after_modifier_name"],
                "after_stats": obs["after_stats"],
                "sample_count": 0,
                "isolated_sample_count": 0,
                "likely_sample_count": 0,
                "duplicate_sample_count": 0,
                "sample_ids_set": set(),
                "character_levels_set": set(),
            }

        group = groups[key]
        group["sample_count"] += 1
        group["sample_ids_set"].add(obs["test_id"])
        if obs["character_level"]:
            group["character_levels_set"].add(obs["character_level"])

        if obs["confidence"] == "confirmed_isolated":
            group["isolated_sample_count"] += 1
        elif obs["confidence"] in ("likely_by_order", "likely_by_name", "likely_by_order_fallback"):
            group["likely_sample_count"] += 1
        elif obs["confidence"] == "duplicate_observation":
            group["duplicate_sample_count"] += 1

    summaries: list[dict[str, object]] = []
    for group in groups.values():
        sample_count = group["sample_count"]
        isolated_sample_count = group["isolated_sample_count"]
        likely_sample_count = group["likely_sample_count"]
        duplicate_sample_count = group["duplicate_sample_count"]

        if isolated_sample_count >= 1:
            confidence_summary = "confirmed_candidate"
        elif likely_sample_count >= 1 and isolated_sample_count == 0:
            confidence_summary = "likely_candidate"
        elif duplicate_sample_count == sample_count:
            confidence_summary = "duplicate_only"
        else:
            confidence_summary = "ambiguous"

        summaries.append(
            {
                "before_modifier_name": group["before_modifier_name"],
                "before_stats": group["before_stats"],
                "after_modifier_name": group["after_modifier_name"],
                "after_stats": group["after_stats"],
                "sample_count": sample_count,
                "isolated_sample_count": isolated_sample_count,
                "likely_sample_count": likely_sample_count,
                "duplicate_sample_count": duplicate_sample_count,
                "sample_ids": "|".join(sorted(group["sample_ids_set"])),
                "character_levels": "|".join(sorted(group["character_levels_set"])),
                "confidence_summary": confidence_summary,
            }
        )

    return summaries


def summarize_mapping_families(observations: list[dict]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], dict[str, object]] = {}

    for obs in observations:
        key = (
            obs["before_stat_template"],
            obs["after_stat_template"],
        )

        if key not in groups:
            groups[key] = {
                "before_stat_template": obs["before_stat_template"],
                "after_stat_template": obs["after_stat_template"],
                "sample_count": 0,
                "isolated_sample_count": 0,
                "likely_sample_count": 0,
                "duplicate_sample_count": 0,
                "sample_ids_set": set(),
                "character_levels_set": set(),
                "before_modifier_names_set": set(),
                "after_modifier_names_set": set(),
                "example_before_stats": "",
                "example_after_stats": "",
            }

        group = groups[key]
        group["sample_count"] += 1
        group["sample_ids_set"].add(obs["test_id"])
        if obs["character_level"]:
            group["character_levels_set"].add(obs["character_level"])
        group["before_modifier_names_set"].add(obs["before_modifier_name"])
        group["after_modifier_names_set"].add(obs["after_modifier_name"])
        if not group["example_before_stats"]:
            group["example_before_stats"] = obs["before_stats"]
        if not group["example_after_stats"]:
            group["example_after_stats"] = obs["after_stats"]

        if obs["confidence"] == "confirmed_isolated":
            group["isolated_sample_count"] += 1
        elif obs["confidence"] in ("likely_by_order", "likely_by_name", "likely_by_order_fallback"):
            group["likely_sample_count"] += 1
        elif obs["confidence"] == "duplicate_observation":
            group["duplicate_sample_count"] += 1

    summaries: list[dict[str, object]] = []
    for group in groups.values():
        if group["sample_count"] == group["duplicate_sample_count"]:
            confidence_summary = "duplicate_only"
        elif group["isolated_sample_count"] >= 1:
            confidence_summary = "confirmed_family"
        elif group["likely_sample_count"] >= 1:
            confidence_summary = "likely_family"
        else:
            confidence_summary = "ambiguous"

        summaries.append(
            {
                "before_stat_template": group["before_stat_template"],
                "after_stat_template": group["after_stat_template"],
                "before_modifier_names": ", ".join(sorted(group["before_modifier_names_set"])),
                "after_modifier_names": ", ".join(sorted(group["after_modifier_names_set"])),
                "sample_count": group["sample_count"],
                "isolated_sample_count": group["isolated_sample_count"],
                "likely_sample_count": group["likely_sample_count"],
                "duplicate_sample_count": group["duplicate_sample_count"],
                "sample_ids": "|".join(sorted(group["sample_ids_set"])),
                "character_levels": "|".join(sorted(group["character_levels_set"])),
                "confidence_summary": confidence_summary,
                "example_before_stats": group["example_before_stats"],
                "example_after_stats": group["example_after_stats"],
            }
        )

    return summaries


def write_mapping_csvs(pairs: list[dict]) -> None:
    observations = build_mapping_observations(pairs)
    summaries = summarize_mapping_candidates(observations)
    family_summaries = summarize_mapping_families(observations)

    with paths.MAPPING_OBSERVATIONS_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(
            [
                "test_id",
                "character_level",
                "category",
                "confidence",
                "match_method",
                "before_block_index",
                "before_modifier_kind",
                "before_modifier_name",
                "before_tier",
                "before_header",
                "before_stats",
                "after_block_index",
                "after_modifier_kind",
                "after_modifier_name",
                "after_tier",
                "after_header",
                "after_stats",
                "is_exact_duplicate",
                "duplicate_of",
            ]
        )

        for obs in observations:
            writer.writerow(
                [
                    obs["test_id"],
                    obs["character_level"],
                    obs["category"],
                    obs["confidence"],
                    obs["match_method"],
                    obs["before_block_index"],
                    obs["before_modifier_kind"],
                    obs["before_modifier_name"],
                    obs["before_tier"],
                    obs["before_header"],
                    obs["before_stats"],
                    obs["after_block_index"],
                    obs["after_modifier_kind"],
                    obs["after_modifier_name"],
                    obs["after_tier"],
                    obs["after_header"],
                    obs["after_stats"],
                    str(obs["is_exact_duplicate"]),
                    obs["duplicate_of"],
                ]
            )

    with paths.MAPPING_CANDIDATES_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(
            [
                "before_modifier_name",
                "before_stats",
                "after_modifier_name",
                "after_stats",
                "sample_count",
                "isolated_sample_count",
                "likely_sample_count",
                "duplicate_sample_count",
                "sample_ids",
                "character_levels",
                "confidence_summary",
            ]
        )

        for group in summaries:
            writer.writerow(
                [
                    group["before_modifier_name"],
                    group["before_stats"],
                    group["after_modifier_name"],
                    group["after_stats"],
                    group["sample_count"],
                    group["isolated_sample_count"],
                    group["likely_sample_count"],
                    group["duplicate_sample_count"],
                    group["sample_ids"],
                    group["character_levels"],
                    group["confidence_summary"],
                ]
            )

    with paths.MAPPING_FAMILIES_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(
            [
                "before_stat_template",
                "after_stat_template",
                "before_modifier_names",
                "after_modifier_names",
                "sample_count",
                "isolated_sample_count",
                "likely_sample_count",
                "duplicate_sample_count",
                "sample_ids",
                "character_levels",
                "confidence_summary",
                "example_before_stats",
                "example_after_stats",
            ]
        )

        for group in family_summaries:
            writer.writerow(
                [
                    group["before_stat_template"],
                    group["after_stat_template"],
                    group["before_modifier_names"],
                    group["after_modifier_names"],
                    group["sample_count"],
                    group["isolated_sample_count"],
                    group["likely_sample_count"],
                    group["duplicate_sample_count"],
                    group["sample_ids"],
                    group["character_levels"],
                    group["confidence_summary"],
                    group["example_before_stats"],
                    group["example_after_stats"],
                ]
            )

    reference_entries = load_glove_mod_pool()
    write_glove_coverage_files(pairs, observations, family_summaries, reference_entries)
