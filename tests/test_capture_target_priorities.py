from stonefist_dataset.coverage import build_capture_targets

COVERAGE_ROWS = [
    {
        "stat_template": "+#% to Fire Resistance",
        "modifier_names": "of the Ember",
        "glove_classes": "dex",
        "pool_types": "explicit",
        "coverage_status": "missing_input_sample",
        "isolated_sample_count": 0,
        "likely_sample_count": 0,
        "sample_ids": "",
    },
    {
        "stat_template": "#% increased Armour",
        "modifier_names": "Reinforced",
        "glove_classes": "str",
        "pool_types": "explicit",
        "coverage_status": "likely_mapping",
        "isolated_sample_count": 0,
        "likely_sample_count": 2,
        "sample_ids": "TEST-0002|TEST-0003",
    },
    {
        "stat_template": "Break #% increased Armour",
        "modifier_names": "CorruptionArmourBreak1",
        "glove_classes": "dex",
        "pool_types": "corrupted_enchantment",
        "coverage_status": "corruption_only_missing",
        "isolated_sample_count": 0,
        "likely_sample_count": 0,
        "sample_ids": "",
    },
    {
        "stat_template": "+# to Strength",
        "modifier_names": "of the Brute",
        "glove_classes": "str",
        "pool_types": "explicit",
        "coverage_status": "confirmed_mapping",
        "isolated_sample_count": 1,
        "likely_sample_count": 0,
        "sample_ids": "TEST-0001",
    },
]


def test_capture_target_priorities():
    targets = build_capture_targets(COVERAGE_ROWS)
    by_status = {t["current_status"]: t for t in targets}

    assert by_status["missing_input_sample"]["priority"] == 1
    assert by_status["likely_mapping"]["priority"] == 2
    assert by_status["corruption_only_missing"]["priority"] == 3
    assert by_status["confirmed_mapping"]["priority"] == 4
