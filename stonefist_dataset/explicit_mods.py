from __future__ import annotations

import re


def parse_explicit_modifier_blocks(text: str) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    lines = [line.rstrip() for line in text.splitlines()]

    header_pattern = re.compile(
        r'^(?:\{\s*)?(?P<kind>.+?)\s+"(?P<name>[^"]+)"(?:\s+\(Tier:\s*(?P<tier>\d+)\))?.*$'
    )

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        match = header_pattern.match(line)
        if not match:
            i += 1
            continue

        kind = match.group("kind").strip()
        if kind.endswith(" Modifier"):
            kind = kind[: -len(" Modifier")].strip()

        block = {
            "block_index": len(blocks) + 1,
            "modifier_kind": kind,
            "modifier_name": match.group("name").strip(),
            "tier": match.group("tier") or "",
            "header_line": line,
            "stat_lines": [],
        }

        i += 1
        while i < len(lines):
            stat_line = lines[i].strip()
            if not stat_line or stat_line == "--------":
                break
            if header_pattern.match(stat_line):
                break
            block["stat_lines"].append(stat_line)
            i += 1

        blocks.append(block)
        continue

    return blocks
