from __future__ import annotations

from stonefist_dataset.item_text import (
    classify_pair,
    content_hash,
    count_explicit_headers,
    get_basic_stats,
    get_field,
    get_item_class,
    get_name_base,
    get_rarity,
    interesting_mod_lines,
    load_meta,
    pair_hash,
    read_text,
    uid_status,
)
from stonefist_dataset import paths


def annotate_exact_duplicates(pairs: list[dict]) -> None:
    groups: dict[str, list[dict]] = {}

    for pair in pairs:
        groups.setdefault(pair["pair_hash"], []).append(pair)

    for duplicates in groups.values():
        group_size = len(duplicates)
        canonical = duplicates[0]
        canonical["is_exact_duplicate"] = False
        canonical["duplicate_of"] = ""
        canonical["duplicate_group_size"] = group_size

        for duplicate in duplicates[1:]:
            duplicate["is_exact_duplicate"] = True
            duplicate["duplicate_of"] = canonical["test_id"]
            duplicate["duplicate_group_size"] = group_size

        if group_size == 1:
            canonical["is_exact_duplicate"] = False
            canonical["duplicate_of"] = ""
            canonical["duplicate_group_size"] = 1


def load_pairs() -> list[dict]:
    if not paths.PAIRS_DIR.exists():
        raise SystemExit(f"Could not find {paths.PAIRS_DIR}")

    pairs: list[dict] = []

    for pair_dir in sorted(paths.PAIRS_DIR.iterdir()):
        if not pair_dir.is_dir():
            continue

        before_path = pair_dir / "before.txt"
        after_path = pair_dir / "after.txt"

        if not before_path.exists() or not after_path.exists():
            continue

        before = read_text(before_path)
        after = read_text(after_path)

        before_name, before_base = get_name_base(before)
        after_name, after_base = get_name_base(after)

        before_lines = interesting_mod_lines(before)
        after_lines = interesting_mod_lines(after)

        before_uid = get_field(before, r"Unique ID:\s*(.+)")
        after_uid = get_field(after, r"Unique ID:\s*(.+)")

        before_rarity = get_rarity(before)
        after_rarity = get_rarity(after)

        meta = load_meta(pair_dir)
        status = uid_status(before_uid, after_uid)
        category = classify_pair(before_rarity, after_rarity)
        before_hash = content_hash(before)
        after_hash = content_hash(after)
        pair_hash_value = pair_hash(before, after)

        pairs.append(
            {
                "test_id": pair_dir.name,
                "before_path": str(before_path),
                "after_path": str(after_path),
                "before_text": before,
                "after_text": after,
                "before_item_class": get_item_class(before),
                "after_item_class": get_item_class(after),
                "before_rarity": before_rarity,
                "after_rarity": after_rarity,
                "category": category,
                "is_unique": category == "unique",
                "before_name": before_name,
                "before_base": before_base,
                "after_name": after_name,
                "after_base": after_base,
                "before_item_level": get_field(before, r"Item Level:\s*(.+)"),
                "after_item_level": get_field(after, r"Item Level:\s*(.+)"),
                "before_unique_id": before_uid,
                "after_unique_id": after_uid,
                "uid_status": status,
                "before_stats": get_basic_stats(before),
                "after_stats": get_basic_stats(after),
                "before_lines": before_lines,
                "after_lines": after_lines,
                "before_explicit_count": count_explicit_headers(before_lines),
                "after_explicit_count": count_explicit_headers(after_lines),
                "before_hash": before_hash,
                "after_hash": after_hash,
                "pair_hash": pair_hash_value,
                "captured_at": meta["captured_at"],
                "character_level": meta["character_level"],
                "capture_version": meta["capture_version"],
                "notes": meta["notes"],
                "is_exact_duplicate": False,
                "duplicate_of": "",
                "duplicate_group_size": 1,
            }
        )

    annotate_exact_duplicates(pairs)
    return pairs
