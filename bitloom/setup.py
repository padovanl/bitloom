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


KAS_HEADER = re.compile(r"^header:\s*$", re.M)


def kas_includes(path: Path, root: Path) -> list[Path]:
    """Local files a kas configuration includes (header: includes:); includes from other repos are skipped."""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    block = re.search(r"^header:\s*\n((?:[ \t]+.*\n?|\s*\n)*)", text, re.M)
    items = re.search(r"^([ \t]+)includes:\s*\n((?:\1[ \t]+.*\n?)*)", block[1], re.M) if block else None
    result = []
    for name in re.findall(r"^\s*-\s*['\"]?([^'\"\s{}]+\.ya?ml)['\"]?\s*$", items[2] if items else "", re.M):
        # kas resolves local includes from the top of the repository holding the file.
        for base in (root, path.parent):
            if (base / name).is_file():
                result.append((base / name).resolve())
                break
    return result


def kas_values(path: Path, root: Path, seen=None) -> dict:
    """machine, distro and target as kas resolves them: includes first, the file itself last."""
    seen = seen or set()
    if path in seen:
        return {}
    seen.add(path)
    values = {}
    for include in kas_includes(path, root):
        values.update(kas_values(include, root, seen))
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return values
    for key in ("machine", "distro", "target"):
        match = re.search(rf"^{key}:[ \t]*['\"]?([^'\"\s#]+)", text, re.M)
        if match:
            values[key] = match[1]
    list_target = re.search(r"^target:[ \t]*\n((?:[ \t]+-[ \t]*\S+[ \t]*(?:\n|$))+)", text, re.M)
    if list_target:
        values["target"] = " ".join(re.findall(r"-\s*(\S+)", list_target[1]))
    return values


KAS_MODES = ("kas", "kas-container", "wrapper")


def profile_kas_files(profile) -> list[Path]:
    """The kas files a profile builds with: kas_file for kas and kas-container (overlays in order), the file a
    launcher script's variable names (YML=…) for wrapper profiles. With kas, local.conf and bblayers.conf are
    generated from these on every run: configuration is changed here, not in build/conf."""
    names = [n for n in (profile.kas_file or "").split(":") if n] if profile.mode in ("kas", "kas-container") else []
    if profile.mode == "wrapper" or not names:
        names += [part for value in profile.environment.values() for part in value.split(":") if part.endswith((".yml", ".yaml"))]
    files = []
    for name in names:
        path = (profile.root_path / name).resolve()
        if path.suffix in (".yml", ".yaml") and path.is_file() and path not in files:
            files.append(path)
    return files


def kas_local_conf_lines(path: Path) -> list[tuple[int, str]]:
    """(line number in the .yml, configuration line) for every line of the local_conf_header blocks."""
    lines = path.read_text(errors="replace").splitlines()
    result, inside, block_indent = [], False, None
    for number, line in enumerate(lines, 1):
        if re.match(r"^local_conf_header:\s*$", line):
            inside, block_indent = True, None
            continue
        if inside and line and not line[0].isspace():
            inside = False
        if not inside or not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if re.match(r"^\s+[\w\-]+:\s*\|", line):
            block_indent = None
            continue
        if block_indent is None:
            block_indent = indent
        result.append((number, line[block_indent:]))
    return result


def machine_and_distro(profile) -> dict:
    """MACHINE and DISTRO as the build sees them: the kas files when they set them (later files and overlays win,
    the file a launcher's variable names included; Bitloom does not export the profile's values over them), then
    the profile, bitbake-setup's fragments, auto.conf and local.conf. Empty when nothing says it."""
    kas = {}
    for path in profile_kas_files(profile):
        kas.update({k: v for k, v in kas_values(path, profile.root_path).items() if v})
    found = {"MACHINE": kas.get("machine") or profile.machine, "DISTRO": kas.get("distro") or profile.distro}
    fragments = read_assignments(profile.build_path / "conf/toolcfg.conf").get("OE_FRAGMENTS", "").split()
    conf = {**read_assignments(profile.build_path / "conf/local.conf"), **read_assignments(profile.build_path / "conf/auto.conf")}
    for key, kas_key, prefix in (("MACHINE", "machine", "machine/"), ("DISTRO", "distro", "distro/")):
        if not found[key]:
            fragment = next((f.split("/", 1)[1] for f in fragments if f.startswith(prefix)), "")
            found[key] = kas.get(kas_key) or fragment or conf.get(key, "")
    return found


