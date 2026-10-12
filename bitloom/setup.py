"""Guided project setup: find how a project builds and propose ready-to-use profiles.

Detection is read-only and bounded: kas configurations, Poky/OE-Core init scripts,
existing build directories and project launcher scripts that call kas."""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .commands import which
from .models import Profile, Settings, read_assignments

SKIP = {".git", ".venv", "node_modules", ".bitloom", "tmp", "sstate-cache", "downloads", "build", "__pycache__", ".repo"}
INIT_SCRIPTS = ("oe-init-build-env", "poky/oe-init-build-env", "sources/poky/oe-init-build-env", "layers/poky/oe-init-build-env",
                "openembedded-core/oe-init-build-env", "layers/openembedded-core/oe-init-build-env", "sources/openembedded-core/oe-init-build-env")


@dataclass
class Candidate:
    mode: str
    title: str
    evidence: list[str]
    profile: dict
    score: int = 0
    hints: list[str] = field(default_factory=list)


def _files(root: Path, depth: int = 2, limit: int = 4000):
    count = 0
    for directory, dirs, files in os.walk(root):
        base = Path(directory)
        level = len(base.relative_to(root).parts)
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith(".")) if level < depth else []
        for name in sorted(files):
            yield base / name
            count += 1
            if count >= limit:
                return


def kas_files(root: Path) -> list[Path]:
    found = []
    for path in _files(root):
        if path.suffix in {".yml", ".yaml"} and path.stat().st_size < 512 * 1024:
            try:
                head = path.read_text(errors="replace")[:4000]
            except OSError:
                continue
            if re.search(r"^header:\s*$", head, re.M) and re.search(r"^\s+version:\s*\d+", head, re.M) and re.search(r"^(repos|includes|machine|distro|target):", head, re.M | re.S):
                found.append(path)
    # Top-level configurations (with machine/target) first; fragments meant for includes later.
    return sorted(found, key=lambda p: (not re.search(r"^(machine|target):", p.read_text(errors="replace"), re.M), len(p.parts), str(p)))


def launchers(root: Path) -> list[tuple[Path, list[str]]]:
    """Executable scripts that run kas; returns the environment variables they read."""
    found = []
    for path in _files(root, depth=2):
        if path.suffix not in {".sh", ""} or not os.access(path, os.X_OK) or path.stat().st_size > 256 * 1024:
            continue
        try:
            text = path.read_text(errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if not text.startswith("#!") or not re.search(r"\bkas(-container)?\b", text):
            continue
        variables = sorted({v for v in re.findall(r"\$\{?([A-Z][A-Z0-9_]*)", text)
                            if v not in {"HOME", "PATH", "PWD", "USER", "UID", "GID", "SHELL", "TERM", "OLDPWD", "BASH_SOURCE", "KAS_CONTAINER_ENGINE",
                                         "KAS_WORK_DIR", "KAS_BUILD_DIR", "KAS_CONTAINER_IMAGE", "DISPLAY"}})
        found.append((path, variables))
    return found


def build_dirs(root: Path) -> list[Path]:
    result = []
    for conf in sorted(root.glob("*/conf/local.conf")) + sorted(root.glob("*/*/conf/local.conf")):
        if conf.parent.parent.name not in {"meta", "meta-poky"}:
            result.append(conf.parent.parent)
    return result[:10]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", text.lower()).strip("-") or "project"


def detect(root: Path) -> list[Candidate]:
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"{root} is not a directory")
    candidates = []
    configs = kas_files(root)
    engine = "docker" if shutil.which("docker") else "podman" if shutil.which("podman") else "docker"
    for script, variables in launchers(root):
        relative = "./" + str(script.relative_to(root))
        config_var = next((v for v in variables if re.search(r"YML|YAML|KAS|CONF|CONFIG|FILE", v)), variables[0] if variables else "")
        environment = {}
        evidence = [f"{relative} is executable and runs kas"]
        hints = ["The script must accept kas subcommands (build, dump…) and forward 'shell -c COMMAND' for BitBake commands and probes."]
        if config_var:
            environment[config_var] = str(configs[0].relative_to(root)) if configs else ""
            evidence.append(f"reads ${config_var}" + (f"; first kas file: {environment[config_var]}" if configs else ""))
        candidates.append(Candidate("wrapper", f"Launcher script {relative}", evidence,
                                    {"name": slug(root.name + "-" + script.stem), "root": str(root), "mode": "wrapper", "launcher": [relative],
                                     "launcher_shell": ["shell", "-c", "{command}"], "environment": environment}, 30, hints))
    for config in configs[:6]:
        relative = str(config.relative_to(root))
        values = config.read_text(errors="replace")
        machine = (re.search(r"^machine:\s*(\S+)", values, re.M) or [None, ""])[1]
        target = (re.search(r"^target:\s*(\S+)", values, re.M) or [None, ""])[1]
        evidence = [f"kas configuration {relative}" + (f" (machine {machine})" if machine else "")]
        container = bool(which("kas-container")) or not which("kas")
        work = str(Path.home() / "bitloom-work" / slug(root.name + "-" + config.stem))
        profile = {"name": slug(root.name + "-" + config.stem), "root": str(root), "mode": "kas-container" if container else "kas",
                   "kas_file": relative, "machine": machine, "targets": [target] if target else ["core-image-minimal"],
                   "environment": {"KAS_WORK_DIR": work, "KAS_CONTAINER_ENGINE": engine} if container else {}}
        hints = ["kas-container needs a separate work directory on a Linux filesystem (not /mnt/<drive>)."] if container else []
        evidence.append("kas-container found" if which("kas-container") else "kas found" if which("kas") else "neither kas nor kas-container in PATH yet")
        candidates.append(Candidate(profile["mode"], f"kas: {relative}", evidence, profile, 20 if re.search(r"^machine:", values, re.M) else 10, hints))
    for script in INIT_SCRIPTS:
        if (root / script).is_file():
            builds = build_dirs(root) or [root / "build"]
            for build in builds[:3]:
                conf = read_assignments(build / "conf/local.conf")
                evidence = [f"init script {script}", f"build directory {build.relative_to(root) if build.is_relative_to(root) else build}" +
                            (" with conf/local.conf" if (build / "conf/local.conf").exists() else " (created on first build)")]
                candidates.append(Candidate("host", f"Host build: {build.name}", evidence,
                                            {"name": slug(root.name + "-" + build.name), "root": str(root), "mode": "host", "init_script": script,
                                             "build_dir": str(build.relative_to(root)) if build.is_relative_to(root) else str(build),
                                             "machine": conf.get("MACHINE", ""), "distro": conf.get("DISTRO", "")}, 15))
            break
    return sorted(candidates, key=lambda c: -c.score)


