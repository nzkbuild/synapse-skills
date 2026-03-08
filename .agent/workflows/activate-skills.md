---
description: Auto-select and execute skills for a task. Use /activate-skills <task> to run end-to-end.
---

# Activate Skills Router

You are an intelligent skill router. When the user invokes `/activate-skills <task>`, you automatically select and apply the best skills for their task.

## Usage

```text
/activate-skills <task description>
/activate-skills --bundle frontend <task>
/activate-skills --verify
```

## Execution Steps

### Step 1: Locate Synapse

Find the synapse package. Check in order:

1. Run `synapse --version` to verify installation
2. Check `SYNAPSE_SKILLS_ROOT` environment variable
3. Check `~/.codex/skills` for installed skills
4. Check `.agent/skills/` in current project

### Step 2: Run the Router

Execute the Synapse CLI to get recommended skills:

```bash
synapse "<user's task>"
```

With a bundle:

```bash
synapse --bundle frontend "<user's task>"
```

The router outputs something like:

```text
/skill frontend-design (score: 15)
  ✓ keyword:frontend(+8) ✓ tag:design(+4) ✓ semantic(+3.2)
/skill ui-ux-pro-max (score: 12)
  ✓ keyword:design(+6) ✓ tag:ui(+4) ✓ groove(+2.0)
/skill page-cro (score: 10)
  ✓ tag:landing-page(+4) ✓ semantic(+6.1)
```

### Step 3: Parse the Output

Extract the skill IDs from lines starting with `/skill`:

Example: `/skill frontend-design`, `/skill ui-ux-pro-max`, `/skill page-cro`
→ skills = ["frontend-design", "ui-ux-pro-max", "page-cro"]

### Step 4: Load Each Skill

For each skill ID, read its SKILL.md file from:

- `.agent/skills/skills/<skill-id>/SKILL.md` (project-local)
- `~/.codex/skills/skills/<skill-id>/SKILL.md` (global install)

Read the first 300-500 lines of each skill to understand its instructions.

### Step 5: Apply Routing Guardrails

- Cap skills to **3–5** (drop extras if needed).
- If the router suggests heavy/overkill skills (e.g., `loki-mode`), only keep them when the user explicitly asked for autonomous multi-agent execution. Otherwise drop them.
- Prefer skills that directly match the task's domain (design, backend, security, etc.).

### Step 6: Execute the Task

Apply the loaded skill instructions to complete the user's task. The skills provide:

- Best practices and patterns to follow
- Code templates and examples
- Quality standards and checklists

Combine insights from all loaded skills to deliver a high-quality result.

### Step 7: Report What You Used

After completing the task, briefly mention which skills were applied:

```text
[OK] Task completed using: frontend-design, ui-ux-pro-max, page-cro
```

## Groove Feedback

Synapse tracks skill quality with Groove (outcome-based learning):

- Rate skills: `synapse --rate good` or `synapse --rate bad`
- View stats: `synapse --stats`
- Per-project tracking adjusts scores over time

## Special Commands

### --verify

Run `synapse --verify` to check skill counts and integrity.

### --bundle

Use a preset bundle (frontend, backend, marketing, security, product, fullstack, devops, testing, data-science, mobile, documentation, performance, ai-engineering, architecture, startup, refactoring).

Example: `synapse --bundle frontend "build a landing page"`

### --stats

View routing analytics: `synapse --stats`

## Error Handling

- If `synapse` command not found: Ask user to install with `pip install synapse-skills`
- If skill file not found: Skip that skill and continue with others
- If no skills match: Use the "brainstorming" skill as fallback
- If skills not downloaded: Run `synapse setup` first

## Token Budget

- Load maximum 5 skills per task to stay within context limits
- Read 300-500 lines per skill (not entire files)
- If task is simple, 1-2 skills may be sufficient
