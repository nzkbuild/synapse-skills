# Synapse Skills

[![CI](https://github.com/nzkbuild/synapse-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/nzkbuild/synapse-skills/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/synapse-skills)](https://pypi.org/project/synapse-skills/)
[![Python](https://img.shields.io/pypi/pyversions/synapse-skills)](https://pypi.org/project/synapse-skills/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Universal AI skill routing for every coding agent.**

Synapse is the intelligent layer between you and 1,200+ AI skills. It understands what you need, remembers what worked, and gets smarter every session. All offline. All free.

## Quick Start

```bash
pip install synapse-skills
synapse setup
synapse "build a react landing page with auth"
```

Optional semantic matching (recommended):

```bash
pip install synapse-skills[embeddings]
```

## Usage

```bash
# Route skills for a task
synapse "build a react landing page with auth"

# Use a skill bundle
synapse --bundle frontend "redesign the homepage"

# Explain why skills were chosen
synapse --why "fix the login flow"

# Search past sessions (Tracer)
synapse --echo "react"

# Refine a vague prompt (Distill)
synapse --distill "fix my thing"

# Rate skill quality (Groove)
synapse --rate good
synapse --rate bad

# View routing analytics
synapse --stats

# Search skills
synapse --search "authentication"

# Check ecosystem health
synapse --verify
```

## Features

| Feature | What it does |
|---|---|
| **Drift** | Invisible skill routing — AI auto-selects the best skills |
| **Fuse** | Hybrid semantic + keyword matching (never breaks) |
| **Groove** | Tracks outcomes, auto-adjusts future routing |
| **Marq** | Auto-detects your project type, boosts relevant skills |
| **Tracer** | Remembers past sessions, searchable with `--echo` |
| **Distill** | Turns vague prompts into clear, actionable briefs |
| **Offgrid** | 100% offline, zero API keys, zero cost |

## How It Works

```
Your prompt → Distill (refine) → Fuse (match) → Marq (context) → Groove (learn) → Skills
```

1. **Distill** sharpens vague prompts into clear briefs
2. **Fuse** matches using meaning (semantic) + keywords (hybrid)
3. **Marq** boosts skills based on your project type
4. **Groove** adjusts based on what worked before
5. **Drift** outputs the best skills invisibly

Each layer is optional. No semantic model? Keyword-only. No history? Fresh routing. Always works.

## Skill Bundles

16 built-in bundles for common workflows:

```bash
synapse --list-bundles              # See all bundles
synapse --bundle frontend "task"    # Frontend stack
synapse --bundle backend "task"     # Backend stack
synapse --bundle security "task"    # Security audit
synapse --bundle devops "task"      # DevOps/CI/CD
synapse --bundle fullstack "task"   # Full stack
```

Available: `frontend`, `backend`, `marketing`, `security`, `product`, `fullstack`, `devops`, `testing`, `data-science`, `mobile`, `documentation`, `performance`, `ai-engineering`, `architecture`, `startup`, `refactoring`

## Configuration

### Master Memory

Create `.agent/master-memory.md` in your project root to set preferences:

```markdown
- **Preferred Skills:** react-best-practices, api-patterns
- **Avoid Skills:** mobile-ux
- **Notes:** This is a Next.js monorepo
```

### Custom Skills

Drop custom skills in `.agent/skills/custom/<skill-id>/SKILL.md` — Synapse auto-discovers them.

## All Commands

```bash
synapse "task"                  # Route skills
synapse setup                   # First-run setup
synapse --echo "keyword"        # Search past sessions
synapse --distill "vague text"  # Refine prompt
synapse --bundle <name> "task"  # Use bundle
synapse --search "keyword"      # Search skills
synapse --info <skill-id>       # Skill details
synapse --list-bundles          # List bundles
synapse --verify                # Health check
synapse --why "task"            # Explain scoring
synapse --stats                 # Routing analytics
synapse --rate good|bad         # Rate last routing
synapse --feedback <skill>      # Boost a skill
synapse --no-profile "task"     # Skip Marq
synapse --no-memory "task"      # Skip Tracer
synapse --no-embeddings "task"  # Keyword-only mode
synapse --no-clipboard "task"   # No clipboard copy
synapse --max 5 "task"          # Max skills
synapse --version               # Version
```

## Requirements

- Python 3.8+
- That's it.

Optional: `pip install synapse-skills[embeddings]` adds ONNX-based semantic matching (~53MB, no GPU needed).

## License

MIT
