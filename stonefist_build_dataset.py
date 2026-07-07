from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime
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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def get_field(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def normalise_item_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def content_hash(text: str) -> str:
    normalized = normalise_item_text(text)
    return hashlib.sha1(normalized.encode("utf-8", errors="ignore")).hexdigest()


def pair_hash(before: str, after: str) -> str:
    before_norm = normalise_item_text(before)
    after_norm = normalise_item_text(after)
    combined = f"{before_norm}\n---PAIR---\n{after_norm}"
    return hashlib.sha1(combined.encode("utf-8", errors="ignore")).hexdigest()


def get_rarity(text: str) -> str:
    return get_field(text, r"Rarity:\s*(.+)")


def get_item_class(text: str) -> str:
    return get_field(text, r"Item Class:\s*(.+)")


def load_meta(pair_dir: Path) -> dict[str, object]:
    meta_path = pair_dir / "meta.json"
    if not meta_path.exists():
        return {
            "captured_at": "",
            "character_level": "",
            "capture_version": None,
            "notes": "",
        }

    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "captured_at": "",
            "character_level": "",
            "capture_version": None,
            "notes": "",
        }

    return {
        "captured_at": data.get("captured_at", ""),
        "character_level": data.get("character_level", ""),
        "capture_version": data.get("capture_version"),
        "notes": data.get("notes", ""),
    }


def parse_explicit_modifier_blocks(text: str) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    lines = [line.rstrip() for line in text.splitlines()]

    header_pattern = re.compile(
        r'^(?:\{\s*)?(?P<kind>.+?)\s+"(?P<name>[^"]+)"(?:\s+\(Tier:\s*(?P<tier>\d+)\))?.*$'
    )

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        match = header_pattern.match(line)
        if not match:
            i += 1
            continue

        kind = match.group("kind").strip()
        if kind.endswith(" Modifier"):
            kind = kind[: -len(" Modifier")].strip()

        block = {
            "block_index": len(blocks) + 1,
            "modifier_kind": kind,
            "modifier_name": match.group("name").strip(),
            "tier": match.group("tier") or "",
            "header_line": line,
            "stat_lines": [],
        }

        i += 1
        while i < len(lines):
            stat_line = lines[i].strip()
            if not stat_line or stat_line == "--------":
                break
            if header_pattern.match(stat_line):
                break
            block["stat_lines"].append(stat_line)
            i += 1

        blocks.append(block)
        continue

    return blocks


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

    if GLOVE_MOD_POOL_JSON_PATH.exists():
        try:
            data = json.loads(GLOVE_MOD_POOL_JSON_PATH.read_text(encoding="utf-8"))
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

    if GLOVE_MOD_POOL_CSV_PATH.exists():
        entries = []
        with GLOVE_MOD_POOL_CSV_PATH.open("r", encoding="utf-8", newline="") as f:
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
    with CAPTURE_TARGETS_PATH.open("w", newline="", encoding="utf-8") as f:
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
        with GLOVE_COVERAGE_PATH.open("w", newline="", encoding="utf-8") as f:
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

        with TRANSFORMED_OUTPUT_ONLY_PATH.open("w", newline="", encoding="utf-8") as f:
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

    with GLOVE_COVERAGE_PATH.open("w", newline="", encoding="utf-8") as f:
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

    with TRANSFORMED_OUTPUT_ONLY_PATH.open("w", newline="", encoding="utf-8") as f:
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


def uid_status(before_uid: str, after_uid: str) -> str:
    if not before_uid and not after_uid:
        return "not present"
    if before_uid and after_uid and before_uid == after_uid:
        return "match"
    if before_uid and after_uid and before_uid != after_uid:
        return "mismatch"
    return "partial"


