from __future__ import annotations

import os
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from .models import Profile, read_assignments


@dataclass
class Entry:
    name: str
    kind: str
    path: Path
    size: int = 0
    modified: float = 0
    detail: str = ""


def walk_files(root: Path, limit: int = 20000):
    if not root.is_dir():
        return
    count = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in {".git", ".venv", "node_modules", ".yoctotui"})
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_symlink():
                continue
            yield path
            count += 1
            if count >= limit:
                return


def metadata(profile: Profile) -> list[Entry]:
    entries = []
    # Do not traverse tmp/downloads while indexing metadata.
    skip = {profile.build_path.resolve(), cache_path(profile, "downloads").resolve(), cache_path(profile, "sstate").resolve()}
    roots = [profile.root_path]
    if profile.mode in {"kas", "kas-container"} and profile.environment.get("KAS_WORK_DIR"):
        work = Path(profile.environment["KAS_WORK_DIR"]).expanduser().resolve()
        if work != profile.root_path and not work.is_relative_to(profile.root_path):
            roots.append(work)
    for root in roots:
        for directory, dirs, files in os.walk(root, followlinks=False):
            base = Path(directory)
            dirs[:] = sorted(d for d in dirs if d not in {".git", ".venv", "node_modules", ".yoctotui", "tmp", "sstate-cache", "downloads"} and (base / d).resolve() not in skip)
            for name in sorted(files):
                p = base / name
                if p.is_symlink():
                    continue
                if name == "layer.conf" and base.name == "conf":
                    v = read_assignments(p)
                    entries.append(Entry(base.parent.name, "layer", base.parent, detail=v.get("LAYERSERIES_COMPAT:" + base.parent.name, "See layer.conf")))
                elif p.suffix in {".bb", ".bbappend", ".bbclass"}:
                    entries.append(Entry(name, p.suffix[1:], p, detail=str(base.relative_to(root))))
                elif p.suffix in {".yml", ".yaml"}:
                    entries.append(Entry(name, "yaml", p))
                if len(entries) >= 15000:
                    return entries
    return entries


def cache_path(profile: Profile, kind: str) -> Path:
    explicit = profile.downloads if kind == "downloads" else profile.sstate
    key = "DL_DIR" if kind == "downloads" else "SSTATE_DIR"
    value = explicit or read_assignments(profile.build_path / "conf/local.conf").get(key, "")
    value = value.replace("${TOPDIR}", str(profile.build_path))
    if not value or "${" in value:
        return profile.build_path / ("downloads" if kind == "downloads" else "sstate-cache")
    p = Path(value).expanduser()
    return p if p.is_absolute() else profile.build_path / p


def inventory(path: Path, limit=20000) -> list[Entry]:
    items = []
    for p in walk_files(path, limit):
        try:
            s = p.stat()
            items.append(Entry(p.name, p.suffix.lstrip(".") or "file", p, s.st_size, s.st_mtime, str(p.relative_to(path))))
        except OSError:
            continue
    return items


def task_logs(profile: Profile) -> list[Entry]:
    items = []
    work = profile.build_path / "tmp/work"
    # Enumerate only known task-log locations; avoid walking recipe source trees.
    if work.exists():
        for architecture in work.iterdir():
            if not architecture.is_dir() or architecture.is_symlink():
                continue
            for recipe in architecture.iterdir():
                if not recipe.is_dir() or recipe.is_symlink():
                    continue
                for version in recipe.iterdir():
                    temp = version / "temp"
                    if not temp.is_dir() or version.is_symlink():
                        continue
                    for p in temp.glob("log.*"):
                        try:
                            if p.is_symlink():
                                continue
                            s = p.stat()
                            items.append(Entry(p.name, "task log", p, s.st_size, s.st_mtime, recipe.name))
                        except OSError:
                            pass
    return sorted(items, key=lambda e: e.modified, reverse=True)[:3000]


def diagnostics(profile: Profile) -> list[tuple[str, str, str]]:
    results = []
    def check(ok, name, detail):
        results.append(("OK" if ok else "WARN", name, detail))
    check(profile.root_path.is_dir(), "Project root", str(profile.root_path))
    check(profile.build_path.is_dir(), "Build directory", str(profile.build_path))
    for name in ("local.conf", "bblayers.conf"):
        p = profile.build_path / "conf" / name
        check(p.exists(), name, str(p))
    binary = {"host": "bitbake", "kas": "kas", "container": profile.engine, "kas-container": "kas-container"}[profile.mode]
    check(bool(shutil.which(binary)), "Runtime", f"{binary}: {shutil.which(binary) or 'not in PATH; host may need init script'}")
    free = shutil.disk_usage(profile.root_path if profile.root_path.exists() else Path.cwd()).free
    check(free > 20 * 1024**3, "Free disk", f"{human_size(free)} available (20 GiB suggested minimum)")
    for kind in ("downloads", "sstate"):
        p = cache_path(profile, kind)
        check(p.is_dir(), kind, str(p))
    conf = read_assignments(profile.build_path / "conf/local.conf")
    results += [("INFO", k, conf.get(k, "not explicitly set; inspect bitbake -e")) for k in ("MACHINE", "DISTRO", "BB_NUMBER_THREADS", "PARALLEL_MAKE", "INHERIT", "SSTATE_MIRRORS", "PREMIRRORS", "BB_NO_NETWORK", "TMPDIR")]
    return results


def human_size(n: int) -> str:
    value = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return str(n)


def search_log(path: Path, query: str = "", errors_only=False, context=3, max_lines=5000) -> str:
    from collections import deque
    if not query and not errors_only:
        with path.open(errors="replace") as stream:
            return "".join(deque(stream, maxlen=max_lines)).rstrip("\n")
    # Search the complete file while keeping only a bounded set of context lines.
    previous = deque(maxlen=context)
    output = deque(maxlen=max_lines)
    last_added = -1
    until = -1
    matches = 0
    with path.open(errors="replace") as stream:
        for i, raw in enumerate(stream):
            line = raw.rstrip("\n")
            match = query.casefold() in line.casefold() if query else True
            if errors_only:
                match = match and bool(re.search(r"error|failed|fatal|traceback|exception", line, re.I))
            if match:
                matches += 1
                for number, before in previous:
                    if number > last_added:
                        output.append(f"{number+1}: {before}")
                        last_added = number
                until = i + context
            if i <= until and i > last_added:
                output.append(f"{i+1}: {line}")
                last_added = i
            previous.append((i, line))
    if not matches:
        return "No matches in the complete log."
    return f"{matches} matches · showing at most {max_lines} context lines\n" + "\n".join(output)


def cache_candidates(entries: list[Entry], days: int) -> list[Entry]:
    cutoff = time.time() - days * 86400
    protected = {"git2", "svn", "hg", "cvs", "npm2", ".git"}
    return [e for e in entries if e.modified < cutoff
            and not e.name.endswith((".lock", ".done"))
            and not protected.intersection(e.path.parts)
            and not e.path.with_name(e.name + ".lock").exists()]


def prune_cache(root: Path, entries: list[Entry]) -> tuple[int, int]:
    """Delete only explicitly selected stale files, never follow links or delete roots."""
    root = root.resolve()
    removed = freed = 0
    for entry in entries:
        p = entry.path
        if p.is_symlink() or not p.is_file() or p.with_name(p.name + ".lock").exists():
            continue
        try:
            p.resolve().relative_to(root)
            s = p.stat()
            if s.st_mtime != entry.modified or s.st_size != entry.size:
                continue
            p.unlink()
            removed += 1
            freed += s.st_size
        except (OSError, ValueError):
            continue
    return removed, freed
