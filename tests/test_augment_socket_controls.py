import shutil
from pathlib import Path

import pytest

import stonefist_build_dataset as sbd

FIXTURE_PAIRS_DIR = Path(__file__).parent / "fixtures" / "mini_pairs_augment_socket"


def test_extract_socket_lines_and_count():
    text = "Item Class: Gloves\nSockets: S S\n--------\nItem Level: 80\n"
    lines = sbd.extract_socket_lines(text)

    assert lines == ["Sockets: S S"]
    assert sbd.count_sockets(lines) == 2


def test_count_sockets_handles_no_sockets_line():
    assert sbd.count_sockets(sbd.extract_socket_lines("Item Class: Gloves\n")) == 0


def test_extract_augment_lines_captures_rune_and_following_stat_line():
    text = (
        "Sockets: S\n"
        "--------\n"
        "Rune: Iron Rune\n"
        "+10 to Strength\n"
        "--------\n"
        "Item Level: 80\n"
    )

    assert sbd.extract_augment_lines(text) == ["Rune: Iron Rune", "+10 to Strength"]


def test_extract_augment_lines_empty_when_no_rune():
    assert sbd.extract_augment_lines("Sockets: S\n--------\nItem Level: 80\n") == []


@pytest.mark.parametrize(
    ("augment_lines", "socket_count", "expected"),
    [
        ([], 1, "empty_socket"),
        ([], 0, "unknown"),
        (["Rune: Iron Rune", "+10 to Strength"], 1, "attribute"),
        (["Rune: X", "+10% to Fire Resistance"], 1, "resistance"),
        (["Rune: X", "+20 to Armour"], 1, "armour_evasion_energy_shield"),
        (["Rune: X", "0.5 Mana Regeneration per Second"], 1, "mana_regen"),
        (["Rune: X", "0.5 Life Regeneration per Second"], 1, "life_regen"),
        (["Rune: X", "Idol Socket"], 1, "idol"),
        (["Rune: X", "Some unrecognised effect"], 1, "other"),
    ],
)
def test_derive_augment_family(augment_lines, socket_count, expected):
    assert sbd.derive_augment_family(augment_lines, socket_count) == expected


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
    assert sbd.classify_socket_behaviour(before_count, after_count) == expected


@pytest.mark.parametrize(
    ("before_lines", "after_lines", "expected"),
    [
        ([], [], "preserved"),
        (["Rune: X"], ["Rune: X"], "preserved"),
        (["Rune: X"], [], "removed"),
        ([], ["Rune: X"], "changed"),
        (["Rune: X"], ["Rune: Y"], "changed"),
    ],
)
def test_classify_augment_behaviour(before_lines, after_lines, expected):
    assert sbd.classify_augment_behaviour(before_lines, after_lines) == expected


def _make_pair(**overrides) -> dict:
    pair = {
        "test_id": "STONEFIST-0001",
        "character_level": "80",
        "before_rarity": "Rare",
        "before_name": "Test Gloves",
        "before_base": "Adorned Wraps",
        "after_name": "Test Gloves",
        "after_base": "Fists of Stone",
        "before_text": "Sockets: S\n--------\nItem Level: 80\n",
        "after_text": "Fists of Stone\nSockets: S\n--------\nItem Level: 80\n",
        "notes": "",
    }
    pair.update(overrides)
    return pair


def test_compute_augment_socket_rows_detects_control_pair():
    rows = sbd.compute_augment_socket_rows([_make_pair()])

    assert len(rows) == 1
    row = rows[0]
    assert row["sample_id"] == "STONEFIST-0001"
    assert row["before_socket_count"] == 1
    assert row["after_socket_count"] == 1
    assert row["socket_behaviour"] == "preserved"
    assert row["augment_family"] == "empty_socket"
    assert row["augment_behaviour"] == "preserved"


def test_compute_augment_socket_rows_ignores_pairs_without_before_sockets():
    pair = _make_pair(before_text="Item Class: Gloves\n--------\nItem Level: 80\n")
    assert sbd.compute_augment_socket_rows([pair]) == []


def test_compute_augment_socket_rows_ignores_non_stonefist_after():
    pair = _make_pair(after_text="Some Other Item\nSockets: S\n")
    assert sbd.compute_augment_socket_rows([pair]) == []


def test_compute_augment_socket_rows_handles_no_pairs_gracefully():
    """Zero-data case: must return an empty list, never crash."""
    assert sbd.compute_augment_socket_rows([]) == []


def test_compute_augment_socket_rows_from_real_fixture_pair(tmp_path, monkeypatch):
    """End-to-end through the real load_pairs() parsing pipeline, using a
    fixture pair with an actual socketed rune (attribute augment)."""
    pairs_dir = tmp_path / "pairs"
    shutil.copytree(FIXTURE_PAIRS_DIR, pairs_dir)

    monkeypatch.setattr(sbd, "PAIRS_DIR", pairs_dir)
    pairs = sbd.load_pairs()
    assert len(pairs) == 1

    rows = sbd.compute_augment_socket_rows(pairs)

    assert len(rows) == 1
    row = rows[0]
    assert row["sample_id"] == "STONEFIST-0001"
    assert row["before_socket_count"] == 1
    assert row["after_socket_count"] == 1
    assert row["socket_behaviour"] == "preserved"
    assert row["before_augment_lines"] == "Rune: Iron Rune | +10 to Strength"
    assert row["after_augment_lines"] == "Rune: Iron Rune | +10 to Strength"
    assert row["augment_behaviour"] == "preserved"
    assert row["augment_family"] == "attribute"
    assert row["notes"] == "Socketed Iron Rune control. Attribute augment preserved through Stonefist."
