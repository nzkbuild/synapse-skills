# Synapse Skills — Project Context

> **Read this first in any new conversation.** This file is the single source of truth.

## Identity

- **Name:** Synapse Skills
- **Repo:** github.com/nzkbuild/synapse-skills
- **Install:** `pip install synapse-skills`
- **CLI:** `synapse "your task"`
- **Tagline:** Universal AI skill routing for every coding agent
- **Previous name:** Antigravity Optimizer (repo: nzkbuild/antigravity-optimizer)
- **Version:** 3.0.0-alpha.1

## What It Does

Synapse is a cognitive layer between users and 1,200+ AI skills. It understands task intent, remembers what worked, auto-detects project context, and routes the best skills invisibly.

## Signature Features

| Name | What | Status |
|---|---|---|
| **Drift** | Invisible skill routing | ✅ Done |
| **Fuse** | Semantic + keyword hybrid matching | ⚠️ Keyword done, semantic (ONNX) = Phase 2 |
| **Marq** | Auto-detect project type, boost skills | ✅ Done |
| **Tracer** | Session memory + diary + echo recall | ✅ Done |
| **Distill** | Refine vague prompts into clear briefs | ✅ Done |
| **Groove** | Outcome-based learning | ❌ Phase 3 |
| **Offgrid** | 100% offline, zero API keys | ✅ Done |
| **Index** | 1,200+ skill library | ✅ Done |

## Architecture

```
Prompt → Distill (refine) → Fuse (match) → Marq (context) → Groove (learn) → Drift (output)
```

Each layer is optional. Without semantic = keyword-only. Without memory = fresh. Always works.

## Package Structure

```
synapse/
├── cli.py        — Entry point (`synapse` command)
├── config.py     — Paths, constants, defaults
├── router.py     — Core scoring + selection (Drift + Fuse)
├── memory.py     — Tracer (session + diary + echo)
├── profiles.py   — Marq (project detection)
├── distill.py    — Distill (prompt refiner)
└── __init__.py   — Version
```

## Tech Stack

- Python 3.8+ (only prerequisite)
- Optional: `onnxruntime` + `numpy` for semantic matching
- No database — flat JSON + Markdown files
- CI: 3 OS × 2 Python versions

## Roadmap

### Phase 1 — Foundation ✅ DONE
- Package scaffolding, all core modules, CLI, CI, README

### Phase 2 — Semantic Brain (Fuse)
- `synapse/embeddings.py` — ONNX model loader + encoder
- Hybrid scoring: semantic similarity + keyword bonus
- Graceful fallback when no ONNX installed

### Phase 3 — Intelligence (Groove)
- `--stats` command for routing analytics
- Outcome prompt: "Did these skills help?"
- Auto-boost/penalize based on outcomes
- Skill quality scoring

### Phase 4 — Distribution
- Publish to PyPI
- `synapse setup` first-run experience (zero questions)
- Auto-detect IDE + platform
- Skills download via HTTPS (no git needed)

### Phase 5 — Ecosystem Polish
- Expand bundles (12 → 15+)
- New workflows: `/update-synapse`, `/skill-health`, `/recall-sessions`
- Updated rules block for GEMINI.md
- Update old antigravity-optimizer README → redirect
- Migration guide

## Design Principles

1. If the user has to configure something, we failed to auto-detect it
2. Zero questions during setup — smart defaults for everything
3. Every layer is optional — graceful degradation always
4. One prerequisite (Python) — that's it
5. Offline-first — no API keys, no cloud, no cost

## Key Decisions Made

- **Fresh repo** (not a rename) — clean start for new identity
- **pip install** as primary distribution — not git clone
- **`--recall` renamed to `--echo`** — matches Tracer feature name
- **`--intake` renamed to `--distill`** — matches Distill feature name
- **ONNX-only** for embeddings — no PyTorch dependency (~53MB vs ~2GB)
- **12 bundles** expanded from original 7

## Previous Planning Docs

Detailed planning artifacts from the design phase are at:
`C:\Users\nbzkr\.gemini\antigravity\brain\eeeca2c9-e44d-4136-ac05-4cca5f5c1b3e\`

- `implementation_plan.md` — Master plan (consolidated)
- `vision.md` — Project vision and identity
- `evolution_plan.md` — Technical roadmap details
- `ux_simplification.md` — UX complexity audit
- `synapse_ecosystem.md` — Ecosystem map
- `strategic_reality_check.md` — Honest self-assessment
