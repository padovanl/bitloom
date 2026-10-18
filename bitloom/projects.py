"""Projects: open existing folders, create a new Yocto project, clone one from Git,
and remember recent projects. Every project becomes a profile."""
from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import module_command
from .models import Profile

# Pinned, verified release templates (the same tags Bitloom's real validation builds use).
RELEASES = {
    "scarthgap": {
        "title": "Scarthgap 5.0 LTS (support until 2028-04)",
        "repos": {"poky": {"url": "https://git.yoctoproject.org/poky", "tag": "yocto-5.0.8",
                           "commit": "dc4827b3660bc1a03a2bc3b0672615b50e9137ff", "layers": ["meta", "meta-poky", "meta-yocto-bsp"]}},
        "build_system": None,
    },
    "wrynose": {
        "title": "Wrynose 6.0 LTS (support until 2030-04)",
        "repos": {"bitbake": {"url": "https://git.openembedded.org/bitbake", "tag": "yocto-6.0.2",
                              "commit": "acfe02fa38b5da9e6a36c6cedcf91d4fcbefbfbd", "layers": None},
                  "openembedded-core": {"url": "https://git.openembedded.org/openembedded-core", "tag": "yocto-6.0.2",
                                        "commit": "5d1aa5c806c061a2994f4decb59016610f093213", "layers": ["meta"]},
                  "meta-yocto": {"url": "https://git.yoctoproject.org/meta-yocto", "tag": "yocto-6.0.2",
                                 "commit": "24c24cef5d1523fefe43a3e3d34667b37ae551f3", "layers": ["meta-poky", "meta-yocto-bsp"]}},
        "build_system": "openembedded",
    },
}
MACHINES = ("qemux86-64", "qemuarm64", "qemuarm", "qemuriscv64", "genericx86-64", "beaglebone-yocto")
IMAGES = ("core-image-minimal", "core-image-base", "core-image-full-cmdline", "core-image-weston")
NAME = re.compile(r"[a-z][a-z0-9-]*")
GIT_URL = re.compile(r"(https://|ssh://|git://|file://|git@)[A-Za-z0-9._~:/@+%-]+")


def kas_yaml(release: str, machine: str, distro: str, target: str, layer: str | None) -> str:
    spec = RELEASES[release]
    lines = ["# Created with Bitloom: " + spec["title"] + ".",
             "# Update the pinned tags/commits deliberately; `kas lock` (Kas → Generate kas lock file) records them.",
             "header:", "  version: 14"]
    if spec["build_system"]:
        lines.append(f"build_system: {spec['build_system']}")
    lines += [f"machine: {machine}", f"distro: {distro}", f"target: {target}", "repos:"]
    if layer:
        lines += [f"  {layer.replace('-', '_')}:", f"    path: {layer}"]
    for name, repo in spec["repos"].items():
        lines += [f"  {name}:", f"    url: {repo['url']}", f"    tag: {repo['tag']}", f"    commit: {repo['commit']}", "    layers:"]
        lines += ["      .: disabled"] if repo["layers"] is None else [f"      {item}:" for item in repo["layers"]]
    lines += ["local_conf_header:", "  bitloom: |", '    INHERIT += "buildhistory"', '    BUILDHISTORY_COMMIT = "1"']
    return "\n".join(lines) + "\n"


def new_project_plan(directory: str, name: str, release: str, machine: str, distro: str, target: str, own_layer: bool, owner: str) -> dict:
    root = Path(directory).expanduser()
    if not root.is_absolute():
        raise ValueError("Choose an absolute directory for the new project")
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"{root} exists and is not empty; choose a new folder")
    if not NAME.fullmatch(name or ""):
        raise ValueError("Project name: lowercase letters, digits and hyphens")
    if release not in RELEASES:
        raise ValueError("Choose scarthgap or wrynose")
    for label, value in (("MACHINE", machine), ("DISTRO", distro), ("target", target)):
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value or ""):
            raise ValueError(f"{label} must be a lowercase identifier")
    layer = f"meta-{name}" if own_layer else None
    files = {"kas.yml": kas_yaml(release, machine, distro, target, layer),
             ".gitignore": "build/\n/tmp/\n*.bak-*\n.bitloom/\n",
             "README.md": (f"# {name}\n\nYocto project created with Bitloom ({RELEASES[release]['title']}).\n\n"
                           f"* Build: `kas-container build kas.yml` or Bitloom → `b`\n* MACHINE `{machine}`, DISTRO `{distro}`, image `{target}`\n")}
    if layer:
        from .studio import layer_files
        files.update({f"{layer}/{path}": text for path, text in layer_files(layer, name.replace("-", "_"), "7", "core", release, owner or name).items()})
    return {"root": str(root), "name": name, "release": release, "files": files, "layer": layer}


