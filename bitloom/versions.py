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


# Yocto release series, oldest first: (series, version, end of community support, LTS).
# Source: Yocto Project release schedule (docs.yoctoproject.org/releases.html).
from datetime import date as _date
SERIES = [
    ("kirkstone", "4.0", _date(2026, 4, 30), True), ("langdale", "4.1", _date(2023, 5, 31), False),
    ("mickledore", "4.2", _date(2023, 11, 30), False), ("nanbield", "4.3", _date(2024, 5, 31), False),
    ("scarthgap", "5.0", _date(2028, 4, 30), True), ("styhead", "5.1", _date(2025, 5, 31), False),
    ("walnascar", "5.2", _date(2025, 11, 30), False), ("whinlatter", "5.3", _date(2026, 5, 31), False),
    ("wrynose", "6.0", _date(2030, 4, 30), True),
]
ORDER = {name: index for index, (name, *_rest) in enumerate(SERIES)}
INFO = {name: (version, end, lts) for name, version, end, lts in SERIES}


def detect_release(profile: Profile, entries=None) -> str | None:
    """Release series from the core layer's LAYERSERIES_CORENAMES (newest name wins)."""
    from .models import read_assignments
    roots = [profile.root_path]
    if profile.environment.get("KAS_WORK_DIR"):
        roots.append(Path(profile.environment["KAS_WORK_DIR"]).expanduser())
    candidates = [root / sub for root in roots for sub in
                  ("poky/meta/conf/layer.conf", "meta/conf/layer.conf", "openembedded-core/meta/conf/layer.conf",
                   "layers/openembedded-core/meta/conf/layer.conf", "sources/poky/meta/conf/layer.conf", "sources/openembedded-core/meta/conf/layer.conf")]
    candidates += [e.path / "conf/layer.conf" for e in entries or [] if e.kind == "layer" and e.name == "meta"]
    for path in candidates:
        names = read_assignments(path).get("LAYERSERIES_CORENAMES", "").split()
        known = [name for name in names if name in ORDER]
        if known:
            return max(known, key=ORDER.get)
        if names:
            return names[0]
    return None


def describe(series: str | None) -> str:
    if series in INFO:
        version, end, lts = INFO[series]
        return f"{series} {version}{' LTS' if lts else ''}"
    return series or "release unknown"


def support(series: str | None, since: str = "", until: str = "") -> tuple[bool | None, str]:
    """(True/False, reason) when the release decides; None when it cannot be known locally."""
    if not since and not until:
        return True, ""
    if series not in ORDER:
        return None, "release not detected; the runtime decides"
    if since and ORDER[series] < ORDER[since]:
        return False, f"needs {describe(since)} or newer (this build: {describe(series)})"
    if until and ORDER[series] > ORDER[until]:
        return False, f"removed after {describe(until)} (this build: {describe(series)})"
    return True, ""
