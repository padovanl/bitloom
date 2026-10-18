"""Guided migration between Yocto releases, built from the official migration guides.

Every release step (5.0 -> 5.1, 5.1 -> 5.2, ...) is a list of rules taken from that release's migration guide
(docs.yoctoproject.org/migration-guides/migration-X.Y.html). A migration from one LTS to the next chains the
steps in between, so Scarthgap -> Wrynose runs the 5.1, 5.2, 5.3 and 6.0 rules; a future release only adds
a step.

Rules look only at what you own: your layers, the build configuration and the kas files of the project.
Upstream layers are replaced by the new release, not migrated. Each finding says where, why (with the
guide's section) and what to do; when the change is mechanical and safe, it carries a line fix that can be
previewed as a diff and applied with a backup. Moving the checkout itself (the kas repositories) is written to
a new kas file, never over the current one, so the old build keeps working while the new one is tried.
"""
from __future__ import annotations

import difflib
import json
import re
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .models import Profile
from .versions import INFO, ORDER

GUIDES = "https://docs.yoctoproject.org/migration-guides"
SEVERITIES = {"breaks": "Breaks the build", "review": "Changes behaviour: review", "info": "Good to know"}


@dataclass
class Fix:
    path: str
    line: int                 # 1-based
    old: str                  # the whole line as it is now (checked again before applying)
    new: str | None           # None removes the line


@dataclass
class Finding:
    rule: str
    step: str                 # the release the rule comes from (styhead, walnascar...)
    severity: str
    title: str
    where: str                # path:line, or a path
    detail: str
    advice: str
    guide: str
    fixes: list[Fix] = field(default_factory=list)


@dataclass
class Rule:
    id: str
    step: str
    severity: str
    title: str
    anchor: str
    advice: str
    check: object = None      # function(ctx, rule) -> list[Finding]


# --- what is scanned ---------------------------------------------------------------------------------------

SOURCE_SUFFIXES = (".bb", ".bbappend", ".bbclass", ".inc", ".conf")


