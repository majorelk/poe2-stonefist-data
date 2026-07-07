import shutil
from pathlib import Path

import pytest

import stonefist_build_dataset as sbd

FIXTURE_PAIRS_DIR = Path(__file__).parent / "fixtures" / "mini_pairs_base_control"
FIXTURE_AUGMENT_SOCKET_DIR = Path(__file__).parent / "fixtures" / "mini_pairs_augment_socket"
FIXTURE_AUGMENT_SOCKET_IGNORED_DIR = Path(__file__).parent / "fixtures" / "mini_pairs_augment_socket_ignored"


@pytest.mark.parametrize(
    ("armour", "evasion", "energy_shield", "expected"),
    [
        ("120", "", "", "STR"),
        ("", "80", "", "DEX"),
        ("", "", "40", "INT"),
        ("120", "80", "", "STR/DEX"),
        ("120", "", "40", "STR/INT"),
        ("", "80", "40", "DEX/INT"),
        ("", "", "", "unknown"),
        ("120", "80", "40", "unknown"),
    ],
)
def test_derive_defence_family(armour, evasion, energy_shield, expected):
    before_stats = {"armour": armour, "evasion": evasion, "energy_shield": energy_shield}
    assert sbd.derive_defence_family(before_stats) == expected


def test_extract_stonefist_implicit_lines():
    after_text = (
        "Item Class: Gloves\n"
        "Rarity: Normal\n"
        "Fists of Stone\n"
        "--------\n"
        "Evasion Rating: 240 (augmented)\n"
        "Energy Shield: 80 (augmented)\n"
        "--------\n"
        "{ Implicit Modifier }\n"
        "Has +3 to Evasion Rating per player level\n"
        "Has +1 to maximum Energy Shield per player level\n"
        "--------\n"
        "Unmodifiable\n"
    )

    lines = sbd.extract_stonefist_implicit_lines(after_text)

    assert lines == [
        "Has +3 to Evasion Rating per player level",
        "Has +1 to maximum Energy Shield per player level",
    ]


def _make_pair(**overrides) -> dict:
    pair = {
        "test_id": "STONEFIST-0001",
        "character_level": "80",
        "before_name": "Ornate Mitts",
        "before_rarity": "Normal",
        "before_explicit_count": 0,
        "before_stats": {"armour": "171", "evasion": "", "energy_shield": ""},
        "before_text": "Rarity: Normal\nOrnate Mitts\n--------\nArmour: 171\n--------\nItem Level: 80\n",
        "after_stats": {"armour": "", "evasion": "240 (augmented)", "energy_shield": "80 (augmented)"},
        "after_text": (
            "Rarity: Normal\nFists of Stone\n"
            "{ Implicit Modifier }\n"
            "Has +3 to Evasion Rating per player level\n"
            "Has +1 to maximum Energy Shield per player level\n"
        ),
        "notes": "",
    }
    pair.update(overrides)
    return pair


def test_compute_base_control_rows_detects_normal_base_control():
    rows = sbd.compute_base_control_rows([_make_pair()])

    assert len(rows) == 1
    row = rows[0]
    assert row["sample_id"] == "STONEFIST-0001"
    assert row["before_defence_family"] == "STR"
    assert row["evasion_per_level"] == "3"
    assert row["energy_shield_per_level"] == "1"
    assert row["after_implicit_templates"] == (
        "Has +# to Evasion Rating per player level | Has +# to maximum Energy Shield per player level"
    )


def test_compute_base_control_rows_ignores_non_normal_rarity():
    pair = _make_pair(before_rarity="Rare")
    assert sbd.compute_base_control_rows([pair]) == []


def test_compute_base_control_rows_ignores_pairs_with_explicit_mods():
    pair = _make_pair(before_explicit_count=2)
    assert sbd.compute_base_control_rows([pair]) == []


def test_compute_base_control_rows_ignores_non_stonefist_after():
    pair = _make_pair(after_text="Rarity: Normal\nSome Other Base\n")
    assert sbd.compute_base_control_rows([pair]) == []


def test_compute_base_control_rows_handles_no_pairs_gracefully():
    assert sbd.compute_base_control_rows([]) == []


def test_compute_base_control_rows_excludes_pairs_with_sockets():
    """A normal, no-explicit-modifier glove that also has a socket is
    augment/socket evidence, not base-implicit evidence - Base Controls and
    Augment Controls must be mutually exclusive."""
    pair = _make_pair(
        before_text=(
            "Rarity: Normal\nOrnate Mitts\n--------\nArmour: 171\n--------\nSockets: S\n--------\nItem Level: 80\n"
        )
    )
    assert sbd.compute_base_control_rows([pair]) == []


