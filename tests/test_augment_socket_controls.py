import shutil
from pathlib import Path

import pytest

from stonefist_dataset import paths as dataset_paths
from stonefist_dataset.augment_controls import (
    classify_augment_effect_status_for_capture_character,
    classify_augment_line_behaviour,
    classify_socket_behaviour,
    classify_socketed_augment_source,
    classify_usability_behaviour,
    compute_augment_socket_rows,
    count_sockets,
    derive_augment_family,
    extract_augment_lines,
    extract_display_name_and_base,
    extract_socket_lines,
    usability_for_capture_character,
)
from stonefist_dataset.explicit_mods import parse_explicit_modifier_blocks
from stonefist_dataset.pairs import load_pairs

FIXTURE_PAIRS_DIR = Path(__file__).parent / "fixtures" / "mini_pairs_augment_socket"
FIXTURE_IGNORED_PAIRS_DIR = Path(__file__).parent / "fixtures" / "mini_pairs_augment_socket_ignored"
FIXTURE_IDOL_PAIRS_DIR = Path(__file__).parent / "fixtures" / "mini_pairs_augment_socket_idol"

USABILITY_WARNING_TEXT = "You cannot use this item. Its stats will be ignored"


def test_extract_socket_lines_and_count():
    text = "Item Class: Gloves\nSockets: S S\n--------\nItem Level: 80\n"
    lines = extract_socket_lines(text)

    assert lines == ["Sockets: S S"]
    assert count_sockets(lines) == 2


def test_count_sockets_handles_no_sockets_line():
    assert count_sockets(extract_socket_lines("Item Class: Gloves\n")) == 0


def test_extract_augment_lines_captures_multiple_standalone_rune_lines():
    """Real PoE2 clipboard text does not use a 'Rune:' header - rune effects
    appear as standalone lines each ending in '(rune)'."""
    text = (
        "Sockets: S\n"
        "--------\n"
        "Item Level: 71\n"
        "--------\n"
        "Gain 3 Life per Enemy Hit with Attacks (rune)\n"
        "Gain 1 Mana per Enemy Hit with Attacks (rune)\n"
    )

    assert extract_augment_lines(text) == [
        "Gain 3 Life per Enemy Hit with Attacks (rune)",
        "Gain 1 Mana per Enemy Hit with Attacks (rune)",
    ]


def test_extract_augment_lines_captures_combo_rune():
    text = "Sockets: S\n--------\n50% chance to build an additional Combo on Hit (rune)\n"

    assert extract_augment_lines(text) == [
        "50% chance to build an additional Combo on Hit (rune)"
    ]


def test_extract_augment_lines_does_not_require_rune_header():
    text = "+10% to Fire Resistance (rune)\n"
    assert extract_augment_lines(text) == ["+10% to Fire Resistance (rune)"]


def test_extract_augment_lines_still_supports_legacy_rune_header():
    text = "Rune: Iron Rune\n+10 to Strength\n--------\nItem Level: 80\n"
    assert extract_augment_lines(text) == ["Rune: Iron Rune", "+10 to Strength"]


def test_extract_augment_lines_empty_when_no_rune_evidence():
    assert extract_augment_lines("Sockets: S\n--------\nItem Level: 80\n") == []


def test_visible_rune_line_is_not_treated_as_natural_explicit_modifier():
    """Rune lines like '... (rune)' must never be picked up by the explicit
    modifier block parser - only real '{ Prefix/Suffix Modifier "Name" }'
    blocks count as natural glove affixes."""
    text = (
        'Sockets: S\n'
        '--------\n'
        '50% chance to build an additional Combo on Hit (rune)\n'
        '--------\n'
        '{ Suffix Modifier "of the Ice" (Tier: 2) — Elemental, Cold, Resistance }\n'
        '+36(36-40)% to Cold Resistance\n'
    )

    blocks = parse_explicit_modifier_blocks(text)

    assert len(blocks) == 1
    assert blocks[0]["modifier_name"] == "of the Ice"


@pytest.mark.parametrize(
    ("augment_lines", "socket_count", "expected"),
    [
        ([], 1, "empty_socket"),
        ([], 0, "unknown"),
        (["50% chance to build an additional Combo on Hit (rune)"], 1, "combo"),
        (["Gain 3 Life per Enemy Hit with Attacks (rune)"], 1, "life_mana_on_hit"),
        (["Gain 1 Mana per Enemy Hit with Attacks (rune)"], 1, "life_mana_on_hit"),
        (["25% increased Accuracy Rating (rune)"], 1, "accuracy"),
        (["+12 to Strength (rune)"], 1, "attribute"),
        (["+10% to Fire Resistance (rune)"], 1, "resistance"),
        (["18% increased Armour, Evasion and Energy Shield (rune)"], 1, "armour_evasion_energy_shield"),
        (["0.5 Mana Regeneration per Second (rune)"], 1, "mana_regen"),
        (["0.5 Life Regeneration per Second (rune)"], 1, "life_regen"),
        (["Idol Socket (rune)"], 1, "idol"),
        (["20% increased Runic Ward (rune)"], 1, "other"),
    ],
)
def test_derive_augment_family(augment_lines, socket_count, expected):
    assert derive_augment_family(augment_lines, socket_count) == expected


