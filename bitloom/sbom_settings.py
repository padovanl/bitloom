"""SBOM, vulnerability and traceability settings with explanations, applied as one
managed block: local.conf for host/container profiles, a kas overlay for kas
profiles. Variable names follow the Yocto reference manual glossary; options
whose first release is not confirmed are marked for runtime verification."""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

from .models import Profile, read_assignments
from .versions import describe, support

BEGIN = "# >>> bitloom sbom settings (managed: edit in Bitloom or remove the block) >>>"
END = "# <<< bitloom sbom settings <<<"
OVERLAY = "bitloom-sbom.yml"


@dataclass(frozen=True)
class Option:
    id: str
    title: str
    kind: str                     # inherit | flag | choice | text | fragment
    name: str                     # class, variable or fragment
    info: str
    cra: str = ""
    choices: tuple[str, ...] = ()
    default: str = ""
    since: str = ""
    until: str = ""
    verified: bool = True         # False: first release not confirmed; verify with bitbake-getvar
    lines: tuple[str, ...] = field(default=())  # extra fixed lines when enabled


OPTIONS = [
    Option("create-spdx", "Generate SPDX SBOMs", "inherit", "create-spdx",
           "Writes IMAGE-MACHINE.spdx.json next to every image and per-recipe documents in tmp/deploy/spdx. "
           "Poky enables it by default; other distros may not. SPDX 3.0 is the default format from 5.1 and the only one in 6.0 Wrynose.",
           "CRA Annex I asks manufacturers to identify and document components, including a machine-readable SBOM of at least top-level dependencies.",
           since="kirkstone"),
    Option("supplier", "Package supplier (SPDX_PACKAGE_SUPPLIER)", "text", "SPDX_PACKAGE_SUPPLIER",
           "Organisation recorded as suppliedBy for every package. Sets SPDX_PACKAGE_SUPPLIER_name and _type = \"organization\". "
           "Recipes can override it with SPDX_PACKAGE_SUPPLIER:pn-<recipe>.",
           "Identifies the manufacturer in the SBOM; scanners and authorities see who supplies each component.",
           since="styhead", verified=False),
    Option("image-supplier", "Image supplier (SPDX_IMAGE_SUPPLIER)", "text", "SPDX_IMAGE_SUPPLIER",
           "Organisation recorded as suppliedBy on the root elements of the image SBOM (_name, _type = \"organization\").",
           "The product-level SBOM names the manufacturer placing it on the market.", since="styhead", verified=False),
    Option("include-vex", "VEX data in SBOMs (SPDX_INCLUDE_VEX)", "choice", "SPDX_INCLUDE_VEX",
           "none: no VEX. current (default): vulnerabilities not fixed upstream. all: also historical, fixed ones (large and slow).",
           "VEX states whether a known vulnerability affects the product: the basis for vulnerability handling and user advisories.",
           choices=("none", "current", "all"), default="current", since="styhead", verified=False),
    Option("vex-class", "VEX metadata class", "inherit", "vex",
           "Adds do_generate_vex to every recipe; image builds produce a VEX report of all packages in DEPLOY_DIR_IMAGE for external scanners.",
           "Lets external vulnerability tools assess the product without rebuilding it.", verified=False),
    Option("sbom-cve-check", "sbom-cve-check on image builds", "fragment", "core/yocto/sbom-cve-check",
           "Post-build CVE analysis of the image's SPDX 3 SBOM (Bootlin sbom-cve-check). Enabled with "
           "bitbake-config-build enable-fragment; reports in DEPLOY_DIR_IMAGE according to SBOM_CVE_CHECK_EXPORT_VARS.",
           "Continuous identification of known vulnerabilities in shipped components.", since="wrynose"),
    Option("sbom-cve-warnings", "Warn on unpatched CVEs", "flag", "SBOM_CVE_CHECK_SHOW_WARNINGS",
           "Shows a build warning for each CVE with the Unpatched status found by sbom-cve-check.",
           "Surfaces actionable vulnerabilities during development instead of after release.", since="wrynose"),
    Option("cve-check", "cve-check class (pre-Wrynose)", "inherit", "cve-check",
           "Classic per-recipe CVE checking against the NVD database; summary in tmp/log/cve. Removed in 6.0 Wrynose, replaced by sbom-cve-check.",
           "Continuous identification of known vulnerabilities on releases before 6.0.", until="whinlatter"),
    Option("include-sources", "Describe source files (SPDX_INCLUDE_SOURCES)", "flag", "SPDX_INCLUDE_SOURCES",
           "Adds every source file used in the build to the SPDX output. Much larger SBOMs; useful for licence audits.",
           "Deeper component evidence when customers or auditors require file-level provenance.", since="kirkstone"),
    Option("compiled-sources", "Only compiled sources (SPDX_INCLUDE_COMPILED_SOURCES)", "flag", "SPDX_INCLUDE_COMPILED_SOURCES",
           "Like SPDX_INCLUDE_SOURCES but limited to files compiled into delivered packages, using debug-source information.",
           "File-level provenance focused on what is actually shipped.", verified=False),
    Option("kernel-config", "Kernel configuration in SBOM", "flag", "SPDX_INCLUDE_KERNEL_CONFIG",
           "Exports the Linux kernel .config as a separate Build object (SPDX 3.0 only).",
           "Documents which kernel features (attack surface) are enabled.", since="styhead", verified=False),
    Option("packageconfig", "PACKAGECONFIG in SBOM", "flag", "SPDX_INCLUDE_PACKAGECONFIG",
           "Exports PACKAGECONFIG features and their enabled/disabled state (SPDX 3.0 only).",
           "Shows the configuration of each component, which decides whether a CVE applies.", since="styhead", verified=False),
    Option("pretty", "Readable SBOM JSON (SPDX_PRETTY)", "flag", "SPDX_PRETTY",
           "Indented, multi-line SPDX JSON. Easier to review and diff, larger on disk.", since="kirkstone"),
    Option("buildhistory", "Build history with Git commits", "inherit", "buildhistory",
           "Records image, package and SDK contents per build and commits them (BUILDHISTORY_COMMIT = \"1\"), so every change is diffable.",
           "Traceability of what changed between released versions.", since="kirkstone", lines=('BUILDHISTORY_COMMIT = "1"',)),
]
BY_ID = {option.id: option for option in OPTIONS}


