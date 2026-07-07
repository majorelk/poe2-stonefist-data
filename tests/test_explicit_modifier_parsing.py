from pathlib import Path

from stonefist_dataset.explicit_mods import parse_explicit_modifier_blocks

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "two_mod_item.txt"


def test_parses_two_explicit_modifier_blocks():
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    blocks = parse_explicit_modifier_blocks(text)

    assert len(blocks) == 2

    prefix, suffix = blocks

    assert prefix["modifier_kind"] == "Prefix"
    assert prefix["modifier_name"] == "Hunter's"
    assert prefix["tier"] == "3"
    assert prefix["stat_lines"] == ["+336(237-346) to Accuracy Rating"]

    assert suffix["modifier_kind"] == "Suffix"
    assert suffix["modifier_name"] == "of the Maelstrom"
    assert suffix["tier"] == ""
    assert suffix["stat_lines"] == ["+33(31-35)% to Lightning Resistance"]