def get_name_base(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        if line.startswith("Rarity:"):
            name = lines[i + 1] if i + 1 < len(lines) else ""
            maybe_base = lines[i + 2] if i + 2 < len(lines) else ""

            if maybe_base == "--------":
                return name, ""

            return name, maybe_base

    return "", ""


def get_basic_stats(text: str) -> dict:
    return {
        "quality": get_field(text, r"Quality:\s*(.+)"),
        "evasion": get_field(text, r"Evasion(?: Rating)?:\s*(.+)"),
        "energy_shield": get_field(text, r"Energy Shield:\s*(.+)"),
        "armour": get_field(text, r"Armour:\s*(.+)"),
        "sockets": get_field(text, r"Sockets:\s*(.+)"),
        "rune": get_field(text, r"Rune:\s*(.+)"),
        "requirements": get_field(text, r"Requires:\s*(.+)"),
    }


def interesting_mod_lines(text: str) -> list[str]:
    ignored_prefixes = (
        "Item Class:",
        "Rarity:",
        "--------",
        "Item Level:",
        "Unique ID:",
        "Quality:",
        "Sockets:",
        "Rune:",
        "Requires:",
        "LevelReq:",
        "Implicits:",
        "Evasion:",
        "Evasion Rating:",
        "Energy Shield:",
        "Armour:",
    )

    out: list[str] = []

    for line in text.splitlines():
        s = line.strip()

        if not s:
            continue

        if s.startswith(ignored_prefixes):
            continue

        if (
            s.startswith("{")
            or s.startswith("+")
            or s.startswith("-")
            or "increased" in s
            or "reduced" in s
            or "more " in s
            or "less " in s
            or "chance" in s
            or "Leech" in s
            or "Recouped" in s
            or "per player level" in s
            or "Resistance" in s
            or "Accuracy" in s
            or "Blind" in s
            or "Onslaught" in s
            or s == "Unmodifiable"
        ):
            out.append(s)

    return out


def count_explicit_headers(lines: list[str]) -> int:
    return sum(
        1
        for line in lines
        if (
            "Prefix Modifier" in line
            or "Suffix Modifier" in line
            or "Crafted Prefix Modifier" in line
            or "Crafted Suffix Modifier" in line
            or "Desecrated Prefix Modifier" in line
            or "Desecrated Suffix Modifier" in line
        )
        and "Implicit Modifier" not in line
    )


def classify_pair(before_rarity: str, after_rarity: str) -> str:
    if before_rarity == "Unique" or after_rarity == "Unique":
        return "unique"
    if before_rarity == "Rare" or after_rarity == "Rare":
        return "rare"
    if before_rarity == "Magic" or after_rarity == "Magic":
        return "magic"
    if before_rarity == "Normal" or after_rarity == "Normal":
        return "normal"
    return "unknown"


def annotate_exact_duplicates(pairs: list[dict]) -> None:
    groups: dict[str, list[dict]] = {}

    for pair in pairs:
        groups.setdefault(pair["pair_hash"], []).append(pair)

    for duplicates in groups.values():
        group_size = len(duplicates)
        canonical = duplicates[0]
        canonical["is_exact_duplicate"] = False
        canonical["duplicate_of"] = ""
        canonical["duplicate_group_size"] = group_size

        for duplicate in duplicates[1:]:
            duplicate["is_exact_duplicate"] = True
            duplicate["duplicate_of"] = canonical["test_id"]
            duplicate["duplicate_group_size"] = group_size

        if group_size == 1:
            canonical["is_exact_duplicate"] = False
            canonical["duplicate_of"] = ""
            canonical["duplicate_group_size"] = 1


def load_pairs() -> list[dict]:
    if not PAIRS_DIR.exists():
        raise SystemExit(f"Could not find {PAIRS_DIR}")

    pairs: list[dict] = []

    for pair_dir in sorted(PAIRS_DIR.iterdir()):
        if not pair_dir.is_dir():
            continue

        before_path = pair_dir / "before.txt"
        after_path = pair_dir / "after.txt"

        if not before_path.exists() or not after_path.exists():
            continue

        before = read_text(before_path)
        after = read_text(after_path)

        before_name, before_base = get_name_base(before)
        after_name, after_base = get_name_base(after)

        before_lines = interesting_mod_lines(before)
        after_lines = interesting_mod_lines(after)

        before_uid = get_field(before, r"Unique ID:\s*(.+)")
        after_uid = get_field(after, r"Unique ID:\s*(.+)")

        before_rarity = get_rarity(before)
        after_rarity = get_rarity(after)

        meta = load_meta(pair_dir)
        status = uid_status(before_uid, after_uid)
        category = classify_pair(before_rarity, after_rarity)
        before_hash = content_hash(before)
        after_hash = content_hash(after)
        pair_hash_value = pair_hash(before, after)

        pairs.append(
            {
                "test_id": pair_dir.name,
                "before_path": str(before_path),
                "after_path": str(after_path),
                "before_text": before,
                "after_text": after,
                "before_item_class": get_item_class(before),
                "after_item_class": get_item_class(after),
                "before_rarity": before_rarity,
                "after_rarity": after_rarity,
                "category": category,
                "is_unique": category == "unique",
                "before_name": before_name,
                "before_base": before_base,
                "after_name": after_name,
                "after_base": after_base,
                "before_item_level": get_field(before, r"Item Level:\s*(.+)"),
                "after_item_level": get_field(after, r"Item Level:\s*(.+)"),
                "before_unique_id": before_uid,
                "after_unique_id": after_uid,
                "uid_status": status,
                "before_stats": get_basic_stats(before),
                "after_stats": get_basic_stats(after),
                "before_lines": before_lines,
                "after_lines": after_lines,
                "before_explicit_count": count_explicit_headers(before_lines),
                "after_explicit_count": count_explicit_headers(after_lines),
                "before_hash": before_hash,
                "after_hash": after_hash,
                "pair_hash": pair_hash_value,
                "captured_at": meta["captured_at"],
                "character_level": meta["character_level"],
                "capture_version": meta["capture_version"],
                "notes": meta["notes"],
                "is_exact_duplicate": False,
                "duplicate_of": "",
                "duplicate_group_size": 1,
            }
        )

    annotate_exact_duplicates(pairs)
    return pairs


def write_json_dataset(pairs: list[dict]) -> None:
    dataset = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "pair_count": len(pairs),
        "pairs": pairs,
    }

    DATASET_PATH.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")


