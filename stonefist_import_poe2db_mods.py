from __future__ import annotations

import argparse
import csv
import html
import json
import re
import urllib.request
from pathlib import Path

from stonefist_dataset.item_text import normalise_stat_template

RAW_DIR = Path("stonefist-reference") / "raw-poe2db"
CSV_PATH = Path("stonefist-reference") / "glove_mod_pool.csv"
JSON_PATH = Path("stonefist-reference") / "glove_mod_pool.json"

FIELDNAMES = [
    "source_url",
    "glove_class",
    "pool_type",
    "modifier_kind",
    "modifier_name",
    "tier",
    "min_item_level",
    "tags",
    "stat_text",
    "stat_template",
]

KEY_FIELDS = ("glove_class", "pool_type", "modifier_kind", "modifier_name", "tier", "stat_template")

KNOWN_URLS = {
    "str": "https://poe2db.tw/us/Gloves_str#ModifiersCalc",
    "dex": "https://poe2db.tw/us/Gloves_dex#ModifiersCalc",
    "int": "https://poe2db.tw/us/Gloves_int#ModifiersCalc",
    "str_dex": "https://poe2db.tw/us/Gloves_str_dex#ModifiersCalc",
    "str_int": "https://poe2db.tw/us/Gloves_str_int#ModifiersCalc",
    "dex_int": "https://poe2db.tw/us/Gloves_dex_int#ModifiersCalc",
}

# (JSON section key, pool_type). Other sections (essence-only mods, influence
# tags, veiled, breach, etc.) are special restricted pools outside the scope
# of the explicit/corrupted_enchantment/unknown schema and are skipped.
POOL_SECTIONS = [
    ("normal", "explicit"),
    ("desecrated", "explicit"),
    ("corrupted", "corrupted_enchantment"),
]

_DASH_CHARS = "‒–—−"


def derive_glove_class(stem: str) -> str:
    name = stem.lower()
    if name.startswith("gloves_"):
        name = name[len("gloves_") :]
    return name


def extract_modsview_data(text: str) -> dict | None:
    marker = "new ModsView("
    start = text.find(marker)
    if start == -1:
        return None

    i = start + len(marker)
    if i >= len(text) or text[i] != "{":
        return None

    start_brace = i
    depth = 0
    in_str = False
    esc = False
    while i < len(text):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
        i += 1

    blob = text[start_brace:i]
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


def strip_html_to_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", "", fragment)
    text = html.unescape(text)
    for dash in _DASH_CHARS:
        text = text.replace(dash, "-")
    return re.sub(r"\s+", " ", text).strip()


def split_stat_lines(raw_html: str) -> list[str]:
    parts = re.split(r"<br\s*/?>", raw_html, flags=re.IGNORECASE)
    return [line for line in (strip_html_to_text(part) for part in parts) if line]


def synthesize_rolled_text(text: str) -> str:
    """Rewrite an unrolled '(min-max)' range as 'max(min-max)', the same shape
    a real captured roll takes, so normalise_stat_template collapses it to the
    same '#' template regardless of which specific value was ever rolled."""

    def repl(match: re.Match) -> str:
        sign = match.group("sign") or ""
        lo = match.group("lo")
        hi = match.group("hi")
        return f"{sign}{hi}({lo}-{hi})"

    return re.sub(
        r"(?P<sign>[+-]?)\((?P<lo>\d+(?:\.\d+)?)-(?P<hi>\d+(?:\.\d+)?)\)",
        repl,
        text,
    )


def extract_tags(mod_no: object) -> str:
    tags: set[str] = set()
    if isinstance(mod_no, list):
        for fragment in mod_no:
            for m in re.finditer(r'data-tag="([^"]+)"', str(fragment)):
                tags.add(m.group(1))
    return ", ".join(sorted(tags))


def _level_sort_value(level: object) -> float:
    try:
        return float(level)
    except (TypeError, ValueError):
        return 0.0


def compute_tiers(entries: list[dict]) -> dict[int, int]:
    groups: dict[tuple[str, tuple[str, ...]], list[int]] = {}
    for idx, entry in enumerate(entries):
        gen_id = str(entry.get("ModGenerationTypeID", ""))
        family = tuple(sorted(entry.get("ModFamilyList") or []))
        groups.setdefault((gen_id, family), []).append(idx)

    tier_by_index: dict[int, int] = {}
    for indices in groups.values():
        ordered = sorted(indices, key=lambda i: _level_sort_value(entries[i].get("Level")), reverse=True)
        for tier, idx in enumerate(ordered, start=1):
            tier_by_index[idx] = tier
    return tier_by_index


