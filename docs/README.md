# Visual guide to the report

This is a quick, non-technical tour of `stonefist-captures/report.html`. Open that file in any browser after running the build and report scripts (see the main [README](../README.md)).

The report is a single page with tabs across the top. Click a tab to switch views.

## Overview

Your at-a-glance dashboard: total pairs captured, how many went through Stonefist, unique samples, duplicates, and a breakdown of capture-target priorities and coverage status.

Check this tab first after every rebuild, as a sanity check that things look right.

![Overview tab](assets/report-overview.png)

## Capture Targets

A prioritised to-do list of what to go capture next in-game.

- **P1** - modifier is known, but you haven't captured it as an input yet. Go find one.
- **P2** - you have some evidence, but it needs a cleaner, isolated sample to confirm.
- **P3** - corruption/enchantment-only data missing. Lower priority.
- **P4** - already confirmed. Nothing to do.

Filter to `P1` first, then `P2`, when deciding what to hunt for.

![Capture Targets tab](assets/report-capture-targets.png)

## Mapping Families

The heart of the tool: shows what Stonefist appears to turn each modifier into, grouped by the underlying stat rather than exact rolled numbers.

This is where you answer "if my glove has X, what will it become?"

![Mapping Families tab](assets/report-mapping-families.png)

## Modifier Coverage

Compares the full known pool of glove modifiers against what has actually been captured, so you can see what's confirmed, likely, missing, or corruption-only at a glance.

## Output Only

Stat lines seen after Stonefist that don't match anything in the known glove modifier pool. These aren't things you can go capture as an input - they're just outputs Stonefist can produce.

## Pair Explorer

Every captured before/after pair, individually. Expand a row to see item stats, parsed modifiers, capture notes, and the raw item text if you want to double-check the evidence yourself.

![Pair Explorer tab](assets/report-pair-explorer.png)

## Raw Evidence

Not a separate table - raw item text lives inside each row in **Pair Explorer**, under the collapsed "Raw item text" section, so the page doesn't balloon in size.

## Adding your own screenshots

Drop PNG files into `assets/` using these names and they'll show up automatically in this guide and the main README:

- `assets/report-overview.png`
- `assets/report-capture-targets.png`
- `assets/report-mapping-families.png`
- `assets/report-pair-explorer.png`