@pytest.mark.parametrize(
    ("before_count", "after_count", "expected"),
    [
        (0, 0, "unknown"),
        (1, 1, "preserved"),
        (2, 2, "preserved"),
        (1, 0, "removed"),
        (1, 2, "changed"),
    ],
)
def test_classify_socket_behaviour(before_count, after_count, expected):
    assert classify_socket_behaviour(before_count, after_count) == expected


@pytest.mark.parametrize(
    ("before_lines", "after_lines", "expected"),
    [
        ([], [], "absent"),
        (["+12 to Strength (rune)"], ["+12 to Strength (rune)"], "preserved"),
        (["+12 to Strength (rune)"], [], "removed"),
        ([], ["+12 to Strength (rune)"], "changed"),
        (["+12 to Strength (rune)"], ["+10% to Fire Resistance (rune)"], "changed"),
    ],
)
def test_classify_augment_line_behaviour(before_lines, after_lines, expected):
    assert classify_augment_line_behaviour(before_lines, after_lines) == expected


def test_usability_detects_warning_text():
    usable, ignored = usability_for_capture_character(USABILITY_WARNING_TEXT, notes="")
    assert usable == "false"
    assert ignored is True


def test_usability_defaults_to_unknown_without_warning_or_confirming_notes():
    usable, ignored = usability_for_capture_character("Fists of Stone\n", notes="")
    assert usable == "unknown"
    assert ignored is False


def test_usability_true_only_when_notes_confirm_usable():
    usable, ignored = usability_for_capture_character("Fists of Stone\n", notes="Confirmed usable and equipped.")
    assert usable == "true"
    assert ignored is False


@pytest.mark.parametrize(
    ("before_usable", "after_usable", "expected"),
    [
        ("unknown", "unknown", "unknown"),
        ("unknown", "false", "unknown_to_unusable"),
        ("true", "true", "usable_to_usable"),
        ("true", "false", "usable_to_unusable"),
    ],
)
def test_classify_usability_behaviour(before_usable, after_usable, expected):
    assert classify_usability_behaviour(before_usable, after_usable) == expected


@pytest.mark.parametrize(
    ("augment_line_behaviour", "after_stats_ignored", "after_usable", "expected"),
    [
        ("absent", False, "unknown", "unknown"),
        ("preserved", True, "false", "ignored"),
        ("preserved", False, "true", "active"),
        ("preserved", False, "unknown", "unknown"),
    ],
)
def test_classify_augment_effect_status_for_capture_character(
    augment_line_behaviour, after_stats_ignored, after_usable, expected
):
    assert (
        classify_augment_effect_status_for_capture_character(
            augment_line_behaviour, after_stats_ignored, after_usable
        )
        == expected
    )


@pytest.mark.parametrize(
    ("notes", "expected"),
    [
        ("Cat Idol socketed - 25% increased Accuracy Rating.", "idol"),
        ("Idol control sample", "idol"),
        ("Socketed Iron Rune control", "rune"),
        ("resistance control (fire)", "unknown"),
        ("", "unknown"),
    ],
)
def test_classify_socketed_augment_source(notes, expected):
    assert classify_socketed_augment_source(notes) == expected


def _make_pair(**overrides) -> dict:
    pair = {
        "test_id": "STONEFIST-0001",
        "character_level": "80",
        "before_rarity": "Rare",
        "before_text": "Rarity: Rare\nTest Gloves\nAdorned Wraps\n--------\nSockets: S\n--------\nItem Level: 80\n",
        "after_text": (
            "Rarity: Rare\nTest Gloves\nFists of Stone\n--------\nSockets: S\n--------\nItem Level: 80\n"
        ),
        "notes": "",
    }
    pair.update(overrides)
    return pair


def test_compute_augment_socket_rows_detects_true_empty_socket():
    rows = compute_augment_socket_rows([_make_pair()])

    assert len(rows) == 1
    row = rows[0]
    assert row["sample_id"] == "STONEFIST-0001"
    assert row["before_socket_count"] == 1
    assert row["after_socket_count"] == 1
    assert row["socket_behaviour"] == "preserved"
    assert row["augment_family"] == "empty_socket"
    assert row["augment_line_behaviour"] == "absent"
    assert row["augment_effect_status_for_capture_character"] == "unknown"


def test_compute_augment_socket_rows_ignores_pairs_without_before_sockets():
    pair = _make_pair(before_text="Item Class: Gloves\n--------\nItem Level: 80\n")
    assert compute_augment_socket_rows([pair]) == []


def test_compute_augment_socket_rows_ignores_non_stonefist_after():
    pair = _make_pair(after_text="Some Other Item\nSockets: S\n")
    assert compute_augment_socket_rows([pair]) == []


def test_compute_augment_socket_rows_handles_no_pairs_gracefully():
    """Zero-data case: must return an empty list, never crash."""
    assert compute_augment_socket_rows([]) == []


