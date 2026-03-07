"""Synapse Distill — Refine vague prompts into clear, actionable briefs."""
import sys


def normalize_choice(value, options, default):
    value = (value or "").strip().lower()
    if not value:
        return default
    return options.get(value, default)


def run_distill(initial_task):
    """Interactive prompt refinement (Distill feature)."""
    print("\u2728 Synapse Distill \u2014 Let's sharpen your prompt.", file=sys.stderr)
    task = initial_task.strip()
    if not task:
        task = input("What do you want to build or improve? ").strip()

    area = normalize_choice(
        input("Which area? [A] Design [B] Copy/Marketing [C] Engineering [D] Not sure: "),
        {"a": "design", "b": "copy/marketing", "c": "engineering", "d": "unsure"},
        "unsure",
    )
    platform = normalize_choice(
        input("Where will it run? [A] Web [B] Mobile [C] Backend [D] Not sure: "),
        {"a": "web", "b": "mobile", "c": "backend", "d": "unsure"},
        "unsure",
    )
    stack = normalize_choice(
        input("Tech stack? [A] React/Next [B] Vue/Nuxt [C] Svelte [D] Not sure: "),
        {"a": "react/next", "b": "vue/nuxt", "c": "svelte", "d": "unsure"},
        "unsure",
    )

    brief_parts = [f"Task: {task}", f"Area: {area}", f"Platform: {platform}", f"Stack: {stack}"]
    return " | ".join(brief_parts)
