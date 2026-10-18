"""Yocto best practices, checked on the project: what it follows, what it does not, where and how to fix it.

Built-in rules come from the Yocto Project documentation (layers, new recipes, "What I wish I'd known") and
from common release engineering; each names its source. A project (or a company) tunes them in
bitloom-practices.json at the project root, committed with the project:

    {
      "disabled": ["layer-security-policy"],
      "severity": {"own-distro": "warning"},
      "rules": [
        {"id": "acme-maintainer", "title": "Recipes name a maintainer", "severity": "warning",
         "why": "Our release process needs an owner per component.", "fix": "Add MAINTAINER = \\"…\\" to the recipe.",
         "check": {"type": "files-must-match", "files": "*.bb", "pattern": "^MAINTAINER\\\\s*="}}
      ]
    }

Company rules are declarative (no code runs): files-must-match, files-must-not-match, layer-file-exists and
variable. Only your own layers are checked by file rules; upstream layers are never judged.
"""
from __future__ import annotations

import fnmatch
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .models import Profile, read_assignments

CONFIG = "bitloom-practices.json"
SEVERITIES = ("error", "warning", "info")
DOCS = "https://docs.yoctoproject.org"
LAYERS_DOC = f"{DOCS}/dev-manual/layers.html"
RECIPE_DOC = f"{DOCS}/dev-manual/new-recipe.html"
WISH_DOC = f"{DOCS}/what-i-wish-id-known.html"
SECURITY_DOC = f"{DOCS}/security-manual/index.html"
STANDARD_LAYER_VARS = re.compile(r"^(BBPATH|BBFILES|BBFILE_COLLECTIONS|BBFILE_PATTERN_\S+|BBFILE_PRIORITY_\S+|LAYERDEPENDS_\S+|LAYERRECOMMENDS_\S+|"
                                 r"LAYERSERIES_COMPAT_\S+|LAYERVERSION_\S+|LAYERDIR\S*|BBFILES_DYNAMIC|BBMASK)$")
ACCESS_FEATURES = ("debug-tweaks", "empty-root-password", "allow-empty-password", "allow-root-login", "post-install-logging")


@dataclass
class Finding:
    where: str
    detail: str = ""


@dataclass
class Rule:
    id: str
    category: str
    title: str
    why: str
    fix: str
    source: str = ""
    severity: str = "warning"
    custom: bool = False
    check_spec: dict = field(default_factory=dict)


@dataclass
class Context:
    """What the rules look at: your layers, the upstream ones, recipes, appends and the build configuration."""
    profile: Profile
    series: str | None
    entries: list
    mine: list[Path]
    upstream: list[Path]

    def files(self, suffixes, layers=None):
        for layer in layers if layers is not None else self.mine:
            for path in sorted(layer.rglob("*")):
                if path.suffix in suffixes and path.is_file() and ".git" not in path.parts:
                    yield layer, path

    def text(self, path: Path) -> str:
        try:
            return path.read_text(errors="replace")
        except OSError:
            return ""

    def rel(self, path: Path) -> str:
        for layer in self.mine + self.upstream:
            try:
                return f"{layer.name}/{path.relative_to(layer)}"
            except ValueError:
                continue
        return str(path)


def _layer_conf(layer: Path) -> dict:
    return read_assignments(layer / "conf/layer.conf")


def _assignment_lines(text: str):
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^\s*([A-Za-z_][\w:${}./+-]*)\s*(\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)\s*(.*)$", line)
        if match:
            yield number, match[1], match[3]


# --- built-in checks: each returns findings (empty: followed) or None (does not apply to this project) ----

def check_layer_name(ctx):
    return [Finding(layer.name, "rename to meta-<name>") for layer in ctx.mine if not layer.name.startswith("meta-")] if ctx.mine else None


def check_layer_conf(ctx):
    if not ctx.mine:
        return None
    found = []
    for layer in ctx.mine:
        values = " ".join(f"{k} " for k in _layer_conf(layer))
        text = ctx.text(layer / "conf/layer.conf")
        missing = [key for key in ("BBFILE_COLLECTIONS", "BBFILE_PATTERN", "BBFILE_PRIORITY", "LAYERSERIES_COMPAT") if key not in values and key not in text]
        if missing:
            found.append(Finding(f"{layer.name}/conf/layer.conf", "missing " + ", ".join(missing)))
    return found


def check_layer_compat(ctx):
    if not ctx.mine or not ctx.series:
        return None
    found = []
    for layer in ctx.mine:
        compat = " ".join(v for k, v in _layer_conf(layer).items() if k.startswith("LAYERSERIES_COMPAT")) or \
            " ".join(v.strip('"') for _, k, v in _assignment_lines(ctx.text(layer / "conf/layer.conf")) if k.startswith("LAYERSERIES_COMPAT"))
        if ctx.series not in compat.split():
            found.append(Finding(f"{layer.name}/conf/layer.conf", f"LAYERSERIES_COMPAT is “{compat.strip() or 'unset'}”, the project builds {ctx.series}"))
    return found


