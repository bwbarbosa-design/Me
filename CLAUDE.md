# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: graphify — Litigation Map Generator

Two complementary tools for visualizing legal case knowledge as an interactive force-directed graph (D3.js):

| File | Purpose |
|---|---|
| `graphify.py` | CLI — reads `graphify.json`, validates, outputs `graph.html` |
| `graphify.json` | Data — nodes (processes, lawyers, entities, events) + links |
| `graphify_codex.html` | Browser tool — paste free text → Claude API → auto-generates graph |

Current case: **Bloco Galeão — A-CEM Fração A/100** (Olhão, Portugal).

## Commands

```bash
# Generate the HTML graph from graphify.json
python graphify.py

# Custom output file
python graphify.py --output mapa.html

# Validate JSON without generating HTML
python graphify.py --validate

# Show graph statistics
python graphify.py --stats

# Use a different data file
python graphify.py --data outro.json
```

No install required — only Python stdlib. Open the generated `graph.html` directly in a browser.

## Data Schema (`graphify.json`)

**Node required fields:** `id`, `label`, `type`, `color`  
**Node optional:** `r` (radius, default 12), `detail.type`, `detail.info[]` (array of `{h, t}` key-value pairs)

**Node types:** `core` · `proc` · `hist` · `lawyer` · `adverse` · `entity` · `event` · `witness`

**Link required fields:** `s` (source id), `t` (target id)  
**Link optional:** `label`, `color`, `strength` (0–1), `dash` (`"4,4"` for indirect relationships)

The `_meta` block (`tool`, `version`, `project`, `updated`) is for display only and not validated.

## `graphify_codex.html` — AI-Powered Generation

Standalone browser tool: paste a free-text knowledge base → calls Claude API → renders graph.

**Security warning:** The current file calls `api.anthropic.com` directly from the browser using a hardcoded model, which requires an API key in client-side code. Never commit a real API key into this file. The intended usage is local-only (open the HTML file directly, enter the key in a prompt or env — currently the fetch has no Authorization header in the uploaded version, meaning the API call will fail until a key is added). If this tool is ever hosted publicly, the API call must be proxied through a backend.

**Model reference:** The file currently references `claude-sonnet-4-20250514`. The current equivalent model ID is `claude-sonnet-4-6`.

## Architecture Notes

`graphify.py` embeds the entire D3.js visualization as a raw string template (`HTML_TEMPLATE`) and injects the graph data as inline JSON via `{{GRAPH_DATA}}` placeholder replacement. There is no build step — the output is a fully self-contained HTML file that loads D3 from CDN.

`graphify_codex.html` is also self-contained. It uses the same D3 force simulation and CSS design system as the static tool, adding a loader screen, Claude API call, and JSON parsing layer on top.

The design system is shared between both tools: dark theme (`#0a0a0f` bg), EB Garamond + JetBrains Mono typography, gold (`#c9a84c`) as primary accent, and a fixed color-per-node-type palette defined in both the Python template and the JS `TYPE_COLORS` map.
