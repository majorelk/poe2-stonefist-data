import json
import sys

import pytest

import stonefist_capture as sc

BEFORE_TEXT = """
Item Class: Gloves
Rarity: Rare
Test Gloves
Dread Knuckle
--------
Item Level: 82
--------
{ Prefix Modifier "Hunter's" (Tier: 3) — Attack }
+336(237-346) to Accuracy Rating
--------
""".strip()

AFTER_TEXT = """
Item Class: Gloves
Rarity: Rare
Test Gloves
Fists of Stone
--------
Item Level: 82
--------
{ Prefix Modifier "Hunter's" }
30(30-32)% chance to Blind Enemies on Hit with Attacks
--------
""".strip()


def test_resolve_pair_notes_keeps_session_note_when_blank():
    assert sc.resolve_pair_notes("session note", "") == "session note"
    assert sc.resolve_pair_notes("session note", "   ") == "session note"


def test_resolve_pair_notes_prefers_per_pair_note_when_given():
    assert sc.resolve_pair_notes("session note", "Desecrated dual-resistance target.") == (
        "Desecrated dual-resistance target."
    )


def test_save_meta_stores_session_notes_by_default(tmp_path):
    sc.save_meta(
        tmp_path,
        "STONEFIST-0001",
        "80",
        "2026-01-01T00:00:00",
        "Normal white base control. No explicit modifiers. DEX base.",
    )

    meta = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
    assert meta["test_id"] == "STONEFIST-0001"
    assert meta["character_level"] == "80"
    assert meta["notes"] == "Normal white base control. No explicit modifiers. DEX base."


def test_save_meta_stores_per_pair_notes(tmp_path):
    sc.save_meta(
        tmp_path,
        "STONEFIST-0002",
        "80",
        "2026-01-01T00:00:00",
        "Essence-forced off-class evasion mod.",
    )

    meta = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
    assert meta["notes"] == "Essence-forced off-class evasion mod."


def test_save_meta_defaults_notes_to_empty_string(tmp_path):
    sc.save_meta(tmp_path, "STONEFIST-0003", "80", "2026-01-01T00:00:00")

    meta = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
    assert meta["notes"] == ""


def test_ctrl_c_at_per_pair_notes_prompt_keeps_session_meta(tmp_path, monkeypatch):
    """A KeyboardInterrupt while answering the --prompt-notes per-pair prompt
    must not leave a pair folder without meta.json - the session/default note
    should already be written before that prompt is asked."""
    raw_dir = tmp_path / "raw"
    pairs_dir = tmp_path / "pairs"
    raw_dir.mkdir()
    pairs_dir.mkdir()

    monkeypatch.setattr(sc, "RAW_DIR", raw_dir)
    monkeypatch.setattr(sc, "PAIRS_DIR", pairs_dir)
    monkeypatch.setattr(sc.time, "sleep", lambda *_a, **_kw: None)
    monkeypatch.setattr(sys, "argv", ["stonefist_capture.py", "--prompt-notes"])

    clip_values = iter([BEFORE_TEXT, AFTER_TEXT])
    monkeypatch.setattr(sc.pyperclip, "paste", lambda: next(clip_values))

    responses = iter(["82", "control capture session note"])

    def fake_input(prompt: str = "") -> str:
        try:
            return next(responses)
        except StopIteration:
            raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", fake_input)

    with pytest.raises(KeyboardInterrupt):
        sc.main()

    pair_dirs = [p for p in pairs_dir.iterdir() if p.is_dir()]
    assert len(pair_dirs) == 1
    pair_dir = pair_dirs[0]

    assert (pair_dir / "before.txt").exists()
    assert (pair_dir / "after.txt").exists()

    meta_path = pair_dir / "meta.json"
    assert meta_path.exists()

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["character_level"] == "82"
    assert meta["notes"] == "control capture session note"