def check_layer_depends(ctx):
    if not ctx.mine:
        return None
    collections = set()
    for layer in ctx.mine + ctx.upstream:
        collections.update(_layer_conf(layer).get("BBFILE_COLLECTIONS", "").split())
        for _, key, value in _assignment_lines(ctx.text(layer / "conf/layer.conf")):
            if key == "BBFILE_COLLECTIONS":
                collections.update(value.strip('"').split())
    found = []
    for layer in ctx.mine:
        for _, key, value in _assignment_lines(ctx.text(layer / "conf/layer.conf")):
            if key.startswith("LAYERDEPENDS"):
                for name in re.sub(r"\([^)]*\)", "", value.strip('"')).split():
                    if name not in collections:
                        found.append(Finding(f"{layer.name}/conf/layer.conf", f"depends on “{name}”, which no layer of the project provides"))
    return found


def check_layer_readme(ctx):
    if not ctx.mine:
        return None
    return [Finding(layer.name, "no README") for layer in ctx.mine
            if not any(p.is_file() and p.stat().st_size for p in layer.glob("README*"))]


def check_layer_security(ctx):
    if not ctx.mine:
        return None
    found = []
    for layer in ctx.mine:
        top = _git_top(layer)
        if not (any(layer.glob("SECURITY*")) or (top and any(top.glob("SECURITY*")))):
            found.append(Finding(layer.name, "no SECURITY.md in the layer or its repository"))
    return found


def check_layer_license(ctx):
    if not ctx.mine:
        return None
    return [Finding(layer.name, "no COPYING or LICENSE file") for layer in ctx.mine if not (any(layer.glob("COPYING*")) or any(layer.glob("LICENSE*")))]


def check_layer_globals(ctx):
    if not ctx.mine:
        return None
    found = []
    for layer in ctx.mine:
        for number, key, _ in _assignment_lines(ctx.text(layer / "conf/layer.conf")):
            if not STANDARD_LAYER_VARS.match(key):
                found.append(Finding(f"{layer.name}/conf/layer.conf:{number}", f"{key} is set for every build that includes the layer"))
    return found


def check_layer_mixed(ctx):
    if not ctx.mine:
        return None
    return [Finding(layer.name, "machines, a distribution and recipes in one layer") for layer in ctx.mine
            if any(layer.glob("conf/machine/*.conf")) and any(layer.glob("conf/distro/*.conf")) and any(layer.glob("recipes-*"))]


def _git_top(path: Path) -> Path | None:
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def check_layer_git(ctx):
    if not ctx.mine:
        return None
    return [Finding(layer.name, "not in a Git repository") for layer in ctx.mine if _git_top(layer) is None]


def check_upstream_untouched(ctx):
    if not ctx.upstream or not shutil.which("git"):
        return None
    tops = sorted({top for layer in ctx.upstream if (top := _git_top(layer))})
    if not tops:
        return None
    found = []
    for top in tops:
        try:
            out = subprocess.run(["git", "-C", str(top), "status", "--porcelain"], capture_output=True, text=True, timeout=20).stdout
        except (OSError, subprocess.TimeoutExpired):
            continue
        changed = [line[3:] for line in out.splitlines() if line.strip()]
        if changed:
            found.append(Finding(top.name, f"{len(changed)} changed or new files, e.g. {', '.join(changed[:3])}"))
    return found


def _recipes(ctx, layers):
    names = {}
    for layer, path in ctx.files({".bb"}, layers):
        names.setdefault(path.name.split("_")[0].removesuffix(".bb"), []).append(path)
    return names


def check_no_copied_recipe(ctx):
    if not ctx.mine:
        return None
    upstream = _recipes(ctx, ctx.upstream)
    return [Finding(ctx.rel(path), f"also in {ctx.rel(upstream[name][0])}: extend it with a .bbappend instead")
            for name, paths in _recipes(ctx, ctx.mine).items() if name in upstream for path in paths]


def check_bbappend_matches(ctx):
    appends = list(ctx.files({".bbappend"}))
    if not appends:
        return None
    recipes = [p.name[:-3] for _, p in ctx.files({".bb"}, ctx.mine + ctx.upstream)]
    found = []
    for _, path in appends:
        pattern = path.name[:-len(".bbappend")].replace("%", "*")
        if not any(fnmatch.fnmatch(name, pattern) for name in recipes):
            found.append(Finding(ctx.rel(path), "no recipe matches this append; BitBake stops at parse time"))
    return found


