# Synapse Skills — Full Audit Report & Fix Instructions

**Context:** This repo was built in 5 phases across 2 AI sessions. Phase 1 by Gemini, Phases 2-5 by Claude. An independent audit has been done. Below are ALL findings.

---

## 🔴 CRITICAL: Crash-Level Bugs (MUST FIX FIRST)

### Bug 1: [synapse/config.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/config.py) — Missing `import os`

**Line 2-3 currently:**
```python
import sys
from pathlib import Path
```

**Must be:**
```python
import os
import sys
from pathlib import Path
```

**Impact:** [config.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/config.py) is imported by EVERY module. `os.getenv()` is used on lines 36, 45, 63. Everything crashes with `NameError: name 'os' is not defined`.

**Verified:** `python -c "from synapse.config import get_synapse_home"` → crashes.

---

### Bug 2: [synapse/groove.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/groove.py) — Missing `from pathlib import Path`

**Line 6-8 currently:**
```python
import json
import sys
from datetime import datetime
```

**Must add:**
```python
from pathlib import Path
```

**Impact:** [_detect_project()](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/groove.py#71-79) on line 73 calls `Path.cwd()` but `Path` is never imported. Any call to `--rate` or Groove scoring crashes.

**Verified:** `python -c "from synapse.groove import _detect_project"` → crashes.

---

## 🟡 STRUCTURAL: Missing Skills Pipeline

### The core problem: Synapse is a router without skills.

The repo contains:
- ✅ Router code (Python package [synapse/](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/config.py#34-40) — 10 modules)
- ✅ Data (bundles.json, 16 bundles)
- ✅ Templates (GEMINI_RULES.md, master-memory.md)
- ✅ Workflows (3 files in `.agent/workflows/`)
- ✅ Tests (4 test files)
- ❌ **ZERO actual SKILL.md files** — no skills in this repo
- ❌ **No [skills_sources.json](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/skills_sources.json)** — the upstream source config from old repo wasn't migrated
- ❌ **No working download mechanism** — [setup.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/setup.py) references non-existent GitHub Release URLs

### Where skills actually are:
Skills live in 3 **upstream repos** (configured in old [antigravity-optimizer/skills_sources.json](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/skills_sources.json)):

| Source | Repo | Skills |
|---|---|---|
| sickn33 | `sickn33/antigravity-awesome-skills` | ~1,200 (primary) |
| Anthropic | `anthropics/skills` | Official doc skills |
| Guanyang | `guanyang/antigravity-skills` | 57 curated |

### What must happen:
1. Copy [skills_sources.json](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/skills_sources.json) from old repo → `data/skills_sources.json`
2. Update [synapse/setup.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/setup.py) to clone skills via git (like old [setup.ps1](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/setup.ps1) did) OR create a GitHub Release with `skills.tar.gz` + `skills_index.json`
3. Without this, `synapse setup` will always fail and `synapse "any task"` will say "skills_index.json not found"

---

## 🟡 STRUCTURAL: Rules Not Auto-Installed

### Current:
[templates/GEMINI_RULES.md](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/templates/GEMINI_RULES.md) exists (44 lines) — but it's just a template. Users must manually copy-paste it into their GEMINI.md.

### What old system did:
[install.ps1](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/scripts/install.ps1) auto-appended a rules block to `~/.gemini/GEMINI.md` (or project-level) with version tracking and auto-replacement on upgrade.

### What must happen:
Add a function in [synapse/setup.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/setup.py) (step between templates and verify) that:
1. Detects `~/.gemini/GEMINI.md` (or creates it)
2. Checks if Synapse rules block already exists (look for `<!-- SYNAPSE_VERSION:`)
3. Replaces old block or appends new one
4. Also handle old `ANTIGRAVITY_OPTIMIZER_VERSION` blocks → migrate them

---

## 🟡 STRUCTURAL: Workflows Not Deployed

### Current:
3 workflow files exist at `.agent/workflows/` inside the synapse-skills repo:
- `recall-sessions.md`
- `skill-health.md`
- `update-synapse.md`

**But:** These only work if the user clones this repo. They're not installed to the user's project or global workflows directory.

### What must happen:
[synapse/setup.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/setup.py) should copy workflow files to either:
- `~/.gemini/antigravity/global_workflows/` (global, like old system)
- Or project-level `.agent/workflows/` (project-specific)

Also missing: The main [activate-skills.md](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/workflows/activate-skills.md) workflow (the core one that tells AI how to use Synapse). This was 127 lines in the old system and is the most important workflow.

---

## ✅ What's Good (No Changes Needed)

| File | Lines | Status |
|---|---|---|
| [synapse/cli.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/cli.py) | 345 | ✅ Solid — all flags integrated, Groove interactive rating, lazy imports |
| `synapse/router.py` | ~350 | ✅ Core scoring works, [pick_skills](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/tools/skill_router.py#308-354) updated for embeddings passthrough |
| [synapse/embeddings.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/embeddings.py) | 324 | ✅ Clean Embedder class, ONNX download, caching, graceful degradation |
| `synapse/memory.py` | ~200 | ✅ Tracer works — session, diary, echo, master memory |
| `synapse/profiles.py` | ~120 | ✅ Marq works — project detection, LRU profiles |
| `synapse/distill.py` | ~40 | ✅ Simple but functional |
| [synapse/tokenizer.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/tokenizer.py) | 111 | ✅ Clean WordPiece tokenizer, no deps |
| [synapse/groove.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/groove.py) | 221 | ✅ Good (minus the missing import) — outcomes, per-project, stats |
| [synapse/setup.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/setup.py) | 236 | ⚠️ Framework is good, but download URLs don't work |
| `data/bundles.json` | — | ✅ 16 bundles (expanded from 12) |
| [templates/GEMINI_RULES.md](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/templates/GEMINI_RULES.md) | 44 | ✅ Good content, just not auto-installed |
| `.agent/workflows/` | 3 files | ✅ Good content, just not deployed |
| `tests/` | 4 files | ✅ Exist, coverage unknown |
| [pyproject.toml](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/pyproject.toml) | — | ✅ Correct entry points, deps, metadata |
| `.github/workflows/ci.yml` | — | ✅ Multi-platform CI |

---

## 📋 Prioritized Fix List

### Priority 1: Make it not crash
1. Add `import os` to [synapse/config.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/config.py) (line 2)
2. Add `from pathlib import Path` to [synapse/groove.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/groove.py) (line 6)

### Priority 2: Make skills actually available
3. Copy [skills_sources.json](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/skills_sources.json) to `data/skills_sources.json`
4. Update [synapse/setup.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/setup.py) → add git-based skills download as primary method (clone sparse from `sickn33/antigravity-awesome-skills` etc.)
5. Keep HTTP download as fallback (for when GitHub Releases exist)

### Priority 3: Auto-install rules and workflows
6. Add rules injection to [synapse/setup.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/setup.py) — auto-append GEMINI rules block
7. Add workflow deployment to [synapse/setup.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/setup.py) — copy workflows to user's config
8. Create [activate-skills.md](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/workflows/activate-skills.md) workflow (the main one that tells AI how to use Synapse)

### Priority 4: Verify end-to-end
9. Run `pip install -e .` successfully
10. Run `synapse setup` → skills download
11. Run `synapse "build a react app"` → get skills output
12. Run `pytest` → all pass
13. Run `ruff check synapse/` → no lint errors

### Priority 5: Polish
14. Update CONTEXT.md to reflect current state (all phases done, bugs fixed)
15. Create GitHub Release with proper tags (v3.0.0-beta.1)

---

## File-by-File Change Summary

| File | Action | What to do |
|---|---|---|
| `synapse/config.py:2` | **FIX** | Add `import os` |
| `synapse/groove.py:6` | **FIX** | Add `from pathlib import Path` |
| `data/skills_sources.json` | **CREATE** | Copy from old repo, update descriptions |
| [synapse/setup.py](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/synapse/setup.py) | **MODIFY** | Add git clone skills download, rules injection, workflow deploy |
| `.agent/workflows/activate-skills.md` | **CREATE** | Main workflow telling AI how to use Synapse |
| [CONTEXT.md](file:///c:/Users/nbzkr/OneDrive/Documents/Coding/antigravity-optimizer/synapse-skills/CONTEXT.md) | **UPDATE** | Mark bugs as fixed, document current state |
