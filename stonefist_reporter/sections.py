from __future__ import annotations

import html
from collections import Counter

STATUS_BADGE_KIND = {
    "confirmed_mapping": "success",
    "confirmed_family": "success",
    "confirmed_candidate": "success",
    "likely_mapping": "accent",
    "likely_family": "accent",
    "likely_candidate": "accent",
    "missing_input_sample": "warning",
    "corruption_only_missing": "danger",
    "captured_unmapped": "muted",
    "ambiguous": "muted",
    "duplicate_only": "muted",
}

PRIORITY_BADGE_KIND = {"1": "warning", "2": "accent", "3": "danger", "4": "success"}

UID_BADGE_KIND = {"match": "success", "mismatch": "danger", "partial": "warning", "not present": "muted"}

UID_BADGE_TEXT = {
    "match": "✅ match",
    "mismatch": "❌ mismatch",
    "partial": "⚠️ partial",
    "not present": "— not present",
}


def esc(value: object) -> str:
    return html.escape(str(value))


def badge(text: str, kind: str) -> str:
    return f'<span class="badge badge-{kind}">{esc(text)}</span>'


def status_badge(status: str) -> str:
    return badge(status, STATUS_BADGE_KIND.get(status, "muted"))


def priority_badge(priority: str) -> str:
    return badge(f"P{priority}" if priority else "-", PRIORITY_BADGE_KIND.get(priority, "muted"))


def uid_badge(status: str) -> str:
    return badge(UID_BADGE_TEXT.get(status, status), UID_BADGE_KIND.get(status, "muted"))


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


def _confidence_sort_key(order: dict[str, int]):
    def sort_key(row: dict[str, str]) -> tuple[int, int]:
        return (
            order.get(row.get("confidence_summary", "ambiguous"), 4),
            -int(row.get("sample_count", "0") or "0"),
        )

    return sort_key