def check_filesextrapaths(ctx):
    found = []
    for _, path in ctx.files({".bbappend"}):
        for number, line in enumerate(ctx.text(path).splitlines(), 1):
            if "FILESEXTRAPATHS" in line and not re.match(r'^\s*FILESEXTRAPATHS:prepend\s*:=\s*"[^"]*:"\s*$', line):
                found.append(Finding(f"{ctx.rel(path)}:{number}", line.strip()[:90]))
            if re.match(r"^\s*THISDIR\s*=", line):
                found.append(Finding(f"{ctx.rel(path)}:{number}", "THISDIR is set by BitBake; never assign it"))
    return found


def check_override_syntax(ctx):
    found = []
    for _, path in ctx.files({".bb", ".bbappend", ".inc", ".conf", ".bbclass"}):
        for number, line in enumerate(ctx.text(path).splitlines(), 1):
            if not line.lstrip().startswith("#") and re.search(r"\b[A-Z][A-Z0-9_]*_(append|prepend|remove)\b|\bdo_\w+_(append|prepend)\b", line):
                found.append(Finding(f"{ctx.rel(path)}:{number}", line.strip()[:90]))
    return found


def check_no_image_append(ctx):
    return [Finding(ctx.rel(path), "write your own image recipe instead of appending this one") for _, path in ctx.files({".bbappend"})
            if re.search(r"(^core-image|-image)[-_%.]", path.name)]


def check_recipe_naming(ctx):
    found = []
    for _, path in ctx.files({".bb"}):
        name = path.name[:-3]
        if name != name.lower():
            found.append(Finding(ctx.rel(path), "use lowercase names"))
        elif re.search(r"-(native|cross|initial|dev)(_|$)", name) and "native" not in ctx.text(path):
            found.append(Finding(ctx.rel(path), "reserved suffix in the name"))
    return found


def _exempt_from_license_file(text: str) -> bool:
    return bool(re.search(r'^\s*(inherit\s+[^\n]*\b(core-image|image|packagegroup)\b|LICENSE\s*=\s*"CLOSED")', text, re.M) or re.search(r"^\s*require\s+\S*image\S*\.bb", text, re.M))


def check_recipe_license(ctx):
    found = []
    for _, path in ctx.files({".bb"}):
        text = ctx.text(path)
        if not re.search(r"^\s*LICENSE\s*\??=", text, re.M) and not re.search(r"^\s*require\s", text, re.M):
            found.append(Finding(ctx.rel(path), "no LICENSE"))
        elif not _exempt_from_license_file(text) and not re.search(r"^\s*LIC_FILES_CHKSUM\s*\??=", text, re.M) and not re.search(r"^\s*require\s", text, re.M):
            found.append(Finding(ctx.rel(path), "no LIC_FILES_CHKSUM: licence changes upstream would go unnoticed"))
    return found


def check_src_checksums(ctx):
    found = []
    for layer, path in ctx.files({".bb", ".inc"}):
        text = ctx.text(path)
        urls = re.findall(r"\b((?:https?|ftp)://[^\s\"\\;]+)((?:;[^\s\"\\]*)?)", text)
        if urls and "sha256sum" not in text:
            found.append(Finding(ctx.rel(path), f"no SRC_URI[sha256sum] for {urls[0][0][:70]}"))
        if "md5sum]" in text:
            found.append(Finding(ctx.rel(path), "SRC_URI[md5sum] is deprecated: use sha256sum"))
    return found


def check_srcrev_pinned(ctx):
    found = []
    for _, path in ctx.files({".bb", ".bbappend", ".inc"}):
        text = ctx.text(path)
        for number, key, value in _assignment_lines(text):
            if key.startswith("SRCREV") and "AUTOREV" in value:
                found.append(Finding(f"{ctx.rel(path)}:{number}", "AUTOREV: every build may fetch a different commit"))
        if re.search(r"\bgit(sm)?://", text) and path.suffix == ".bb" and not re.search(r"^\s*SRCREV", text, re.M) and not re.search(r"^\s*require\s", text, re.M):
            found.append(Finding(ctx.rel(path), "git source without SRCREV"))
    return found


def check_patch_status(ctx):
    found = []
    for _, path in ctx.files({".patch", ".diff"}):
        if "Upstream-Status:" not in ctx.text(path)[:8000]:
            found.append(Finding(ctx.rel(path), "no Upstream-Status: line"))
    return found


def _config_files(ctx) -> list[Path]:
    build = ctx.profile.build_path / "conf"
    files = [build / "local.conf", build / "auto.conf"]
    files += [p for layer in ctx.mine for p in layer.glob("conf/distro/*.conf")]
    files += [p for layer in ctx.mine for p in layer.glob("recipes-*/images/*.bb")]
    files += [p for p in ctx.profile.root_path.glob("*.yml")] + [p for p in ctx.profile.root_path.glob("kas/*.yml")]
    return [p for p in files if p.is_file()]


