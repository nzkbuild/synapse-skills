# Synapse Skills — GEMINI.md Rules Block

> Paste this into your project's `GEMINI.md` (or equivalent AI config file)
> to integrate Synapse skill routing into your coding agent.

---

## Skill Routing (Synapse)

Before starting any non-trivial task, use Synapse to load relevant skills:

```bash
synapse "your task description"
```

### When to Route
- **Always route** for: new features, refactoring, debugging, architecture decisions
- **Skip routing** for: typo fixes, simple renames, one-line changes

### Workflow Commands
- `/update-synapse` — Update to the latest skills
- `/skill-health` — Check routing analytics
- `/recall-sessions` — Search past routing history

### Scoring Modes
Synapse uses hybrid scoring (keyword + semantic + outcome learning):
- **Keyword**: Exact token matching against skill names, descriptions, tags
- **Semantic**: ONNX-based sentence embeddings for meaning-level matching
- **Groove**: Outcome-based learning — skills rated as helpful get boosted

### CLI Reference
```bash
synapse "build a REST API"          # Route skills
synapse setup                       # First-run setup
synapse --why "task"                # Explain scoring
synapse --stats                     # Routing analytics
synapse --rate good                 # Rate last routing
synapse --rate bad                  # Rate last routing
synapse --echo "query"              # Search past sessions
synapse --bundle frontend "task"    # Use preset bundle
synapse --no-embeddings "task"      # Keyword-only mode
synapse --verify                    # Check skills integrity
```