def check(profile: Profile) -> list[tuple[str, str]]:
    """Fast checks shown while editing: (status, message)."""
    results = []
    results.append(("OK" if profile.root_path.is_dir() else "ERR", f"project root {profile.root_path}"))
    if profile.mode in {"kas", "kas-container"}:
        for name in profile.kas_file.split(":"):
            results.append(("OK" if (profile.root_path / name).is_file() else "ERR", f"kas file {name}"))
        binary = "kas-container" if profile.mode == "kas-container" else "kas"
        results.append(("OK" if which(binary) else "WARN", f"{binary} {'found' if which(binary) else 'not in PATH'}"))
        work = profile.environment.get("KAS_WORK_DIR", "")
        if profile.mode == "kas-container":
            if not work:
                results.append(("ERR", "set KAS_WORK_DIR to a separate directory"))
            elif str(Path(work).expanduser()).startswith("/mnt/"):
                results.append(("WARN", "KAS_WORK_DIR on /mnt/<drive> is slow and breaks permissions on WSL"))
            else:
                results.append(("OK", f"work directory {work}"))
    elif profile.mode == "wrapper":
        launcher = profile.launcher[0] if profile.launcher else ""
        path = profile.root_path / launcher
        results.append(("OK" if launcher and path.is_file() and os.access(path, os.X_OK) else "ERR", f"launcher {launcher or '(missing)'}"))
        for key, value in profile.environment.items():
            if value.endswith((".yml", ".yaml")):
                results.append(("OK" if (profile.root_path / value).is_file() or Path(value).is_file() else "WARN", f"{key}={value}"))
    elif profile.mode == "host":
        script = profile.init_script
        results.append(("OK" if not script or (profile.root_path / script).is_file() else "ERR", f"init script {script or '(none: start from an initialised shell)'}"))
    try:
        profile.validate()
        results.append(("OK", "profile is valid"))
    except ValueError as exc:
        results.append(("ERR", str(exc)))
    return results


def save(settings: Settings, profile: Profile) -> None:
    """Add (or replace a personal profile with the same name) and make it active."""
    if profile.name in settings.shared:
        raise ValueError("A team profile already uses this name; choose another")
    profile.validate()
    if profile.mode == "kas-container" and profile.environment.get("KAS_WORK_DIR"):
        Path(profile.environment["KAS_WORK_DIR"]).expanduser().mkdir(parents=True, exist_ok=True)
    settings.profiles = [p for p in settings.profiles if p.name != profile.name or p.name in settings.shared] + [profile]
    # A first run starts with an implicit 'default' profile for the working directory: drop it while untouched.
    implicit = getattr(settings, "implicit_default", None)
    if implicit:
        settings.profiles = [p for p in settings.profiles if p is profile or asdict(p) != implicit]
        settings.implicit_default = None
    settings.active = profile.name
    settings.save()


def candidate_json(candidate: Candidate) -> dict:
    return asdict(candidate)
