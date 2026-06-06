# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Status

This is a personal design portfolio/website repository (`bwbarbosa-design/Me`) that is in early setup. No application code exists yet — project files, build system, and framework will be added as the project progresses.

## Knowledge Graph (graphify)

This project is configured to use **graphify** for codebase navigation. When `graphify-out/graph.json` exists:

- For codebase questions: `graphify query "<question>"` — returns a scoped subgraph, much smaller than raw grep output
- For relationships between files/concepts: `graphify path "<A>" "<B>"`
- For focused concept exploration: `graphify explain "<concept>"`
- After modifying code: `graphify update .` to keep the graph current (AST-only, no API cost)
- For broad architecture review: read `graphify-out/GRAPH_REPORT.md`
- For broad navigation (if it exists): `graphify-out/wiki/index.md`

Prefer graphify queries over grep/read for answering questions when the graph is available. Read raw source files only to modify or debug specific code, or when the graph lacks the detail needed.

When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.

## Claude Code Settings

`.claude/settings.json` configures `PreToolUse` hooks that automatically remind Claude to use graphify instead of grep/read/glob when a knowledge graph exists. These hooks are already active — no manual steps needed.