def check_access_features(ctx):
    found = []
    for path in _config_files(ctx):
        for number, line in enumerate(ctx.text(path).splitlines(), 1):
            if re.search(r"IMAGE_FEATURES|EXTRA_IMAGE_FEATURES", line) and not line.lstrip().startswith("#"):
                bad = [f for f in ACCESS_FEATURES if re.search(rf"\b{f}\b", line)]
                if bad:
                    found.append(Finding(f"{path.name}:{number}", ", ".join(bad) + ": fine on a development board, never in a product"))
    return found


def check_shared_caches(ctx):
    conf = read_assignments(ctx.profile.build_path / "conf/local.conf")
    environment = ctx.profile.environment
    found = []
    for name in ("DL_DIR", "SSTATE_DIR"):
        if name not in conf and not environment.get(name) and not environment.get("KAS_DL_DIR" if name == "DL_DIR" else "SSTATE_DIR"):
            found.append(Finding("conf/local.conf", f"{name} is inside the build directory: every new build directory downloads and rebuilds everything"))
    return found


def check_own_distro(ctx):
    conf = read_assignments(ctx.profile.build_path / "conf/local.conf")
    distro = ctx.profile.distro or conf.get("DISTRO", "")
    if not distro:
        return None
    return [Finding("DISTRO", f"“{distro}” is Poky's reference distribution: a product defines its own (Studio → Distribution)")] if distro.startswith("poky") else []


def check_product_config_in_local(ctx):
    local = ctx.profile.build_path / "conf/local.conf"
    text = ctx.text(local)
    if not text:
        return None
    product = [(n, k) for n, k, _ in _assignment_lines(text) if re.match(r"^(IMAGE_INSTALL|DISTRO_FEATURES|PREFERRED_PROVIDER_virtual/kernel|PREFERRED_VERSION_\S+|IMAGE_FSTYPES|PACKAGE_CLASSES)\b", k)]
    return [Finding(f"local.conf:{n}", f"{k}: product configuration belongs in your distro, machine or image") for n, k in product]


def check_buildhistory(ctx):
    conf = read_assignments(ctx.profile.build_path / "conf/local.conf")
    if not conf:
        return None
    return [] if "buildhistory" in conf.get("INHERIT", "") else [Finding("conf/local.conf", 'INHERIT += "buildhistory" is not set')]


def check_rm_work(ctx):
    conf = read_assignments(ctx.profile.build_path / "conf/local.conf")
    if not conf:
        return None
    return [] if "rm_work" in conf.get("INHERIT", "") else [Finding("conf/local.conf", 'INHERIT += "rm_work" is not set: tmp/work keeps every source tree')]


