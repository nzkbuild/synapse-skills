# Migration Guide: Antigravity Optimizer → Synapse Skills

## Overview

Synapse Skills (v3.0) is the successor to Antigravity Optimizer (v2.x). This guide covers
migrating from the old system to the new one.

## What Changed

| Feature | Antigravity v2 | Synapse v3 |
|---------|---------------|------------|
| Package name | `antigravity-optimizer` | `synapse-skills` |
| CLI command | `activate-skills` | `synapse` |
| Skill routing | Keyword-only | Keyword + Semantic + Groove |
| Setup | Manual configuration | `synapse setup` (zero questions) |
| Memory | Basic session log | Tracer (session + diary + echo) |
| Learning | None | Groove (outcome-based) |
| Bundles | 5 presets | 16 presets |

## Migration Steps

### 1. Install Synapse

```bash
pip install synapse-skills

# Optional: enable semantic matching
pip install synapse-skills[embeddings]
```

### 2. Run Setup

```bash
synapse setup
```

This auto-detects your platform and IDE, downloads the skills library, and configures everything.

### 3. Update Your Config Files

**Old (GEMINI.md / rules):**
```
activate-skills "task"
@activate-skills "task"
```

**New:**
```
synapse "task"
```

### 4. Update Workflows

**Old workflow references:**
- `/activate-skills` → `synapse "task"`
- `@activate-skills` → `synapse "task"`

**New workflow commands:**
- `/update-synapse` — Update to latest skills
- `/skill-health` — Check routing analytics
- `/recall-sessions` — Search past routing sessions

### 5. Remove Old Package

```bash
pip uninstall antigravity-optimizer
```

### 6. Skills Library

Your existing `.agent/skills/` directory is compatible — Synapse reads the same `skills_index.json` format. No skill files need to change.

## New Features to Try

- `synapse --why "task"` — See why skills were selected (keyword + semantic scores)
- `synapse --stats` — View routing analytics
- `synapse --rate good` — Rate the last routing (teaches the system)
- `synapse --echo "query"` — Search past routing sessions
- `synapse --bundle devops "task"` — Use a preset skill bundle

## FAQ

**Q: Do I need to re-download all skills?**
A: No. `synapse setup` will install them fresh, but existing `.agent/skills/` directories are compatible.

**Q: Does Synapse require internet access?**
A: Only for `synapse setup` (initial skills download) and the first-run ONNX model download. After that, it works fully offline.

**Q: What if I don't want semantic matching?**
A: Use `synapse --no-embeddings "task"` or simply don't install the `[embeddings]` extra. It falls back to keyword-only scoring.