def render_mapping_candidates(candidates: list[dict[str, str]]) -> str:
    if not candidates:
        return "<p><em>No provisional modifier mapping candidates available.</em></p>"

    order = {"confirmed_candidate": 0, "likely_candidate": 1, "ambiguous": 2, "duplicate_only": 3}
    sorted_candidates = sorted(candidates, key=_confidence_sort_key(order))

    rows = []
    for c in sorted_candidates:
        rows.append(
            f"""
            <tr>
                <td><code>{esc(c.get('before_modifier_name', ''))}</code></td>
                <td><code>{esc(c.get('before_stats', ''))}</code></td>
                <td><code>{esc(c.get('after_modifier_name', ''))}</code></td>
                <td><code>{esc(c.get('after_stats', ''))}</code></td>
                <td>{status_badge(c.get('confidence_summary', ''))}</td>
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


def render_mapping_families(families: list[dict[str, str]]) -> str:
    if not families:
        return "<p><em>No provisional stat families available.</em></p>"

    order = {"confirmed_family": 0, "likely_family": 1, "ambiguous": 2, "duplicate_only": 3}
    sorted_families = sorted(families, key=_confidence_sort_key(order))

    rows = []
    for c in sorted_families:
        rows.append(
            f"""
            <tr>
                <td><code>{esc(c.get('before_stat_template', ''))}</code></td>
                <td><code>{esc(c.get('after_stat_template', ''))}</code></td>
                <td>{esc(c.get('before_modifier_names', ''))}</td>
                <td>{esc(c.get('after_modifier_names', ''))}</td>
                <td>{status_badge(c.get('confidence_summary', ''))}</td>
                <td>{esc(c.get('sample_count', '0'))}</td>
                <td>{esc(c.get('character_levels', ''))}</td>
                <td><code>{esc(c.get('example_before_stats', ''))}</code><br><code>{esc(c.get('example_after_stats', ''))}</code></td>
            </tr>
            """
        )

    return f"""
    <table>
        <thead>
            <tr>
                <th>Before stat family</th>
                <th>After stat family</th>
                <th>Before modifier names</th>
                <th>After modifier names</th>
                <th>Confidence</th>
                <th>Samples</th>
                <th>Character levels</th>
                <th>Example</th>
            </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
    </table>
    """


def render_glove_coverage_summary(coverage: list[dict[str, str]], output_only: list[dict[str, str]]) -> str:
    total_reference = len(coverage)
    captured_input = sum(1 for row in coverage if row.get("seen_as_before_input", "false").lower() == "true")
    confirmed_mappings = sum(1 for row in coverage if row.get("coverage_status") == "confirmed_mapping")
    likely_mappings = sum(1 for row in coverage if row.get("coverage_status") == "likely_mapping")
    missing_input = sum(1 for row in coverage if row.get("coverage_status") == "missing_input_sample")
    corruption_only = sum(1 for row in coverage if row.get("coverage_status") == "corruption_only_missing")
    transformed_only = len(output_only)

    cards = [
        ("Total reference stat families", total_reference),
        ("Captured input families", captured_input),
        ("Confirmed mappings", confirmed_mappings),
        ("Likely mappings", likely_mappings),
        ("Missing input samples", missing_input),
        ("Transformed-output-only families", transformed_only),
        ("Corruption-only missing", corruption_only),
    ]

    return "<div class=\"stats\">" + "".join(
        f"<div class=\"card\"><div>{esc(label)}</div><div class=\"num\">{esc(value)}</div></div>"
        for label, value in cards
    ) + "</div>"


def render_glove_coverage_table(coverage: list[dict[str, str]]) -> str:
    if not coverage:
        return "<p><em>No glove modifier reference pool loaded yet.</em></p>"

    rows = []
    for row in coverage:
        status = row.get("coverage_status", "")
        rows.append(
            f"""
            <tr data-status="{esc(status)}">
                <td><code>{esc(row.get('stat_template', ''))}</code></td>
                <td>{esc(row.get('modifier_names', ''))}</td>
                <td>{esc(row.get('glove_classes', ''))}</td>
                <td>{esc(row.get('pool_types', ''))}</td>
                <td>{status_badge(status)}</td>
                <td>{esc(row.get('sample_ids', ''))}</td>
            </tr>
            """
        )

    return f"""
    <table id="coverage-table">
        <thead>
            <tr>
                <th>Stat template</th>
                <th>Modifier names</th>
                <th>Glove classes</th>
                <th>Pool types</th>
                <th>Coverage status</th>
                <th>Samples</th>
            </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
    </table>
    """


def render_transformed_output_only(output_only: list[dict[str, str]]) -> str:
    if not output_only:
        return "<p><em>No transformed output-only stats found.</em></p>"

    rows = []
    for row in output_only:
        rows.append(
            f"""
            <tr>
                <td><code>{esc(row.get('after_stat_template', ''))}</code></td>
                <td>{esc(row.get('example_after_stats', ''))}</td>
                <td>{esc(row.get('sample_count', '0'))}</td>
                <td>{esc(row.get('sample_ids', ''))}</td>
            </tr>
            """
        )

    return f"""
    <table>
        <thead>
            <tr>
                <th>After stat template</th>
                <th>Example after stats</th>
                <th>Sample count</th>
                <th>Sample ids</th>
            </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
    </table>
    """


def render_capture_targets(targets: list[dict[str, str]]) -> str:
    if not targets:
        return "<p><em>No capture targets available yet.</em></p>"

    rows = []
    for t in targets:
        priority = t.get("priority", "")
        sample_ids = [s for s in t.get("sample_ids", "").split("|") if s]
        rows.append(
            f"""
            <tr data-priority="{esc(priority)}">
                <td>{priority_badge(priority)}</td>
                <td>{esc(t.get('reason', ''))}</td>
                <td><code>{esc(t.get('stat_template', ''))}</code></td>
                <td>{esc(t.get('modifier_names', ''))}</td>
                <td>{esc(t.get('glove_classes', ''))}</td>
                <td>{esc(t.get('pool_types', ''))}</td>
                <td>{esc(t.get('suggested_action', ''))}</td>
                <td>{len(sample_ids)}</td>
            </tr>
            """
        )

    return f"""
    <table id="capture-targets-table">
        <thead>
            <tr>
                <th>Priority</th>
                <th>Reason</th>
                <th>Stat template</th>
                <th>Modifier names</th>
                <th>Glove classes</th>
                <th>Pool types</th>
                <th>Suggested action</th>
                <th>Samples</th>
            </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
    </table>
    """


def render_priority_summary(targets: list[dict[str, str]]) -> str:
    counts = Counter(t.get("priority", "") for t in targets)
    cards = [(f"P{p} capture targets", counts.get(str(p), 0)) for p in (1, 2, 3, 4)]

    return "<div class=\"stats\">" + "".join(
        f"<div class=\"card\"><div>{esc(label)}</div><div class=\"num\">{esc(value)}</div></div>"
        for label, value in cards
    ) + "</div>"


def _render_pair_row(p: dict) -> str:
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

    return f"""
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
        <td>{uid_badge(p["uid_status"])}</td>
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


def render_overview_section(
    pairs: list[dict],
    coverage: list[dict[str, str]],
    transformed_only: list[dict[str, str]],
    capture_targets: list[dict[str, str]],
) -> str:
    status_counts = Counter(p["uid_status"] for p in pairs)
    category_counts = Counter(p["category"] for p in pairs)
    duplicate_count = sum(1 for p in pairs if p.get("is_exact_duplicate"))
    stonefist_count = sum(1 for p in pairs if "Fists of Stone" in p["after_text"])

    return f"""
    <div class="tab-panel" id="tab-overview">
        <p class="lede">High-level counts across the whole dataset. Use the other tabs for detail and filtering.</p>

        <div class="stats">
            <div class="card"><div>Total pairs</div><div class="num">{len(pairs)}</div></div>
            <div class="card"><div>After Fists of Stone</div><div class="num">{stonefist_count}</div></div>
            <div class="card"><div>Unique samples</div><div class="num">{category_counts.get("unique", 0)}</div></div>
            <div class="card"><div>UID not present</div><div class="num">{status_counts.get("not present", 0)}</div></div>
            <div class="card"><div>UID matches</div><div class="num">{status_counts.get("match", 0)}</div></div>
            <div class="card"><div>Exact duplicates</div><div class="num">{duplicate_count}</div></div>
        </div>

        <h3>Capture targets by priority</h3>
        {render_priority_summary(capture_targets)}

        <h3>Glove modifier coverage status</h3>
        {render_glove_coverage_summary(coverage, transformed_only)}

        <p class="subtle">
        Data source: <code>dataset.json</code>. Generated files: <code>pair_summary.csv</code>, <code>mapping_observations.csv</code>, <code>mapping_candidates.csv</code>, <code>mapping_families.csv</code>, <code>glove_mod_coverage.csv</code>, <code>transformed_output_only.csv</code>, and <code>capture_targets.csv</code>.
        </p>
    </div>
    """


def render_capture_targets_section(capture_targets: list[dict[str, str]]) -> str:
    return f"""
    <div class="tab-panel" id="tab-capture-targets">
        <p class="lede">Capture targets are generated from the glove modifier reference pool and current Stonefist mapping coverage. They are intended to guide what to pick up or isolate next.</p>

        <select id="capture-priority-filter">
            <option value="">All priorities</option>
            <option value="1">P1</option>
            <option value="2">P2</option>
            <option value="3">P3</option>
            <option value="4">P4</option>
        </select>

        {render_capture_targets(capture_targets)}
    </div>
    """


def render_mapping_families_section(
    families: list[dict[str, str]], candidates: list[dict[str, str]]
) -> str:
    return f"""
    <div class="tab-panel" id="tab-mapping-families">
        <p class="lede">
        Mapping candidates are derived from explicit modifier block matching. Multi-mod items are matched by modifier name where possible and should still be treated as provisional until confirmed by isolated samples.
        </p>

        <h3>Modifier stat families</h3>
        <p class="subtle">Stat families group mapping candidates by normalised stat text, so different rolls of the same stat can be reviewed together. These are still provisional.</p>
        {render_mapping_families(families)}

        <h3>Modifier mapping candidates</h3>
        <p class="subtle">Per-modifier-name candidates behind the stat families above.</p>
        {render_mapping_candidates(candidates)}
    </div>
    """


def render_modifier_coverage_section(coverage: list[dict[str, str]]) -> str:
    return f"""
    <div class="tab-panel" id="tab-modifier-coverage">
        <p class="lede">This section compares the PoE2DB glove modifier pool against captured Stonefist samples and shows which reference families are covered.</p>

        <select id="coverage-status-filter">
            <option value="">All statuses</option>
            <option value="missing_input_sample">Missing input sample</option>
            <option value="likely_mapping">Likely mapping</option>
            <option value="confirmed_mapping">Confirmed mapping</option>
            <option value="corruption_only_missing">Corruption-only missing</option>
        </select>

        {render_glove_coverage_table(coverage)}
    </div>
    """


def render_output_only_section(transformed_only: list[dict[str, str]]) -> str:
    return f"""
    <div class="tab-panel" id="tab-output-only">
        <p class="lede">These stat templates are Stonefist transformation outputs that are not present in the loaded glove reference pool. They are not directly targetable as a glove input capture unless they also appear in the reference pool.</p>
        {render_transformed_output_only(transformed_only)}
    </div>
    """


def render_pair_explorer_section(pairs: list[dict]) -> str:
    rows = "".join(_render_pair_row(p) for p in pairs)

    return f"""
    <div class="tab-panel" id="tab-pair-explorer">
        <p class="lede">Search and filter captured before/after pairs. Expand a row's details to see stats, mods, raw item text, and capture metadata.</p>

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
                {rows}
            </tbody>
        </table>
    </div>
    """


def render_raw_evidence_section() -> str:
    return """
    <div class="tab-panel" id="tab-raw-evidence">
        <p class="lede">
        Raw before/after item text is not duplicated here to keep the page small. It remains available inside each
        <strong>Pair Explorer</strong> row, under the collapsed "Raw item text" detail for that pair.
        </p>
    </div>
    """
