from __future__ import annotations

import csv
import re

from stonefist_dataset.augment_controls import extract_augment_lines, extract_socket_lines
from stonefist_dataset.item_text import normalise_stat_template
from stonefist_dataset import paths


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
    with paths.BASE_CONTROL_SUMMARY_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(paths.BASE_CONTROL_FIELDNAMES)
        for row in rows:
            writer.writerow([row.get(field, "") for field in paths.BASE_CONTROL_FIELDNAMES])