def join_stats_for_csv(lines: list[str]) -> str:
    return " | ".join(line for line in lines if line)


def normalise_stat_template(stat_text: str) -> str:
    text = stat_text
    text = re.sub(
        r'([+-]?)\d+(?:\.\d+)?\(\d+(?:\.\d+)?-\d+(?:\.\d+)?\)',
        r'\1#',
        text,
    )
    text = re.sub(
        r'([+-]?)\d+(?:\.\d+)?-\d+(?:\.\d+)?',
        r'\1#-#',
        text,
    )
    text = re.sub(
        r'([+-]?)\d+(?:\.\d+)?',
        r'\1#',
        text,
    )
    return text


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

    with MAPPING_OBSERVATIONS_PATH.open("w", newline="", encoding="utf-8") as f:
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

    with MAPPING_CANDIDATES_PATH.open("w", newline="", encoding="utf-8") as f:
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

    with MAPPING_FAMILIES_PATH.open("w", newline="", encoding="utf-8") as f:
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

DEFENCE_FAMILY_BY_STATS = {
    (True, False, False): "STR",
    (False, True, False): "DEX",
    (False, False, True): "INT",
    (True, True, False): "STR/DEX",
    (True, False, True): "STR/INT",
    (False, True, True): "DEX/INT",
}

STONEFIST_EVASION_IMPLICIT_RE = re.compile(r"Has\s+\+(\d+(?:\.\d+)?)\s+to\s+Evasion Rating per player level")
STONEFIST_ENERGY_SHIELD_IMPLICIT_RE = re.compile(
    r"Has\s+\+(\d+(?:\.\d+)?)\s+to\s+maximum Energy Shield per player level"
)


