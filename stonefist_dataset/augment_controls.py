from __future__ import annotations

import csv

from stonefist_dataset import paths


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
    with paths.AUGMENT_SOCKET_SUMMARY_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(paths.AUGMENT_SOCKET_FIELDNAMES)
        for row in rows:
            writer.writerow([row.get(field, "") for field in paths.AUGMENT_SOCKET_FIELDNAMES])
