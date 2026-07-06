# Level 82 repeat capture plan

Short working notes for the planned repeat capture pass at character level 82.

## Goal

Re-capture the same 82 gloves already in the dataset, this time at character
level 82, so the level-80 and level-82 results can eventually be compared
for the same glove.

## Plan

1. Capture the same 82 gloves again, at character level 82.
2. Keep the same glove order as the original level-80 pass where possible,
   so pair `STONEFIST-000N` (level 80) and its level-82 counterpart are easy
   to line up by eye later.
3. Do not mix targeted new-modifier hunting into this pass. This pass is
   purely a level repeat of existing gloves - it is not the place to chase
   `P1`/`P2` capture targets from the report. Keep that as separate, later
   work.
4. After capturing, rebuild the dataset and regenerate the report (see
   Validation below).
5. Expected result after a full pass: **164 total pairs** - the existing
   82 at level 80, plus 82 new ones at level 82.

## Out of scope for this pass

- No changes to `stonefist_capture.py` or any other capture logic.
- No manual edits to generated `dataset.json` / CSV / `report.html` outputs.
- No edits to existing raw pair data under `stonefist-captures/pairs/`.
- No targeted hunting for missing/likely modifiers from `capture_targets.csv`.

## Future follow-up

Once both passes exist, add a same-before-hash level comparison: group pairs
by `before_hash` (or another stable identity for "the same glove") across
character levels, so before/after transformations at level 80 vs level 82
can be diffed directly. Not part of this pass - noted here so it isn't lost.

## Validation

Run the normal pipeline after capturing the level-82 batch:

```bash
uv run --python 3.12 python stonefist_build_dataset.py
uv run --python 3.12 python stonefist_report.py
```

Then check the pair/level counts:

```bash
python3 - <<'PY'
import json
from collections import Counter

with open("stonefist-captures/dataset.json", encoding="utf-8") as f:
    data = json.load(f)

pairs = data["pairs"] if isinstance(data, dict) and "pairs" in data else data
levels = Counter(str(p.get("character_level", "")) for p in pairs)

print("pairs:", len(pairs))
print("levels:", levels)
PY
```

Note: `character_level` is a top-level field on each pair in the current
`dataset.json` schema (not nested under a `metadata` key), so the snippet
above reads it directly. Expect `pairs: 164` and `levels` showing `80: 82`
and `82: 82` once the level-82 pass is captured and rebuilt.
