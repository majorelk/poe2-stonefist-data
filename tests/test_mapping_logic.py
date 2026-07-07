from stonefist_dataset.mapping import build_mapping_observations

# Before/after blocks are in swapped order on purpose: a position-based
# matcher would pair "Hunter's" (before) with "of the Maelstrom" (after).
# Matching by modifier_name should pair each mod with its correct counterpart.
BEFORE_TEXT = """
{ Prefix Modifier "Hunter's" (Tier: 3) — Attack }
+336(237-346) to Accuracy Rating
{ Suffix Modifier "of the Maelstrom" (Tier: 3) — Elemental, Lightning, Resistance }
+33(31-35)% to Lightning Resistance
""".strip()

AFTER_TEXT = """
{ Suffix Modifier "of the Maelstrom" }
+2% to Maximum Lightning Resistance
{ Prefix Modifier "Hunter's" }
30(30-32)% chance to Blind Enemies on Hit with Attacks
""".strip()


def test_mapping_prefers_modifier_name_over_position():
    pair = {
        "test_id": "TEST-0001",
        "character_level": "80",
        "category": "rare",
        "before_text": BEFORE_TEXT,
        "after_text": AFTER_TEXT,
        "is_exact_duplicate": False,
        "duplicate_of": "",
    }

    observations = build_mapping_observations([pair])

    assert len(observations) == 2
    by_before_name = {obs["before_modifier_name"]: obs for obs in observations}

    assert by_before_name["Hunter's"]["after_modifier_name"] == "Hunter's"
    assert by_before_name["of the Maelstrom"]["after_modifier_name"] == "of the Maelstrom"
    assert all(obs["match_method"] == "modifier_name" for obs in observations)
