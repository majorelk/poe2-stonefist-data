from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path("stonefist-captures")
DATASET_PATH = ROOT / "dataset.json"
MAPPING_CANDIDATES_PATH = ROOT / "mapping_candidates.csv"
REPORT_PATH = ROOT / "report.html"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def get_field(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def get_rarity(text: str) -> str:
    return get_field(text, r"Rarity:\s*(.+)")


def get_item_class(text: str) -> str:
    return get_field(text, r"Item Class:\s*(.+)")


def uid_status(before_uid: str, after_uid: str) -> str:
    if not before_uid and not after_uid:
        return "not present"
    if before_uid and after_uid and before_uid == after_uid:
        return "match"
    if before_uid and after_uid and before_uid != after_uid:
        return "mismatch"
    return "partial"


def uid_badge(status: str) -> str:
    if status == "match":
        return "✅ match"
    if status == "mismatch":
        return "❌ mismatch"
    if status == "partial":
        return "⚠️ partial"
    return "— not present"


def get_name_base(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        if line.startswith("Rarity:"):
            name = lines[i + 1] if i + 1 < len(lines) else ""
            maybe_base = lines[i + 2] if i + 2 < len(lines) else ""

            # Magic/normal items often only have one display line, then divider.
            if maybe_base == "--------":
                return name, ""

            return name, maybe_base

    return "", ""


def get_basic_stats(text: str) -> dict:
    return {
        "quality": get_field(text, r"Quality:\s*(.+)"),
        "evasion": get_field(text, r"Evasion(?: Rating)?:\s*(.+)"),
        "energy_shield": get_field(text, r"Energy Shield:\s*(.+)"),
        "armour": get_field(text, r"Armour:\s*(.+)"),
        "sockets": get_field(text, r"Sockets:\s*(.+)"),
        "rune": get_field(text, r"Rune:\s*(.+)"),
        "requirements": get_field(text, r"Requires:\s*(.+)"),
    }


def interesting_mod_lines(text: str) -> list[str]:
    ignored_prefixes = (
        "Item Class:",
        "Rarity:",
        "--------",
        "Item Level:",
        "Unique ID:",
        "Quality:",
        "Sockets:",
        "Rune:",
        "Requires:",
        "LevelReq:",
        "Implicits:",
        "Evasion:",
        "Evasion Rating:",
        "Energy Shield:",
        "Armour:",
    )

    out: list[str] = []

    for line in text.splitlines():
        s = line.strip()

        if not s:
            continue

        if s.startswith(ignored_prefixes):
            continue

        if (
            s.startswith("{")
            or s.startswith("+")
            or s.startswith("-")
            or "increased" in s
            or "reduced" in s
            or "more " in s
            or "less " in s
            or "chance" in s
            or "Leech" in s
            or "Recouped" in s
            or "per player level" in s
            or "Resistance" in s
            or "Accuracy" in s
            or "Blind" in s
            or "Onslaught" in s
            or s == "Unmodifiable"
        ):
            out.append(s)

    return out


def count_explicit_headers(lines: list[str]) -> int:
    return sum(
        1
        for line in lines
        if (
            "Prefix Modifier" in line
            or "Suffix Modifier" in line
            or "Crafted Prefix Modifier" in line
            or "Crafted Suffix Modifier" in line
            or "Desecrated Prefix Modifier" in line
            or "Desecrated Suffix Modifier" in line
        )
        and "Implicit Modifier" not in line
    )


def classify_pair(before_rarity: str, after_rarity: str) -> str:
    if before_rarity == "Unique" or after_rarity == "Unique":
        return "unique"
    if before_rarity == "Rare" or after_rarity == "Rare":
        return "rare"
    if before_rarity == "Magic" or after_rarity == "Magic":
        return "magic"
    if before_rarity == "Normal" or after_rarity == "Normal":
        return "normal"
    return "unknown"


def load_dataset() -> list[dict]:
    if not DATASET_PATH.exists():
        raise SystemExit(f"Could not find {DATASET_PATH}")

    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "pairs" not in data:
        raise SystemExit(f"Invalid dataset format in {DATASET_PATH}")

    return data["pairs"]


def load_mapping_candidates() -> list[dict[str, str]]:
    if not MAPPING_CANDIDATES_PATH.exists():
        return []

    with MAPPING_CANDIDATES_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def esc(value: object) -> str:
    return html.escape(str(value))


def display_base(name: str, base: str) -> str:
    if base:
        return f"{name}<br><small>{base}</small>"
    return f"{name}<br><small>(no separate base line)</small>"


def render_mod_list(lines: list[str]) -> str:
    if not lines:
        return "<em>No parsed mod lines</em>"

    return "<ul>" + "".join(f"<li><code>{esc(line)}</code></li>" for line in lines) + "</ul>"


def render_stats_table(before_stats: dict, after_stats: dict) -> str:
    keys = [
        ("quality", "Quality"),
        ("armour", "Armour"),
        ("evasion", "Evasion"),
        ("energy_shield", "Energy Shield"),
        ("sockets", "Sockets"),
        ("rune", "Rune"),
        ("requirements", "Requires"),
    ]

    rows = []
    for key, label in keys:
        before = before_stats.get(key, "")
        after = after_stats.get(key, "")
        if before or after:
            rows.append(
                f"<tr><th>{esc(label)}</th><td>{esc(before)}</td><td>{esc(after)}</td></tr>"
            )

    if not rows:
        return "<em>No basic stats parsed</em>"

    return f"""
    <table class="mini">
        <thead><tr><th>Stat</th><th>Before</th><th>After</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
    </table>
    """


def render_mapping_candidates(candidates: list[dict[str, str]]) -> str:
    if not candidates:
        return "<p><em>No provisional modifier mapping candidates available.</em></p>"

    order = {
        "confirmed_candidate": 0,
        "likely_candidate": 1,
        "ambiguous": 2,
        "duplicate_only": 3,
    }

    def sort_key(candidate: dict[str, str]) -> tuple[int, int]:
        return (
            order.get(candidate.get("confidence_summary", "ambiguous"), 4),
            -int(candidate.get("sample_count", "0") or "0"),
        )

    sorted_candidates = sorted(candidates, key=sort_key)
    rows = []
    for c in sorted_candidates:
        rows.append(
            f"""
            <tr>
                <td><code>{esc(c.get('before_modifier_name', ''))}</code></td>
                <td><code>{esc(c.get('before_stats', ''))}</code></td>
                <td><code>{esc(c.get('after_modifier_name', ''))}</code></td>
                <td><code>{esc(c.get('after_stats', ''))}</code></td>
                <td>{esc(c.get('confidence_summary', ''))}</td>
                <td>{esc(c.get('sample_count', '0'))}</td>
                <td>{esc(c.get('character_levels', ''))}</td>
            </tr>
            """
        )

    return f"""
    <table>
        <thead>
            <tr>
                <th>Before modifier</th>
                <th>Before stats</th>
                <th>After modifier</th>
                <th>After stats</th>
                <th>Confidence</th>
                <th>Samples</th>
                <th>Character levels</th>
            </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
    </table>
    """


def render_html(pairs: list[dict]) -> str:
    total = len(pairs)
    status_counts = Counter(p["uid_status"] for p in pairs)
    category_counts = Counter(p["category"] for p in pairs)
    duplicate_count = sum(1 for p in pairs if p.get("is_exact_duplicate"))
    stonefist_count = sum(
        1
        for p in pairs
        if "Fists of Stone" in p["after_text"]
    )

    rows = []

    for p in pairs:
        searchable = " ".join(
            [
                p["test_id"],
                p["category"],
                p["before_rarity"],
                p["after_rarity"],
                p["before_name"],
                p["before_base"],
                p["after_name"],
                p["after_base"],
                p["uid_status"],
                p.get("captured_at", ""),
                p.get("character_level", ""),
                p.get("notes", ""),
                " ".join(p["before_lines"]),
                " ".join(p["after_lines"]),
            ]
        ).lower()

        unique_tag = '<span class="tag unique">unique</span>' if p["is_unique"] else ""
        category_tag = f'<span class="tag">{esc(p["category"])}</span>'

        before_display = display_base(esc(p["before_name"]), esc(p["before_base"]))
        after_display = display_base(esc(p["after_name"]), esc(p["after_base"]))

        duplicate_state = "duplicate" if p.get("is_exact_duplicate") else "original"
        duplicate_tag = ""
        if p.get("is_exact_duplicate"):
            duplicate_tag = f'<span class="tag duplicate">duplicate of {esc(p["duplicate_of"])}</span>'

        rows.append(
            f"""
            <tr data-search="{esc(searchable)}" data-category="{esc(p["category"])}" data-uid="{esc(p["uid_status"])}" data-duplicate="{duplicate_state}">
                <td>{esc(p["test_id"])}</td>
                <td>
                    <strong>{before_display}</strong>
                    <div class="arrow">→</div>
                    <strong>{after_display}</strong>
                    <div class="tags">{category_tag} {unique_tag} {duplicate_tag}</div>
                    <small>{esc(p["before_rarity"])} → {esc(p["after_rarity"])}</small>
                </td>
                <td>{esc(p["before_item_level"])} → {esc(p["after_item_level"])}</td>
                <td>{esc(uid_badge(p["uid_status"]))}</td>
                <td>{p["before_explicit_count"]} → {p["after_explicit_count"]}</td>
                <td>
                    <details>
                        <summary>Stats</summary>
                        {render_stats_table(p["before_stats"], p["after_stats"])}
                    </details>

                    <details>
                        <summary>Mods</summary>
                        <div class="cols">
                            <div>
                                <h4>Before</h4>
                                {render_mod_list(p["before_lines"])}
                            </div>
                            <div>
                                <h4>After</h4>
                                {render_mod_list(p["after_lines"])}
                            </div>
                        </div>
                    </details>

                    <details>
                        <summary>Raw item text</summary>
                        <div class="cols">
                            <div>
                                <h4>Before raw</h4>
                                <pre>{esc(p["before_text"])}</pre>
                            </div>
                            <div>
                                <h4>After raw</h4>
                                <pre>{esc(p["after_text"])}</pre>
                            </div>
                        </div>
                    </details>

                    <details>
                        <summary>Capture metadata</summary>
                        <table class="mini">
                            <tbody>
                                <tr><th>Captured at</th><td>{esc(p.get("captured_at", ""))}</td></tr>
                                <tr><th>Character level</th><td>{esc(p.get("character_level", ""))}</td></tr>
                                <tr><th>Capture version</th><td>{esc(p.get("capture_version", ""))}</td></tr>
                                <tr><th>Notes</th><td>{esc(p.get("notes", ""))}</td></tr>
                            </tbody>
                        </table>
                    </details>
                </td>
            </tr>
            """
        )

    return f"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Way of the Stonefist Report</title>
<style>
    body {{
        margin: 24px;
        background: #111;
        color: #ddd;
        font-family: system-ui, Segoe UI, sans-serif;
    }}

    h1, h2, h3 {{
        color: #f5d38a;
    }}

    .stats {{
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 18px;
    }}

    .card {{
        background: #1b1b1b;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 12px 16px;
        min-width: 170px;
    }}

    .card .num {{
        font-size: 26px;
        font-weight: 700;
        color: #9cdcfe;
    }}

    input, select {{
        padding: 10px;
        margin: 6px 8px 16px 0;
        background: #1b1b1b;
        border: 1px solid #444;
        color: #eee;
        border-radius: 6px;
        font-size: 15px;
    }}

    input {{
        width: min(720px, 100%);
    }}

    table {{
        border-collapse: collapse;
        width: 100%;
    }}

    th, td {{
        border: 1px solid #333;
        padding: 8px;
        vertical-align: top;
    }}

    th {{
        background: #222;
        color: #f5d38a;
        position: sticky;
        top: 0;
        z-index: 1;
    }}

    tr:nth-child(even) {{
        background: #171717;
    }}

    code {{
        color: #ce9178;
        white-space: pre-wrap;
    }}

    pre {{
        background: #0b0b0b;
        border: 1px solid #333;
        padding: 10px;
        overflow-x: auto;
        white-space: pre-wrap;
        max-height: 520px;
    }}

    details {{
        margin-bottom: 8px;
    }}

    summary {{
        cursor: pointer;
        color: #9cdcfe;
    }}

    .cols {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
    }}

    .mini th {{
        position: static;
        z-index: auto;
    }}

    .tag {{
        display: inline-block;
        background: #263238;
        color: #9cdcfe;
        border: 1px solid #37474f;
        border-radius: 999px;
        padding: 2px 8px;
        margin: 6px 4px 2px 0;
        font-size: 12px;
    }}

    .tag.unique {{
        color: #dcdcaa;
        border-color: #7a6427;
        background: #2f2712;
    }}

    .arrow {{
        color: #888;
        margin: 3px 0;
    }}

    @media (max-width: 1100px) {{
        .cols {{
            grid-template-columns: 1fr;
        }}
    }}
</style>
</head>
<body>
<h1>Way of the Stonefist Transformation Report</h1>

<div class="stats">
    <div class="card">
        <div>Total pairs</div>
        <div class="num">{total}</div>
    </div>
    <div class="card">
        <div>After Fists of Stone</div>
        <div class="num">{stonefist_count}</div>
    </div>
    <div class="card">
        <div>Unique samples</div>
        <div class="num">{category_counts.get("unique", 0)}</div>
    </div>
    <div class="card">
        <div>UID not present</div>
        <div class="num">{status_counts.get("not present", 0)}</div>
    </div>
    <div class="card">
        <div>UID matches</div>
        <div class="num">{status_counts.get("match", 0)}</div>
    </div>
    <div class="card">
        <div>Exact duplicates</div>
        <div class="num">{duplicate_count}</div>
    </div>
</div>

<p>
Mapping candidates are derived from explicit modifier block position and should be treated as provisional until confirmed by isolated samples.
</p>

<section>
    <h2>Modifier mapping candidates</h2>
    {render_mapping_candidates(load_mapping_candidates())}
</section>

<p>
Data source: <code>dataset.json</code>. Generated files: <code>pair_summary.csv</code>, <code>mapping_observations.csv</code>, and <code>mapping_candidates.csv</code>.
</p>

<div>
    <input id="search" placeholder="Filter by mod, base, test id, resistance, onslaught, leech, unique, etc..." />

    <select id="category">
        <option value="">All categories</option>
        <option value="normal">Normal</option>
        <option value="magic">Magic</option>
        <option value="rare">Rare</option>
        <option value="unique">Unique</option>
        <option value="unknown">Unknown</option>
    </select>

    <select id="uid">
        <option value="">All UID statuses</option>
        <option value="not present">UID not present</option>
        <option value="match">UID match</option>
        <option value="mismatch">UID mismatch</option>
        <option value="partial">UID partial</option>
    </select>

    <select id="duplicate">
        <option value="">All duplicate statuses</option>
        <option value="original">Original only</option>
        <option value="duplicate">Duplicates only</option>
    </select>
</div>

<table id="pairs">
    <thead>
        <tr>
            <th>Test</th>
            <th>Item</th>
            <th>Item level</th>
            <th>UID</th>
            <th>Explicit count</th>
            <th>Details</th>
        </tr>
    </thead>
    <tbody>
        {"".join(rows)}
    </tbody>
</table>

<script>
const search = document.getElementById("search");
const category = document.getElementById("category");
const uid = document.getElementById("uid");
const duplicate = document.getElementById("duplicate");
const rows = [...document.querySelectorAll("#pairs tbody tr")];

function applyFilters() {{
    const q = search.value.toLowerCase().trim();
    const cat = category.value;
    const uidStatus = uid.value;
    const duplicateStatus = duplicate.value;

    for (const row of rows) {{
        const matchesSearch = row.dataset.search.includes(q);
        const matchesCategory = !cat || row.dataset.category === cat;
        const matchesUid = !uidStatus || row.dataset.uid === uidStatus;
        const matchesDuplicate = !duplicateStatus || row.dataset.duplicate === duplicateStatus;

        row.style.display = matchesSearch && matchesCategory && matchesUid && matchesDuplicate ? "" : "none";
    }}
}}

search.addEventListener("input", applyFilters);
category.addEventListener("change", applyFilters);
uid.addEventListener("change", applyFilters);
duplicate.addEventListener("change", applyFilters);
</script>

</body>
</html>
"""


def main() -> None:
    pairs = load_dataset()

    if not pairs:
        raise SystemExit("No pairs found in stonefist-captures/dataset.json")

    REPORT_PATH.write_text(render_html(pairs), encoding="utf-8")

    print(f"Loaded {len(pairs)} pairs from {DATASET_PATH}.")
    print(f"Wrote: {REPORT_PATH}")


if __name__ == "__main__":
    main()