def test_compute_base_control_rows_excludes_pairs_with_visible_rune_lines():
    pair = _make_pair(
        before_text=(
            "Rarity: Normal\nOrnate Mitts\n--------\nArmour: 171\n--------\n+12 to Strength (rune)\n--------\nItem Level: 80\n"
        )
    )
    assert sbd.compute_base_control_rows([pair]) == []


@pytest.mark.parametrize(
    "notes",
    [
        "Socketed rune control",
        "Idol control sample",
        "Augment socket control",
        "socketed test",
        "socket control baseline",
        "warn cannot use, stats ignored",
    ],
)
def test_compute_base_control_rows_excludes_pairs_by_note_keywords(notes):
    pair = _make_pair(notes=notes)
    assert sbd.compute_base_control_rows([pair]) == []


def test_compute_base_control_rows_excludes_real_augment_socket_fixture(tmp_path, monkeypatch):
    """The socketed-rune fixture used for Augment Controls tests must never
    also show up as a Base Control, even though it is a Normal-rarity glove
    with zero explicit modifiers."""
    pairs_dir = tmp_path / "pairs"
    shutil.copytree(FIXTURE_AUGMENT_SOCKET_IGNORED_DIR, pairs_dir)

    monkeypatch.setattr(sbd, "PAIRS_DIR", pairs_dir)
    pairs = sbd.load_pairs()
    assert len(pairs) == 1

    assert sbd.compute_base_control_rows(pairs) == []
    assert len(sbd.compute_augment_socket_rows(pairs)) == 1


def test_base_and_augment_controls_are_mutually_exclusive_across_fixtures(tmp_path, monkeypatch):
    """No sample_id should ever appear in both compute_base_control_rows and
    compute_augment_socket_rows for the same dataset."""
    pairs_dir = tmp_path / "pairs"
    shutil.copytree(FIXTURE_PAIRS_DIR, pairs_dir / "base")
    shutil.copytree(FIXTURE_AUGMENT_SOCKET_DIR, pairs_dir / "augment")
    shutil.copytree(FIXTURE_AUGMENT_SOCKET_IGNORED_DIR, pairs_dir / "augment_ignored")

    # Flatten into a single PAIRS_DIR, since load_pairs() expects one
    # directory of STONEFIST-XXXX folders and each fixture reuses the same
    # STONEFIST-0001 id.
    flat_dir = tmp_path / "flat"
    flat_dir.mkdir()
    for i, source in enumerate((pairs_dir / "base", pairs_dir / "augment", pairs_dir / "augment_ignored"), start=1):
        for pair_dir in source.iterdir():
            shutil.copytree(pair_dir, flat_dir / f"STONEFIST-{i:04d}")

    monkeypatch.setattr(sbd, "PAIRS_DIR", flat_dir)
    pairs = sbd.load_pairs()
    assert len(pairs) == 3

    base_ids = {row["sample_id"] for row in sbd.compute_base_control_rows(pairs)}
    augment_ids = {row["sample_id"] for row in sbd.compute_augment_socket_rows(pairs)}

    assert base_ids == {"STONEFIST-0001"}
    assert augment_ids == {"STONEFIST-0002", "STONEFIST-0003"}
    assert base_ids.isdisjoint(augment_ids)


def test_compute_base_control_rows_from_real_fixture_pair(tmp_path, monkeypatch):
    """End-to-end through the real load_pairs() parsing pipeline, using a
    committed fixture pair rather than the real captured dataset."""
    pairs_dir = tmp_path / "pairs"
    shutil.copytree(FIXTURE_PAIRS_DIR, pairs_dir)

    monkeypatch.setattr(sbd, "PAIRS_DIR", pairs_dir)
    pairs = sbd.load_pairs()
    assert len(pairs) == 1

    rows = sbd.compute_base_control_rows(pairs)

    assert len(rows) == 1
    row = rows[0]
    assert row["sample_id"] == "STONEFIST-0001"
    assert row["before_name"] == "Ornate Mitts"
    assert row["before_defence_family"] == "STR"
    assert row["before_armour"] == "171"
    assert row["evasion_per_level"] == "3"
    assert row["energy_shield_per_level"] == "1"
    assert row["notes"] == "Normal white base control. No explicit modifiers. STR base."