BUILTIN = [
    (Rule("layer-name", "Layers", "Your layers are called meta-<name>", "Tools and variables expect the meta- prefix; collection names drop it.",
          "Rename the layer folder meta-<company or product>.", f"{LAYERS_DOC}#creating-your-own-layer", "warning"), check_layer_name),
    (Rule("layer-conf", "Layers", "layer.conf declares the layer completely", "BBFILE_COLLECTIONS, BBFILE_PATTERN, BBFILE_PRIORITY and LAYERSERIES_COMPAT identify the layer and its releases.",
          "Add the missing variables (Studio's Product layer writes a complete layer.conf).", f"{LAYERS_DOC}#creating-your-own-layer", "error"), check_layer_conf),
    (Rule("layer-compat", "Layers", "LAYERSERIES_COMPAT includes the release you build", "It says the layer is current; BitBake warns or stops when it does not match.",
          "Add the release codename to LAYERSERIES_COMPAT_<collection> after checking the layer on it.", f"{LAYERS_DOC}#making-sure-your-layer-is-compatible-with-yocto-project", "error"), check_layer_compat),
    (Rule("layer-depends", "Layers", "LAYERDEPENDS names layers the project has", "Dependencies are collection names; a missing one breaks parsing for everyone who uses the layer.",
          "Fix the name, or add the layer the dependency refers to.", f"{LAYERS_DOC}#creating-your-own-layer", "error"), check_layer_depends),
    (Rule("layer-readme", "Layers", "Each layer has a README", "It says what the layer is for, its dependencies and its maintainer; yocto-check-layer requires it.",
          "Add README with purpose, dependencies, maintainer and how to contribute.", f"{LAYERS_DOC}#yocto-check-layer-script", "warning"), check_layer_readme),
    (Rule("layer-security-policy", "Layers", "Each layer has a SECURITY.md", "It tells users how to report vulnerabilities; yocto-check-layer checks it (and the CRA asks for a contact).",
          "Add SECURITY.md to the layer or its repository.", f"{LAYERS_DOC}#yocto-check-layer-script", "info"), check_layer_security),
    (Rule("layer-license", "Layers", "Each layer states its licence", "The licence of your metadata, separate from what it builds.",
          "Add COPYING.MIT (or your licence) to the layer.", f"{LAYERS_DOC}#creating-your-own-layer", "info"), check_layer_license),
    (Rule("layer-conf-globals", "Layers", "layer.conf sets only layer variables", "Global settings in layer.conf change every build that includes the layer.",
          "Move them to your distro, machine or image configuration.", f"{LAYERS_DOC}#following-best-practices-when-creating-layers", "warning"), check_layer_globals),
    (Rule("layer-split", "Layers", "BSP, distribution and software live in separate layers", "One layer for everything complicates reuse and later customisation.",
          "Split it: meta-<product>-bsp for machines, meta-<product>-distro for policy, meta-<product> for software.", f"{WISH_DOC}", "info"), check_layer_mixed),
    (Rule("layer-in-git", "Layers", "Your layers are under Git", "Updates, reviews and releases need history.", "git init the layer (or its project) and commit it.", WISH_DOC, "warning"), check_layer_git),
    (Rule("upstream-untouched", "Upstream", "Upstream layers are not modified", "“Never. Ever.”: changes in Poky or OE-Core are lost at the next update.",
          "Move each change into a .bbappend or configuration in your layer, then reset the upstream checkout.", WISH_DOC, "error"), check_upstream_untouched),
    (Rule("no-copied-recipes", "Appends", "Upstream recipes are extended, not copied", "A copy must be merged by hand at every update; an append follows upstream automatically.",
          "Delete the copy and put your changes in <recipe>_%.bbappend (Studio → Recipe append).", f"{LAYERS_DOC}#following-best-practices-when-creating-layers", "warning"), check_no_copied_recipe),
    (Rule("bbappend-matches", "Appends", "Every .bbappend has its recipe", "BitBake stops parsing on an append without a recipe.",
          "Rename it to the recipe name with a % version wildcard, or remove it.", f"{LAYERS_DOC}#appending-other-layers-metadata-with-your-layer", "error"), check_bbappend_matches),
    (Rule("filesextrapaths", "Appends", "FILESEXTRAPATHS:prepend := \"${THISDIR}/…:\"", "With := and the trailing colon your files are searched first and the path list stays valid.",
          'Write FILESEXTRAPATHS:prepend := "${THISDIR}/files:" and never assign THISDIR.', f"{LAYERS_DOC}#prioritizing-your-layer", "warning"), check_filesextrapaths),
    (Rule("override-syntax", "Appends", "Overrides use the colon syntax", "_append, _prepend and _remove are the pre-3.4 syntax; current BitBake rejects them.",
          "Replace VAR_append with VAR:append (and do_task_append with do_task:append).", f"{LAYERS_DOC}#appending-other-layers-metadata-with-your-layer", "error"), check_override_syntax),
    (Rule("no-image-append", "Appends", "Product images are your own recipes", "Appending core-image-* ties your product to a reference image that changes between releases.",
          "Create your own image recipe (Studio → Image), starting from core-image if you like.", WISH_DOC, "warning"), check_no_image_append),
    (Rule("recipe-naming", "Recipes", "Recipes are named name_version.bb in lowercase", "Tools derive PN and PV from the file name.",
          "Rename to lowercase <name>_<version>.bb; avoid the -native, -cross, -initial and -dev suffixes.", f"{RECIPE_DOC}#storing-and-naming-the-recipe", "info"), check_recipe_naming),
    (Rule("recipe-license", "Recipes", "Recipes declare LICENSE and LIC_FILES_CHKSUM", "The checksum catches licence changes upstream; the SBOM and licence manifests depend on it.",
          "Add LICENSE and LIC_FILES_CHKSUM = \"file://<licence file>;md5=…\" (devtool add fills them in).", f"{RECIPE_DOC}#licensing", "error"), check_recipe_license),
    (Rule("src-checksums", "Recipes", "Downloads have sha256 checksums", "BitBake verifies what it downloaded; md5 is deprecated.",
          "Add SRC_URI[sha256sum] = \"…\" (the first failed fetch prints it).", f"{RECIPE_DOC}#fetching-code", "error"), check_src_checksums),
    (Rule("srcrev-pinned", "Recipes", "Git sources are pinned to a commit", "AUTOREV or a missing SRCREV makes two builds of the same release differ.",
          "Set SRCREV to the full commit hash; use devtool upgrade to move it.", f"{RECIPE_DOC}#fetching-code", "error"), check_srcrev_pinned),
    (Rule("patch-upstream-status", "Recipes", "Patches say their Upstream-Status", "Reviewers and updates need to know whether a patch was submitted, accepted or is local.",
          "Add an Upstream-Status: line (Pending, Submitted, Backport, Inappropriate [reason]…) to each patch header.", f"{LAYERS_DOC}#yocto-check-layer-script", "warning"), check_patch_status),
    (Rule("no-debug-access", "Security", "No development access features in the product", "debug-tweaks, empty root passwords and root login are for bench boards; shipped devices must not have them.",
          "Keep them in local.conf of developer builds only, never in your distro, image or kas product files.", SECURITY_DOC, "warning"), check_access_features),
    (Rule("shared-caches", "Configuration", "Downloads and sstate are shared outside the build directory", "A new build directory then reuses sources and build results instead of starting over.",
          'Set DL_DIR and SSTATE_DIR to shared folders (site.conf, or the kas environment), e.g. DL_DIR = "${HOME}/yocto/downloads".', WISH_DOC, "info"), check_shared_caches),
    (Rule("own-distro", "Configuration", "The product has its own distribution", "Poky is a reference distribution for trying Yocto; a product needs its own name, version and policies.",
          "Create one with Studio → Distribution and select it with DISTRO.", WISH_DOC, "info"), check_own_distro),
    (Rule("product-config-in-layers", "Configuration", "Product configuration lives in layers, not local.conf", "local.conf is per developer and not versioned with the product.",
          "Move image contents to your image recipe and policies to your distro.", WISH_DOC, "warning"), check_product_config_in_local),
    (Rule("buildhistory", "Configuration", "Build history is recorded", "It shows what changed in images and packages between builds: reviews, regressions, releases.",
          'INHERIT += "buildhistory" and BUILDHISTORY_COMMIT = "1".', f"{DOCS}/dev-manual/build-quality.html", "info"), check_buildhistory),
    (Rule("rm-work", "Configuration", "rm_work keeps tmp/work small", "Work directories of finished recipes take most of the disk.",
          'INHERIT += "rm_work" (keep RM_WORK_EXCLUDE for the recipes you debug).', f"{DOCS}/dev-manual/disk-space.html", "info"), check_rm_work),
]


