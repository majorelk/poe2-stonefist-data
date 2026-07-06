from __future__ import annotations

from stonefist_reporter import assets, loaders, sections

TABS = [
    ("overview", "Overview"),
    ("capture-targets", "Capture Targets"),
    ("mapping-families", "Mapping Families"),
    ("modifier-coverage", "Modifier Coverage"),
    ("output-only", "Output Only"),
    ("pair-explorer", "Pair Explorer"),
    ("raw-evidence", "Raw Evidence"),
]


def render_html(pairs: list[dict]) -> str:
    coverage = loaders.load_glove_coverage()
    transformed_only = loaders.load_transformed_output_only()
    capture_targets = loaders.load_capture_targets()
    mapping_families = loaders.load_mapping_families()
    mapping_candidates = loaders.load_mapping_candidates()

    stonefist_count = sum(1 for p in pairs if "Fists of Stone" in p["after_text"])

    nav_buttons = "".join(
        f'<button class="tab-btn" data-tab="{tab_id}">{label}</button>' for tab_id, label in TABS
    )

    sections_html = "".join(
        [
            sections.render_overview_section(pairs, coverage, transformed_only, capture_targets),
            sections.render_capture_targets_section(capture_targets),
            sections.render_mapping_families_section(mapping_families, mapping_candidates),
            sections.render_modifier_coverage_section(coverage),
            sections.render_output_only_section(transformed_only),
            sections.render_pair_explorer_section(pairs),
            sections.render_raw_evidence_section(),
        ]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Way of the Stonefist Report</title>
<style>{assets.CSS}</style>
</head>
<body>

<header class="page-header">
    <h1>Way of the Stonefist</h1>
    <p class="subtitle">Evidence-based glove modifier mapping, generated from captured Stonefist transformation pairs.</p>
    <p class="meta"><strong>{len(pairs)}</strong> pairs captured &middot; <strong>{stonefist_count}</strong> confirmed transformed by Fists of Stone</p>
</header>

<nav class="tabs">
{nav_buttons}
</nav>

{sections_html}

<script>{assets.SCRIPT}</script>
</body>
</html>
"""


def main() -> None:
    pairs = loaders.load_dataset()

    if not pairs:
        raise SystemExit("No pairs found in stonefist-captures/dataset.json")

    loaders.REPORT_PATH.write_text(render_html(pairs), encoding="utf-8")

    print(f"Loaded {len(pairs)} pairs from {loaders.DATASET_PATH}.")
    print(f"Wrote: {loaders.REPORT_PATH}")