class Context:
    """Your files, read once: layers' metadata, build configuration, kas files (local_conf_header included)."""

    def __init__(self, profile: Profile, layers: list[Path], kas_files: list[Path]):
        self.profile = profile
        self.layers = layers
        self.kas_files = kas_files
        self.files: dict[Path, list[str]] = {}
        for layer in layers:
            for path in sorted(layer.rglob("*")):
                if path.suffix in SOURCE_SUFFIXES and path.is_file() and ".git" not in path.parts and path.stat().st_size < 1024 * 1024:
                    self.files[path] = path.read_text(errors="replace").splitlines()
        build = profile.build_path / "conf"
        # With kas, local.conf and bblayers.conf are generated from the kas files (scanned below): only what kas leaves alone.
        generated = ("local.conf", "bblayers.conf") if profile.mode in ("kas", "kas-container", "wrapper") and kas_files else ()
        for name in ("local.conf", "auto.conf", "site.conf", "bblayers.conf"):
            if name in generated:
                continue
            if (build / name).is_file():
                self.files[build / name] = (build / name).read_text(errors="replace").splitlines()
        for path in kas_files:
            self.files[path] = path.read_text(errors="replace").splitlines()

    def rel(self, path: Path) -> str:
        for base in [self.profile.root_path, *[layer.parent for layer in self.layers]]:
            try:
                return str(path.relative_to(base))
            except ValueError:
                continue
        return str(path)

    def logical(self, kinds=SOURCE_SUFFIXES + (".yml", ".yaml")):
        """(path, first line number, joined text, [line numbers]) for each logical line (backslash continuations joined)."""
        for path, lines in self.files.items():
            if path.suffix not in kinds:
                continue
            number, buffer, numbers = 0, [], []
            for index, line in enumerate(lines, 1):
                if not buffer:
                    number = index
                numbers.append(index)
                if line.rstrip().endswith("\\"):
                    buffer.append(line.rstrip()[:-1])
                    continue
                buffer.append(line)
                yield path, number, " ".join(part.strip() if i else part for i, part in enumerate(buffer)), numbers
                buffer, numbers = [], []

    def assignments(self, names=None):
        """(path, line, variable, overrides, operator, value) for assignments, kas local_conf_header included."""
        pattern = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][\w\-${}/.+]*?)((?::[\w\-${}.+]+)*)(\[[\w\-.]+\])?\s*(\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)\s*(["\'])(.*)\5\s*(?:#.*)?$')
        for path, number, text, _ in self.logical():
            m = pattern.match(text)
            if m and (names is None or m[1] in names):
                yield path, number, m[1], m[2] + (m[3] or ""), m[4], m[6]


def _where(ctx, path, line=None):
    return f"{ctx.rel(path)}:{line}" if line else ctx.rel(path)


def _finding(ctx, rule, path, line, detail, fixes=None, advice=None):
    return Finding(rule.id, rule.step, rule.severity, rule.title, _where(ctx, path, line), detail, advice or rule.advice,
                   f"{GUIDES}/migration-{INFO[rule.step][0]}.html{rule.anchor}", fixes or [])


def _line_fix(ctx, path, number, transform):
    """A fix for one physical line, or None when the transformation changes nothing."""
    old = ctx.files[path][number - 1]
    new = transform(old)
    return Fix(str(path), number, old, new) if new != old else None


# --- rule helpers ------------------------------------------------------------------------------------------

def _removed_variables(names: dict):
    def check(ctx, rule):
        found = []
        for path, line, var, _, _, _ in ctx.assignments(set(names)):
            found.append(_finding(ctx, rule, path, line, f"{var} was removed", advice=names[var]))
        return found
    return check


DEPENDENCY_VARS = re.compile(r"^(DEPENDS|RDEPENDS|RRECOMMENDS|RSUGGESTS|IMAGE_INSTALL|PACKAGE_INSTALL|CORE_IMAGE_EXTRA_INSTALL|"
                             r"TOOLCHAIN_TARGET_TASK|TOOLCHAIN_HOST_TASK|PACKAGECONFIG_CONFARGS|PREFERRED_PROVIDER\S*)$")


def _removed_recipes(recipes: dict):
    """recipes: name -> (replacement or "", advice). Finds them in dependencies and in your appends."""
    def check(ctx, rule):
        found = []
        for path, line, var, _, _, value in ctx.assignments():
            if not DEPENDENCY_VARS.match(var):
                continue
            for word in value.split():
                base = re.sub(r"-(native|nativesdk)$", "", word.removeprefix("nativesdk-"))
                if base in recipes:
                    replacement, advice = recipes[base]
                    fix = _line_fix(ctx, path, line, lambda text, w=word, b=base, r=replacement: re.sub(rf"(?<![\w-]){re.escape(w)}(?![\w-])", w.replace(b, r), text)) if replacement else None
                    found.append(_finding(ctx, rule, path, line, f"{var} uses {word}, removed from OE-Core", [fix] if fix else [], advice))
        for path in ctx.files:
            if path.suffix == ".bbappend":
                name = path.name.split("_")[0].removesuffix(".bbappend")
                if name in recipes:
                    found.append(_finding(ctx, rule, path, None, f"an append to {name}, which no longer exists in OE-Core", advice=recipes[name][1]))
        return found
    return check


def _removed_classes(classes: dict):
    def check(ctx, rule):
        found = []
        for path, number, text, _ in ctx.logical():
            m = re.match(r'^\s*(?:inherit|inherit_defer)\s+(.*)$', text) or re.match(r'^\s*(?:INHERIT|IMAGE_CLASSES|KERNEL_CLASSES)\s*\+?=\s*"([^"]*)"', text)
            if m:
                for name in m[1].split():
                    if name in classes:
                        found.append(_finding(ctx, rule, path, number, f"uses the {name} class, removed in {rule.step}", advice=classes[name]))
        return found
    return check


def _removed_packageconfig(options: dict):
    """options: recipe -> {option: advice}. Looks at PACKAGECONFIG in appends of that recipe and PACKAGECONFIG:pn-<recipe>."""
    def check(ctx, rule):
        found = []
        for path, line, var, overrides, _, value in ctx.assignments({"PACKAGECONFIG"}):
            recipe = re.search(r":pn-([\w\-+.]+)", overrides)
            recipe = recipe[1] if recipe else path.name.split("_")[0].removesuffix(".bbappend") if path.suffix == ".bbappend" else ""
            for option, advice in options.get(recipe, {}).items():
                if option in value.split():
                    found.append(_finding(ctx, rule, path, line, f"{recipe} no longer has the PACKAGECONFIG option {option}", advice=advice))
        return found
    return check


def _feature_words(var_names, words: dict):
    def check(ctx, rule):
        found = []
        for path, line, var, _, _, value in ctx.assignments(set(var_names)):
            for word in value.split():
                if word in words:
                    replacement = words[word]
                    fix = _line_fix(ctx, path, line, lambda text, w=word, r=replacement: re.sub(rf"(?<![\w-]){re.escape(w)}(?![\w-])", r, text)) if replacement is not None else None
                    found.append(_finding(ctx, rule, path, line, f"{var} contains {word}", [fix] if fix else []))
        return found
    return check


# --- the rules, per release step (from the official migration guides) ---------------------------------------

def check_layerseries(ctx, rule):
    found = []
    target = ctx.target
    for layer in ctx.layers:
        conf = layer / "conf/layer.conf"
        if conf not in ctx.files:
            continue
        for number, text in enumerate(ctx.files[conf], 1):
            m = re.match(r'^(\s*LAYERSERIES_COMPAT[_:][\w\-]+\s*\??=\s*)"([^"]*)"(.*)$', text)
            if m and target not in m[2].split():
                fix = Fix(str(conf), number, text, f'{m[1]}"{target}"{m[3]}')
                found.append(_finding(ctx, rule, conf, number, f"{layer.name} declares “{m[2]}”; the target release is {target}", [fix],
                                      f'Set it to "{target}" once the layer is migrated (keep both names only if one branch really serves both releases).'))
    return found


def check_s_workdir(ctx, rule):
    found = []
    for path, line, var, overrides, op, value in ctx.assignments({"S"}):
        if value in ("${WORKDIR}", "${WORKDIR}/"):
            fix = _line_fix(ctx, path, line, lambda t: t.replace("${WORKDIR}", "${UNPACKDIR}", 1))
            found.append(_finding(ctx, rule, path, line, 'S = "${WORKDIR}" is refused from 5.1', [fix] if fix else []))
    return found


def check_workdir_files(ctx, rule):
    """${WORKDIR}/<file> where the file comes from SRC_URI (file://): it now unpacks into UNPACKDIR."""
    found = []
    by_file: dict[Path, set] = {}
    for path, line, var, _, _, value in ctx.assignments({"SRC_URI"}):
        names = {Path(re.sub(r";.*", "", u[len("file://"):])).name for u in value.split() if u.startswith("file://")}
        by_file.setdefault(path, set()).update(n for n in names if n)
    for path, lines in ctx.files.items():
        local = by_file.get(path, set())
        if path.suffix == ".bbappend" or not local:
            # an append's files usually come with its own SRC_URI:append
            local = local or set()
        for number, text in enumerate(lines, 1):
            for m in re.finditer(r"\$\{WORKDIR\}/([\w.\-+]+)", text):
                if m[1] in local:
                    fix = _line_fix(ctx, path, number, lambda t, n=m[1]: t.replace("${WORKDIR}/" + n, "${UNPACKDIR}/" + n))
                    found.append(_finding(ctx, rule, path, number, f"${{WORKDIR}}/{m[1]} is a file from SRC_URI: it is in ${{UNPACKDIR}} now", [fix] if fix else []))
    return found


def check_s_workdir_sub(ctx, rule):
    found = []
    for path, line, var, overrides, op, value in ctx.assignments({"S"}):
        if value in ("${WORKDIR}/git", "${UNPACKDIR}/git"):
            found.append(_finding(ctx, rule, path, line, f'S = "{value}": the Git fetcher unpacks into ${{BP}} now, which is S\'s default',
                                  [Fix(str(path), line, ctx.files[path][line - 1], None)], "Remove the line (S defaults to the checkout)."))
        elif value.startswith("${WORKDIR}/") and value not in ("${WORKDIR}/${BP}",):
            fix = _line_fix(ctx, path, line, lambda t: t.replace("${WORKDIR}/", "${UNPACKDIR}/", 1))
            found.append(_finding(ctx, rule, path, line, f'S = "{value}" is refused from 5.3', [fix] if fix else []))
    return found


def check_git_branch(ctx, rule):
    found = []
    for path, line, var, _, _, value in ctx.assignments({"SRC_URI"}):
        for uri in value.split():
            if uri.startswith(("git://", "gitsm://")) or ";protocol=" in uri and uri.startswith("git"):
                params = dict(p.split("=", 1) for p in uri.split(";")[1:] if "=" in p)
                if "branch" not in params and params.get("nobranch") != "1":
                    found.append(_finding(ctx, rule, path, line, f"{uri.split(';')[0]} has no branch= (an error from 5.2)",
                                          advice="Add ;branch=<the branch that contains SRCREV>, or ;nobranch=1 for a commit on no branch."))
                if "," in params.get("branch", ""):
                    found.append(_finding(ctx, rule, path, line, "one Git URL with several branches (branch=a,b) is no longer supported",
                                          advice="Split it into one SRC_URI entry per branch, each with its own name= and SRCREV_<name>."))
    return found


VIRTUAL_RENAMES = [
    (r"virtual/\$\{(?:HOST|TARGET)_PREFIX\}binutils", "virtual/cross-binutils"), (r"virtual/\$\{(?:HOST|TARGET)_PREFIX\}gcc", "virtual/cross-cc"),
    (r"virtual/\$\{SDK_PREFIX\}gcc", "virtual/nativesdk-cross-cc"), (r"virtual/nativesdk-\$\{SDK_PREFIX\}compilerlibs", "virtual/nativesdk-compilerlibs"),
    (r"virtual/\$\{(?:HOST|TARGET)_PREFIX\}compilerlibs", "virtual/compilerlibs"), (r"virtual/\$\{TARGET_PREFIX\}g\+\+", "virtual/cross-c++"),
]


def check_virtual(ctx, rule):
    found = []
    for path, lines in ctx.files.items():
        for number, text in enumerate(lines, 1):
            new = text
            for pattern, replacement in VIRTUAL_RENAMES:
                new = re.sub(pattern, replacement, new)
            if new != text:
                found.append(_finding(ctx, rule, path, number, "a toolchain provider with the target prefix", [Fix(str(path), number, text, new)]))
    return found


def check_uboot_entry(ctx, rule):
    found = []
    for path, line, var, _, _, value in ctx.assignments({"UBOOT_ENTRYPOINT", "UBOOT_LOADADDRESS"}):
        if re.fullmatch(r"[0-9a-fA-F]{6,}", value):
            fix = _line_fix(ctx, path, line, lambda t, v=value: t.replace(f'"{v}"', f'"0x{v}"', 1))
            found.append(_finding(ctx, rule, path, line, f"{var} = \"{value}\" without 0x", [fix] if fix else []))
    return found


def check_zstd(ctx, rule):
    found = []
    for path, line, var, _, _, value in ctx.assignments({"ZSTD_COMPRESSION_LEVEL"}):
        if value.startswith("-") and value[1:].isdigit():
            fix = _line_fix(ctx, path, line, lambda t, v=value: t.replace(f'"{v}"', f'"{v[1:]}"', 1))
            found.append(_finding(ctx, rule, path, line, f'ZSTD_COMPRESSION_LEVEL = "{value}" is now a plain number', [fix] if fix else []))
    return found


def check_current_mc(ctx, rule):
    found = []
    for path, lines in ctx.files.items():
        for number, text in enumerate(lines, 1):
            if re.search(r"BB_CURRENT_MC['\"]?\)?\s*(==|!=)\s*['\"]default['\"]", text) or re.search(r"getVar\(['\"]BB_CURRENT_MC['\"]\)\s*(==|!=)\s*['\"]default", text):
                found.append(_finding(ctx, rule, path, number, "compares BB_CURRENT_MC with “default”: it is an empty string now"))
    return found


def check_equals_space(ctx, rule):
    """FOO="bar": a warning from 5.3 (lack of whitespace around the assignment)."""
    found = []
    pattern = re.compile(r'^(\s*(?:export\s+)?[A-Za-z_][\w\-${}:\[\].+]*?)(\s*)(\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)(\s*)(".*)$')
    for path, lines in ctx.files.items():
        if path.suffix not in SOURCE_SUFFIXES:
            continue
        for number, text in enumerate(lines, 1):
            m = pattern.match(text)
            if m and (not m[2] or not m[4]) and not text.lstrip().startswith("#"):
                fix = Fix(str(path), number, text, f"{m[1].rstrip()} {m[3]} {m[5]}")
                found.append(_finding(ctx, rule, path, number, f"no space around “{m[3]}”", [fix]))
    return found


def check_wic_plugins(ctx, rule):
    found = []
    for layer in ctx.layers:
        for plugin in (layer / "scripts/lib/wic/plugins/source").glob("*-*.py"):
            found.append(_finding(ctx, rule, plugin, None, f"a Wic plugin with a dash in its name: {plugin.name}",
                                  advice=f"Rename it to {plugin.name.replace('-', '_')} and use --source {plugin.stem.replace('-', '_')} in your WKS files."))
    return found


def check_fitimage(ctx, rule):
    found = []
    for path, line, var, _, _, value in ctx.assignments({"KERNEL_IMAGETYPE", "KERNEL_IMAGETYPES", "KERNEL_CLASSES"}):
        if "fitImage" in value.split() or "kernel-fitimage" in value.split():
            found.append(_finding(ctx, rule, path, line, f"{var} uses the FIT image from the kernel recipe, moved to a recipe of its own in 5.3"))
    return found


def check_flags_native(ctx, rule):
    found = []
    for path in ctx.files:
        if path.suffix != ".bb" or not any("BBCLASSEXTEND" in l and "native" in l for l in ctx.files[path]):
            continue
        for number, text in enumerate(ctx.files[path], 1):
            if re.match(r'^\s*(CPPFLAGS|CFLAGS|CXXFLAGS|LDFLAGS)\s*\+=', text):
                found.append(_finding(ctx, rule, path, number, "a += on a *FLAGS variable now also applies to the -native build",
                                      advice="Use TARGET_" + text.split()[0] + " if it was meant for the target only."))
    return found


def check_poky_repo(ctx, rule):
    found = []
    for path in ctx.kas_files:
        for number, text in enumerate(ctx.files[path], 1):
            if re.search(r"url:\s*['\"]?https?://git\.yoctoproject\.org/(git/)?poky(\.git)?['\"]?\s*$", text):
                found.append(_finding(ctx, rule, path, number, "the project takes its layers from the poky repository, no longer updated from 5.3",
                                      advice="Use bitbake, openembedded-core and meta-yocto directly: “Write the kas file for the new release” does it for you."))
    return found


def check_backfill(ctx, rule):
    renames = {"DISTRO_FEATURES_BACKFILL_CONSIDERED": "DISTRO_FEATURES_OPTED_OUT", "MACHINE_FEATURES_BACKFILL_CONSIDERED": "MACHINE_FEATURES_OPTED_OUT"}
    review = {"DISTRO_FEATURES_BACKFILL", "MACHINE_FEATURES_BACKFILL", "DISTRO_FEATURES_DEFAULT"}
    found = []
    for path, line, var, _, _, _ in ctx.assignments(set(renames) | review):
        if var in renames:
            fix = _line_fix(ctx, path, line, lambda t, v=var: re.sub(rf"\b{v}\b", renames[v], t, count=1))
            found.append(_finding(ctx, rule, path, line, f"{var} is now {renames[var]}", [fix] if fix else []))
        else:
            found.append(_finding(ctx, rule, path, line, f"{var} is obsolete in 6.0",
                                  advice="Defaults now come from DISTRO_FEATURES_DEFAULTS / MACHINE_FEATURES_DEFAULTS: remove this and list what you do not want in *_OPTED_OUT."))
    return found


def check_templates(ctx, rule):
    found = []
    for path, lines in ctx.files.items():
        for number, text in enumerate(lines, 1):
            if "meta-poky/conf/templates/default" in text:
                found.append(_finding(ctx, rule, path, number, "uses meta-poky/conf/templates/default, removed in 6.0",
                                      advice="Use meta/conf/templates/default from OE-Core, or your own templates in your layer."))
    return found


def check_uboot_config(ctx, rule):
    found = []
    for path, line, var, overrides, _, value in ctx.assignments({"UBOOT_CONFIG"}):
        if overrides.startswith("[") and value.count(",") >= 1:
            found.append(_finding(ctx, rule, path, line, f"UBOOT_CONFIG{overrides} = \"{value}\": the comma form is deprecated and goes in the next release",
                                  advice="Keep only the defconfig in UBOOT_CONFIG[x]; move images and binary to UBOOT_CONFIG_IMAGE_FSTYPES[x] and UBOOT_CONFIG_BINARY[x]."))
    return found


def check_pkgconfig(ctx, rule):
    found = []
    for path, lines in ctx.files.items():
        if path.suffix not in (".bb", ".bbappend", ".inc"):
            continue
        text = "\n".join(lines)
        if re.search(r"\bPKG_CONFIG_(PATH|SYSROOT_DIR|LIBDIR)\b", text) and not re.search(r"^\s*inherit\b.*\bpkgconfig\b", text, re.M):
            number = next(i for i, l in enumerate(lines, 1) if re.search(r"\bPKG_CONFIG_", l))
            found.append(_finding(ctx, rule, path, number, "uses PKG_CONFIG_* without inherit pkgconfig: they are no longer exported by default"))
    return found


def check_spdx22(ctx, rule):
    found = []
    for path, number, text, _ in ctx.logical():
        if re.search(r"\bcreate-spdx-2\.2\b", text):
            fix = _line_fix(ctx, path, number, lambda t: t.replace("create-spdx-2.2", "create-spdx"))
            found.append(_finding(ctx, rule, path, number, "inherits create-spdx-2.2, removed in 6.0", [fix] if fix else []))
    return found


def check_cve_check(ctx, rule):
    found = []
    for path, line, var, overrides, op, value in ctx.assignments({"INHERIT"}):
        if "cve-check" in value.split():
            words = [w for w in value.split() if w != "cve-check"]
            old = ctx.files[path][line - 1]
            if words:
                new = old.replace(value, " ".join(words), 1)
                fixes = [Fix(str(path), line, old, new)]
            else:
                fixes = [Fix(str(path), line, old, None)]
            indent = re.match(r"^\s*", old)[0]
            fixes.append(Fix(str(path), line, "", f'{indent}OE_FRAGMENTS += "core/yocto/sbom-cve-check"'))   # inserted after
            found.append(_finding(ctx, rule, path, line, "the cve-check class was removed in 6.0", fixes,
                                  'Replace it with OE_FRAGMENTS += "core/yocto/sbom-cve-check" (sbom-cve-check with the recommended settings).'))
    for path, line, var, _, _, _ in ctx.assignments({"CVE_CHECK_SHOW_WARNINGS"}):
        fix = _line_fix(ctx, path, line, lambda t: t.replace("CVE_CHECK_SHOW_WARNINGS", "SBOM_CVE_CHECK_SHOW_WARNINGS", 1))
        found.append(_finding(ctx, rule, path, line, "CVE_CHECK_SHOW_WARNINGS is now SBOM_CVE_CHECK_SHOW_WARNINGS", [fix] if fix else []))
    for path, line, var, _, _, _ in ctx.assignments():
        if var.startswith("CVE_CHECK_") and var != "CVE_CHECK_SHOW_WARNINGS" and var not in ("CVE_CHECK_IGNORE",):
            found.append(_finding(ctx, rule, path, line, f"{var} belonged to cve-check, removed in 6.0",
                                  advice="See SBOM_CVE_CHECK_* (for example SBOM_CVE_CHECK_EXPORT_VARS) for the sbom-cve-check equivalent."))
    return found


def check_cve_product(ctx, rule):
    found = []
    for path, line, var, _, _, value in ctx.assignments({"CVE_PRODUCT"}):
        if "\\" in value:
            fix = _line_fix(ctx, path, line, lambda t, v=value: t.replace(v, v.replace("\\", ""), 1))
            found.append(_finding(ctx, rule, path, line, "CVE_PRODUCT no longer needs escaping", [fix] if fix else []))
    return found


def check_wic_sector(ctx, rule):
    found = []
    for path, line, var, _, op, value in ctx.assignments({"WIC_SECTOR_SIZE"}):
        old = ctx.files[path][line - 1]
        indent = re.match(r"^\s*", old)[0]
        fix = Fix(str(path), line, old, f'{indent}WIC_CREATE_EXTRA_ARGS += "--sector-size {value}"') if value.isdigit() else None
        found.append(_finding(ctx, rule, path, line, "WIC_SECTOR_SIZE is deprecated", [fix] if fix else []))
    return found


def check_wks_location(ctx, rule):
    found = []
    for layer in ctx.layers:
        for folder in ("wic", "scripts/lib/wic/canned-wks"):
            for wks in sorted((layer / folder).glob("*.wks*")):
                found.append(_finding(ctx, rule, wks, None, f"{folder}/{wks.name} must move to files/wic in 6.0",
                                      advice=f"git mv {folder}/{wks.name} files/wic/{wks.name} (inside {layer.name})"))
    return found


def check_init_both(ctx, rule):
    found = []
    for path, line, var, overrides, op, value in ctx.assignments({"DISTRO_FEATURES"}):
        if "systemd" in value.split() and "sysvinit" in value.split():
            found.append(_finding(ctx, rule, path, line, "systemd and sysvinit together: no longer possible in 6.0",
                                  advice='Choose one: INIT_MANAGER = "systemd" or "sysvinit" in your distro.'))
    return found


def check_nodistro(ctx, rule):
    found = []
    distro = ctx.profile.distro or ""
    for path, line, var, _, _, value in ctx.assignments({"DISTRO"}):
        distro = distro or value
    if distro in ("", "nodistro"):
        found.append(_finding(ctx, rule, ctx.profile.build_path / "conf/local.conf", None, "without a DISTRO, the default init manager becomes systemd in 6.0",
                              advice='Set INIT_MANAGER = "sysvinit" in your distro if you rely on SysVinit.'))
    return found


def check_vex_name(ctx, rule):
    found = []
    for path, line, var, _, _, value in ctx.assignments({"INHERIT", "IMAGE_CLASSES"}):
        if "vex" in value.split():
            found.append(_finding(ctx, rule, path, line, "the VEX document of images is now *.rootfs.vex.json (was *.rootfs.json)",
                                  advice="Update scripts or CI jobs that pick up the old name."))
    return found


def check_debug_build(ctx, rule):
    return [_finding(ctx, rule, path, line, "with DEBUG_BUILD, native and cross binaries are stripped again in 6.0")
            for path, line, var, _, _, value in ctx.assignments({"DEBUG_BUILD"}) if value == "1"]


def check_go(ctx, rule):
    found = []
    for path, lines in ctx.files.items():
        text = "\n".join(lines)
        if path.suffix in (".bb", ".inc") and re.search(r"^\s*inherit\b.*\bgo(-mod)?\b", text, re.M) and "GO_SRCURI_DESTSUFFIX" not in text:
            found.append(_finding(ctx, rule, path, None, "a Go recipe without destsuffix=${GO_SRCURI_DESTSUFFIX} in SRC_URI"))
    return found


def check_license_qa(ctx, rule):
    found = []
    for path, line, var, _, _, value in ctx.assignments({"ERROR_QA", "WARN_QA", "INSANE_SKIP"}):
        if "license-incompatible" in value.split():
            fix = _line_fix(ctx, path, line, lambda t: t.replace("license-incompatible", "license-exception"))
            found.append(_finding(ctx, rule, path, line, "license-incompatible is now license-exception", [fix] if fix else []))
    return found


def check_lic_parent(ctx, rule):
    return [_finding(ctx, rule, path, line, "LIC_FILES_CHKSUM points outside the source with ../")
            for path, line, var, _, _, value in ctx.assignments({"LIC_FILES_CHKSUM"}) if "file://../" in value]


def check_systemd_usr(ctx, rule):
    return [_finding(ctx, rule, path, line, "systemd no longer has the usrmerge PACKAGECONFIG (always merged)")
            for path, line, var, overrides, _, value in ctx.assignments({"PACKAGECONFIG"})
            if "usrmerge" in value.split() and ("pn-systemd" in overrides or path.name.startswith("systemd_"))]


def check_uboot_env(ctx, rule):
    found = []
    for path, lines in ctx.files.items():
        text = "\n".join(lines)
        if "UBOOT_ENV" in text and re.search(r"kernel-fitimage|fitImage", text):
            found.append(_finding(ctx, rule, path, None, "UBOOT_ENV for the kernel FIT image is now FIT_UBOOT_ENV"))
    return found


RULES = [
    # 5.1 styhead
    Rule("s-workdir", "styhead", "breaks", 'S = "${WORKDIR}" is no longer supported', "#s-workdir-no-longer-supported",
         'S = "${UNPACKDIR}"', check_s_workdir),
    Rule("workdir-files", "styhead", "breaks", "Files from SRC_URI are in ${UNPACKDIR}", "#workdir-references-in-recipes",
         "Use ${UNPACKDIR}/<file> (or ${S}) for files listed in SRC_URI.", check_workdir_files),
    Rule("lic-parent", "styhead", "review", "References to ../ may need ${UNPACKDIR}", "#workdir-references-in-recipes",
         "Check the path: sources now unpack into WORKDIR/sources-unpack.", check_lic_parent),
    Rule("go-destsuffix", "styhead", "breaks", "Go recipes need destsuffix=${GO_SRCURI_DESTSUFFIX}", "#go-language-changes",
         "Add ;destsuffix=${GO_SRCURI_DESTSUFFIX} to the Go module's SRC_URI.", check_go),
    Rule("vars-5.1", "styhead", "breaks", "Variables removed in 5.1", "#removed-variables", "", _removed_variables({
        "TCLIBCAPPEND": "Remove it: TMPDIR is shared between libc providers.",
        "VOLATILE_LOG_DIR": "Use FILESYSTEM_PERMS_TABLES (remove files/fs-perms-volatile-log.txt from it for a persistent /var/log).",
        "VOLATILE_TMP_DIR": "Use FILESYSTEM_PERMS_TABLES (remove files/fs-perms-volatile-tmp.txt from it for a persistent /tmp)."})),
    Rule("recipes-5.1", "styhead", "breaks", "Recipes removed in 5.1", "#removed-recipes", "", _removed_recipes({
        "liba52": ("", "Use ffmpeg."), "libomxil": ("", "Removed with its only consumer."), "libnewt": ("", "Add meta-oe (meta-openembedded)."),
        "mpeg2dec": ("", "Use ffmpeg."), "pytest-runner": ("", "Add meta-python."), "python3-importlib-metadata": ("", "Add meta-python."),
        "python3-pathlib2": ("", "Add meta-python."), "python3-py": ("", "Add meta-python."), "python3-rfc3986-validator": ("", "Add meta-python."),
        "python3-toml": ("", "Add meta-python."), "python3-tomli": ("", "Add meta-python."), "usbinit": ("", "Removed: no replacement.")})),
    Rule("classes-5.1", "styhead", "breaks", "Classes removed in 5.1", "#removed-classes", "", _removed_classes({"siteconfig": "Remove the inherit."})),
    Rule("license-qa", "styhead", "breaks", "license-incompatible QA check renamed", "#miscellaneous-changes", "Use license-exception.", check_license_qa),
    # 5.2 walnascar
    Rule("debug-tweaks", "walnascar", "breaks", "debug-tweaks removed from IMAGE_FEATURES", "#debug-tweaks-removed-from-image-features",
         "Use the features it stood for, and only on development images.",
         _feature_words({"IMAGE_FEATURES", "EXTRA_IMAGE_FEATURES"}, {"debug-tweaks": "allow-empty-password allow-root-login empty-root-password post-install-logging"})),
    Rule("git-branch", "walnascar", "breaks", "Git SRC_URI: branch= is required, one branch per URL", "#git-fetcher-branch-parameter-now-required-in-src-uri", "", check_git_branch),
    Rule("virtual-cross", "walnascar", "breaks", "Toolchain virtual providers renamed", "#virtual-toolchain-provider-changes", "Use the virtual/cross-* names.", check_virtual),
    Rule("current-mc", "walnascar", "breaks", "BB_CURRENT_MC is empty for the default configuration", "#multiconfig-changes", "Compare with an empty string.", check_current_mc),
    Rule("uboot-entry", "walnascar", "breaks", "UBOOT_ENTRYPOINT needs 0x", "#uboot-entrypoint-changes", "", check_uboot_entry),
    Rule("zstd-level", "walnascar", "breaks", "ZSTD_COMPRESSION_LEVEL is a plain number", "#miscellaneous-changes", "", check_zstd),
    Rule("systemd-usrmerge", "walnascar", "review", "systemd always merges /usr", "#systemd-changes", "Remove usrmerge from systemd's PACKAGECONFIG.", check_systemd_usr),
    Rule("uboot-env", "walnascar", "review", "UBOOT_ENV no longer goes into the kernel FIT image", "#miscellaneous-changes", "Use FIT_UBOOT_ENV for the FIT image.", check_uboot_env),
    Rule("ld-gold", "walnascar", "breaks", "The ld-is-gold distro feature was removed", "#removed-features", "Remove it from DISTRO_FEATURES.",
         _feature_words({"DISTRO_FEATURES"}, {"ld-is-gold": None})),
    Rule("vars-5.2", "walnascar", "breaks", "Variables removed in 5.2", "#removed-variables", "", _removed_variables({
        "PACKAGE_SNAP_LIB_SYMLINKS": "Remove it.", "SETUPTOOLS_INSTALL_ARGS": "Remove it.", "ACLOCALDIR": "Remove it (aclocal is invoked differently); use EXTRA_AUTORECONF += \"-I path/to/m4\".",
        "ACLOCALEXTRAPATH": "Remove it; use EXTRA_AUTORECONF += \"-I path/to/m4\".",
        "BB_DANGLINGAPPENDS_WARNONLY": "Remove it: dangling appends are errors; use BBMASK or dynamic layers instead."})),
    Rule("recipes-5.2", "walnascar", "breaks", "Recipes removed or renamed in 5.2", "#removed-recipes", "", _removed_recipes({
        "libnss-mdns": ("avahi-libnss-mdns", "Renamed to avahi-libnss-mdns."), "liburi-perl": ("", "Add meta-perl."), "python3-isodate": ("", "Add meta-python."),
        "python3-iniparse": ("", "Removed: no replacement."), "blktool": ("", "Use hdparm."), "cargo-c-native": ("cargo-c", "Now a target recipe: cargo-c.")})),
    Rule("classes-5.2", "walnascar", "breaks", "Classes removed in 5.2", "#removed-classes", "", _removed_classes({"migrate_localcount": "Remove the inherit."})),
    # 5.3 whinlatter
    Rule("poky-repo", "whinlatter", "breaks", "The poky repository is no longer updated", "#the-poky-repository-master-branch-is-no-longer-updated", "", check_poky_repo),
    Rule("s-workdir-sub", "whinlatter", "breaks", 'S = "${WORKDIR}/…" is no longer supported; S for Git checkouts goes', "#workdir-changes", "", check_s_workdir_sub),
    Rule("assign-space", "whinlatter", "review", "Spaces around assignments", "#space-around-equal-assignment", 'FOO = "bar"', check_equals_space),
    Rule("wic-dash", "whinlatter", "breaks", "Wic plugins with dashes must be renamed", "#wic-plugins-containing-dashes-should-be-renamed", "", check_wic_plugins),
    Rule("fitimage", "whinlatter", "breaks", "fitImage is no longer a KERNEL_IMAGETYPE", "#fitimage-no-longer-supported-for-kernel-imagetype",
         'Use the kernel-fit-image class: KERNEL_CLASSES += "kernel-fit-extra-artifacts" and build linux-yocto-fitimage.', check_fitimage),
    Rule("flags-native", "whinlatter", "review", "*FLAGS += now applies to native and nativesdk too", "#flags-variables-behavior-change-for-native-and-nativesdk-classes", "", check_flags_native),
    Rule("vars-5.3", "whinlatter", "breaks", "Variables removed in 5.3", "#removed-variables", "", _removed_variables({
        "BUILDHISTORY_RESET": "Remove it.", "GPE_MIRROR": "Remove it.", "GDK_PIXBUF_LOADERS": "Change gdk-pixbuf's PACKAGECONFIG instead."})),
    Rule("recipes-5.3", "whinlatter", "breaks", "Recipes removed in 5.3", "#removed-recipes", "", _removed_recipes({
        "libsoup-2.4": ("", "Add meta-oe, or move to libsoup 3."), "glibc-y2038-tests": ("glibc-testsuite", "Use glibc-testsuite."),
        "python3-ndg-httpsclient": ("", "Removed: no replacement."), "xf86-input-mouse": ("", "Removed: use libinput."), "xf86-input-vmmouse": ("", "Removed."),
        "babeltrace": ("babeltrace2", "Use babeltrace2."), "cwautomacros": ("", "Removed."), "rust-llvm": ("", "Rust now uses the llvm recipe.")})),
    Rule("packageconfig-5.3", "whinlatter", "breaks", "PACKAGECONFIG options removed in 5.3", "#removed-packageconfig-entries", "", _removed_packageconfig({
        "dropbear": {"enable-x11-forwarding": "Renamed to x11."}, "libxml2": {"ipv6": "Remove it."}, "squashfs-tools": {"reproducible": "Remove it."},
        "mesa": {"kmsro": "Remove it.", "osmesa": "Remove it.", "xa": "Remove it."}, "systemd": {"dbus": "Remove it."}})),
    Rule("classes-5.3", "whinlatter", "breaks", "Classes removed in 5.3", "#removed-classes", "", _removed_classes({
        "kernel-fitimage": "Use kernel-fit-image and a FIT image recipe (linux-yocto-fitimage).", "icecc": "Remove it: it had been broken since 4.2."})),
    # 6.0 wrynose
    Rule("layerseries", "wrynose", "breaks", "Your layers must declare the new release", "#", "", check_layerseries),
    Rule("backfill", "wrynose", "breaks", "How default DISTRO and MACHINE features are provided changed", "#changes-in-how-default-distro-features-and-machine-features-are-provided", "", check_backfill),
    Rule("templates", "wrynose", "breaks", "meta-poky's default configuration templates were removed", "#default-configuration-templates-removed-from-meta-poky", "", check_templates),
    Rule("spdx22", "wrynose", "breaks", "SPDX 2.2 support removed", "#support-for-spdx-2-2-removed", "Use create-spdx (SPDX 3.0).", check_spdx22),
    Rule("cve-check", "wrynose", "breaks", "The cve-check class was removed", "#cve-check-class-removed", "", check_cve_check),
    Rule("cve-product", "wrynose", "review", "CVE_PRODUCT is no longer escaped", "#cve-product-character-escaping-change", "Remove the backslashes.", check_cve_product),
    Rule("wic-sector", "wrynose", "review", "WIC_SECTOR_SIZE is deprecated", "#wic-sector-size-should-be-replaced-by-sector-size", 'WIC_CREATE_EXTRA_ARGS += "--sector-size N"', check_wic_sector),
    Rule("wks-location", "wrynose", "breaks", "WKS files move to files/wic", "#wic-kickstart-files-to-be-moved-under-files-wic", "", check_wks_location),
    Rule("init-both", "wrynose", "breaks", "systemd and sysvinit cannot be used together", "#support-for-sysvinit-compatibility-in-systemd-was-dropped", "", check_init_both),
    Rule("uboot-config", "wrynose", "review", "UBOOT_CONFIG flags are split", "#u-boot-configuration-flow-changes-uboot-config", "", check_uboot_config),
    Rule("pkgconfig", "wrynose", "breaks", "pkg-config variables are no longer exported by default", "#pkgconfig-related-variables-are-no-longer-automatically-exported",
         "Add inherit pkgconfig.", check_pkgconfig),
    Rule("vex-name", "wrynose", "info", "VEX documents are now .vex.json", "#vex-output-json-document-extension-change", "", check_vex_name),
    Rule("debug-build", "wrynose", "info", "DEBUG_BUILD strips native and cross binaries again", "#native-and-cross-classes-debug-build-change",
         'INHIBIT_SYSROOT_STRIP:class-native = "${@oe.utils.vartrue(\'DEBUG_BUILD\', \'1\', \'\', d)}" restores the old behaviour.', check_debug_build),
    Rule("nodistro-init", "wrynose", "info", "systemd is the default init manager without a DISTRO", "#default-init-manager-definition-changed-to-systemd", "", check_nodistro),
    Rule("recipes-6.0", "wrynose", "breaks", "Recipes removed or renamed in 6.0", "#removed-recipes", "", _removed_recipes({
        "jquery": ("", "Removed."), "systemd-compat-units": ("", "Removed with SysVinit support in systemd."),
        "gstreamer1.0-vaapi": ("", "Use the va PACKAGECONFIG of gstreamer1.0-plugins-bad."), "pkgconfig": ("pkgconf", "Use pkgconf."),
        "python3-pyzstd": ("", "Python 3.14 has zstd built in."), "cve-update-db-native": ("", "Removed with cve-check."),
        "cve-update-nvd2-native": ("", "Removed with cve-check."), "python3-roman-numerals-py": ("python3-roman-numerals", "Renamed.")})),
    Rule("packageconfig-6.0", "wrynose", "breaks", "PACKAGECONFIG options removed in 6.0", "#removed-packageconfig-options", "", _removed_packageconfig({
        "mesa": {"freedreno-fdperf": "Remove it."}, "libcxx": {"no-atomics": "Remove it."}, "systemd": {"sysvinit": "Remove it: choose one init manager."},
        "gstreamer1.0-plugins-good": {"soup2": "Remove it (libsoup 3)."}, "webkitgtk": {"soup2": "Remove it (libsoup 3)."}})),
    Rule("classes-6.0", "wrynose", "breaks", "Classes removed in 6.0", "#removed-classes", "", _removed_classes({"oelint": "Remove it."})),
    Rule("vars-6.0", "wrynose", "breaks", "Variables removed in 6.0", "#cve-check-class-removed", "", _removed_variables({
        "DISTRO_FEATURES_BACKFILL": "Remove it; list unwanted defaults in DISTRO_FEATURES_OPTED_OUT."})),
]


# --- the plan -------------------------------------------------------------------------------------------------

def path_between(source: str, target: str) -> list[str]:
    """The releases a migration goes through, each with its own guide: scarthgap -> wrynose = styhead … wrynose."""
    if source not in ORDER or target not in ORDER:
        raise ValueError(f"Unknown release: {source if source not in ORDER else target}")
    if ORDER[target] <= ORDER[source]:
        raise ValueError(f"{target} is not newer than {source}")
    covered = {rule.step for rule in RULES}
    steps = [name for name in ORDER if ORDER[source] < ORDER[name] <= ORDER[target]]
    missing = [s for s in steps if s not in covered]
    if missing:
        raise ValueError(f"No migration rules for {', '.join(missing)} yet: Bitloom covers {', '.join(sorted(covered, key=ORDER.get))}")
    return steps


def targets_for(source: str | None) -> list[str]:
    covered = {rule.step for rule in RULES}
    if source not in ORDER:
        return []
    return [name for name in ORDER if ORDER[name] > ORDER[source] and all(s in covered for s in ORDER if ORDER[source] < ORDER[s] <= ORDER[name])]


def _kas_files(profile: Profile) -> list[Path]:
    from .setup import profile_kas_files
    return profile_kas_files(profile)


def scan(profile: Profile, target: str, entries=None, source: str | None = None) -> dict:
    """Everything that needs attention to move the project to target, grouped by release step."""
    from .inspectors import metadata, organize
    from .studio import product_layers
    from .versions import detect_release
    entries = organize(list(entries if entries is not None else metadata(profile)))
    source = source or detect_release(profile, entries)
    if not source:
        raise ValueError("The project's release is not known: build or set up the profile first")
    steps = path_between(source, target)
    ctx = Context(profile, product_layers(entries, profile), _kas_files(profile))
    ctx.target = target
    findings = []
    for rule in RULES:
        if rule.step in steps:
            try:
                findings += rule.check(ctx, rule)
            except (OSError, ValueError, re.error) as exc:
                findings.append(Finding(rule.id, rule.step, "info", rule.title, "", f"could not check: {exc}", "", ""))
    findings.sort(key=lambda f: (list(SEVERITIES).index(f.severity), ORDER[f.step], f.where))
    return {"source": source, "target": target, "steps": [{"series": s, "version": INFO[s][0], "guide": f"{GUIDES}/migration-{INFO[s][0]}.html"} for s in steps],
            "layers": [layer.name for layer in ctx.layers], "kas_files": [ctx.rel(p) for p in ctx.kas_files], "files_scanned": len(ctx.files),
            "findings": [asdict(f) for f in findings],
            "counts": {sev: sum(f.severity == sev for f in findings) for sev in SEVERITIES},
            "fixable": sum(bool(f.fixes) for f in findings), "rules": len([r for r in RULES if r.step in steps])}


# --- applying fixes -------------------------------------------------------------------------------------------

def _group(fixes: list[dict]) -> dict[str, list[dict]]:
    by_file: dict[str, list[dict]] = {}
    for fix in fixes:
        by_file.setdefault(fix["path"], []).append(fix)
    return by_file


def _compose(current: str, old: str, new: str) -> str:
    """Replay the change old -> new on a line another fix already changed (several fixes on one line)."""
    out = current
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        before = old[i1:i2]
        context = old[max(0, i1 - 12):i1]
        anchor = out.find(context + before) if context + before else -1
        if before and anchor < 0 and out.count(before) == 1:
            anchor, context = out.find(before), ""          # the context itself was changed by another fix
        if before and anchor >= 0:
            start = anchor + len(context)
            out = out[:start] + new[j1:j2] + out[start + len(before):]
        elif not before and context and out.find(context) >= 0:
            start = out.find(context) + len(context)
            out = out[:start] + new[j1:j2] + out[start:]
        else:
            raise ValueError("overlapping changes")
    return out


def _patched(lines: list[str], fixes: list[dict]) -> list[str]:
    """Apply line fixes (replace, remove, or insert after when old is empty) from the bottom up; several fixes on
    the same line are composed in order."""
    result = list(lines)
    by_line: dict[int, list[dict]] = {}
    for fix in fixes:
        by_line.setdefault(fix["line"], []).append(fix)
    for number in sorted(by_line, reverse=True):
        index = number - 1
        items = by_line[number]
        edits = [f for f in items if f["old"] != ""]
        inserts = [f["new"] for f in items if f["old"] == ""]
        removed = False
        if edits:
            if index >= len(result) or result[index] != edits[0]["old"]:
                raise ValueError(f"{edits[0]['path']}:{number} changed since the scan; scan again")
            original, current = result[index], result[index]
            for fix in edits:
                if fix["old"] != original:
                    raise ValueError(f"{fix['path']}:{number} changed since the scan; scan again")
                if fix["new"] is None:
                    removed = True
                    continue
                try:
                    current = fix["new"] if current == original else _compose(current, original, fix["new"])
                except ValueError:
                    raise ValueError(f"{fix['path']}:{number}: two fixes overlap; apply them one at a time") from None
            if removed:
                del result[index]
            else:
                result[index] = current
        position = index if removed else index + 1
        for text in reversed(inserts):
            result.insert(position, text)
    return result


def preview(fixes: list[dict], bases: list[Path] = ()) -> list[dict]:
    """Unified diffs of what applying these fixes would change, per file (paths shown relative to bases)."""
    out = []
    for path, items in _group(fixes).items():
        lines = Path(path).read_text(errors="replace").splitlines()
        new = _patched(lines, items)
        shown = path
        for base in bases:
            try:
                shown = str(Path(path).resolve().relative_to(Path(base).resolve()))
                break
            except ValueError:
                continue
        diff = "\n".join(difflib.unified_diff(lines, new, fromfile=shown, tofile=shown, lineterm="", n=1))
        out.append({"path": path, "shown": shown, "diff": diff, "changes": len(items)})
    return out


def apply(profile: Profile, state: Path, fixes: list[dict], allowed_roots: list[Path]) -> dict:
    """Write the fixes, keeping the original files in the state folder so they can be restored."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = Path(state) / "migration-backups" / stamp
    written = []
    roots = [p.resolve() for p in allowed_roots]
    plans = {}
    for path, items in _group(fixes).items():
        target = Path(path).resolve()
        if not any(target == r or r in target.parents for r in roots):
            raise ValueError(f"{path} is outside your layers and project: not changed")
        lines = target.read_text(errors="replace").splitlines()
        plans[target] = (lines, _patched(lines, items))       # all checked before anything is written
    for target, (lines, new) in plans.items():
        copy = backup / str(target).lstrip("/")
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, copy)
        ending = "\n" if target.read_text(errors="replace").endswith("\n") else ""
        temporary = target.with_name(target.name + ".bitloom-tmp")
        temporary.write_text("\n".join(new) + ending)
        temporary.chmod(target.stat().st_mode)
        temporary.replace(target)
        written.append(str(target))
    if written:
        (backup / "manifest.json").write_text(json.dumps({"profile": profile.name, "files": written, "at": stamp}, indent=2))
    return {"written": written, "backup": str(backup) if written else ""}


def backups(state: Path) -> list[dict]:
    rows = []
    for manifest in sorted((Path(state) / "migration-backups").glob("*/manifest.json"), reverse=True):
        try:
            rows.append({"id": manifest.parent.name, **json.loads(manifest.read_text())})
        except (OSError, ValueError):
            continue
    return rows


def restore(state: Path, ident: str) -> list[str]:
    folder = Path(state) / "migration-backups" / ident
    if not re.fullmatch(r"\d{8}-\d{6}", ident) or not (folder / "manifest.json").is_file():
        raise ValueError("Unknown backup")
    restored = []
    for name in json.loads((folder / "manifest.json").read_text())["files"]:
        copy = folder / name.lstrip("/")
        if copy.is_file():
            shutil.copy2(copy, name)
            restored.append(name)
    return restored


# --- moving the checkout: a kas file for the target release --------------------------------------------------

def kas_for(profile: Profile, target: str) -> dict:
    """The project's kas file rewritten for the target release, as a new file next to it."""
    from .projects import RELEASES
    files = _kas_files(profile)
    main = next((p for p in files if re.search(r"^repos:", p.read_text(errors="replace"), re.M)), None)
    if main is None:
        raise ValueError("No kas file with repos in this profile: move the checkout by hand (see the guide)")
    text = main.read_text(errors="replace")
    spec = RELEASES.get(target)
    if not spec:
        raise ValueError(f"Bitloom has no verified pins for {target} yet")
    lines = text.splitlines()
    out, notes, i = [], [], 0
    poky_layers = []
    while i < len(lines):
        line = lines[i]
        block = re.match(r"^(\s+)([\w.\-]+):\s*$", line)
        if block and i + 1 < len(lines):
            indent = block[1]
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip()) > len(indent)):
                j += 1
            body = lines[i + 1:j]
            joined = "\n".join(body)
            if re.search(r"url:\s*['\"]?https?://git\.yoctoproject\.org/(git/)?poky", joined):
                poky_layers = [m[1] for m in re.finditer(r"^\s+([\w.\-]+):\s*$", joined.split("layers:", 1)[1], re.M)] if "layers:" in joined else ["meta", "meta-poky", "meta-yocto-bsp"]
                for name, repo in spec["repos"].items():
                    wanted = [l for l in poky_layers if (l in ("meta", "meta-selftest", "meta-skeleton") and name == "openembedded-core") or
                              (l.startswith(("meta-poky", "meta-yocto")) and name == "meta-yocto")]
                    if repo["layers"] is not None and not wanted:
                        continue
                    out += [f"{indent}{name}:", f"{indent}  url: {repo['url']}", f"{indent}  tag: {repo['tag']}", f"{indent}  commit: {repo['commit']}", f"{indent}  layers:"]
                    out += [f"{indent}    .: disabled"] if repo["layers"] is None else [f"{indent}    {l}:" for l in wanted]
                notes.append(f"poky ({', '.join(poky_layers)}) → bitbake, openembedded-core and meta-yocto at {spec['repos']['bitbake']['tag']}")
                i = j
                continue
            if re.search(r"^\s+branch:\s*['\"]?(scarthgap|styhead|walnascar|whinlatter)['\"]?\s*$", joined, re.M):
                new_body = [re.sub(r"(branch:\s*['\"]?)(scarthgap|styhead|walnascar|whinlatter)", rf"\g<1>{target}", b) for b in body if not re.match(r"^\s+commit:", b)]
                out.append(line)
                out += new_body
                notes.append(f"{block[2]}: branch → {target}, commit removed (run Kas → Generate kas lock file after the first checkout)")
                i = j
                continue
        out.append(line)
        i += 1
    if spec.get("build_system") and not re.search(r"^build_system:", "\n".join(out), re.M):
        index = next((k for k, l in enumerate(out) if re.match(r"^header:", l)), -1)
        k = index + 1
        while 0 <= index and k < len(out) and out[k].startswith(" "):
            k += 1
        out.insert(k if index >= 0 else 0, f"build_system: {spec['build_system']}")
        notes.append(f"build_system: {spec['build_system']} (bitbake is its own repository)")
    header = [f"# {main.name} moved to {spec['title']} by Bitloom's migration assistant on {time.strftime('%Y-%m-%d')}.",
              f"# The original {main.name} is unchanged. Review, build with a separate KAS_WORK_DIR, then replace it."]
    new_text = "\n".join(header + out) + "\n"
    name = f"{main.stem}-{target}{main.suffix}"
    destination = main.with_name(name)
    n = 2
    while destination.exists():
        destination = main.with_name(f"{main.stem}-{target}-{n}{main.suffix}")
        n += 1
    other = [str(p.relative_to(profile.root_path)) for p in files if p != main]
    return {"source": str(main), "path": str(destination), "name": destination.name, "text": new_text, "notes": notes,
            "diff": "\n".join(difflib.unified_diff(text.splitlines(), new_text.splitlines(), fromfile=main.name, tofile=destination.name, lineterm="", n=2)),
            "kas_file": ":".join([str(destination.relative_to(profile.root_path)), *other])}


