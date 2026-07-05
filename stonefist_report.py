from __future__ import annotations

import csv
import html
import re
from pathlib import Path


ROOT = Path("stonefist-captures")
PAIRS_DIR = ROOT / "pairs"
REPORT_PATH = ROOT / "report.html"
PAIR_CSV_PATH = ROOT / "pair_summary.csv"
MOD_CSV_PATH = ROOT / "mod_lines.csv"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def get_field(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def get_name_base(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        if line.startswith("Rarity:"):
            name = lines[i + 1] if i + 1 < len(lines) else ""
            base = lines[i + 2] if i + 2 < len(lines) else ""
            return name, base

    return "", ""


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
            or "chance" in s
            or "Leech" in s
            or "Recouped" in s
            or "per player level" in s
            or s == "Unmodifiable"
            or "Resistance" in s
            or "Accuracy" in s
            or "Blind" in s
            or "Onslaught" in s
        ):
            out.append(s)

    return out


def count_explicit_headers(lines: list[str]) -> int:
    return sum(
        1
        for line in lines
        if "Prefix Modifier" in line or "Suffix Modifier" in line
    )


def load_pairs() -> list[dict]:
    pairs: list[dict] = []

    if not PAIRS_DIR.exists():
        raise SystemExit(f"Could not find {PAIRS_DIR}")

    for pair_dir in sorted(PAIRS_DIR.iterdir()):
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

        pairs.append(
            {
                "test_id": pair_dir.name,
                "before_path": str(before_path),
                "after_path": str(after_path),
                "before_text": before,
                "after_text": after,
                "before_name": before_name,
                "before_base": before_base,
                "after_name": after_name,
                "after_base": after_base,
                "before_ilvl": get_field(before, r"Item Level:\s*(.+)"),
                "after_ilvl": get_field(after, r"Item Level:\s*(.+)"),
                "before_uid": before_uid,
                "after_uid": after_uid,
                "uid_match": bool(before_uid and after_uid and before_uid == after_uid),
                "before_lines": before_lines,
                "after_lines": after_lines,
                "before_explicit_count": count_explicit_headers(before_lines),
                "after_explicit_count": count_explicit_headers(after_lines),
            }
        )

    return pairs


def write_csvs(pairs: list[dict]) -> None:
    with PAIR_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "test_id",
                "before_name",
                "before_base",
                "before_item_level",
                "after_name",
                "after_base",
                "after_item_level",
                "unique_id_match",
                "before_explicit_count",
                "after_explicit_count",
                "before_file",
                "after_file",
            ]
        )

        for p in pairs:
            writer.writerow(
                [
                    p["test_id"],
                    p["before_name"],
                    p["before_base"],
                    p["before_ilvl"],
                    p["after_name"],
                    p["after_base"],
                    p["after_ilvl"],
                    p["uid_match"],
                    p["before_explicit_count"],
                    p["after_explicit_count"],
                    p["before_path"],
                    p["after_path"],
                ]
            )

    with MOD_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["test_id", "side", "line_number", "mod_line"])

        for p in pairs:
            for i, line in enumerate(p["before_lines"], start=1):
                writer.writerow([p["test_id"], "before", i, line])

            for i, line in enumerate(p["after_lines"], start=1):
                writer.writerow([p["test_id"], "after", i, line])


def esc(value: object) -> str:
    return html.escape(str(value))


def render_mod_list(lines: list[str]) -> str:
    if not lines:
        return "<em>No parsed mod lines</em>"

    return "<ul>" + "".join(f"<li><code>{esc(line)}</code></li>" for line in lines) + "</ul>"


def render_html(pairs: list[dict]) -> str:
    total = len(pairs)
    uid_matches = sum(1 for p in pairs if p["uid_match"])
    stonefist_count = sum(1 for p in pairs if p["after_base"] == "Fists of Stone")

    rows = []

    for p in pairs:
        searchable = " ".join(
            [
                p["test_id"],
                p["before_name"],
                p["before_base"],
                p["after_name"],
                p["after_base"],
                " ".join(p["before_lines"]),
                " ".join(p["after_lines"]),
            ]
        ).lower()

        rows.append(
            f"""
            <tr data-search="{esc(searchable)}">
                <td>{esc(p["test_id"])}</td>
                <td>
                    <strong>{esc(p["before_name"])}</strong><br>
                    {esc(p["before_base"])} → <strong>{esc(p["after_base"])}</strong>
                </td>
                <td>{esc(p["before_ilvl"])} → {esc(p["after_ilvl"])}</td>
                <td>{"✅" if p["uid_match"] else "⚠️"}</td>
                <td>{p["before_explicit_count"]} → {p["after_explicit_count"]}</td>
                <td>
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
        min-width: 160px;
    }}

    .card .num {{
        font-size: 28px;
        font-weight: 700;
        color: #9cdcfe;
    }}

    input {{
        width: 100%;
        padding: 10px;
        margin: 12px 0 18px;
        background: #1b1b1b;
        border: 1px solid #444;
        color: #eee;
        border-radius: 6px;
        font-size: 15px;
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
        <div>Unique ID matches</div>
        <div class="num">{uid_matches}</div>
    </div>
    <div class="card">
        <div>After base = Fists of Stone</div>
        <div class="num">{stonefist_count}</div>
    </div>
</div>

<p>
Generated files:
<code>pair_summary.csv</code> and <code>mod_lines.csv</code>.
</p>

<input id="search" placeholder="Filter by mod, base, test id, resistance, onslaught, leech, etc..." />

<table id="pairs">
    <thead>
        <tr>
            <th>Test</th>
            <th>Item</th>
            <th>Item level</th>
            <th>UID match</th>
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
const rows = [...document.querySelectorAll("#pairs tbody tr")];

search.addEventListener("input", () => {{
    const q = search.value.toLowerCase().trim();

    for (const row of rows) {{
        row.style.display = row.dataset.search.includes(q) ? "" : "none";
    }}
}});
</script>

</body>
</html>
"""


def main() -> None:
    pairs = load_pairs()

    if not pairs:
        raise SystemExit("No before/after pairs found in stonefist-captures/pairs")

    write_csvs(pairs)
    REPORT_PATH.write_text(render_html(pairs), encoding="utf-8")

    print(f"Loaded {len(pairs)} pairs.")
    print(f"Wrote: {REPORT_PATH}")
    print(f"Wrote: {PAIR_CSV_PATH}")
    print(f"Wrote: {MOD_CSV_PATH}")


if __name__ == "__main__":
    main()