# --- configuration: disabled rules, severities and company rules ----------------------------------------

def config_path(profile: Profile) -> Path:
    return profile.root_path / CONFIG


def load_config(profile: Profile) -> dict:
    path = config_path(profile)
    if not path.is_file():
        return {"disabled": [], "severity": {}, "rules": []}
    try:
        data = json.loads(path.read_text())
    except ValueError as exc:
        raise ValueError(f"{CONFIG}: not valid JSON ({exc})") from exc
    data.setdefault("disabled", []); data.setdefault("severity", {}); data.setdefault("rules", [])
    validate(data)
    return data


CHECK_TYPES = {
    "files-must-match": ("files", "pattern"),
    "files-must-not-match": ("files", "pattern"),
    "layer-file-exists": ("path",),
    "variable": ("name", "op"),
}
VARIABLE_OPS = ("set", "unset", "equals", "contains", "not-contains")


def validate(data: dict) -> None:
    if not isinstance(data.get("disabled"), list) or not all(isinstance(i, str) for i in data["disabled"]):
        raise ValueError("disabled must be a list of rule ids")
    if not isinstance(data.get("severity"), dict) or any(v not in SEVERITIES for v in data["severity"].values()):
        raise ValueError(f"severity values must be one of {', '.join(SEVERITIES)}")
    builtin = {rule.id for rule, _ in BUILTIN}
    ids = set()
    for rule in data.get("rules", []):
        if not isinstance(rule, dict) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", str(rule.get("id", ""))):
            raise ValueError("each rule needs an id of lowercase letters, digits and hyphens")
        if rule["id"] in builtin or rule["id"] in ids:
            raise ValueError(f"rule id {rule['id']} is already used")
        ids.add(rule["id"])
        if not str(rule.get("title", "")).strip():
            raise ValueError(f"rule {rule['id']}: a title is required")
        if rule.get("severity", "warning") not in SEVERITIES:
            raise ValueError(f"rule {rule['id']}: severity must be one of {', '.join(SEVERITIES)}")
        spec = rule.get("check")
        if not isinstance(spec, dict) or spec.get("type") not in CHECK_TYPES:
            raise ValueError(f"rule {rule['id']}: check.type must be one of {', '.join(CHECK_TYPES)}")
        for key in CHECK_TYPES[spec["type"]]:
            if not str(spec.get(key, "")).strip():
                raise ValueError(f"rule {rule['id']}: check.{key} is required")
        if "pattern" in spec:
            try:
                re.compile(spec["pattern"], re.M)
            except re.error as exc:
                raise ValueError(f"rule {rule['id']}: pattern is not a valid regular expression ({exc})") from exc
        if spec["type"] == "variable" and spec["op"] not in VARIABLE_OPS:
            raise ValueError(f"rule {rule['id']}: check.op must be one of {', '.join(VARIABLE_OPS)}")
        if spec["type"] == "layer-file-exists" and (".." in Path(spec["path"]).parts or Path(spec["path"]).is_absolute()):
            raise ValueError(f"rule {rule['id']}: path must stay inside the layer")