def derive_defence_family(before_stats: dict[str, str]) -> str:
    has_armour = bool((before_stats.get("armour") or "").strip())
    has_evasion = bool((before_stats.get("evasion") or "").strip())
    has_energy_shield = bool((before_stats.get("energy_shield") or "").strip())

    return DEFENCE_FAMILY_BY_STATS.get((has_armour, has_evasion, has_energy_shield), "unknown")


def extract_stonefist_implicit_lines(after_text: str) -> list[str]:
    lines: list[str] = []
    for line in after_text.splitlines():
        s = line.strip()
        if STONEFIST_EVASION_IMPLICIT_RE.search(s) or STONEFIST_ENERGY_SHIELD_IMPLICIT_RE.search(s):
            lines.append(s)
    return lines


# "socket" alone (not just "socketed"/"socket control") deliberately covers
# every socket-related note wording. "rune"/"idol" as bare keywords also
# cover more specific phrasing like "Cat Idol", "Rune of Accumulation", and
# "Rune of Culmination" as substrings, without needing to list every case.
BASE_CONTROL_EXCLUDED_NOTE_KEYWORDS = (
    "socket",
    "rune",
    "idol",
    "augment",
    "stats ignored",
    "cannot use",
)


def is_normal_base_control_pair(pair: dict) -> bool:
    """Pure base-transformation controls only.

    Base Controls and Augment Controls must be mutually distinct: a normal,
    no-explicit-modifier glove that also has a socket (empty or not) is
    augment/socket evidence, not base-implicit evidence, even though it
    would otherwise satisfy the rarity/explicit-count/Stonefist conditions.
    """
    if pair.get("before_rarity") != "Normal":
        return False
    if int(pair.get("before_explicit_count", 0) or 0) != 0:
        return False
    if "Fists of Stone" not in pair.get("after_text", ""):
        return False

    before_text = pair.get("before_text", "")
    if extract_socket_lines(before_text):
        return False
    if extract_augment_lines(before_text):
        return False

    notes_lower = (pair.get("notes", "") or "").lower()
    if any(keyword in notes_lower for keyword in BASE_CONTROL_EXCLUDED_NOTE_KEYWORDS):
        return False

    return True


