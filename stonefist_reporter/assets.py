"""CSS and JS for the generated report page.

Plain string constants (not f-strings), so normal single braces are used
throughout instead of the doubled {{ }} needed inside an f-string.
"""

CSS = """
:root {
    --bg: #0a0d12;
    --surface: #12161f;
    --surface-hover: #171c27;
    --border: #262c38;
    --text: #e7ebf0;
    --text-muted: #8b93a5;
    --accent: #22d3ee;
    --accent-soft: rgba(34, 211, 238, 0.12);
    --success: #34d399;
    --success-soft: rgba(52, 211, 153, 0.12);
    --warning: #f5b942;
    --warning-soft: rgba(245, 185, 66, 0.12);
    --danger: #fb7185;
    --danger-soft: rgba(251, 113, 133, 0.12);
    --special: #b48bfa;
    --special-soft: rgba(180, 139, 250, 0.12);
    --radius: 10px;
    --radius-sm: 6px;
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.5), 0 6px 20px rgba(0, 0, 0, 0.35);
    --nav-h: 56px;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 0 24px 32px;
    background: var(--bg);
    color: var(--text);
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
    line-height: 1.5;
}

h1, h2, h3 {
    color: var(--text);
    font-weight: 700;
}

h2 {
    font-size: 20px;
    margin: 28px 0 6px;
}

h3 {
    font-size: 15px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 24px 0 10px;
}

a {
    color: var(--accent);
}

.page-header {
    padding: 24px 0 12px;
}

.page-header h1 {
    font-size: 28px;
    margin: 0 0 6px;
    background: linear-gradient(90deg, var(--text), var(--accent));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}

.page-header .subtitle {
    color: var(--text-muted);
    margin: 0 0 4px;
    font-size: 14.5px;
}

.page-header .meta {
    color: var(--text-muted);
    font-size: 13px;
    margin: 0;
}

.page-header .meta strong {
    color: var(--text);
}

.tabs {
    position: sticky;
    top: 0;
    z-index: 20;
    background: var(--bg);
    padding: 12px 0;
    margin-bottom: 20px;
    border-bottom: 1px solid var(--border);
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    overflow-x: auto;
}

.tab-btn {
    background: var(--surface);
    color: var(--text-muted);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 8px 14px;
    font-size: 13.5px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}

.tab-btn:hover {
    color: var(--text);
    border-color: var(--accent);
}

.tab-btn.active {
    background: var(--accent-soft);
    color: var(--accent);
    border-color: var(--accent);
}

.tab-panel {
    display: none;
}

.tab-panel.active {
    display: block;
}

.lede {
    color: var(--text-muted);
    max-width: 90ch;
}

.subtle {
    color: var(--text-muted);
    font-size: 13px;
}

.stats {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin: 12px 0 20px;
}

.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 14px 18px;
    min-width: 160px;
}

.card > div:first-child {
    color: var(--text-muted);
    font-size: 12.5px;
    margin-bottom: 4px;
}

.card .num {
    font-size: 24px;
    font-weight: 700;
    color: var(--text);
}

input, select {
    padding: 9px 12px;
    margin: 4px 8px 16px 0;
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: var(--radius-sm);
    font-size: 14px;
    font-family: inherit;
}

input:focus, select:focus {
    outline: none;
    border-color: var(--accent);
}

input {
    width: min(680px, 100%);
}

table {
    border-collapse: collapse;
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 13.5px;
}

th, td {
    border-bottom: 1px solid var(--border);
    padding: 10px 12px;
    vertical-align: top;
    text-align: left;
}

th {
    background: #161b25;
    color: var(--text-muted);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    position: sticky;
    top: var(--nav-h);
    z-index: 5;
}

tbody tr:hover {
    background: var(--surface-hover);
}

tbody tr:nth-child(even) {
    background: rgba(255, 255, 255, 0.015);
}

tr[data-priority="1"], tr[data-status="missing_input_sample"] {
    border-left: 3px solid var(--warning);
}

tr[data-priority="2"], tr[data-status="likely_mapping"] {
    border-left: 3px solid var(--accent);
}

tr[data-priority="3"], tr[data-status="corruption_only_missing"] {
    border-left: 3px solid var(--danger);
}

tr[data-priority="4"], tr[data-status="confirmed_mapping"] {
    border-left: 3px solid var(--success);
}

code {
    color: #d3c6a2;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 4px;
    padding: 1px 4px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    font-family: "Cascadia Code", Consolas, monospace;
    font-size: 12.5px;
}

pre {
    background: #06080b;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 12px;
    overflow-x: auto;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    max-height: 520px;
    font-family: "Cascadia Code", Consolas, monospace;
    font-size: 12.5px;
}

details {
    margin-bottom: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 4px 12px;
}

summary {
    cursor: pointer;
    color: var(--accent);
    font-weight: 600;
    padding: 8px 0;
}

.cols {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding-bottom: 10px;
}

.mini th {
    position: static;
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 700;
    border: 1px solid transparent;
    white-space: nowrap;
}

.badge-success { background: var(--success-soft); color: var(--success); border-color: rgba(52, 211, 153, 0.35); }
.badge-warning { background: var(--warning-soft); color: var(--warning); border-color: rgba(245, 185, 66, 0.35); }
.badge-danger { background: var(--danger-soft); color: var(--danger); border-color: rgba(251, 113, 133, 0.35); }
.badge-accent { background: var(--accent-soft); color: var(--accent); border-color: rgba(34, 211, 238, 0.35); }
.badge-special { background: var(--special-soft); color: var(--special); border-color: rgba(180, 139, 250, 0.35); }
.badge-muted { background: rgba(139, 147, 165, 0.12); color: var(--text-muted); border-color: rgba(139, 147, 165, 0.3); }

.tag {
    display: inline-block;
    background: rgba(139, 147, 165, 0.12);
    color: var(--text-muted);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 2px 9px;
    margin: 6px 4px 2px 0;
    font-size: 11.5px;
}

.tag.unique {
    color: var(--special);
    border-color: rgba(180, 139, 250, 0.35);
    background: var(--special-soft);
}

.tag.duplicate {
    color: var(--warning);
    border-color: rgba(245, 185, 66, 0.35);
    background: var(--warning-soft);
}

.arrow {
    color: var(--text-muted);
    margin: 3px 0;
}

@media (max-width: 1100px) {
    .cols {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 720px) {
    body {
        padding: 0 12px 24px;
    }

    .tabs {
        flex-wrap: nowrap;
    }
}
"""

