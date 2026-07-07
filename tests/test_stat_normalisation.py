import pytest

from stonefist_dataset.item_text import normalise_stat_template


@pytest.mark.parametrize(
    ("stat_text", "expected"),
    [
        ("+336(237-346) to Accuracy Rating", "+# to Accuracy Rating"),
        ("+11(10-12)% to all Elemental Resistances", "+#% to all Elemental Resistances"),
        (
            "Adds 7(1-13) to 218(168-231) Lightning Damage",
            "Adds # to # Lightning Damage",
        ),
    ],
)
def test_normalise_stat_template(stat_text, expected):
    assert normalise_stat_template(stat_text) == expected
