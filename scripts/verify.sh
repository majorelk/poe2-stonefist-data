#!/usr/bin/env bash
set -euo pipefail

uv run pytest
uv run python stonefist_build_dataset.py
uv run python stonefist_report.py