def kas_files(root: Path) -> list[Path]:
    """kas configurations under root: the ones you build first (not included by another file, with a
    machine once includes are resolved), fragments meant for includes last."""
    found = []
    for path in _files(root):
        if path.suffix in {".yml", ".yaml"} and path.stat().st_size < 512 * 1024:
            try:
                head = path.read_text(errors="replace")[:4000]
            except OSError:
                continue
            if KAS_HEADER.search(head) and re.search(r"^\s+version:\s*\d+", head, re.M) and re.search(r"^(repos|machine|distro|target):|^\s+includes:", head, re.M):
                found.append(path)
    included = {inc for path in found for inc in kas_includes(path, root)}
    return sorted(found, key=lambda p: (p.resolve() in included, "machine" not in kas_values(p.resolve(), root), len(p.parts), str(p)))


def _default_value(text: str, name: str) -> str | None:
    """The default in ${NAME:-default}, which may itself hold ${…} (balanced braces)."""
    start = text.find("${" + name + ":-")
    if start < 0:
        return None
    position, depth = start + len(name) + 4, 1
    for index in range(position, len(text)):
        if text.startswith("${", index):
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[position:index]
    return None


def _shell_value(raw: str) -> str:
    """One assignment's value as written: a trailing comment or command dropped, quotes removed
    ("$(dirname "$0")"/out → $(dirname $0)/out)."""
    return re.split(r"\s+#|\s*;\s*|\s+&&\s+(?![^()]*\))", raw.strip())[0].replace('"', "").replace("'", "")


def _bitbake_setup_dir(path: Path) -> bool:
    return (path / "build/init-build-env").is_file() and (path / "config").is_dir() and (path / "layers").is_dir()


def script_work_dir(script: Path, root: Path, variables: dict | None = None) -> str:
    """The KAS_WORK_DIR a launcher script sets or defaults to, with $HOME, $PWD, the script's folder,
    simple variables the script assigns (SCRIPT_DIR=…) and the profile's own variables (YML=kas/a.yml:
    ${YML%.yml}, $(basename $YML .yml)) expanded; "" when it uses something only known at run time."""
    try:
        text = script.read_text(errors="replace")
    except OSError:
        return ""
    default = _default_value(text, "KAS_WORK_DIR")
    match = [None, default] if default is not None else re.search(r"^\s*(?:export\s+)?KAS_WORK_DIR=(.+)$", text, re.M)
    if not match:
        return ""
    assigned = {name: _shell_value(raw) for name, raw in re.findall(r"^\s*(?:export\s+|readonly\s+|local\s+)?([A-Z_][A-Z0-9_]*)=(.+)$", text, re.M)
                if name != "KAS_WORK_DIR" and name not in (variables or {})}
    here = r"\$\(\s*(?:cd\s+)?\$\(\s*dirname\s+\$(?:\{BASH_SOURCE\[0\]\}|BASH_SOURCE|\{?0\}?)\s*\)(?:\s*&&\s*pwd)?\s*\)|\$\(\s*dirname\s+\$(?:\{BASH_SOURCE\[0\]\}|\{?0\}?)\s*\)|\$\(\s*(?:realpath|readlink\s+-f)\s+\$\(\s*dirname\s+\$\{?0\}?\s*\)\s*\)"

    def expand(value: str, depth: int = 0) -> str:
        value = re.sub(here, str(script.parent), value)
        for name, replacement in (("HOME", str(Path.home())), ("PWD", str(root))):
            value = re.sub(rf"\$\{{{name}\}}|\${name}\b", replacement, value)
        value = re.sub(r"\$\(\s*pwd\s*\)", str(root), value)
        for name, given in (variables or {}).items():
            stem = Path(given).name.rsplit(".", 1)[0]
            value = re.sub(rf"\$\(\s*basename\s+\$\{{?{name}\}}?(?:\s+\.ya?ml)?\s*\)", stem, value)
            value = re.sub(rf"\$\{{{name}%%?\.\*\}}|\$\{{{name}%\.ya?ml\}}", given.rsplit(".", 1)[0], value)
            value = re.sub(rf"\$\{{{name}\}}|\${name}\b", given, value)
        if depth < 3:
            for name, raw in assigned.items():
                if re.search(rf"\$\{{{name}\}}|\${name}\b", value):
                    value = re.sub(rf"\$\{{{name}\}}|\${name}\b", lambda _m: expand(raw, depth + 1), value)
        return re.sub(r"^~(?=/|$)", str(Path.home()), value)

    value = expand(_shell_value(match[1]))
    if "$" in value or "`" in value:
        return ""
    path = Path(value)
    return str(path if path.is_absolute() else (root / path).resolve())


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


