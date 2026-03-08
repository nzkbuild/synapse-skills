"""Synapse CLI — Entry point for the `synapse` command."""
import argparse
import os
import shutil
import subprocess
import sys

from synapse import __version__
from synapse.config import (
    FEEDBACK_CAP, MAX_SKILLS, MAX_TASK_LENGTH,
    get_skills_root,
)


def copy_to_clipboard(text):
    """Cross-platform clipboard copy."""
    try:
        if os.name == "nt":
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
                input=text, text=True, capture_output=True,
            )
            return proc.returncode == 0
        elif shutil.which("pbcopy"):
            proc = subprocess.run(["pbcopy"], input=text.encode(), capture_output=True)
            return proc.returncode == 0
        elif shutil.which("xclip"):
            proc = subprocess.run(["xclip", "-selection", "clipboard"],
                                  input=text.encode(), capture_output=True)
            return proc.returncode == 0
        elif shutil.which("xsel"):
            proc = subprocess.run(["xsel", "--clipboard", "--input"],
                                  input=text.encode(), capture_output=True)
            return proc.returncode == 0
    except Exception:
        pass
    return False


def parse_args():
    parser = argparse.ArgumentParser(
        prog="synapse",
        description="Synapse \u2014 Smart skill routing for AI coding agents.",
    )
    parser.add_argument("task", nargs="*", help="Task text to route")
    parser.add_argument("--version", action="version", version=f"synapse {__version__}")
    parser.add_argument("--max", type=int, default=3, help="Max skills to emit (default: 3)")
    parser.add_argument("--feedback", nargs="+", help="Boost skills for future routing")
    parser.add_argument("--verify", action="store_true", help="Verify skills index vs disk")
    parser.add_argument("--bundle", type=str, help="Use a preset skill bundle")
    parser.add_argument("--distill", action="store_true", help="Refine a vague prompt into a clear brief")
    parser.add_argument("--no-clipboard", action="store_true", help="Disable auto-copy")
    parser.add_argument("--no-profile", action="store_true", help="Disable Marq project detection")
    parser.add_argument("--no-memory", action="store_true", help="Disable Tracer memory")
    parser.add_argument("--echo", type=str, metavar="QUERY", help="Search past sessions (Tracer)")
    parser.add_argument("--list-bundles", action="store_true", help="List all bundles")
    parser.add_argument("--search", type=str, metavar="KEYWORD", help="Search skills")
    parser.add_argument("--info", type=str, metavar="SKILL_ID", help="Skill details")
    parser.add_argument("--why", action="store_true", help="Explain scoring")
    parser.add_argument("--no-embeddings", action="store_true",
                        help="Disable semantic matching (keyword-only)")
    return parser.parse_args()


