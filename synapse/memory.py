"""Synapse Memory (Tracer) — Session memory, routing diary, and echo recall."""
import re
from datetime import datetime
from pathlib import Path

MAX_SESSION_LINES = 500
MEMORY_DIR_NAME = ".agent"
DIARY_DIR_NAME = "routing-diary"


def get_memory_root():
    return Path.cwd() / MEMORY_DIR_NAME

def get_session_memory_path():
    return get_memory_root() / "session-memory.md"

def get_diary_dir():
    return get_memory_root() / DIARY_DIR_NAME

def get_master_memory_path():
    return get_memory_root() / "master-memory.md"


# === Session Memory ===

def write_session_entry(task, picked, bundle_name, scores=None):
    """Append a routing session to session-memory.md."""
    path = get_session_memory_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    skills_str = ", ".join(picked) if picked else "none"

    entry_lines = [
        f"\n## Session: {now}\n",
        f"- **Task:** {task}\n",
        f"- **Skills:** {skills_str}\n",
        f"- **Bundle:** {bundle_name or 'none'}\n",
    ]
    if scores:
        score_parts = [f"{name}({score:.1f})" for name, score in scores[:5]]
        entry_lines.append(f"- **Scores:** {', '.join(score_parts)}\n")
    entry_lines.append("\n")

    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    new_content = existing + "".join(entry_lines)

    lines = new_content.splitlines(keepends=True)
    if len(lines) > MAX_SESSION_LINES:
        overflow = lines[:len(lines) - MAX_SESSION_LINES]
        _archive_to_diary(overflow)
        new_content = "".join(lines[len(lines) - MAX_SESSION_LINES:])

    path.write_text(new_content, encoding="utf-8")


# === Routing Diary ===

def _archive_to_diary(overflow_lines):
    diary_dir = get_diary_dir()
    diary_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    diary_file = diary_dir / f"{today}.md"
    header = f"# Routing Diary \u2014 {today}\n\n" if not diary_file.exists() else ""
    with diary_file.open("a", encoding="utf-8") as f:
        if header:
            f.write(header)
        f.writelines(overflow_lines)


def write_diary_entry(task, picked, bundle_name, scores=None):
    """Write a routing entry directly to today's diary file."""
    diary_dir = get_diary_dir()
    diary_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M:%S")
    diary_file = diary_dir / f"{today}.md"
    header = f"# Routing Diary \u2014 {today}\n\n" if not diary_file.exists() else ""
    skills_str = ", ".join(picked) if picked else "none"
    entry = f"### {now}\n- Task: {task}\n- Skills: {skills_str}\n- Bundle: {bundle_name or 'none'}\n"
    if scores:
        score_parts = [f"{n}({s:.1f})" for n, s in scores[:5]]
        entry += f"- Scores: {', '.join(score_parts)}\n"
    entry += "\n"
    with diary_file.open("a", encoding="utf-8") as f:
        if header:
            f.write(header)
        f.write(entry)


def archive_old_diaries():
    """Move diary files older than current month to archive/."""
    diary_dir = get_diary_dir()
    if not diary_dir.exists():
        return
    current_month = datetime.now().strftime("%Y-%m")
    archive_base = diary_dir / "archive"
    for diary_file in diary_dir.glob("*.md"):
        name = diary_file.stem
        if len(name) == 10 and name[:7] != current_month:
            month_dir = archive_base / name[:7]
            month_dir.mkdir(parents=True, exist_ok=True)
            diary_file.rename(month_dir / diary_file.name)


# === Echo Recall (Tracer) ===

def echo(query, max_results=10):
    """Search past routing sessions by keyword (Tracer echo)."""
    diary_dir = get_diary_dir()
    results = []
    query_tokens = set(query.lower().split())

    search_dirs = [diary_dir]
    archive_dir = diary_dir / "archive"
    if archive_dir.exists():
        for month_dir in sorted(archive_dir.iterdir(), reverse=True):
            if month_dir.is_dir():
                search_dirs.append(month_dir)

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for diary_file in sorted(search_dir.glob("*.md"), reverse=True):
            if len(results) >= max_results:
                break
            try:
                content = diary_file.read_text(encoding="utf-8")
                entries = re.split(r"^### ", content, flags=re.MULTILINE)
                for entry in entries:
                    if not entry.strip():
                        continue
                    if any(t in entry.lower() for t in query_tokens):
                        task_match = re.search(r"Task:\s*(.+)", entry)
                        skills_match = re.search(r"Skills:\s*(.+)", entry)
                        time_match = re.match(r"(\d{2}:\d{2})", entry)
                        if task_match:
                            results.append({
                                "date": diary_file.stem,
                                "time": time_match.group(1) if time_match else "??:??",
                                "task": task_match.group(1).strip(),
                                "skills": skills_match.group(1).strip() if skills_match else "unknown",
                            })
                    if len(results) >= max_results:
                        break
            except Exception:
                continue

    # Also search session memory
    session_path = get_session_memory_path()
    if session_path.exists() and len(results) < max_results:
        try:
            content = session_path.read_text(encoding="utf-8")
            entries = re.split(r"^## Session:", content, flags=re.MULTILINE)
            for entry in entries:
                if not entry.strip():
                    continue
                if any(t in entry.lower() for t in query_tokens):
                    task_match = re.search(r"\*\*Task:\*\*\s*(.+)", entry)
                    skills_match = re.search(r"\*\*Skills:\*\*\s*(.+)", entry)
                    date_match = re.match(r"\s*(\d{4}-\d{2}-\d{2})", entry)
                    if task_match:
                        results.append({
                            "date": date_match.group(1) if date_match else "today",
                            "time": "",
                            "task": task_match.group(1).strip(),
                            "skills": skills_match.group(1).strip() if skills_match else "unknown",
                        })
                if len(results) >= max_results:
                    break
        except Exception:
            pass

    return results


# === Master Memory ===

def load_master_memory():
    """Load master-memory.md and extract preferences."""
    path = get_master_memory_path()
    if not path.exists():
        return {"preferred": set(), "avoid": set(), "notes": []}
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return {"preferred": set(), "avoid": set(), "notes": []}

    preferred, avoid, notes = set(), set(), []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("- **Preferred Skills:**"):
            preferred = {s.strip() for s in line.split(":", 1)[1].split(",") if s.strip()}
        elif line.startswith("- **Avoid Skills:**"):
            avoid = {s.strip() for s in line.split(":", 1)[1].split(",") if s.strip()}
        elif line.startswith("- **Notes:**"):
            notes.append(line.split(":", 1)[1].strip())
    return {"preferred": preferred, "avoid": avoid, "notes": notes}


def get_master_memory_boosts():
    """Return (boost_set, penalty_set) from master memory."""
    mem = load_master_memory()
    return mem["preferred"], mem["avoid"]
