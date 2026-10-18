"""What the project's Yocto release can do, in one place.

Each capability names the release where it appeared or disappeared, and, when the project can be inspected,
the evidence that decides it for this very project: a class in its layers (vex.bbclass, sbom-cve-check.bbclass),
a tool in its own BitBake (bitbake-setup, bitbake-config-build) or the kind of workspace. Evidence wins over
the release number: a backport is found, a missing class is not offered. Operations, SBOM settings, the CRA
checks and Studio all ask here, so a feature is never offered where the release does not have it, and the
answer always says why and what to use instead.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from .versions import describe, support


@dataclass(frozen=True)
class Capability:
    name: str
    title: str
    since: str = ""          # first release with it (fallback when the project cannot be inspected)
    until: str = ""          # last release with it
    bbclass: str = ""        # a class that must exist in the project's layers
    tool: str = ""           # a tool that must exist in the project's BitBake (bin/)
    workspace: str = ""      # "bitbake-setup": a workspace made by bitbake-setup init
    instead: str = ""        # capability to use where this one is missing
    note: str = ""


CAPABILITIES = {c.name: c for c in [
    Capability("spdx2", "SPDX 2.2 SBOMs (create-spdx-2.2)", until="whinlatter", bbclass="create-spdx-2.2", instead="spdx3"),
    Capability("spdx3", "SPDX 3.0 SBOMs (create-spdx-3.0)", since="styhead", bbclass="create-spdx-3.0", instead="spdx2"),
    Capability("spdx-supplier-3", "SBOM supplier variables SPDX_PACKAGE_SUPPLIER / SPDX_IMAGE_SUPPLIER", since="styhead", bbclass="create-spdx-3.0"),
    Capability("cve-check", "cve-check class", until="whinlatter", bbclass="cve-check", instead="sbom-cve-check"),
    Capability("sbom-cve-check", "sbom-cve-check on image SBOMs", since="wrynose", bbclass="sbom-cve-check", instead="cve-check"),
    Capability("sbom-cve-check-recipe", "sbom-cve-check for one recipe", since="wrynose", bbclass="sbom-cve-check-recipe", instead="cve-check"),
    Capability("recipe-sbom", "Recipe SBOM task (do_create_recipe_sbom)", since="wrynose", bbclass="sbom-cve-check-recipe"),
    Capability("vex", "VEX metadata class", since="styhead", bbclass="vex"),
    Capability("fragments", "Configuration fragments (bitbake-config-build)", since="walnascar", tool="bitbake-config-build"),
    Capability("bitbake-setup", "bitbake-setup workspaces", tool="bitbake-setup", workspace="bitbake-setup"),
    Capability("unpackdir", "Sources unpacked in UNPACKDIR", since="styhead", note="before 5.1 recipes read files from WORKDIR"),
    Capability("image-access-split", "allow-empty-password, empty-root-password, allow-root-login", since="styhead",
               note="before 5.1 a single debug-tweaks feature"),
    Capability("debug-tweaks", "debug-tweaks image feature", until="scarthgap", instead="image-access-split"),
    Capability("systemd-default", "systemd as the default init manager", since="wrynose"),
]}

_classes_cache: dict[str, tuple[float, set[str]]] = {}
SKIP = {".git", "build", "tmp", "downloads", "sstate-cache", "cache", "__pycache__", "node_modules", ".bitloom"}


def _roots(profile) -> list[Path]:
    if profile is None:
        return []
    roots = [profile.root_path]
    environment = getattr(profile, "environment", None) or {}
    if environment.get("KAS_WORK_DIR"):
        roots.append(Path(environment["KAS_WORK_DIR"]).expanduser())
    return [r for r in roots if r.is_dir()]


def project_classes(profile) -> set[str]:
    """Names of the BitBake classes in the project's layers (empty when the layers are not visible here)."""
    found: set[str] = set()
    for root in _roots(profile):
        key = str(root)
        cached = _classes_cache.get(key)
        if cached and time.monotonic() - cached[0] < 60:
            found |= cached[1]
            continue
        names: set[str] = set()
        base_depth = len(root.parts)
        for directory, dirs, files in os.walk(root):
            depth = len(Path(directory).parts) - base_depth
            dirs[:] = [d for d in dirs if d not in SKIP and depth < 6]
            if Path(directory).name in {"classes", "classes-global", "classes-recipe"}:
                names.update(f[:-len(".bbclass")] for f in files if f.endswith(".bbclass"))
        _classes_cache[key] = (time.monotonic(), names)
        found |= names
    return found


def bitbake_bin(profile) -> Path | None:
    """bin/ of the project's own BitBake checkout: bitbake-setup workspaces, kas work directories, Poky and split checkouts."""
    for root in _roots(profile):
        for sub in ("layers/bitbake", "bitbake", "poky/bitbake", "sources/bitbake", "sources/poky/bitbake"):
            if (root / sub / "bin/bitbake").is_file():
                return root / sub / "bin"
    return None


def setup_workspace(profile) -> bool:
    """A workspace made by bitbake-setup init: build/init-build-env next to config/ and layers/."""
    root = profile.root_path if profile is not None else None
    return bool(root and (root / "build/init-build-env").is_file() and (root / "config").is_dir() and (root / "layers").is_dir())


def check(name: str, series: str | None, profile=None) -> tuple[bool | None, str]:
    """(True | False | None when it cannot be known here, reason). Evidence from the project decides first."""
    cap = CAPABILITIES[name]
    release = describe(series) if series else "release unknown"
    if cap.tool:
        bin_dir = bitbake_bin(profile)
        if bin_dir is not None:
            if not (bin_dir / cap.tool).is_file():
                return False, _missing(cap, f"{cap.tool} is not in this project's BitBake ({release})")
            if cap.workspace == "bitbake-setup" and not setup_workspace(profile):
                return False, "this project was not set up with bitbake-setup (it uses kas or oe-init-build-env), so there is nothing for bitbake-setup to manage"
            return True, ""
        if not cap.since and not cap.until:
            return None, "the project's BitBake checkout was not found here; availability unknown"
    if cap.bbclass:
        classes = project_classes(profile)
        if classes:
            if cap.bbclass in classes:
                return True, ""
            return False, _missing(cap, f"{cap.bbclass}.bbclass is not in this project's layers ({release})")
    ok, reason = support(series, cap.since, cap.until)
    if ok is False:
        return False, _missing(cap, reason)
    return ok, reason


def _missing(cap: Capability, why: str) -> str:
    alternative = CAPABILITIES.get(cap.instead)
    return why + (f"; use {alternative.title} instead" if alternative else "")


def has(name: str, series: str | None, profile=None) -> bool:
    """True only when the capability is known to be there."""
    return check(name, series, profile)[0] is True


def check_all(names, series: str | None, profile=None) -> tuple[bool | None, str]:
    """All of them: the first missing one decides; unknown when none is missing but one cannot be known."""
    unknown = None
    for name in names:
        ok, reason = check(name, series, profile)
        if ok is False:
            return False, reason
        if ok is None and unknown is None:
            unknown = reason
    return (None, unknown) if unknown is not None else (True, "")


def matrix(series: str | None, profile=None) -> list[dict]:
    """Every capability for this project, for the documentation, the Health view and the tests."""
    rows = []
    for cap in CAPABILITIES.values():
        ok, reason = check(cap.name, series, profile)
        rows.append({"name": cap.name, "title": cap.title, "available": ok, "reason": reason, "note": cap.note})
    return rows
