"""Create a project with bitbake-setup (BitBake 2.16+, Yocto 5.3 Whinlatter and later), as a job.

Run as `python -m bitloom.bbsetup --top DIR --config ID --name NAME --choice distro/poky --choice machine/qemux86-64`.
When bitbake-setup is not on the PATH, BitBake is fetched once at the release's pinned tag into a cache folder;
then `bitbake-setup init --non-interactive` creates the setup in DIR/NAME. The choices are those of the official
configuration templates, so the result is the same as following the Yocto Quick Build with bitbake-setup."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Official templates in BitBake's default registry, and what they let you choose.
TEMPLATES = {
    "wrynose": {"config": "poky-wrynose", "bitbake_tag": "yocto-6.0.2", "configurations": ("poky", "poky-with-sstate"),
                "machines": ("qemux86-64", "qemuarm64", "qemuriscv64", "genericarm64", "genericx86-64"),
                "distros": ("poky", "poky-altcfg", "poky-tiny")},
}
BITBAKE_URL = "https://git.openembedded.org/bitbake"
# The kas build image: Yocto's host packages, the en_US.UTF-8 locale and Python, maintained upstream.
IMAGE = "ghcr.io/siemens/kas/kas:4.8.1"


def cache_dir() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "bitloom"


def tool(tag: str, container: bool = False) -> list[str]:
    """The bitbake-setup to run: the one on the PATH (host only), or BitBake's own at the pinned tag (fetched once)."""
    found = shutil.which("bitbake-setup")
    if found and not container:
        return [found]
    checkout = cache_dir() / f"bitbake-{tag}"
    script = checkout / "bin/bitbake-setup"
    if not script.is_file():
        checkout.parent.mkdir(parents=True, exist_ok=True)
        print(f"NOTE: fetching BitBake {tag} for bitbake-setup into {checkout}", flush=True)
        subprocess.run(["git", "clone", "--depth", "1", "--branch", tag, "--", BITBAKE_URL, str(checkout)], check=True)
    return ["python3" if container else sys.executable, str(script)]


def host_problems() -> list[str]:
    """What stops BitBake on this host before it starts (the container has all of it)."""
    problems = []
    try:
        locales = subprocess.run(["locale", "-a"], capture_output=True, text=True, timeout=10).stdout.lower().replace("-", "")
    except (OSError, subprocess.SubprocessError):
        locales = ""
    if "en_us.utf8" not in locales:
        problems.append("the en_US.UTF-8 locale is missing (sudo locale-gen en_US.UTF-8, or on Debian/Ubuntu: sudo dpkg-reconfigure locales)")
    for name in ("git", "python3", "gcc", "make", "chrpath", "diffstat", "lz4c", "zstd"):
        if not shutil.which(name):
            problems.append(f"{name} is not installed")
    return problems


def container_prefix(engine: str, image: str, top: Path) -> list[str]:
    """Run inside the build image with the project at the same path, so the absolute paths bitbake-setup writes stay valid."""
    cache = cache_dir()
    prefix = [engine, "run", "--rm", "-i", "--init", "-v", f"{top}:{top}", "-v", f"{cache}:{cache}", "-w", str(top), "-e", "HOME=/tmp"]
    if hasattr(os, "getuid"):
        prefix += ["--user", f"{os.getuid()}:{os.getgid()}"]
    return prefix + ["--entrypoint", "", image]


def argv(top: Path, config: str, name: str, configuration: str, choices: list[str], command: list[str]) -> list[str]:
    return [*command, "--setting", "default", "top-dir-prefix", str(top.parent), "--setting", "default", "top-dir-name", top.name,
            "init", "--non-interactive", "--no-init-vscode", "--setup-dir-name", name, config, configuration, *choices]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", required=True, type=Path)
    parser.add_argument("--release", required=True, choices=sorted(TEMPLATES))
    parser.add_argument("--name", required=True)
    parser.add_argument("--configuration", default="poky")
    parser.add_argument("--choice", action="append", default=[])
    parser.add_argument("--engine", choices=["docker", "podman"], help="run bitbake-setup in a container (with --image)")
    parser.add_argument("--image", default=IMAGE)
    args = parser.parse_args()
    spec = TEMPLATES[args.release]
    args.top.mkdir(parents=True, exist_ok=True)
    if not args.engine:
        problems = host_problems()
        if problems:
            print("ERROR: this host cannot run BitBake yet: " + "; ".join(problems) + ".", flush=True)
            print("ERROR: install the Yocto host packages (docs.yoctoproject.org → Required Packages for the Build Host), or create the project with the container runtime.", flush=True)
            return 1
    command = tool(spec["bitbake_tag"], container=bool(args.engine))
    if args.engine:
        command = container_prefix(args.engine, args.image, args.top) + command
    command = argv(args.top, spec["config"], args.name, args.configuration, args.choice, command)
    print("NOTE: " + " ".join(command), flush=True)
    result = subprocess.run(command, cwd=args.top)
    if result.returncode == 0:
        print(f"NOTE: setup ready in {args.top / args.name}: source build/init-build-env there, or let Bitloom set up the profile.", flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