def compute_base_control_rows(pairs: list[dict]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for p in pairs:
        if not is_normal_base_control_pair(p):
            continue

        before_stats = p.get("before_stats", {}) or {}
        after_stats = p.get("after_stats", {}) or {}
        after_text = p.get("after_text", "")

        implicit_lines = extract_stonefist_implicit_lines(after_text)
        implicit_template = " | ".join(normalise_stat_template(line) for line in implicit_lines)

        evasion_per_level = ""
        energy_shield_per_level = ""
        for line in implicit_lines:
            evasion_match = STONEFIST_EVASION_IMPLICIT_RE.search(line)
            if evasion_match:
                evasion_per_level = evasion_match.group(1)
            energy_shield_match = STONEFIST_ENERGY_SHIELD_IMPLICIT_RE.search(line)
            if energy_shield_match:
                energy_shield_per_level = energy_shield_match.group(1)

        rows.append(
            {
                "sample_id": p.get("test_id", ""),
                "character_level": p.get("character_level", ""),
                "before_name": p.get("before_name", ""),
                "before_base_type": p.get("before_name", ""),
                "before_defence_family": derive_defence_family(before_stats),
                "before_armour": before_stats.get("armour", ""),
                "before_evasion": before_stats.get("evasion", ""),
                "before_energy_shield": before_stats.get("energy_shield", ""),
                "after_evasion": after_stats.get("evasion", ""),
                "after_energy_shield": after_stats.get("energy_shield", ""),
                "evasion_per_level": evasion_per_level,
                "energy_shield_per_level": energy_shield_per_level,
                "after_implicit_templates": implicit_template,
                "notes": p.get("notes", ""),
            }
        )

    rows.sort(key=lambda row: row["sample_id"])
    return rows


def write_base_control_summary_csv(rows: list[dict[str, object]]) -> None:
    with BASE_CONTROL_SUMMARY_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(BASE_CONTROL_FIELDNAMES)
        for row in rows:
            writer.writerow([row.get(field, "") for field in BASE_CONTROL_FIELDNAMES])


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

# Not an exhaustive augment database - just enough keyword grouping to give
# representative control evidence about whether Stonefist preserves sockets
# and whatever is socketed into them. Checked in order, so more specific
# families (combo, life/mana-on-hit, accuracy) are matched before broader
# ones. This classifies the *visible effect text* only - see
# classify_socketed_augment_source for what item produced that effect.
AUGMENT_FAMILY_KEYWORDS = [
    ("combo", ("Combo",)),
    ("life_mana_on_hit", ("Life per Enemy Hit", "Mana per Enemy Hit")),
    ("accuracy", ("Accuracy Rating", "Accuracy")),
    ("attribute", ("Strength", "Dexterity", "Intelligence")),
    ("resistance", ("Resistance",)),
    ("armour_evasion_energy_shield", ("Armour", "Evasion", "Energy Shield")),
    ("mana_regen", ("Mana Regeneration", "Mana per Second", "Mana Regen")),
    ("life_regen", ("Life Regeneration", "Life per Second", "Life Regen")),
    ("idol", ("Idol",)),
]

# The PoE2 clipboard shows this exact line when the transformed item cannot be
# used by the currently logged-in (capture) character - e.g. a class/ascendancy
# mismatch. It is a per-character fact, not a global "item is unusable" fact.
USABILITY_WARNING_TEXT = "You cannot use this item. Its stats will be ignored"

# PoE2 renders a socketed Idol's effect the same way as a socketed Rune's
# effect - a standalone "... (rune)" line. The visible item text does not
# preserve which kind of augment item was actually used, so the augment
# *source* can only be inferred from capture notes/meta, never from the
# stat line itself. augment_family above is the visible effect; this is the
# separate, optional, notes-only claim about what produced it.
SOCKETED_AUGMENT_SOURCE_KEYWORDS = [
    ("idol", ("idol",)),
    ("rune", ("rune",)),
]

USABILITY_LABELS = {"true": "usable", "false": "unusable", "unknown": "unknown"}


def extract_socket_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip().startswith("Sockets:")]


def count_sockets(socket_lines: list[str]) -> int:
    total = 0
    for line in socket_lines:
        _, _, value = line.partition(":")
        total += len(value.split())
    return total


