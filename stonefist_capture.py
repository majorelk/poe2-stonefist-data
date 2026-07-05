from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path

import pyperclip


OUT_DIR = Path("stonefist-captures")
RAW_DIR = OUT_DIR / "raw"
PAIRS_DIR = OUT_DIR / "pairs"
CSV_PATH = OUT_DIR / "pairs.csv"
JSONL_PATH = OUT_DIR / "pairs.jsonl"

OUT_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(exist_ok=True)
PAIRS_DIR.mkdir(exist_ok=True)


def short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:12]


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def is_likely_poe_item(text: str) -> bool:
    if not text or len(text.strip()) < 20:
        return False

    item_markers = [
        "Item Class:",
        "Rarity:",
        "Item Level:",
        "Unique ID:",
        "Sockets:",
        "Requires:",
        "LevelReq:",
        "Evasion Rating:",
        "Energy Shield:",
        "Armour:",
    ]

    return sum(marker in text for marker in item_markers) >= 2


def is_stonefist_transformed(text: str) -> bool:
    return (
        "Fists of Stone" in text
        or "per player level" in text
        or "Unmodifiable" in text and "Evasion Rating" in text and "Energy Shield" in text
    )


def get_field(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def get_name_and_base(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Normal PoE Ctrl+C format:
    # Item Class: Gloves
    # Rarity: Rare
    # Dread Knuckle
    # Fists of Stone
    for i, line in enumerate(lines):
        if line.startswith("Rarity:"):
            name = lines[i + 1] if i + 1 < len(lines) else ""
            base = lines[i + 2] if i + 2 < len(lines) else ""
            return name, base

    # Fallback for formats without Item Class / Rarity:
    # Dread Knuckle
    # Adorned Wraps
    ignored_prefixes = (
        "Item Class:",
        "Rarity:",
        "--------",
        "Evasion:",
        "Evasion Rating:",
        "Energy Shield:",
        "Armour:",
        "Unique ID:",
        "Item Level:",
        "Quality:",
        "Sockets:",
        "Rune:",
        "LevelReq:",
        "Requires:",
        "Implicits:",
    )

    candidate_lines = [
        line for line in lines
        if not line.startswith(ignored_prefixes)
        and not line.startswith("{")
        and not line.startswith("+")
        and not line.startswith("-")
    ]

    name = candidate_lines[0] if len(candidate_lines) > 0 else ""
    base = candidate_lines[1] if len(candidate_lines) > 1 else ""
    return name, base


def guess_mod_lines(text: str) -> list[str]:
    useful = []

    for line in text.splitlines():
        clean = line.strip()

        if not clean:
            continue

        if clean.startswith((
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
        )):
            continue

        if (
            clean.startswith("{")
            or clean.startswith("+")
            or clean.startswith("-")
            or "increased" in clean
            or "reduced" in clean
            or "chance" in clean
            or "Leech" in clean
            or "Recouped" in clean
            or "per player level" in clean
            or clean == "Unmodifiable"
        ):
            useful.append(clean)

    return useful


def save_raw_capture(text: str, kind: str) -> dict:
    name, base = get_name_and_base(text)
    h = short_hash(text)
    file_path = RAW_DIR / f"{timestamp()}-{kind}-{h}.txt"
    file_path.write_text(text, encoding="utf-8")

    return {
        "kind": kind,
        "name": name,
        "base": base,
        "item_level": get_field(text, r"Item Level:\s*(.+)"),
        "unique_id": get_field(text, r"Unique ID:\s*(.+)"),
        "hash": h,
        "file": str(file_path),
        "mods_guess": guess_mod_lines(text),
        "raw_text": text,
    }


def ensure_csv_header() -> None:
    if CSV_PATH.exists():
        return

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "test_id",
            "timestamp",
            "character_level",
            "original_name",
            "original_base",
            "original_item_level",
            "original_unique_id",
            "transformed_name",
            "transformed_base",
            "transformed_item_level",
            "transformed_unique_id",
            "before_file",
            "after_file",
            "notes",
        ])


def append_pair_csv(pair: dict) -> None:
    ensure_csv_header()

    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            pair["test_id"],
            pair["timestamp"],
            pair["character_level"],
            pair["before"]["name"],
            pair["before"]["base"],
            pair["before"]["item_level"],
            pair["before"]["unique_id"],
            pair["after"]["name"],
            pair["after"]["base"],
            pair["after"]["item_level"],
            pair["after"]["unique_id"],
            pair["before_file"],
            pair["after_file"],
            pair["notes"],
        ])


def append_pair_jsonl(pair: dict) -> None:
    with JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(pair, ensure_ascii=False) + "\n")


def main() -> None:
    print("Way of the Stonefist clipboard capture")
    print()
    print("Use this order:")
    print("1. Hover the original glove while unequipped/in inventory, then press Ctrl+C in PoE2.")
    print("2. Equip the glove with Way of the Stonefist allocated.")
    print("3. Hover the transformed glove, then press Ctrl+C in PoE2.")
    print()
    print("Press Ctrl+C in this terminal to stop.")
    print()

    character_level = input("Character level for this session, or blank to skip: ").strip()

    last_clip_hash = ""
    pending_before = None
    test_number = 1

    while True:
        try:
            clip = pyperclip.paste()
        except Exception as exc:
            print(f"Could not read clipboard: {exc}")
            time.sleep(1)
            continue

        clip_hash = short_hash(clip)

        if clip_hash == last_clip_hash:
            time.sleep(0.25)
            continue

        last_clip_hash = clip_hash

        if not is_likely_poe_item(clip):
            time.sleep(0.25)
            continue

        kind = "after" if is_stonefist_transformed(clip) else "before"
        record = save_raw_capture(clip, kind)

        if kind == "before":
            pending_before = record
            print(f"[BEFORE] {record['name']} / {record['base']} / ilvl {record['item_level']}")
            time.sleep(0.25)
            continue

        print(f"[AFTER]  {record['name']} / {record['base']} / ilvl {record['item_level']}")

        if pending_before is None:
            print("No pending BEFORE capture. Saved raw AFTER only.")
            time.sleep(0.25)
            continue

        test_id = f"STONEFIST-{test_number:04d}"
        test_number += 1

        pair_dir = PAIRS_DIR / test_id
        pair_dir.mkdir(exist_ok=True)

        before_path = pair_dir / "before.txt"
        after_path = pair_dir / "after.txt"

        before_path.write_text(pending_before["raw_text"], encoding="utf-8")
        after_path.write_text(record["raw_text"], encoding="utf-8")

        before_for_json = {k: v for k, v in pending_before.items() if k != "raw_text"}
        after_for_json = {k: v for k, v in record.items() if k != "raw_text"}

        pair = {
            "test_id": test_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "character_level": character_level,
            "before_file": str(before_path),
            "after_file": str(after_path),
            "before": before_for_json,
            "after": after_for_json,
            "notes": "Original copied before transformation. Transformed copied while equipped with Way of the Stonefist.",
        }

        append_pair_csv(pair)
        append_pair_jsonl(pair)

        print(f"Paired as {test_id}")
        print(f"Saved to: {pair_dir}")
        print()

        pending_before = None
        time.sleep(0.25)


if __name__ == "__main__":
    main()