def availability(option: Option, series: str | None) -> tuple[bool | None, str]:
    ok, reason = support(series, option.since, option.until)
    if ok is not False and not option.verified:
        note = f"first release not confirmed; verify on {describe(series)} with bitbake-getvar {option.name}" if option.kind != "inherit" \
            else f"first release not confirmed; the class must exist in {describe(series)}"
        return (None if ok is None else ok), (reason + "; " if reason else "") + note
    return ok, reason


def target(profile: Profile) -> Path:
    """Where the managed block lives for this profile's runtime."""
    if profile.mode in {"kas", "kas-container", "wrapper"}:
        return profile.root_path / OVERLAY
    return profile.build_path / "conf/local.conf"


def render(values: dict[str, str]) -> list[str]:
    lines = []
    for option in OPTIONS:
        value = values.get(option.id)
        if not value:
            continue
        if option.kind == "fragment":
            # Fragments are enabled by bitbake-config-build; the line records the intent.
            lines.append(f"# fragment: {option.name} (enabled with bitbake-config-build)")
            continue
        if option.kind == "inherit":
            lines.append(f'INHERIT += "{option.name}"')
        elif option.kind == "flag":
            lines.append(f'{option.name} = "1"')
        elif option.kind == "choice":
            lines.append(f'{option.name} = "{value}"')
        elif option.kind == "text":
            safe = value.replace('"', "'").replace("\\", "")
            lines += [f'{option.name}_name = "{safe}"', f'{option.name}_type = "organization"']
        lines += list(option.lines)
    return lines