def save_config(profile: Profile, data: dict) -> None:
    validate(data)
    path = config_path(profile)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def _fold_overrides(assignments: dict) -> dict:
    """DISTRO_FEATURES:append = " x" counts as part of DISTRO_FEATURES (unconditional :append, :prepend, :remove only)."""
    values = {k: v for k, v in assignments.items() if ":" not in k}
    for key, value in assignments.items():
        name, _, operation = key.rpartition(":")
        if operation == "append":
            values[name] = (values.get(name, "") + value).strip()
        elif operation == "prepend":
            values[name] = (value + values.get(name, "")).strip()
        elif operation == "remove" and name in values:
            values[name] = " ".join(w for w in values.get(name, "").split() if w not in value.split())
    return values


def custom_check(spec: dict):
    kind = spec["type"]

    def run(ctx):
        found = []
        if kind in ("files-must-match", "files-must-not-match"):
            pattern = re.compile(spec["pattern"], re.M)
            files = [(layer, path) for layer, path in ctx.files({".bb", ".bbappend", ".inc", ".bbclass", ".conf", ".patch", ".py", ".sh"})
                     if fnmatch.fnmatch(path.name, spec["files"])] + \
                    [(layer, path) for layer in ctx.mine for path in sorted(layer.rglob(spec["files"])) if path.is_file() and path.suffix not in {".bb", ".bbappend", ".inc", ".bbclass", ".conf", ".patch", ".py", ".sh"}]
            if not files:
                return None
            for _, path in files:
                text = ctx.text(path)
                if kind == "files-must-match" and not pattern.search(text):
                    found.append(Finding(ctx.rel(path), f"does not contain /{spec['pattern']}/"))
                elif kind == "files-must-not-match":
                    for number, line in enumerate(text.splitlines(), 1):
                        if pattern.search(line):
                            found.append(Finding(f"{ctx.rel(path)}:{number}", line.strip()[:90]))
            return found
        if kind == "layer-file-exists":
            if not ctx.mine:
                return None
            return [Finding(layer.name, f"no {spec['path']}") for layer in ctx.mine if not (layer / spec["path"]).exists()]
        # variable: in local.conf, auto.conf, your distro configurations and kas files
        values = {}
        for path in _config_files(ctx):
            if path.suffix == ".conf":
                for key, value in _fold_overrides(read_assignments(path)).items():
                    values.setdefault(key, []).append((path.name, value))
        if spec["name"] in ("DISTRO", "MACHINE"):
            # What the build selects, not the distro or machine file that names itself.
            chosen = getattr(ctx.profile, spec["name"].lower(), "") or ""
            values[spec["name"]] = [("profile", chosen)] if chosen else \
                [(where, value) for where, value in values.get(spec["name"], []) if where in ("local.conf", "auto.conf")]
        present = values.get(spec["name"], [])
        op, wanted = spec["op"], str(spec.get("value", ""))
        if op == "set" and not present:
            return [Finding(spec["name"], "not set in local.conf, auto.conf or your distro")]
        if op == "unset":
            return [Finding(f"{where}", f"{spec['name']} = “{value}”") for where, value in present]
        if op == "equals" and not any(value == wanted for _, value in present):
            return [Finding(spec["name"], f"is “{present[0][1]}”, expected “{wanted}”" if present else f"not set, expected “{wanted}”")]
        if op == "contains" and not any(wanted in value.split() for _, value in present):
            return [Finding(spec["name"], f"does not contain “{wanted}”")]
        if op == "not-contains":
            return [Finding(where, f"{spec['name']} contains “{wanted}”") for where, value in present if wanted in value.split()]
        return []
    return run


# --- the review ---------------------------------------------------------------------------------------------

def rules(profile: Profile) -> list[tuple[Rule, object]]:
    config = load_config(profile)
    result = []
    for rule, check in BUILTIN:
        rule = Rule(**{**rule.__dict__})
        rule.severity = config["severity"].get(rule.id, rule.severity)
        result.append((rule, check))
    for spec in config["rules"]:
        rule = Rule(spec["id"], spec.get("category", "Company"), spec["title"], spec.get("why", ""), spec.get("fix", ""),
                    spec.get("source", ""), config["severity"].get(spec["id"], spec.get("severity", "warning")), True, spec["check"])
        result.append((rule, custom_check(spec["check"])))
    return result