def extract_augment_lines(text: str) -> list[str]:
    """Extract socketed-rune evidence lines.

    Real PoE2 clipboard text does not reliably use a "Rune:" header - a
    socketed rune's effect usually just appears as its own line ending in
    "(rune)", e.g. "Gain 3 Life per Enemy Hit with Attacks (rune)". Multiple
    such lines can belong to the same rune. A "Rune:" header (if it ever
    appears) is still supported, with any immediately following stat lines
    treated as part of that rune's evidence.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    augment_lines: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if "(rune)" in line:
            augment_lines.append(line)
            i += 1
            continue

        if line.startswith("Rune:"):
            augment_lines.append(line)
            i += 1

            while i < len(lines):
                nxt = lines[i].strip()
                if not nxt or nxt == "--------":
                    break
                augment_lines.append(nxt)
                i += 1
            continue

        i += 1

    return augment_lines


def classify_socket_behaviour(before_count: int, after_count: int) -> str:
    """Whether the socket itself survives the transformation.

    Independent of whether the transformed item is usable by the capture
    character - a socket can be preserved on an item that character cannot
    currently wear.
    """
    if before_count == 0 and after_count == 0:
        return "unknown"
    if after_count == before_count:
        return "preserved"
    if after_count == 0:
        return "removed"
    return "changed"


def classify_augment_line_behaviour(before_lines: list[str], after_lines: list[str]) -> str:
    """Whether the socketed rune's displayed text survives the transformation.

    This only compares the visible rune text, not whether its effect is
    actually usable by the capture character - see
    classify_augment_effect_status_for_capture_character for that.
    """
    before_joined = " | ".join(before_lines).strip()
    after_joined = " | ".join(after_lines).strip()

    if not before_joined and not after_joined:
        return "absent"
    if before_joined and not after_joined:
        return "removed"
    if not before_joined and after_joined:
        return "changed"
    if before_joined == after_joined:
        return "preserved"
    return "changed"


def usability_for_capture_character(text: str, notes: str) -> tuple[str, bool]:
    """Returns (usable_for_capture_character, stats_ignored_for_capture_character).

    This is deliberately per-character, not a global item property: the same
    transformed item may be perfectly usable by a different character (or a
    Monk with a different ascendancy). We only ever claim "false" when the
    clipboard itself shows the "cannot use this item" warning for the
    currently logged-in capture character, and only ever claim "true" when
    capture notes explicitly confirm the item was usable/equipped/wearable.
    Otherwise the honest answer is "unknown".
    """
    if USABILITY_WARNING_TEXT in text:
        return "false", True

    notes_lower = (notes or "").lower()
    if any(keyword in notes_lower for keyword in ("usable", "equipped", "wearable")):
        return "true", False

    return "unknown", False


def classify_usability_behaviour(before_usable: str, after_usable: str) -> str:
    before_label = USABILITY_LABELS.get(before_usable, "unknown")
    after_label = USABILITY_LABELS.get(after_usable, "unknown")

    if before_label == "unknown" and after_label == "unknown":
        return "unknown"

    return f"{before_label}_to_{after_label}"


def classify_augment_effect_status_for_capture_character(
    augment_line_behaviour: str,
    after_stats_ignored: bool,
    after_usable: str,
) -> str:
    """Whether the rune's *effect* actually applies for the capture character.

    Rune text can be preserved word-for-word while its effect is ignored,
    if the transformed item cannot currently be used by that character.
    """
    if augment_line_behaviour == "absent":
        return "unknown"
    if after_stats_ignored:
        return "ignored"
    if after_usable == "true":
        return "active"
    return "unknown"


def derive_augment_family(augment_lines: list[str], socket_count: int) -> str:
    if not augment_lines:
        return "empty_socket" if socket_count > 0 else "unknown"

    combined = " ".join(augment_lines)
    for family, keywords in AUGMENT_FAMILY_KEYWORDS:
        if any(keyword in combined for keyword in keywords):
            return family

    return "other"


def classify_socketed_augment_source(notes: str) -> str:
    """What kind of item was socketed to produce the augment effect: 'rune',
    'idol', or 'unknown'.

    Deliberately notes/meta-only, never inferred from the visible item stat
    line - PoE2 renders a socketed Idol's effect the same way as a Rune's
    (a plain "... (rune)" line), so the clipboard text alone cannot tell
    them apart.
    """
    notes_lower = (notes or "").lower()
    for source, keywords in SOCKETED_AUGMENT_SOURCE_KEYWORDS:
        if any(keyword in notes_lower for keyword in keywords):
            return source

    return "unknown"


def extract_display_name_and_base(text: str) -> tuple[str, str]:
    """Like get_name_base, but skips the "cannot use this item" warning line
    if the game inserted it before the real item name/base display line, so
    that column does not end up showing warning text instead of a name."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        if not line.startswith("Rarity:"):
            continue

        j = i + 1
        if j < len(lines) and lines[j] == USABILITY_WARNING_TEXT:
            # The warning is its own header block: warning line, then a
            # "--------" divider, then the real name starts a new block.
            j += 1
            if j < len(lines) and lines[j] == "--------":
                j += 1

        name = lines[j] if j < len(lines) else ""
        maybe_base = lines[j + 1] if j + 1 < len(lines) else ""

        if maybe_base == "--------":
            return name, ""

        return name, maybe_base

    return "", ""


