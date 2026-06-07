#!/bin/bash
# Runs before context compaction — overwrites CONTEXT.md with current repo state.
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
OUTFILE="$ROOT/CONTEXT.md"

{
  echo "# Context — $(date '+%d/%m/%Y %H:%M')"
  echo ""
  echo "## Branch"
  git branch --show-current 2>/dev/null
  echo ""
  echo "## Recent commits"
  git log --oneline -10 2>/dev/null
  echo ""
  echo "## Modified files"
  git status --short 2>/dev/null
  echo ""
  echo "## Tracked files"
  git ls-files 2>/dev/null
} > "$OUTFILE"