def parse(lines: list[str]) -> dict[str, str]:
    values = {}
    text = "\n".join(lines)
    for option in OPTIONS:
        if option.kind == "inherit" and re.search(rf'INHERIT\s*\+=\s*"[^"]*\b{re.escape(option.name)}\b', text):
            values[option.id] = "1"
        elif option.kind == "flag" and re.search(rf'^{option.name}\s*=\s*"1"', text, re.M):
            values[option.id] = "1"
        elif option.kind == "choice":
            match = re.search(rf'^{option.name}\s*=\s*"([^"]*)"', text, re.M)
            if match:
                values[option.id] = match[1]
        elif option.kind == "text":
            match = re.search(rf'^{option.name}_name\s*=\s*"([^"]*)"', text, re.M)
            if match:
                values[option.id] = match[1]
        elif option.kind == "fragment" and f"# fragment: {option.name}" in text:
            values[option.id] = "1"
    return values


def block(text: str) -> list[str]:
    if BEGIN not in text:
        return []
    inner = text.split(BEGIN, 1)[1].split(END, 1)[0]
    return [line.strip() for line in inner.splitlines() if line.strip() and (line.strip().startswith("# fragment:") or not line.strip().startswith(("#", "bitloom-sbom:", "local_conf_header", "header", "version")))]


def current(profile: Profile) -> tuple[dict[str, str], dict[str, str]]:
    """(managed values, values found elsewhere in local.conf as literals)."""
    path = target(profile)
    managed = parse(block(path.read_text(errors="replace"))) if path.exists() else {}
    elsewhere = {}
    local = profile.build_path / "conf/local.conf"
    if local.exists():
        text = local.read_text(errors="replace")
        outside = text.split(BEGIN, 1)[0] + (text.split(END, 1)[1] if END in text else "")
        elsewhere = {k: v for k, v in parse(outside.splitlines()).items() if k not in managed}
    return managed, elsewhere


def preview(profile: Profile, values: dict[str, str]) -> str:
    lines = render(values)
    if profile.mode in {"kas", "kas-container", "wrapper"}:
        body = "\n".join("    " + line for line in lines) or "    # no managed settings"
        return f"header:\n  version: 14\n{BEGIN}\nlocal_conf_header:\n  bitloom-sbom: |\n{body}\n{END}\n"
    return "\n".join([BEGIN, *lines, END]) + "\n"


def apply(profile: Profile, values: dict[str, str]) -> tuple[Path, Path | None]:
    """Write the managed block with a timestamped backup; returns (file, backup)."""
    path = target(profile)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = None
    if profile.mode in {"kas", "kas-container", "wrapper"}:
        text = preview(profile, values)
        if path.exists():
            backup = path.with_name(path.name + ".bak-" + stamp)
            backup.write_text(path.read_text())
    else:
        if not path.exists():
            raise ValueError(f"{path} does not exist yet: initialise the build directory first")
        original = path.read_text(errors="replace")
        backup = path.with_name(path.name + ".bak-" + stamp)
        backup.write_text(original)
        managed = preview(profile, values)
        if BEGIN in original and END in original:
            head, rest = original.split(BEGIN, 1)
            text = head + managed.rstrip("\n") + rest.split(END, 1)[1]
        else:
            text = original.rstrip("\n") + "\n\n" + managed
    temporary = path.with_name(path.name + ".bitloom-tmp")
    temporary.write_text(text)
    if path.exists():
        temporary.chmod(path.stat().st_mode)
    temporary.replace(path)
    return path, backup


def kas_files_with_overlay(profile: Profile) -> str | None:
    """kas_file value including the overlay, or None when already included."""
    files = profile.kas_file.split(":")
    return None if OVERLAY in files else ":".join([*files, OVERLAY])


def info_markdown(option: Option, series: str | None, state: str) -> str:
    ok, reason = availability(option, series)
    badge = {True: "✔ available", False: "✖ not available", None: "? check"}[ok]
    lines = [f"## {option.title}", "", f"`{option.name}` · {option.kind} · **{badge}** in {describe(series)}" + (f" — {reason}" if reason else ""), "",
             option.info, ""]
    if option.cra:
        lines += [f"**CRA relevance:** {option.cra}", ""]
    if option.choices:
        lines += ["Values: " + " · ".join(f"`{c}`" for c in option.choices), ""]
    lines += [f"Current: **{state}**"]
    return "\n".join(lines)