def is_socket_augment_control_pair(pair: dict) -> bool:
    before_socket_count = count_sockets(extract_socket_lines(pair.get("before_text", "")))
    return before_socket_count > 0 and "Fists of Stone" in pair.get("after_text", "")


def compute_augment_socket_rows(pairs: list[dict]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for p in pairs:
        if not is_socket_augment_control_pair(p):
            continue

        before_text = p.get("before_text", "")
        after_text = p.get("after_text", "")

        before_socket_lines = extract_socket_lines(before_text)
        after_socket_lines = extract_socket_lines(after_text)
        before_socket_count = count_sockets(before_socket_lines)
        after_socket_count = count_sockets(after_socket_lines)

        before_augment_lines = extract_augment_lines(before_text)
        after_augment_lines = extract_augment_lines(after_text)

        family_lines = before_augment_lines or after_augment_lines
        notes = p.get("notes", "")

        before_name, before_base_type = extract_display_name_and_base(before_text)
        after_name, after_base_type = extract_display_name_and_base(after_text)
        before_base_type = before_base_type or before_name
        after_base_type = after_base_type or after_name

        augment_line_behaviour = classify_augment_line_behaviour(before_augment_lines, after_augment_lines)
        before_usable, _before_ignored = usability_for_capture_character(before_text, notes)
        after_usable, after_ignored = usability_for_capture_character(after_text, notes)

        rows.append(
            {
                "sample_id": p.get("test_id", ""),
                "character_level": p.get("character_level", ""),
                "before_rarity": p.get("before_rarity", ""),
                "before_name": before_name,
                "before_base_type": before_base_type,
                "after_name": after_name,
                "after_base_type": after_base_type,
                "before_socket_count": before_socket_count,
                "after_socket_count": after_socket_count,
                "before_socket_lines": " | ".join(before_socket_lines),
                "after_socket_lines": " | ".join(after_socket_lines),
                "before_augment_lines": " | ".join(before_augment_lines),
                "after_augment_lines": " | ".join(after_augment_lines),
                "augment_family": derive_augment_family(family_lines, before_socket_count),
                "socketed_augment_source": classify_socketed_augment_source(notes),
                "socket_behaviour": classify_socket_behaviour(before_socket_count, after_socket_count),
                "augment_line_behaviour": augment_line_behaviour,
                "before_usable_for_capture_character": before_usable,
                "after_usable_for_capture_character": after_usable,
                "after_stats_ignored_for_capture_character": str(after_ignored).lower(),
                "usability_behaviour_for_capture_character": classify_usability_behaviour(
                    before_usable, after_usable
                ),
                "augment_effect_status_for_capture_character": classify_augment_effect_status_for_capture_character(
                    augment_line_behaviour, after_ignored, after_usable
                ),
                "notes": notes,
            }
        )

    rows.sort(key=lambda row: row["sample_id"])
    return rows


def write_augment_socket_summary_csv(rows: list[dict[str, object]]) -> None:
    with AUGMENT_SOCKET_SUMMARY_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(AUGMENT_SOCKET_FIELDNAMES)
        for row in rows:
            writer.writerow([row.get(field, "") for field in AUGMENT_SOCKET_FIELDNAMES])


def write_csvs(pairs: list[dict]) -> None:
    with PAIR_SUMMARY_PATH.open("w", newline="", encoding="utf-8") as f:
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

    with MOD_LINES_PATH.open("w", newline="", encoding="utf-8") as f:
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
    print(f"Wrote: {DATASET_PATH}")
    print(f"Wrote: {PAIR_SUMMARY_PATH}")
    print(f"Wrote: {MOD_LINES_PATH}")


if __name__ == "__main__":
    main()