def modifier_kind_for(section: str, gen_id: str, gen_map: dict) -> str:
    base = str(gen_map.get(gen_id, "")).lower()
    if base not in ("prefix", "suffix"):
        base = "unknown"

    if section == "corrupted":
        return "corrupted"
    if section == "desecrated":
        return f"desecrated {base}" if base != "unknown" else "unknown"
    return base


def build_rows_from_data(data: dict, glove_class: str, source_url: str) -> list[dict]:
    gen_map = data.get("gen") or {}
    rows: list[dict] = []

    for section, pool_type in POOL_SECTIONS:
        entries = data.get(section) or []
        if not isinstance(entries, list):
            continue

        tier_by_index = compute_tiers(entries)

        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue

            lines = split_stat_lines(str(entry.get("str", "") or ""))
            if not lines:
                continue

            stat_text = " | ".join(lines)
            stat_template = normalise_stat_template(synthesize_rolled_text(stat_text))
            gen_id = str(entry.get("ModGenerationTypeID", ""))

            rows.append(
                {
                    "source_url": source_url,
                    "glove_class": glove_class,
                    "pool_type": pool_type,
                    "modifier_kind": modifier_kind_for(section, gen_id, gen_map),
                    "modifier_name": str(entry.get("Name", "")).strip(),
                    "tier": str(tier_by_index.get(idx, "")),
                    "min_item_level": str(entry.get("Level", "") or "").strip(),
                    "tags": extract_tags(entry.get("mod_no")),
                    "stat_text": stat_text,
                    "stat_template": stat_template,
                }
            )

    return rows


def load_existing_pool(csv_path: Path) -> dict[tuple, dict]:
    existing: dict[tuple, dict] = {}
    if not csv_path.exists():
        return existing

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = tuple(row.get(field, "") for field in KEY_FIELDS)
            existing[key] = row

    return existing


def upsert_rows(existing: dict[tuple, dict], new_rows: list[dict]) -> dict[tuple, dict]:
    merged = dict(existing)
    for row in new_rows:
        key = tuple(row.get(field, "") for field in KEY_FIELDS)
        merged[key] = row
    return merged


def _tier_sort_value(tier: str) -> int:
    try:
        return int(tier)
    except (TypeError, ValueError):
        return 9999


def sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda r: (
            r.get("glove_class", ""),
            r.get("pool_type", ""),
            r.get("modifier_kind", ""),
            r.get("modifier_name", ""),
            _tier_sort_value(r.get("tier", "")),
            r.get("stat_template", ""),
        ),
    )


def write_outputs(rows: list[dict], csv_path: Path, json_path: Path) -> None:
    ordered = sort_rows(rows)

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        for row in ordered:
            writer.writerow({field: row.get(field, "") for field in FIELDNAMES})

    json_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_pages(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for suffix, url in KNOWN_URLS.items():
        fetch_url = url.split("#", 1)[0]
        request = urllib.request.Request(
            fetch_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; stonefist-data-tool/1.0)"},
        )
        print(f"Fetching {fetch_url} ...")
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")

        out_path = raw_dir / f"gloves_{suffix}.html"
        out_path.write_text(body, encoding="utf-8")
        print(f"  Saved {out_path} ({len(body)} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import PoE2DB glove modifier reference pool.")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Download fresh PoE2DB snapshots into stonefist-reference/raw-poe2db/ before parsing. Never done by default.",
    )
    args = parser.parse_args()

    if args.fetch:
        fetch_pages(RAW_DIR)

    files = sorted(RAW_DIR.glob("*.html")) + sorted(RAW_DIR.glob("*.txt"))
    if not files:
        print(f"No local PoE2DB snapshots found in {RAW_DIR}; nothing to import.")
        return

    all_new_rows: list[dict] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        data = extract_modsview_data(text)
        if data is None:
            print(f"Skipping {path.name}: no ModsView data block found.")
            continue

        glove_class = derive_glove_class(path.stem)
        source_url = KNOWN_URLS.get(glove_class, "")
        rows = build_rows_from_data(data, glove_class, source_url)
        print(f"{path.name}: parsed {len(rows)} modifier rows for glove_class={glove_class!r}")
        all_new_rows.extend(rows)

    existing = load_existing_pool(CSV_PATH)
    merged = upsert_rows(existing, all_new_rows)
    write_outputs(list(merged.values()), CSV_PATH, JSON_PATH)

    print(f"Wrote {len(merged)} total modifier rows to {CSV_PATH} and {JSON_PATH}")


if __name__ == "__main__":
    main()
