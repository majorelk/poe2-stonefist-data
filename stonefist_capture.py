from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path

import pyperclip # pyright: ignore[reportMissingModuleSource]


OUT_DIR = Path("stonefist-captures")
RAW_DIR = OUT_DIR / "raw"
PAIRS_DIR = OUT_DIR / "pairs"

OUT_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(exist_ok=True)
PAIRS_DIR.mkdir(exist_ok=True)


def short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:12]


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def get_field(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def get_rarity(text: str) -> str:
    return get_field(text, r"Rarity:\s*(.+)")


def get_item_class(text: str) -> str:
    return get_field(text, r"Item Class:\s*(.+)")


def uid_status(before_uid: str, after_uid: str) -> str:
    if not before_uid and not after_uid:
        return "not present"
    if before_uid and after_uid and before_uid == after_uid:
        return "match"
    if before_uid and after_uid and before_uid != after_uid:
        return "mismatch"
    return "partial"


def is_likely_poe_item(text: str) -> bool:
    if not text or len(text.strip()) < 20:
        return False

    markers = [
        "Item Class:",
        "Rarity:",
        "Item Level:",
        "Sockets:",
        "Requires:",
        "Evasion Rating:",
        "Energy Shield:",
        "Armour:",
        "Unique ID:",
    ]

    return sum(marker in text for marker in markers) >= 2


def is_glove_item(text: str) -> bool:
    return (
        "Item Class: Gloves" in text
        or "Fists of Stone" in text
        or "Evasion Rating:" in text and "Energy Shield:" in text and "Rarity:" in text
    )


def is_stonefist_transformed(text: str) -> bool:
    return (
        "Fists of Stone" in text
        or "Has +3 to Evasion Rating per player level" in text
        or "Has +1 to maximum Energy Shield per player level" in text
    )


def get_name_and_base(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        if line.startswith("Rarity:"):
            name = lines[i + 1] if i + 1 < len(lines) else ""
            maybe_base = lines[i + 2] if i + 2 < len(lines) else ""

            # Magic/normal items often have only one item display line, then divider.
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


def guess_mod_lines(text: str) -> list[str]:
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


def save_raw_capture(text: str, kind: str) -> dict:
    name, base = get_name_and_base(text)
    h = short_hash(text)
    file_path = RAW_DIR / f"{timestamp()}-{kind}-{h}.txt"
    file_path.write_text(text, encoding="utf-8")

    return {
        "kind": kind,
        "item_class": get_item_class(text),
        "rarity": get_rarity(text),
        "name": name,
        "base": base,
        "item_level": get_field(text, r"Item Level:\s*(.+)"),
        "unique_id": get_field(text, r"Unique ID:\s*(.+)"),
        "hash": h,
        "file": str(file_path),
        "basic_stats": get_basic_stats(text),
        "mods_guess": guess_mod_lines(text),
        "raw_text": text,
    }


def save_meta(pair_dir: Path, test_id: str, character_level: str, captured_at: str) -> None:
    meta = {
        "test_id": test_id,
        "captured_at": captured_at,
        "character_level": character_level,
        "capture_version": 2,
        "notes": "",
    }

    meta_path = pair_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def next_test_number() -> int:
    existing_numbers: list[int] = []

    for pair_dir in PAIRS_DIR.iterdir():
        if not pair_dir.is_dir():
            continue

        match = re.fullmatch(r"STONEFIST-(\d{4})", pair_dir.name)
        if match:
            existing_numbers.append(int(match.group(1)))

    return max(existing_numbers, default=0) + 1


def allocate_pair_dir(test_number: int) -> tuple[str, Path, int]:
    while True:
        test_id = f"STONEFIST-{test_number:04d}"
        pair_dir = PAIRS_DIR / test_id

        if not pair_dir.exists():
            pair_dir.mkdir()
            return test_id, pair_dir, test_number + 1

        test_number += 1


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
    test_number = next_test_number()
    print(f"Next pair ID will be STONEFIST-{test_number:04d}")
    print()

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

        if not is_likely_poe_item(clip) or not is_glove_item(clip):
            time.sleep(0.25)
            continue

        kind = "after" if is_stonefist_transformed(clip) else "before"
        record = save_raw_capture(clip, kind)

        if kind == "before":
            pending_before = record
            print(
                f"[BEFORE] {record['rarity']} | "
                f"{record['name']} / {record['base'] or '(no base line)'} / "
                f"ilvl {record['item_level']}"
            )
            time.sleep(0.25)
            continue

        print(
            f"[AFTER]  {record['rarity']} | "
            f"{record['name']} / {record['base'] or '(no base line)'} / "
            f"ilvl {record['item_level']}"
        )

        if pending_before is None:
            print("No pending BEFORE capture. Saved raw AFTER only.")
            time.sleep(0.25)
            continue

        test_id, pair_dir, test_number = allocate_pair_dir(test_number)

        before_path = pair_dir / "before.txt"
        after_path = pair_dir / "after.txt"
        captured_at = datetime.now().isoformat(timespec="seconds")

        before_path.write_text(pending_before["raw_text"], encoding="utf-8")
        after_path.write_text(record["raw_text"], encoding="utf-8")
        save_meta(pair_dir, test_id, character_level, captured_at)

        status = uid_status(pending_before["unique_id"], record["unique_id"])

        before_for_json = {k: v for k, v in pending_before.items() if k != "raw_text"}
        after_for_json = {k: v for k, v in record.items() if k != "raw_text"}

        pair = {
            "test_id": test_id,
            "timestamp": captured_at,
            "character_level": character_level,
            "uid_status": status,
            "before_file": str(before_path),
            "after_file": str(after_path),
            "before": before_for_json,
            "after": after_for_json,
            "notes": "Original copied before transformation. Transformed copied while equipped with Way of the Stonefist.",
        }

        print(f"Paired as {test_id}")
        print(f"UID status: {status}")
        print(f"Saved to: {pair_dir}")
        print()

        pending_before = None
        time.sleep(0.25)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Capture stopped.")