def bbsetup_plan(directory: str, name: str, release: str, machine: str, distro: str, configuration: str = "poky") -> dict:
    """A project made by bitbake-setup itself: the official template, the chosen machine and distro, run as a job."""
    from .bbsetup import TEMPLATES
    root = Path(directory).expanduser()
    if not root.is_absolute():
        raise ValueError("Choose an absolute directory for the new project")
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"{root} exists and is not empty; choose a new folder")
    if not NAME.fullmatch(name or ""):
        raise ValueError("Project name: lowercase letters, digits and hyphens")
    spec = TEMPLATES.get(release)
    if spec is None:
        raise ValueError(f"bitbake-setup is not available for {release}: it arrived with BitBake 2.16 (Yocto 5.3). Create {release} projects with kas.")
    if machine not in spec["machines"]:
        raise ValueError(f"The {spec['config']} template offers MACHINE {', '.join(spec['machines'])}; for another board use kas, or add its layer after the setup")
    if distro not in spec["distros"]:
        raise ValueError(f"The {spec['config']} template offers DISTRO {', '.join(spec['distros'])}")
    if configuration not in spec["configurations"]:
        raise ValueError(f"Configuration: {', '.join(spec['configurations'])}")
    choices = [f"machine/{machine}", f"distro/{distro}"]
    from .bbsetup import argv
    shown = argv(root, spec["config"], name, configuration, choices, ["bitbake-setup"])
    return {"root": str(root), "name": name, "release": release, "tool": "bitbake-setup", "files": {}, "layer": None,
            "command": shown, "setup": str(root / name),
            "display": " \\\n    ".join(shlex.join(part) for part in (shown[:5], shown[5:9], shown[9:14], shown[14:])),
            "job": module_command("bitloom.bbsetup", "--top", str(root), "--release", release, "--name", name, "--configuration", configuration,
                                  *[x for c in choices for x in ("--choice", c)])}


def bbsetup_request(plan: dict, runtime: str, machine: str, distro: str, target: str) -> dict:
    """The job that runs bitbake-setup, and the profile to save when it succeeds: in the kas build image
    (container, the project mounted at its own path) or on the host."""
    from .bbsetup import IMAGE
    if runtime not in {"container", "host"}:
        raise ValueError("runtime must be container or host")
    engine = "docker" if shutil.which("docker") else "podman" if shutil.which("podman") else ""
    if runtime == "container" and not engine:
        raise ValueError("No docker or podman found: install one, or choose the host runtime")
    setup = plan["setup"]
    profile = Profile(name=plan["name"], root=setup, mode="container" if runtime == "container" else "host", init_script="build/init-build-env",
                      build_dir="build", machine=machine, distro=distro, targets=[target or "core-image-minimal"])
    if runtime == "container":
        profile.engine, profile.image, profile.container_root = engine, IMAGE, setup
    job = plan["job"] + (["--engine", engine, "--image", IMAGE] if runtime == "container" else [])
    return {"top": plan["root"], "job": job, "profile": profile, "dest": setup}


def create_project(plan: dict, runtime: str = "kas-container", work_base: Path | None = None) -> Profile:
    root = Path(plan["root"])
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"{root} exists and is not empty")
    root.mkdir(parents=True, exist_ok=True)
    for name, text in plan["files"].items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as stream:
            stream.write(text)
    if shutil.which("git"):
        subprocess.run(["git", "init", "-q", str(root)], check=False, timeout=30)
    work = (work_base or Path.home() / "bitloom-work") / plan["name"]
    environment = {"KAS_WORK_DIR": str(work)} if runtime == "kas-container" else {}
    if runtime == "kas-container":
        work.mkdir(parents=True, exist_ok=True)
    target = re.search(r"^target: (\S+)", plan["files"]["kas.yml"], re.M)[1]
    return Profile(name=plan["name"], root=str(root), mode=runtime, kas_file="kas.yml", environment=environment, targets=[target])


def clone_argv(url: str, destination: str, branch: str = "") -> list[str]:
    url, destination, branch = url.strip(), destination.strip(), branch.strip()
    if url.startswith("-") or not GIT_URL.fullmatch(url):
        raise ValueError("Enter an https://, ssh://, git@ or file:// URL")
    target = Path(destination).expanduser()
    if not target.is_absolute():
        raise ValueError("Choose an absolute destination folder")
    if target.exists():
        raise ValueError(f"{target} already exists")
    argv = ["git", "clone", "--progress"]
    if branch:
        if branch.startswith("-") or not re.fullmatch(r"[A-Za-z0-9._/-]+", branch):
            raise ValueError("Invalid branch or tag name")
        argv += ["--branch", branch]
    return argv + ["--", url, str(target)]


def default_destination(url: str, base: Path) -> str:
    name = re.sub(r"\.git$", "", url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]) or "project"
    return str(base / name)


def project_rows(settings, recent) -> list[dict]:
    """Recent folders plus every profile's root, once each. A root can hold several profiles
    (YML=a.yml / YML=b.yml on one launcher): all are listed, and the active one is preferred."""
    roots: dict[str, list[str]] = {}
    for profile in settings.profiles:
        roots.setdefault(str(profile.root_path), []).append(profile.name)
    items, seen = [], set()
    for item in recent.load() + [{"root": root, "how": "profile"} for root in roots]:
        if item["root"] in seen:
            continue
        seen.add(item["root"])
        names = roots.get(item["root"], [])
        preferred = settings.active if settings.active in names else (names[0] if names else "")
        items.append({**item, "profile": preferred, "profiles": names, "active": settings.active in names})
    return items


class Recent:
    """Recently opened, created or cloned projects in the state directory."""

    def __init__(self, state: Path):
        self.path = Path(state) / "projects.json"

    def load(self) -> list[dict]:
        try:
            items = json.loads(self.path.read_text())
            return [i for i in items if isinstance(i, dict) and "root" in i][:30]
        except (OSError, ValueError):
            return []

    def add(self, root, profile: str = "", how: str = "opened") -> None:
        items = [i for i in self.load() if i["root"] != str(root)]
        items.insert(0, {"root": str(root), "profile": profile, "how": how, "when": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(items[:30], indent=2))