def write_kas(profile: Profile, target: str) -> dict:
    plan = kas_for(profile, target)
    path = Path(plan["path"])
    with path.open("x") as stream:       # never over an existing file
        stream.write(plan["text"])
    return plan


def migrated_profile(profile: Profile, target: str, kas_file: str) -> Profile:
    """A profile for the migrated project with its own work directory, so the current build is untouched."""
    from dataclasses import replace
    environment = dict(profile.environment)
    for key in ("KAS_WORK_DIR", "KAS_BUILD_DIR"):
        if key in environment:
            environment[key] = environment[key].rstrip("/") + f"-{target}"
    if profile.mode == "wrapper":
        # The launcher script picks the kas file from a variable (YML=…): point it at the new file.
        main = kas_file.split(":")[0]
        old = Path(main).name.replace(f"-{target}", "")
        for key, value in profile.environment.items():
            if value.endswith((".yml", ".yaml")) and Path(value).name == old:
                environment[key] = str(Path(value).parent / Path(main).name) if Path(value).parent != Path(".") else Path(main).name
        return replace(profile, name=f"{profile.name}-{target}"[:40], environment=environment)
    return replace(profile, name=f"{profile.name}-{target}"[:40], kas_file=kas_file, environment=environment)


def checkout_advice(profile: Profile, target: str) -> dict:
    """How to move the checkout when there is no kas file to rewrite."""
    from .bbsetup import TEMPLATES
    root = profile.root_path
    if (root / "build/init-build-env").is_file() and (root / "layers").is_dir():
        template = TEMPLATES.get(target, {}).get("config", f"poky-{target}")
        return {"kind": "bitbake-setup", "text": f"bitbake-setup workspaces belong to one release. Create a new one with the {template} template "
                f"(Configuration → New project → Set up with bitbake-setup), copy your own layers into it, and keep this one until the new build works."}
    if (root / "poky/.git").exists() or (root / "oe-init-build-env").is_file():
        return {"kind": "poky", "text": "Poky has no branch for 5.3 and later: clone bitbake, openembedded-core and meta-yocto at the "
                f"{target} tag into a new folder (or create a {target} project in Configuration → New project), add your layers to its bblayers.conf, "
                "and build there with a new profile; this checkout stays as it is."}
    return {"kind": "manual", "text": f"Move every layer repository to its {target} branch in a separate folder, then point a new profile at it."}


