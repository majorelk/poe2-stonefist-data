#!/usr/bin/env bash
set -euo pipefail

uv run python stonefist_build_dataset.py
uv run python stonefist_report.py

git diff --exit-code -- \
  stonefist-captures/*.csv \
  stonefist-captures/report.html
