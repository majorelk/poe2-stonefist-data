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


def write_csvs(pairs: list[dict]) -> None:
    with PAIR_SUMMARY_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
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
        writer = csv.writer(f)
        writer.writerow(["test_id", "category", "side", "line_number", "mod_line"])

        for p in pairs:
            for i, line in enumerate(p["before_lines"], start=1):
                writer.writerow([p["test_id"], p["category"], "before", i, line])

            for i, line in enumerate(p["after_lines"], start=1):
                writer.writerow([p["test_id"], p["category"], "after", i, line])


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