def report(data: dict, fmt: str = "text") -> str:
    if fmt == "json":
        return json.dumps(data, indent=2)
    md = fmt == "md"
    path = " → ".join([data["source"]] + [s["series"] for s in data["steps"]])
    lines = [("# " if md else "") + f"Migration {data['source']} → {data['target']}", "",
             f"Path: {path} · your layers: {', '.join(data['layers']) or 'none'} · {data['files_scanned']} files · {data['rules']} rules from the official guides",
             f"{data['counts']['breaks']} break the build · {data['counts']['review']} to review · {data['counts']['info']} good to know · {data['fixable']} with a safe fix", ""]
    for severity, title in SEVERITIES.items():
        rows = [f for f in data["findings"] if f["severity"] == severity]
        if not rows:
            continue
        lines += [("## " if md else "") + title.upper() if not md else "## " + title, ""]
        for f in rows:
            mark = "✖" if severity == "breaks" else "▲" if severity == "review" else "●"
            lines.append(f"{'- ' if md else ''}{mark} [{INFO[f['step']][0]}] {f['where']}: {f['detail']}" + ("  (fix available)" if f["fixes"] else ""))
            if f["advice"]:
                lines.append(f"    {f['advice']}")
            lines.append(f"    {f['guide']}")
        lines.append("")
    if not data["findings"]:
        lines.append("Nothing in your files needs changing for this migration.")
    return "\n".join(lines)