def detect(root: Path, profiles=()) -> list[Candidate]:
    """Proposals for a folder. `profiles` lets the scan recognise a kas work directory an existing
    profile already builds, so it is not offered again as an unrelated host build."""
    root = Path(root).expanduser().resolve()
    owners = [p for p in profiles if p.environment.get("KAS_WORK_DIR")
              and Path(p.environment["KAS_WORK_DIR"]).expanduser().resolve() == root]
    if not root.is_dir():
        raise ValueError(f"{root} is not a directory")
    candidates = []
    # bitbake-setup workspaces: this folder, or a top directory (bitbake-builds/ with site.conf) holding several.
    setups = [root] if _bitbake_setup_dir(root) else [d for d in sorted(root.iterdir()) if d.is_dir() and _bitbake_setup_dir(d)] if (root / "site.conf").is_file() else []
    for setup_dir in setups[:8]:
        fragments = read_assignments(setup_dir / "build/conf/toolcfg.conf").get("OE_FRAGMENTS", "").split()
        machine = next((f.split("/", 1)[1] for f in fragments if f.startswith("machine/")), "")
        distro = next((f.split("/", 1)[1] for f in fragments if f.startswith("distro/")), "")
        evidence = [f"bitbake-setup workspace {setup_dir.name}: build/init-build-env, config/ and layers/"]
        if fragments:
            evidence.append("fragments " + " ".join(fragments))
        profile = {"name": slug(setup_dir.name)[:40], "root": str(setup_dir), "mode": "host", "init_script": "build/init-build-env",
                   "build_dir": "build", "machine": machine, "distro": distro, "targets": ["core-image-minimal"]}
        candidates.append(Candidate("host", f"bitbake-setup: {setup_dir.name}", evidence, profile, 35,
                                    ["bitbake-setup status and update, and the configuration fragments, are in Operations (q / F2)."]))
    configs = kas_files(root)
    engine = "docker" if shutil.which("docker") else "podman" if shutil.which("podman") else "docker"
    for script, variables in launchers(root):
        relative = "./" + str(script.relative_to(root))
        config_var = next((v for v in variables if re.search(r"YML|YAML|KAS|CONF|CONFIG|FILE", v)), variables[0] if variables else "")
        hints = ["The script must accept kas subcommands (build, dump…) and forward 'shell -c COMMAND' for BitBake commands and probes."]
        if not script_work_dir(script, root, {config_var: "x.yml"} if config_var else None):
            hints.append(f"KAS_WORK_DIR is not set by {relative}: kas builds in the folder the script runs from, so Bitloom looks for tmp/ in {root}/build. "
                         "Set KAS_WORK_DIR in the profile if the script builds elsewhere.")
        # One profile per product configuration: YML=<file> ./run_kas.sh build is how such projects pick what to build.
        included = {i for o in configs for i in kas_includes(o, root)}
        standalone = [c for c in configs if c.resolve() not in included]
        # A product names a machine (itself or through its includes); other standalone files are shared fragments.
        top = [c for c in standalone if "machine" in kas_values(c.resolve(), root)] or standalone or configs[:1]
        for config in (top if config_var else [None])[:8]:
            environment, evidence = {}, [f"{relative} is executable and runs kas"]
            values = kas_values(config.resolve(), root) if config else {}
            work = script_work_dir(script, root, {config_var: str(config.relative_to(root))} if config is not None else None)
            if config is not None:
                environment[config_var] = str(config.relative_to(root))
                evidence.append(f"reads ${config_var}; {config_var}={environment[config_var]}" + (f" (machine {values['machine']})" if values.get("machine") else ""))
            if work:
                environment["KAS_WORK_DIR"] = work
                evidence.append(f"builds in {work} (KAS_WORK_DIR in the script)")
            name = slug(config.stem if config is not None and len(top) > 1 else root.name + "-" + script.stem)
            title = f"{config_var}={environment[config_var]} {relative} build" if config is not None else f"Launcher script {relative}"
            profile = {"name": name, "root": str(root), "mode": "wrapper", "launcher": [relative],
                       "launcher_shell": ["shell", "-c", "{command}"], "environment": environment}
            if values.get("machine"):
                profile["machine"] = values["machine"]
            if values.get("target"):
                profile["targets"] = values["target"].split()
            candidates.append(Candidate("wrapper", title, evidence, profile, 30, list(hints)))
    for config in configs[:6]:
        relative = str(config.relative_to(root))
        values = config.read_text(errors="replace")
        resolved = kas_values(config.resolve(), root)
        machine, target = resolved.get("machine", ""), resolved.get("target", "").split(" ")[0]
        evidence = [f"kas configuration {relative}" + (f" (machine {machine})" if machine else "")]
        container = bool(which("kas-container")) or not which("kas")
        work = str(Path.home() / "bitloom-work" / slug(root.name + "-" + config.stem))
        profile = {"name": slug(root.name + "-" + config.stem), "root": str(root), "mode": "kas-container" if container else "kas",
                   "kas_file": relative, "machine": machine, "targets": [target] if target else ["core-image-minimal"],
                   "environment": {"KAS_WORK_DIR": work, "KAS_CONTAINER_ENGINE": engine} if container else {}}
        hints = ["kas-container needs a separate work directory on a Linux filesystem (not /mnt/<drive>)."] if container else []
        evidence.append("kas-container found" if which("kas-container") else "kas found" if which("kas") else "neither kas nor kas-container in PATH yet")
        candidates.append(Candidate(profile["mode"], f"kas: {relative}", evidence, profile, 20 if machine else 10, hints))
    for script in INIT_SCRIPTS:
        if (root / script).is_file():
            builds = build_dirs(root) or [root / "build"]
            for build in builds[:3]:
                conf = read_assignments(build / "conf/local.conf")
                evidence = [f"init script {script}", f"build directory {build.relative_to(root) if build.is_relative_to(root) else build}" +
                            (" with conf/local.conf" if (build / "conf/local.conf").exists() else " (created on first build)")]
                hints = []
                if owners:
                    names = ", ".join(f"{p.name} ({p.mode})" for p in owners)
                    evidence.insert(0, f"kas work directory of profile {names}: switch to it with P instead")
                    hints.append("kas regenerates conf/local.conf here on every kas build; a host build bypasses the kas configuration "
                                 "and needs the Yocto host dependencies installed.")
                candidates.append(Candidate("host", f"Host build: {build.name}", evidence,
                                            {"name": slug(root.name + "-" + build.name), "root": str(root), "mode": "host", "init_script": script,
                                             "build_dir": str(build.relative_to(root)) if build.is_relative_to(root) else str(build),
                                             "machine": conf.get("MACHINE", ""), "distro": conf.get("DISTRO", "")}, 1 if owners else 15, hints))
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
        try:
            text = path.read_text(errors="replace") if path.is_file() else ""
        except OSError:
            text = ""
        if text and not re.search(r'"\$@"|\$@|"\$\*"|\$\*|\bshell\b', text):
            results.append(("WARN", f"{launcher} does not seem to pass its arguments on: BitBake commands run as "
                                    f"'{launcher} {' '.join(profile.launcher_shell)}' need it to forward 'shell -c COMMAND'"))
        build = profile.build_path
        results.append(("OK", f"build directory {build}") if (build / "conf").is_dir() or (build / "tmp").is_dir() else
                       ("WARN", f"no build in {build} yet: set KAS_WORK_DIR (or KAS_BUILD_DIR) in the profile if the script builds elsewhere"))
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
