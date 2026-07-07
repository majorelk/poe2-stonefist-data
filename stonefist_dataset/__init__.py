"""Dataset builder for the Stonefist toolchain.

Split by concern:
- paths: generated output paths and CSV fieldname lists
- item_text: generic captured-item-text parsing helpers
- explicit_mods: explicit modifier block parsing
- pairs: raw pair loading/enrichment and duplicate detection
- mapping: mapping observations/candidates/families
- coverage: glove modifier pool coverage and capture targets
- base_controls: normal white base transformation controls
- augment_controls: socket/rune/idol controls
- writers: dataset.json/CSV writing and the main() entry point
"""