def main():
    args = parse_args()
    max_skills = max(1, min(args.max, MAX_SKILLS))
    task = " ".join(args.task or []).strip()

    # Lazy imports for speed
    from synapse.router import (
        get_skill_id, load_bundles, load_feedback, load_index,
        pick_skills, save_feedback,
    )

    SKILLS_ROOT = get_skills_root()
    index_path = SKILLS_ROOT / "skills_index.json"
    if not index_path.exists():
        print(f"Error: skills_index.json not found at {index_path}", file=sys.stderr)
        print("Run 'synapse setup' to install skills.", file=sys.stderr)
        return 1

    skills = load_index(index_path)
    if not skills:
        print("Error: No skills found in index.", file=sys.stderr)
        return 1

    # --list-bundles
    if args.list_bundles:
        bundles = load_bundles()
        print("=" * 50)
        print("AVAILABLE SKILL BUNDLES")
        print("=" * 50)
        for name, bskills in sorted(bundles.items()):
            print(f"\n{name}:")
            for s in bskills:
                print(f"  - {s}")
        print(f"\nUsage: synapse --bundle <name> \"your task\"")
        print("=" * 50)
        return 0

    # --search
    if args.search:
        keyword = args.search.lower()
        matches = [s for s in skills
                   if keyword in get_skill_id(s).lower()
                   or keyword in (s.get("description") or "").lower()]
        print("=" * 50)
        print(f"SEARCH: '{args.search}' \u2014 {len(matches)} results")
        print("=" * 50)
        for skill in matches[:20]:
            sid = get_skill_id(skill)
            desc = (skill.get("description") or "No description")[:60]
            print(f"  {sid}")
            print(f"    {desc}\n")
        if len(matches) > 20:
            print(f"  ... and {len(matches) - 20} more")
        print("=" * 50)
        return 0

    # --info
    if args.info:
        found = next((s for s in skills if get_skill_id(s).lower() == args.info.lower()), None)
        if not found:
            print(f"Error: Skill '{args.info}' not found.", file=sys.stderr)
            return 1
        sid = get_skill_id(found)
        print("=" * 50)
        print(f"SKILL: {sid}")
        print("=" * 50)
        print(f"  Name:     {found.get('name', 'N/A')}")
        print(f"  Category: {found.get('category', 'N/A')}")
        tags = found.get('tags')
        if tags:
            print(f"  Tags:     {', '.join(tags)}")
        print(f"  Source:   {found.get('source', 'N/A')}")
        desc = found.get('description', 'No description.')
        print(f"\n  {desc}")
        print("=" * 50)
        return 0

    # --verify
    if args.verify:
        skills_dir = SKILLS_ROOT / "skills"
        if not skills_dir.exists():
            skills_dir = SKILLS_ROOT
        skill_paths = {str(p.parent.relative_to(SKILLS_ROOT).as_posix()) for p in skills_dir.rglob("SKILL.md")}
        index_paths = {item.get("path") for item in skills if isinstance(item, dict) and item.get("path")}
        missing_disk = sorted(index_paths - skill_paths)
        missing_index = sorted(skill_paths - index_paths)
        print("=" * 50)
        print("SYNAPSE HEALTH CHECK")
        print("=" * 50)
        print(f"  Index entries:    {len(index_paths)}")
        print(f"  Skill folders:    {len(skill_paths)}")
        print(f"  Missing on disk:  {len(missing_disk)}")
        print(f"  Missing in index: {len(missing_index)}")
        status = "SYNCED" if not missing_disk and not missing_index else "MISMATCH"
        print(f"\n  Status: [{status}]")
        print("=" * 50)
        return 0

    # --echo (Tracer)
    if args.echo:
        from synapse.memory import echo
        results = echo(args.echo)
        if results:
            print(f"\U0001f4d4 Tracer found {len(results)} past sessions:\n")
            for r in results:
                print(f"  {r['date']} {r['time']}: \"{r['task']}\" \u2192 {r['skills']}")
        else:
            print(f"No past sessions found matching \"{args.echo}\".")
        return 0

    if not task:
        print("Error: task text is required.", file=sys.stderr)
        print("Usage: synapse \"your task here\"", file=sys.stderr)
        return 1

    if len(task) > MAX_TASK_LENGTH:
        print(f"Error: Task too long ({len(task)} chars, max {MAX_TASK_LENGTH}).", file=sys.stderr)
        return 1

    # --distill (Distill)
    if args.distill:
        from synapse.distill import run_distill
        task = run_distill(task)

    feedback = load_feedback()
    bundles = load_bundles()
    bundle_set = set(bundles.get(args.bundle or "", []))

    # Marq: project profile boosts
    if not args.no_profile:
        try:
            from synapse.profiles import get_profile_boost_set
            bundle_set = bundle_set | get_profile_boost_set()
        except Exception:
            pass

    # Tracer: master memory boosts
    if not args.no_memory:
        try:
            from synapse.memory import get_master_memory_boosts
            master_boost, master_avoid = get_master_memory_boosts()
            bundle_set = bundle_set | master_boost
        except Exception:
            pass

    # Validate bundle
    if args.bundle and bundle_set:
        skill_ids = {get_skill_id(s) for s in skills}
        missing = bundle_set - skill_ids
        if missing:
            print(f"Warning: Bundle '{args.bundle}' has missing skills: {', '.join(sorted(missing))}",
                  file=sys.stderr)

    # Drift: pick skills
    picked, explanations, skipped_heavy, skipped_filtered, semantic_on = pick_skills(
        skills, task, max_skills, feedback, bundle_set,
        explain=args.why, use_embeddings=not args.no_embeddings,
    )

    # --feedback
    if args.feedback:
        skill_ids = {get_skill_id(s) for s in skills}
        for name in args.feedback:
            if name not in skill_ids:
                print(f"Warning: '{name}' not in index, skipping", file=sys.stderr)
                continue
            feedback[name] = min(feedback.get(name, 0) + 2, FEEDBACK_CAP)
        save_feedback(feedback)

    # Output
    output_lines = []
    if picked:
        output_lines.append(" ".join(f"/{name}" for name in picked))
    output_lines.append(task)
    output_text = "\n".join(output_lines)
    print(output_text)

    # --why explanations
    if args.why:
        mode_label = "semantic+keyword" if semantic_on else "keyword-only"
        print(f"[why] Scoring mode: {mode_label}", file=sys.stderr)
        if skipped_heavy:
            print(f"[why] Skipped heavy: {', '.join(sorted(set(skipped_heavy)))}", file=sys.stderr)
        if skipped_filtered:
            print(f"[why] Filtered: {', '.join(sorted(set(skipped_filtered)))}", file=sys.stderr)
        for name, score, reasons in explanations:
            print(f"[why] {name}: score={score:.1f} ({', '.join(reasons) or 'low match'})", file=sys.stderr)

    # Clipboard
    if not args.no_clipboard:
        if not copy_to_clipboard(output_text):
            pass  # Silent fail for clipboard

    # Tracer: write memory
    if not args.no_memory:
        try:
            from synapse.memory import write_session_entry, write_diary_entry
            scores = [(n, s) for n, s, _ in explanations] if explanations else None
            write_session_entry(task, picked, args.bundle, scores)
            write_diary_entry(task, picked, args.bundle, scores)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
