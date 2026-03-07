# Synapse Skills

**Universal AI skill routing for every coding agent.**

Synapse is the intelligent layer between you and 1,200+ AI skills. It understands what you need, remembers what worked, and gets smarter every session. All offline. All free.

## Install

```bash
pip install synapse-skills
```

## Usage

```bash
# Route skills for a task (Drift)
synapse "build a react landing page with auth"

# Search past sessions (Tracer)
synapse --echo "react"

# Refine a vague prompt (Distill)
synapse --distill "fix my thing"

# Use a skill bundle
synapse --bundle frontend "redesign the homepage"

# Search skills
synapse --search "authentication"

# Check ecosystem health
synapse --verify
```

## Signature Features

| Feature | What it does |
|---|---|
| **Drift** | Invisible skill routing — AI auto-selects the best skills |
| **Fuse** | Hybrid semantic + keyword matching (never breaks) |
| **Marq** | Auto-detects your project type, boosts relevant skills |
| **Tracer** | Remembers past sessions, searchable with `--echo` |
| **Distill** | Turns vague prompts into clear, actionable briefs |
| **Groove** | Tracks outcomes, auto-adjusts future routing |
| **Offgrid** | 100% offline, zero API keys, zero cost |
| **Index** | 1,200+ skills from curated upstream sources |

## How It Works

```
Your prompt → Distill (refine) → Fuse (match) → Marq (context) → Groove (learn) → Skills
```

1. **Distill** sharpens vague prompts into clear briefs
2. **Fuse** matches using meaning (semantic) + keywords (hybrid)
3. **Marq** boosts skills based on your project type
4. **Groove** adjusts based on what worked before
5. **Drift** outputs the best skills invisibly

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
synapse --echo "keyword"        # Search past sessions
synapse --distill "vague text"  # Refine prompt
synapse --bundle <name> "task"  # Use bundle
synapse --search "keyword"      # Search skills
synapse --info <skill-id>       # Skill details
synapse --list-bundles          # List bundles
synapse --verify                # Health check
synapse --why "task"            # Explain scoring
synapse --feedback <skill>      # Boost a skill
synapse --no-profile "task"     # Skip Marq
synapse --no-memory "task"      # Skip Tracer
synapse --no-clipboard "task"   # No clipboard copy
synapse --max 5 "task"          # Max skills
synapse --version               # Version
```

## Requirements

- Python 3.8+
- That's it.

Optional: `pip install synapse-skills[embeddings]` for semantic matching (Fuse DualCore).

## License

MIT