SCRIPT = """
const tabButtons = [...document.querySelectorAll(".tab-btn")];
const tabPanels = [...document.querySelectorAll(".tab-panel")];

function activateTab(name) {
    for (const btn of tabButtons) {
        btn.classList.toggle("active", btn.dataset.tab === name);
    }
    for (const panel of tabPanels) {
        panel.classList.toggle("active", panel.id === "tab-" + name);
    }
}

for (const btn of tabButtons) {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
}

activateTab("overview");

const search = document.getElementById("search");
const category = document.getElementById("category");
const uid = document.getElementById("uid");
const duplicate = document.getElementById("duplicate");
const pairRows = [...document.querySelectorAll("#pairs tbody tr")];

function applyFilters() {
    const q = search.value.toLowerCase().trim();
    const cat = category.value;
    const uidStatus = uid.value;
    const duplicateStatus = duplicate.value;

    for (const row of pairRows) {
        const matchesSearch = row.dataset.search.includes(q);
        const matchesCategory = !cat || row.dataset.category === cat;
        const matchesUid = !uidStatus || row.dataset.uid === uidStatus;
        const matchesDuplicate = !duplicateStatus || row.dataset.duplicate === duplicateStatus;

        row.style.display = matchesSearch && matchesCategory && matchesUid && matchesDuplicate ? "" : "none";
    }
}

search.addEventListener("input", applyFilters);
category.addEventListener("change", applyFilters);
uid.addEventListener("change", applyFilters);
duplicate.addEventListener("change", applyFilters);

const capturePriorityFilter = document.getElementById("capture-priority-filter");
const captureRows = [...document.querySelectorAll("#capture-targets-table tbody tr")];

function applyCaptureFilter() {
    const val = capturePriorityFilter.value;
    for (const row of captureRows) {
        row.style.display = !val || row.dataset.priority === val ? "" : "none";
    }
}

capturePriorityFilter.addEventListener("change", applyCaptureFilter);

const coverageStatusFilter = document.getElementById("coverage-status-filter");
const coverageRows = [...document.querySelectorAll("#coverage-table tbody tr")];

function applyCoverageFilter() {
    const val = coverageStatusFilter.value;
    for (const row of coverageRows) {
        row.style.display = !val || row.dataset.status === val ? "" : "none";
    }
}

coverageStatusFilter.addEventListener("change", applyCoverageFilter);
"""
