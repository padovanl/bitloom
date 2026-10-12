"""Day-to-day build insights: time left, what changed since the previous run, and
which recipes fill tmp/work."""
from __future__ import annotations

import json
import os
import re
import shutil
import statistics
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .models import Profile

TASKS = re.compile(r"Running task (\d+) of (\d+)")
SETSCENE = re.compile(r"Running setscene task (\d+) of (\d+)")
SSTATE = re.compile(r"Sstate summary: Wanted (\d+) Local (\d+) Mirrors (\d+) Missed (\d+)")
SUMMARY = re.compile(r"Tasks Summary: Attempted (\d+) tasks of which (\d+) didn't need to be rerun")


def duration(row: dict) -> float | None:
    try:
        end = datetime.fromisoformat(row["finished"]) if row.get("finished") else None
        return (end - datetime.fromisoformat(row["started"])).total_seconds() if end else None
    except (KeyError, TypeError, ValueError):
        return None


def human(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    seconds = int(round(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"


def _argv(value) -> list:
    return json.loads(value) if isinstance(value, str) else list(value)


def previous_runs(history: list[dict], profile: str, argv, before: str | None = None, status="success") -> list[dict]:
    """Earlier runs of the same command in the same profile, newest first (argv as JSON text or list)."""
    wanted = _argv(argv)
    return [r for r in history if r["profile"] == profile and _argv(r["argv"]) == wanted and (status is None or r["status"] == status)
            and (before is None or r["started"] < before)]


def earlier_run(history: list[dict], row: dict) -> dict | None:
    """The previous run of the same command in the same profile (history is newest first):
    the latest successful one if any, otherwise the latest of any status."""
    position = next((i for i, r in enumerate(history) if r.get("id") == row.get("id")), None)
    older = history[position + 1:] if position is not None else [r for r in history if r["started"] < row["started"]]
    same = [r for r in older if r["profile"] == row["profile"] and _argv(r["argv"]) == _argv(row["argv"])]
    return next((r for r in same if r["status"] == "success"), same[0] if same else None)


def eta(history: list[dict], profile: str, argv, started: str, progress, now: datetime | None = None) -> dict | None:
    """Remaining time from task progress and from earlier successful runs of the same command."""
    now = now or datetime.now(timezone.utc)
    try:
        elapsed = (now - datetime.fromisoformat(started)).total_seconds()
    except (TypeError, ValueError):
        return None
    durations = [d for d in (duration(r) for r in previous_runs(history, profile, argv, started)[:5]) if d]
    typical = statistics.median(durations) if durations else None
    estimates, basis = [], []
    done, total = (progress or (0, 0))[:2]
    # Early tasks are cheap and the last image tasks slow: trust the rate only after a while.
    if total and done >= max(20, total * .05) and elapsed > 30:
        estimates.append(elapsed * (total - done) / done)
        basis.append(f"{done}/{total} tasks")
    if typical:
        estimates.append(max(typical - elapsed, 0))
        basis.append(f"previous runs ~{human(typical)}")
    if not estimates:
        return None
    return {"remaining": sum(estimates) / len(estimates), "elapsed": elapsed, "typical": typical, "basis": " · ".join(basis)}


def log_facts(path: Path) -> dict:
    facts = {"tasks": None, "setscene": None, "sstate": None, "attempted": None, "reused": None, "warnings": Counter(), "errors": Counter()}
    try:
        stream = Path(path).open(errors="replace")
    except OSError:
        return facts
    with stream:
        for line in stream:
            if line.startswith("$ "):
                continue
            for key, pattern in (("tasks", TASKS), ("setscene", SETSCENE)):
                match = pattern.search(line)
                if match:
                    facts[key] = int(match[2])
            match = SSTATE.search(line)
            if match:
                wanted, local, mirrors, missed = map(int, match.groups())
                facts["sstate"] = round(100 * (local + mirrors) / wanted, 1) if wanted else None
            match = SUMMARY.search(line)
            if match:
                facts["attempted"], facts["reused"] = int(match[1]), int(match[2])
            for key, marker in (("warnings", "WARNING:"), ("errors", "ERROR:")):
                if marker in line:
                    text = re.sub(r"\b\d+(\.\d+)*\b", "N", line.split(marker, 1)[1].strip())[:200]
                    facts[key][text] += 1
    return facts


def compare(current: dict, previous: dict) -> str:
    """Two history rows of the same command: what changed between the runs."""
    a, b = log_facts(Path(previous["log"])), log_facts(Path(current["log"]))
    rows = [("Duration", human(duration(previous)), human(duration(current))),
            ("Status", previous["status"], current["status"]),
            ("Tasks executed (scheduled)", a["tasks"], b["tasks"]),
            ("Setscene tasks (from sstate)", a["setscene"], b["setscene"]),
            ("Sstate hit rate %", a["sstate"], b["sstate"]),
            ("Tasks reused (summary)", a["reused"], b["reused"]),
            ("Warnings", sum(a["warnings"].values()), sum(b["warnings"].values())),
            ("Errors", sum(a["errors"].values()), sum(b["errors"].values()))]
    lines = [f"Compare runs of: {current['title']}", f"Previous {previous['started']}  →  this {current['started']}", "",
             f"{'':30} {'previous':>14} {'this run':>14}"]
    lines += [f"{name:30} {str(old if old is not None else '—'):>14} {str(new if new is not None else '—'):>14}" for name, old, new in rows]
    new_warnings = sorted(set(b["warnings"]) - set(a["warnings"]))
    gone_warnings = sorted(set(a["warnings"]) - set(b["warnings"]))
    new_errors = sorted(set(b["errors"]) - set(a["errors"]))
    for title, items in (("NEW ERRORS", new_errors), ("NEW WARNINGS", new_warnings), ("WARNINGS GONE", gone_warnings)):
        if items:
            lines += ["", f"{title} ({len(items)})", *(f"  {item}" for item in items[:60])]
    if not (new_errors or new_warnings or gone_warnings):
        lines += ["", "Same warnings and errors as the previous run (numbers are normalised)."]
    lines += ["", "More tasks executed with fewer setscene tasks usually means changed metadata or a cold sstate cache;",
              "use Analysis → Why rebuilding? on a recipe for the signature differences."]
    return "\n".join(lines)


def disk_usage(path: Path, deadline: float) -> int:
    """Allocated bytes of files and directories, like du -s."""
    try:
        total = os.stat(path, follow_symlinks=False).st_blocks * 512
    except OSError:
        return 0
    stack = [path]
    while stack and time.monotonic() < deadline:
        try:
            with os.scandir(stack.pop()) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        total += entry.stat(follow_symlinks=False).st_blocks * 512
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def _du(recipes: list, budget: float) -> dict | None:
    """Sizes with du (several times faster than walking millions of files from Python);
    None when du fails or exceeds the budget."""
    try:
        result = subprocess.run(["du", "-sk", "--", *(str(recipe) for _, recipe in recipes)], capture_output=True,
                                text=True, errors="replace", timeout=budget)
    except (OSError, subprocess.TimeoutExpired):
        return None
    sizes = {}
    for line in result.stdout.splitlines():
        size, _, name = line.partition("\t")
        if size.isdigit():
            sizes[name] = int(size) * 1024
    return sizes or None


def work_usage(profile: Profile, budget: float = 30.0) -> dict:
    """Disk used per recipe work directory in tmp/work (bounded in time)."""
    work = profile.build_path / "tmp/work"
    deadline = time.monotonic() + budget
    rows = []
    recipes = [(arch, recipe) for arch in sorted(p for p in work.iterdir() if p.is_dir() and not p.is_symlink())
               for recipe in sorted(p for p in arch.iterdir() if p.is_dir() and not p.is_symlink())] if work.is_dir() else []
    measured = _du(recipes, budget) if recipes and shutil.which("du") else None
    if measured is not None:
        rows = [{"recipe": recipe.name, "arch": arch.name, "bytes": measured.get(str(recipe), 0)} for arch, recipe in recipes]
    else:
        rows = [{"recipe": recipe.name, "arch": arch.name, "bytes": disk_usage(recipe, deadline)} for arch, recipe in recipes]
    complete = measured is not None or time.monotonic() < deadline
    local = profile.build_path / "conf/local.conf"
    raw = local.read_text(errors="replace") if local.exists() else ""
    return {"rows": sorted(rows, key=lambda r: -r["bytes"]), "complete": complete,
            "rm_work": bool(re.search(r'^\s*INHERIT\s*\+?=\s*"[^"]*\brm_work\b', raw, re.M)),
            "total": sum(r["bytes"] for r in rows)}


def work_report(profile: Profile, data: dict | None = None, limit: int = 30) -> str:
    from .inspectors import human_size
    data = data or work_usage(profile)
    if not data["rows"]:
        return f"tmp/work usage · {profile.name}: {profile.build_path / 'tmp/work'} has no recipe work directories yet (build something first)."
    lines = [f"tmp/work usage · {profile.name} · {human_size(data['total'])} in {len(data['rows'])} recipe work directories"
             + ("" if data["complete"] else " (time budget reached: totals are partial)"), ""]
    lines += [f"{human_size(r['bytes']):>10}  {r['recipe']:40} {r['arch']}" for r in data["rows"][:limit]]
    lines.append("")
    if data["rm_work"]:
        lines.append("rm_work is enabled: work directories are removed after each recipe builds (except RM_WORK_EXCLUDE).")
    else:
        lines += ['rm_work is not enabled. INHERIT += "rm_work" deletes each work directory once its recipe is built,',
                  'typically saving most of tmp/work; keep recipes you debug with RM_WORK_EXCLUDE += "recipe".']
    top = [r["recipe"] for r in data["rows"][:3]]
    if top:
        lines.append("Free space now (sources and sstate stay): " + "; ".join(f"bitbake -c clean {name}" for name in top))
    lines.append("Recipes under devtool keep their sources in the workspace, not in tmp/work.")
    return "\n".join(lines)