def _context(profile: Profile, entries=None, series: str | None = None) -> Context:
    from .inspectors import metadata, organize
    from .studio import product_layers
    from .versions import detect_release
    entries = organize(list(entries if entries is not None else metadata(profile)))
    mine = product_layers(entries, profile)
    upstream = sorted({e.path for e in entries if e.kind == "layer"} - set(mine))
    return Context(profile, series or detect_release(profile), entries, mine, upstream)


def try_rule(profile: Profile, spec: dict, entries=None) -> dict:
    """Run one company rule on the project without saving it: what it would report."""
    validate({"disabled": [], "severity": {}, "rules": [spec]})
    ctx = _context(profile, entries)
    findings = custom_check(spec["check"])(ctx)
    return {"status": "n/a" if findings is None else "pass" if not findings else "fail",
            "findings": [{"where": f.where, "detail": f.detail} for f in (findings or [])][:50],
            "total": len(findings or []), "layers": [p.name for p in ctx.mine]}


def review(profile: Profile, entries=None, series: str | None = None) -> dict:
    """Every rule with its result: followed, not followed (with where), not applicable, or switched off."""
    ctx = _context(profile, entries, series)
    series, mine = ctx.series, ctx.mine
    config = load_config(profile)
    rows = []
    for rule, check in rules(profile):
        row = {"id": rule.id, "category": rule.category, "title": rule.title, "why": rule.why, "fix": rule.fix, "source": rule.source,
               "severity": rule.severity, "custom": rule.custom, "check": rule.check_spec, "enabled": rule.id not in config["disabled"]}
        if not row["enabled"]:
            row.update(status="off", findings=[])
        else:
            try:
                findings = check(ctx)
            except (OSError, ValueError, re.error) as exc:
                findings = [Finding("check", f"could not run: {exc}")]
            row.update(status="n/a" if findings is None else "pass" if not findings else "fail",
                       findings=[{"where": f.where, "detail": f.detail} for f in (findings or [])][:200])
        rows.append(row)
    applicable = [r for r in rows if r["status"] in {"pass", "fail"}]
    return {"rules": rows, "config": str(config_path(profile)), "config_exists": config_path(profile).is_file(),
            "layers": [p.name for p in mine], "series": series,
            "score": round(100 * sum(r["status"] == "pass" for r in applicable) / len(applicable)) if applicable else None,
            "errors": sum(r["status"] == "fail" and r["severity"] == "error" for r in rows),
            "warnings": sum(r["status"] == "fail" and r["severity"] == "warning" for r in rows),
            "infos": sum(r["status"] == "fail" and r["severity"] == "info" for r in rows)}


def _n(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def report(data: dict, fmt: str = "text") -> str:
    if fmt == "json":
        return json.dumps(data, indent=2)
    md = fmt == "md"
    lines = [("# " if md else "") + f"Yocto best practices · {data['score'] if data['score'] is not None else '—'}% followed",
             "", f"{_n(data['errors'], 'error')} · {_n(data['warnings'], 'warning')} · {_n(data['infos'], 'suggestion')} · your layers: {', '.join(data['layers']) or 'none'}"]
    mark = {"pass": "✔", "fail": "✖", "n/a": "–", "off": "○"}
    category = None
    for row in sorted(data["rules"], key=lambda r: (r["category"], {"fail": 0, "pass": 1, "n/a": 2, "off": 3}[r["status"]])):
        if row["category"] != category:
            category = row["category"]
            lines += ["", ("## " if md else "") + category.upper() if not md else "## " + category, ""]
        lines.append(f"{'- ' if md else ''}{mark[row['status']]} {row['title']}" + (f"  [{row['severity']}]" if row["status"] == "fail" else "") + (" (off)" if row["status"] == "off" else ""))
        if row["status"] == "fail":
            for finding in row["findings"][:12]:
                lines.append(f"{'  - ' if md else '    '}{finding['where']}" + (f": {finding['detail']}" if finding["detail"] else ""))
            if len(row["findings"]) > 12:
                lines.append(f"{'  - ' if md else '    '}… {len(row['findings']) - 12} more")
            lines.append(f"{'  - ' if md else '    '}why: {row['why']}")
            lines.append(f"{'  - ' if md else '    '}fix: {row['fix']}" + (f" ({row['source']})" if row["source"] else ""))
    lines += ["", f"Rules: built-in plus {CONFIG} ({'found' if data['config_exists'] else 'not present'}) at {data['config']}."]
    return "\n".join(lines)
