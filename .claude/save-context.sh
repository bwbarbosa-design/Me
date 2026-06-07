#!/bin/bash
# Runs before context compaction — saves a snapshot of current repo state.
SNAPSHOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)/.claude/snapshots"
mkdir -p "$SNAPSHOT_DIR"
OUTFILE="$SNAPSHOT_DIR/$(date +%Y-%m-%d_%H-%M-%S).md"

{
  echo "# Context Snapshot — $(date '+%d/%m/%Y %H:%M')"
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
  echo "## Repo files"
  git ls-files 2>/dev/null
} > "$OUTFILE"

echo "Context snapshot saved: $OUTFILE"
