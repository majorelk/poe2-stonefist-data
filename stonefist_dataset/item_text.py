from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


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
