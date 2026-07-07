from stonefist_dataset.coverage import compute_coverage_rows

REFERENCE_ENTRIES = [
    {
        "stat_template": "+# to Strength",
        "pool_type": "explicit",
        "modifier_name": "of the Brute",
        "glove_class": "str",
        "source_url": "",
    },
    {
        "stat_template": "#% increased Armour",
        "pool_type": "explicit",
        "modifier_name": "Reinforced",
        "glove_class": "str",
        "source_url": "",
    },
    {
        "stat_template": "+#% to Fire Resistance",
        "pool_type": "explicit",
        "modifier_name": "of the Ember",
        "glove_class": "dex",
        "source_url": "",
    },
    {
        "stat_template": "Break #% increased Armour",
        "pool_type": "corrupted_enchantment",
        "modifier_name": "CorruptionArmourBreak1",
        "glove_class": "dex",
        "source_url": "",
    },
]

FAMILY_SUMMARIES = [
    {
        "before_stat_template": "+# to Strength",
        "confidence_summary": "confirmed_family",
        "isolated_sample_count": "1",
        "likely_sample_count": "0",
        "sample_ids": "TEST-0001",
    },
    {
        "before_stat_template": "#% increased Armour",
        "confidence_summary": "likely_family",
        "isolated_sample_count": "0",
        "likely_sample_count": "2",
        "sample_ids": "TEST-0002|TEST-0003",
    },
]


def test_coverage_status_classification():
    rows = compute_coverage_rows([], FAMILY_SUMMARIES, REFERENCE_ENTRIES)
    by_template = {row["stat_template"]: row for row in rows}

    assert by_template["+# to Strength"]["coverage_status"] == "confirmed_mapping"
    assert by_template["#% increased Armour"]["coverage_status"] == "likely_mapping"
    assert by_template["+#% to Fire Resistance"]["coverage_status"] == "missing_input_sample"
    assert by_template["Break #% increased Armour"]["coverage_status"] == "corruption_only_missing"