def test_compute_augment_socket_rows_from_real_fixture_pair(tmp_path, monkeypatch):
    """End-to-end through the real load_pairs() parsing pipeline, using a
    fixture pair with an actual socketed rune (attribute augment, no
    usability warning)."""
    pairs_dir = tmp_path / "pairs"
    shutil.copytree(FIXTURE_PAIRS_DIR, pairs_dir)

    monkeypatch.setattr(dataset_paths, "PAIRS_DIR", pairs_dir)
    pairs = load_pairs()
    assert len(pairs) == 1

    rows = compute_augment_socket_rows(pairs)

    assert len(rows) == 1
    row = rows[0]
    assert row["sample_id"] == "STONEFIST-0001"
    assert row["before_socket_count"] == 1
    assert row["after_socket_count"] == 1
    assert row["socket_behaviour"] == "preserved"
    assert row["before_augment_lines"] == "+12 to Strength (rune)"
    assert row["after_augment_lines"] == "+12 to Strength (rune)"
    assert row["augment_line_behaviour"] == "preserved"
    assert row["augment_family"] == "attribute"
    assert row["after_usable_for_capture_character"] == "unknown"
    assert row["after_stats_ignored_for_capture_character"] == "false"
    assert row["augment_effect_status_for_capture_character"] == "unknown"


def test_compute_augment_socket_rows_from_real_fixture_pair_with_ignored_stats(tmp_path, monkeypatch):
    """End-to-end case matching the real Life/Mana-on-Hit rune samples:
    socket and rune text preserved, but the transformed item warns it cannot
    be used by the capture character, so the effect is ignored - not removed,
    and not an empty socket."""
    pairs_dir = tmp_path / "pairs"
    shutil.copytree(FIXTURE_IGNORED_PAIRS_DIR, pairs_dir)

    monkeypatch.setattr(dataset_paths, "PAIRS_DIR", pairs_dir)
    pairs = load_pairs()
    assert len(pairs) == 1

    rows = compute_augment_socket_rows(pairs)

    assert len(rows) == 1
    row = rows[0]
    assert row["socket_behaviour"] == "preserved"
    assert row["augment_family"] == "life_mana_on_hit"
    assert row["augment_line_behaviour"] == "preserved"
    assert row["before_augment_lines"] == (
        "Gain 3 Life per Enemy Hit with Attacks (rune) | Gain 1 Mana per Enemy Hit with Attacks (rune)"
    )
    assert row["after_augment_lines"] == row["before_augment_lines"]
    assert row["after_usable_for_capture_character"] == "false"
    assert row["after_stats_ignored_for_capture_character"] == "true"
    assert row["usability_behaviour_for_capture_character"] == "unknown_to_unusable"
    assert row["augment_effect_status_for_capture_character"] == "ignored"
    # Must not be misclassified as an empty socket or as the rune being removed.
    assert row["augment_family"] != "empty_socket"
    assert row["augment_line_behaviour"] != "removed"


def test_compute_augment_socket_rows_from_real_fixture_pair_cat_idol(tmp_path, monkeypatch):
    """A socketed Cat Idol renders in the clipboard exactly like a Rune -
    '25% increased Accuracy Rating (rune)' - so augment_family (the visible
    effect) must classify as 'accuracy', while socketed_augment_source (from
    notes only) can separately say 'idol'."""
    pairs_dir = tmp_path / "pairs"
    shutil.copytree(FIXTURE_IDOL_PAIRS_DIR, pairs_dir)

    monkeypatch.setattr(dataset_paths, "PAIRS_DIR", pairs_dir)
    pairs = load_pairs()
    assert len(pairs) == 1

    rows = compute_augment_socket_rows(pairs)

    assert len(rows) == 1
    row = rows[0]
    assert row["before_augment_lines"] == "25% increased Accuracy Rating (rune)"
    assert row["after_augment_lines"] == "25% increased Accuracy Rating (rune)"
    assert row["augment_family"] == "accuracy"
    assert row["augment_line_behaviour"] == "preserved"
    assert row["socket_behaviour"] == "preserved"
    assert row["socketed_augment_source"] == "idol"
    assert row["after_stats_ignored_for_capture_character"] == "false"
    # Notes confirm the item was usable/equipped, so the effect is active.
    assert row["augment_effect_status_for_capture_character"] == "active"


def test_extract_display_name_and_base_skips_usability_warning_block():
    text = (
        "Item Class: Gloves\n"
        "Rarity: Normal\n"
        f"{USABILITY_WARNING_TEXT}\n"
        "--------\n"
        "Fists of Stone\n"
        "--------\n"
        "Evasion Rating: 240 (augmented)\n"
    )

    name, base = extract_display_name_and_base(text)

    assert name == "Fists of Stone"
    assert base == ""


def test_extract_display_name_and_base_normal_case_unaffected():
    text = "Item Class: Gloves\nRarity: Rare\nDread Knuckle\nAdorned Wraps\n--------\nItem Level: 80\n"

    name, base = extract_display_name_and_base(text)

    assert name == "Dread Knuckle"
    assert base == "Adorned Wraps"
