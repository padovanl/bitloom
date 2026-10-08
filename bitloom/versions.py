"""Inspect local release state without fetching or changing branches."""
from pathlib import Path
import re
import subprocess

from .models import Profile
from .inspectors import metadata


def git(path: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else "unavailable"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def release_report(profile: Profile) -> str:
    lines = ["YOCTO RELEASE / LAYER REPORT", "", f"Profile: {profile.name} ({profile.mode})", f"Root: {profile.root_path}", "", "Use separate profiles/build directories for separate release branches.", "Changing branches in a live build is intentionally not automatic.", ""]
    layers = [e for e in metadata(profile) if e.kind == "layer"]
    paths = [profile.root_path] + [e.path for e in layers]
    seen = set()
    for path in paths:
        repo = git(path, "rev-parse", "--show-toplevel")
        if repo in seen or repo == "unavailable":
            continue
        seen.add(repo)
        lines.extend([f"Repository: {repo}", f"  Branch: {git(path, 'branch', '--show-current')}", f"  Revision: {git(path, 'rev-parse', '--short', 'HEAD')}", f"  Describe: {git(path, 'describe', '--tags', '--always')}", f"  Working tree: {'dirty' if git(path, 'status', '--porcelain') else 'clean'}", f"  Local branches: {git(path, 'branch', '--format=%(refname:short)')}", ""])
    core_series = set()
    for layer in layers:
        content = (layer.path / "conf/layer.conf").read_text(errors="replace")
        match = re.search(r'LAYERSERIES_CORENAMES\s*=\s*"([^"\n]+)"', content)
        if match:
            core_series.update(match[1].split())
    lines.append("Core series: " + (", ".join(sorted(core_series)) or "not detected locally"))
    for layer in layers:
        content = (layer.path / "conf/layer.conf").read_text(errors="replace")
        matches = re.findall(r'LAYERSERIES_COMPAT(?:_|:)[\w-]+\s*(?:\?=|=)\s*"([^"\n]+)"', content)
        series = set(" ".join(matches).split())
        verdict = "MATCH" if core_series & series else "CHECK" if not core_series or not series else "MISMATCH"
        lines.append(f"{verdict:8} {layer.name}: {' '.join(sorted(series)) or 'not declared / expression'}")
    lines.extend(["", "Literal compatibility inspection only. bitbake -p is the authoritative metadata validation.", "Documentation: https://docs.yoctoproject.org/"])
    return "\n".join(lines)
