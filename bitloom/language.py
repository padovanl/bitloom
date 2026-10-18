"""A BitBake language assistant built from the project itself: completion, documentation and diagnostics for
recipes, appends, classes, includes and configuration files.

The vocabulary comes from the layers the project builds with, so it matches its release: variable and task
documentation from OE-Core's conf/documentation.conf, classes, include files, recipes, machines, distros,
licences (common-licenses), image features (validitems) and tasks. Nothing is downloaded."""
from __future__ import annotations

import difflib
import re
import time
from pathlib import Path

KEYWORDS = {
    "inherit": "Use the classes listed after it (classes/, classes-recipe/, classes-global/).",
    "inherit_defer": "Like inherit, evaluated at the end of parsing (for class names built from variables).",
    "require": "Include another file; parsing fails when it is missing.",
    "include": "Include another file if it exists.",
    "include_all": "Include the file from every layer that has it.",
    "export": "Export the variable to the task environment.",
    "unset": "Remove a variable (or a variable flag) entirely.",
    "addtask": "Add a task: addtask name after do_x before do_y.",
    "deltask": "Remove a task.",
    "addhandler": "Register an event handler.",
    "EXPORT_FUNCTIONS": "Export class functions so recipes can override them.",
    "python": "A Python function: python do_mytask() { … }.",
    "fakeroot": "Run the shell or Python function under pseudo (as root).",
    "def": "A Python helper function usable in ${@…} expansions.",
}
OPERATORS = ("=", "?=", "??=", ":=", "+=", "=+", ".=", "=.")
BITBAKE_SUFFIXES = (".bb", ".bbappend", ".bbclass", ".inc", ".conf")
FLAGS = {
    "doc": "Documentation of the variable or task.", "depends": "Task dependencies on other recipes' tasks (recipe:do_task).",
    "rdepends": "Runtime task dependencies.", "deptask": "Run this task after the given task of every build dependency.",
    "rdeptask": "As deptask, for runtime dependencies.", "recrdeptask": "Recursive runtime task dependency.",
    "noexec": "The task does nothing; it only orders others.", "nostamp": "Never consider the task done: it always runs.",
    "dirs": "Directories created before the task; the last is its working directory.", "cleandirs": "Directories emptied before the task.",
    "network": "Allow network access in this task (1).", "umask": "umask for the task.", "vardeps": "Extra variables in the task signature.",
    "vardepsexclude": "Variables left out of the task signature.", "vardepvalue": "Use this value for the signature.",
    "postfuncs": "Functions run after the task.", "prefuncs": "Functions run before the task.", "sha256sum": "Checksum of a download (SRC_URI[name.sha256sum]).",
    "md5sum": "Old checksum of a download; use sha256sum.", "number_threads": "Limit how many tasks of this kind run at once.",
    "file-checksums": "Files whose content is part of the task signature.", "lockfiles": "Files locked while the task runs.",
    "validitems": "Accepted values (IMAGE_FEATURES[validitems]).", "type": "Type of a variable (list, boolean…).",
}
OVERRIDE_OPS = {"append": "Add text at the end (no space added: start the value with a space).",
                "prepend": "Add text at the beginning (no space added: end the value with a space).",
                "remove": "Remove every occurrence of these words, after all other operations."}
OVERRIDES_FIXED = {"class-target": "Only when building for the target", "class-native": "Only for -native builds", "class-nativesdk": "Only for nativesdk builds",
                   "class-cross": "Only for cross tools", "libc-glibc": "With glibc", "libc-musl": "With musl", "virtclass-multilib": "In multilib variants"}
TASKS_DEFAULT = ("do_fetch", "do_unpack", "do_patch", "do_configure", "do_compile", "do_install", "do_package", "do_package_write_rpm",
                 "do_package_write_ipk", "do_package_write_deb", "do_populate_sysroot", "do_deploy", "do_image", "do_rootfs", "do_build")
VALUE_KINDS = {  # variable → what its words are
    "DEPENDS": "recipes", "RDEPENDS": "packages", "RRECOMMENDS": "packages", "RSUGGESTS": "packages", "RPROVIDES": "packages",
    "IMAGE_INSTALL": "packages", "CORE_IMAGE_EXTRA_INSTALL": "packages", "PACKAGE_INSTALL": "packages", "TOOLCHAIN_TARGET_TASK": "packages",
    "IMAGE_FEATURES": "image-features", "EXTRA_IMAGE_FEATURES": "image-features",
    "DISTRO_FEATURES": "distro-features", "MACHINE_FEATURES": "machine-features", "MACHINE": "machines", "DISTRO": "distros",
    "LICENSE": "licences", "INHERIT": "classes", "IMAGE_CLASSES": "classes", "PREFERRED_PROVIDER": "recipes",
}
DISTRO_FEATURES_COMMON = ("acl", "alsa", "api-documentation", "bluetooth", "cramfs", "debuginfod", "directfb", "ext2", "gobject-introspection-data",
                          "ipsec", "ipv4", "ipv6", "keyboard", "ld-is-gold", "ldconfig", "lto", "minidebuginfo", "multiarch", "nfc", "nfs",
                          "opengl", "overlayfs", "pam", "pci", "pcmcia", "polkit", "ppp", "ptest", "pulseaudio", "seccomp", "selinux", "smbfs",
                          "systemd", "sysvinit", "usbgadget", "usbhost", "usrmerge", "vfat", "vulkan", "wayland", "wifi", "x11", "xattr", "zeroconf")
MACHINE_FEATURES_COMMON = ("acpi", "alsa", "bluetooth", "efi", "ext2", "keyboard", "numa", "pci", "pcbios", "phone", "qemu-usermode", "rtc",
                           "screen", "serial", "touchscreen", "usbgadget", "usbhost", "vfat", "wifi")
ASSIGN = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_\-${}/.+]*)((?::[A-Za-z0-9_\-${}.+]+)*)(\[[A-Za-z0-9_\-.]+\])?\s*(\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)\s*(.*)$")
_cache: dict[str, tuple[float, dict]] = {}


def _layers(profile, entries) -> list[Path]:
    from .inspectors import metadata, organize
    entries = organize(list(entries if entries is not None else metadata(profile)))
    return sorted({e.path for e in entries if e.kind == "layer"}), entries


def _count_assignments(text: str, used: dict) -> None:
    for line in text.splitlines():
        m = ASSIGN.match(line)
        if m and "$" not in m[1]:
            used[m[1]] = used.get(m[1], 0) + 1


def vocabulary(profile, entries=None) -> dict:
    """Everything the assistant knows about this project, cached until a layer changes."""
    from .inspectors import recipe_name
    layers, entries = _layers(profile, entries)
    stamp = max((p.stat().st_mtime for p in layers if p.exists()), default=0)
    key = f"{profile.name}:{profile.root}"
    cached = _cache.get(key)
    if cached and cached[0] == stamp and time.monotonic() - cached[1].get("_at", 0) < 600:
        return cached[1]
    docs, tasks, classes, includes, machines, distros, licences, features = {}, set(TASKS_DEFAULT), {}, {}, {}, {}, set(), {}
    used: dict[str, int] = {}
    for layer in layers:
        doc = layer / "conf/documentation.conf"
        if doc.is_file():
            for line in doc.read_text(errors="replace").splitlines():
                m = re.match(r'^([A-Za-z0-9_\-]+)\[doc\]\s*=\s*"(.*)"\s*$', line)
                if m:
                    docs[m[1]] = m[2].replace('\\"', '"')
                    if m[1].startswith("do_"):
                        tasks.add(m[1])
        for sub in ("conf/machine", "conf/distro"):
            for conf in (layer / sub).glob("*.conf"):
                (machines if sub.endswith("machine") else distros).setdefault(conf.stem, layer.name)
        licence_dir = layer / "files/common-licenses"
        if licence_dir.is_dir():
            licences.update(p.name for p in licence_dir.iterdir())
        for inc in layer.rglob("*.inc"):
            relative = inc.relative_to(layer)
            if relative.parts[0] in ("conf", "classes", "classes-recipe", "classes-global") or relative.parts[0].startswith("recipes"):
                includes.setdefault(str(relative), layer.name)
                if relative.parts[0] == "conf":
                    _count_assignments(inc.read_text(errors="replace"), used)
        for conf in (layer / "conf").rglob("*.conf") if (layer / "conf").is_dir() else []:
            _count_assignments(conf.read_text(errors="replace"), used)
    for entry in entries:
        if entry.kind == "bbclass":
            name = entry.name.removesuffix(".bbclass")
            classes.setdefault(name, entry.layer)
            try:
                text = entry.path.read_text(errors="replace")
            except OSError:
                continue
            for m in re.finditer(r'^IMAGE_FEATURES\[validitems\]\s*\+?=\s*"([^"]*)"', text, re.M):
                for word in m[1].split():
                    features.setdefault(word, f"from {entry.name}")
            for m in re.finditer(r"^COMPLEMENTARY_GLOB\[([A-Za-z0-9-]+)\]", text, re.M):
                features.setdefault(m[1], f"complementary packages ({entry.name})")
            for m in re.finditer(r"^FEATURE_PACKAGES_([A-Za-z0-9-]+)\s*\??=", text, re.M):
                features.setdefault(m[1], f"FEATURE_PACKAGES in {entry.name}")
            for m in re.finditer(r"^(?:python\s+|fakeroot\s+)*(do_[a-z0-9_]+)\s*\(\)", text, re.M):
                tasks.add(m[1])
            for m in re.finditer(r"^addtask\s+([a-z0-9_]+)", text, re.M):
                tasks.add(m[1] if m[1].startswith("do_") else "do_" + m[1])
            _count_assignments(text, used)
    recipes = sorted({recipe_name(e)[0] for e in entries if e.kind == "bb"})
    data = {"docs": docs, "tasks": sorted(tasks), "classes": classes, "includes": includes, "machines": machines, "distros": distros,
            "licences": sorted(licences), "image_features": features, "recipes": recipes, "used": used, "layers": [p.name for p in layers],
            "layer_paths": [str(p) for p in layers], "_at": time.monotonic()}
    data["variables"] = sorted({v for v in docs if not v.startswith("do_")} | {v for v in used if re.fullmatch(r"[A-Z][A-Z0-9_]+", v)})
    _cache[key] = (stamp, data)
    return data


def _item(label, kind, doc="", insert=None):
    return {"label": label, "kind": kind, "doc": doc, "insert": insert if insert is not None else label}


def complete(vocab: dict, before: str, limit: int = 40) -> dict:
    """Suggestions for the text left of the cursor on its line: {"from": column where the word starts, "items": [...]}"""
    word = re.search(r"[A-Za-z0-9_\-./+]*$", before)[0]
    start = len(before) - len(word)
    lower = word.lower()

    def pick(items):
        exact = [i for i in items if i["label"].lower().startswith(lower)]
        fuzzy = [i for i in items if lower and lower in i["label"].lower() and i not in exact] if len(lower) >= 3 else []
        return {"from": start, "word": word, "items": (exact + fuzzy)[:limit]}
    stripped = before.lstrip()
    # ${VAR} expansion
    m = re.search(r"\$\{([A-Za-z0-9_]*)$", before)
    if m:
        return {"from": len(before) - len(m[1]), "word": m[1], "items": [i for i in (_item(v, "variable", vocab["docs"].get(v, "")) for v in vocab["variables"]) if i["label"].startswith(m[1])][:limit]}
    m = re.match(r"^\s*(inherit|inherit_defer)\s+(?:\S+\s+)*", before)
    if m:
        return pick([_item(c, "class", f"{c}.bbclass in layer {layer}") for c, layer in sorted(vocab["classes"].items())])
    m = re.match(r"^\s*(require|include|include_all)\s+", before)
    if m:
        return pick([_item(i, "file", f"layer {layer}") for i, layer in sorted(vocab["includes"].items())])
    m = re.match(r"^\s*addtask\s+\S+\s+(?:after|before)\s+(?:\S+\s+)*", before) or re.match(r"^\s*(?:deltask)\s+", before)
    if m:
        return pick([_item(t, "task", vocab["docs"].get(t, "")) for t in vocab["tasks"]])
    m = re.match(r"^\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_\-${}]*((?::[A-Za-z0-9_\-${}.+]+)*):([A-Za-z0-9_\-.+]*)$", before)
    if m and "=" not in before:
        items = [_item(op, "operation", doc) for op, doc in OVERRIDE_OPS.items()]
        items += [_item(o, "override", doc) for o, doc in OVERRIDES_FIXED.items()]
        items += [_item(mc, "machine", f"only when MACHINE is {mc}") for mc in sorted(vocab["machines"])]
        items += [_item(d, "distro", f"only when DISTRO is {d}") for d in sorted(vocab["distros"])]
        items += [_item("pn-" + r, "recipe", f"only for {r} (from configuration files)") for r in vocab["recipes"]] if word.startswith("pn-") else []
        items += [_item("task-" + t[3:], "task", f"only while {t} runs") for t in vocab["tasks"]] if word.startswith("task-") else []
        return {"from": len(before) - len(m[2]), "word": m[2], "items": [i for i in items if i["label"].startswith(m[2])][:limit]}
    m = re.match(r"^\s*[A-Za-z_][A-Za-z0-9_\-${}:]*\[([A-Za-z0-9_\-.]*)$", before)
    if m:
        return {"from": len(before) - len(m[1]), "word": m[1], "items": [_item(f, "flag", d) for f, d in FLAGS.items() if f.startswith(m[1])]}
    m = ASSIGN.match(before + ("" if before.rstrip().endswith('"') else ""))
    if m and '"' in m[5]:
        variable = m[1]
        kind = VALUE_KINDS.get(variable) or VALUE_KINDS.get(variable.split("_")[0]) or ("recipes" if variable.startswith("PREFERRED_PROVIDER") else "")
        if kind:
            source = {"recipes": [_item(r, "recipe") for r in vocab["recipes"]],
                      "packages": [_item(r, "recipe") for r in vocab["recipes"]],
                      "image-features": [_item(f, "feature", how) for f, how in sorted(vocab["image_features"].items())],
                      "distro-features": [_item(f, "feature") for f in DISTRO_FEATURES_COMMON],
                      "machine-features": [_item(f, "feature") for f in MACHINE_FEATURES_COMMON],
                      "machines": [_item(mc, "machine", f"layer {layer}") for mc, layer in sorted(vocab["machines"].items())],
                      "distros": [_item(d, "distro", f"layer {layer}") for d, layer in sorted(vocab["distros"].items())],
                      "licences": [_item(lic, "licence") for lic in vocab["licences"]] + [_item("CLOSED", "licence", "proprietary: no licence file needed")],
                      "classes": [_item(c, "class") for c in vocab["classes"]]}[kind]
            return pick(source)
        return {"from": start, "word": word, "items": []}
    if re.match(r"^\s*[A-Za-z0-9_\-]*$", before):
        items = [_item(k, "keyword", d, k + " ") for k, d in KEYWORDS.items()]
        items += [_item(v, "variable", vocab["docs"].get(v, "")) for v in vocab["variables"]]
        items += [_item(t, "task", vocab["docs"].get(t, ""), t + "() {\n    \n}") for t in vocab["tasks"]] if stripped.startswith("do_") else []
        seen = set()
        items = [i for i in items if not (i["label"] in seen or seen.add(i["label"]))]
        return pick(items)
    return {"from": start, "word": word, "items": []}


def explain(vocab: dict, word: str) -> dict:
    """What a word means here: a variable, task, class, keyword, machine, distro or flag."""
    word = word.strip().split(":")[0].split("[")[0]
    if word in vocab["docs"]:
        return {"word": word, "kind": "task" if word.startswith("do_") else "variable", "doc": vocab["docs"][word]}
    if word in KEYWORDS:
        return {"word": word, "kind": "keyword", "doc": KEYWORDS[word]}
    if word in vocab["classes"]:
        return {"word": word, "kind": "class", "doc": f"Class {word}.bbclass in layer {vocab['classes'][word]}"}
    if word in vocab["machines"]:
        return {"word": word, "kind": "machine", "doc": f"Machine defined in {vocab['machines'][word]}/conf/machine/{word}.conf"}
    if word in vocab["distros"]:
        return {"word": word, "kind": "distro", "doc": f"Distribution defined in {vocab['distros'][word]}/conf/distro/{word}.conf"}
    if word in FLAGS:
        return {"word": word, "kind": "flag", "doc": FLAGS[word]}
    if word in vocab["used"]:
        return {"word": word, "kind": "variable", "doc": f"Not documented in documentation.conf; set in {vocab['used'][word]} places of the project's classes."}
    close = difflib.get_close_matches(word, vocab["variables"], 3, 0.8)
    return {"word": word, "kind": "", "doc": "", "suggest": close}


def _one_edit(a: str, b: str) -> bool:
    """True when b is a with one letter changed, added or removed."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def lint(vocab: dict, text: str, filename: str = "") -> list[dict]:
    """Problems a BitBake parse would report, or that it silently accepts and that bite later."""
    problems = []
    add = lambda line, level, message, fix="": problems.append({"line": line, "level": level, "message": message, "fix": fix})
    known = set(vocab["variables"]) | set(vocab["used"])
    lines = text.splitlines()
    in_function = 0
    in_def = False
    continued = False
    for number, raw in enumerate(lines, 1):
        line = raw.rstrip()
        stripped = line.strip()
        if in_function:
            in_function += line.count("{") - line.count("}")
            continue
        if in_def:
            if not stripped or raw[:1] in (" ", "\t"):
                continue
            in_def = False
        if continued:
            continued = line.endswith("\\")
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if re.match(r"^def\s", stripped):
            in_def = True
            continue
        if re.match(r"^(python\s+|fakeroot\s+)*[A-Za-z0-9_\-${}:.]*\s*\(\)\s*\{", stripped):
            in_function = line.count("{") - line.count("}")
            continue
        m = re.match(r"^\s*(inherit|inherit_defer)\s+(.*)$", line)
        if m:
            for name in ([] if "${" in m[2] else m[2].split()):
                if "$" not in name and name not in vocab["classes"]:
                    close = difflib.get_close_matches(name, list(vocab["classes"]), 1, 0.75)
                    add(number, "error", f"class “{name}” is not in this project's layers", f"did you mean “{close[0]}”?" if close else "add the layer that provides it")
            continue
        m = re.match(r"^\s*(require)\s+(\S+)", line)
        if m and "$" not in m[2] and m[2] not in vocab["includes"] and not (Path(filename).parent / m[2]).is_file() and "/" in m[2] \
                and not any((Path(layer) / m[2]).is_file() for layer in vocab.get("layer_paths", [])):
            add(number, "warning", f"“{m[2]}” is not found in the layers (require fails at parse time)", "check the path: it is relative to a layer, or to this file's folder")
            continue
        if re.match(r"^\s*(include|include_all|export|unset|addtask|deltask|addhandler|EXPORT_FUNCTIONS)\b", line):
            continue
        m = ASSIGN.match(line)
        if not m:
            if re.match(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*$", line):
                add(number, "error", "a name without an assignment", "add = \"value\", or remove the line")
            continue
        name, overrides, flag, op, value = m[1], m[2], m[3], m[4], m[5].rstrip()
        continued = value.endswith("\\")
        old = re.match(r"^(.*?)_(append|prepend|remove)(_.*)?$", name)
        if old and old[1].isupper():
            add(number, "error", f"old override syntax “{name}”: BitBake 2.x rejects it", f"use {old[1]}:{old[2]}" + (old[3].replace("_", ":") if old[3] else ""))
        quoted = value.startswith(('"', "'"))
        if quoted and not continued and not (len(value) >= 2 and value.endswith(value[0])):
            add(number, "error", "the value's quotes are not closed", "end the value with the same quote it starts with")
        if not quoted and value and not value.startswith("${@"):
            add(number, "error", "the value must be in double quotes", f'{name}{overrides} {op} "{value}"')
        ops = overrides.split(":")
        inner = value[1:-1] if quoted else value
        if "append" in ops and inner and not inner.startswith((" ", "\\", "${")) and name in VALUE_KINDS | {"SRC_URI": 1, "DEPENDS": 1, "RDEPENDS": 1, "EXTRA_OECONF": 1, "EXTRA_OEMESON": 1, "EXTRA_OECMAKE": 1, "PACKAGECONFIG": 1}:
            add(number, "warning", f"“{name}:append” adds no space: “{inner.split()[0]}” sticks to the previous word", f'{name}:append = " {inner}"')
        if "prepend" in ops and inner and not inner.endswith(" ") and name not in ("FILESEXTRAPATHS",) and name in VALUE_KINDS:
            add(number, "warning", f"“{name}:prepend” adds no space after its words", f'{name}:prepend = "{inner} "')
        if op in ("+=", "=+") and any(o in ("append", "prepend", "remove") for o in ops):
            add(number, "warning", f"“{op}” together with :{next(o for o in ops if o in ('append', 'prepend', 'remove'))}", "use one of them: :append with =, or += alone")
        if name == "FILESEXTRAPATHS":
            if "prepend" in ops and op in ("=", "+="):
                add(number, "warning", "FILESEXTRAPATHS must be expanded at once (:=)", 'FILESEXTRAPATHS:prepend := "${THISDIR}/files:"')
            if inner and not inner.endswith(":"):
                add(number, "error", "FILESEXTRAPATHS without the trailing “:” breaks the search path", 'FILESEXTRAPATHS:prepend := "${THISDIR}/files:"')
        if name == "SRC_URI" and flag and flag[1:-1].endswith("md5sum"):
            add(number, "info", "md5sum checksums are deprecated", "use sha256sum")
        base = name.split("$")[0]
        # A name nobody else uses that is one or two letters away from a known one is almost always a typo;
        # new variables of your own (MY_APP_PORT) have no close match and are left alone.
        if not flag and re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", name) and name not in known and not re.match(r"(FEATURE_PACKAGES|LAYER\w+|BBFILE_\w+|SRCREV)_", name):
            close = [] if "${" + name + "}" in text else \
                [c for c in difflib.get_close_matches(name, vocab["variables"], 3, 0.85) if len(name) >= 6 and _one_edit(name, c)]
            if close:
                add(number, "info", f"“{name}” is not a variable BitBake uses here: a typo?", f"did you mean “{close[0]}”?")
        if base == "MACHINE" and inner and inner not in vocab["machines"] and "$" not in inner and vocab["machines"]:
            add(number, "warning", f"no machine “{inner}” in the project's layers", ", ".join(difflib.get_close_matches(inner, list(vocab["machines"]), 3, 0.5)) or "add its BSP layer")
        if base == "DISTRO" and inner and inner not in vocab["distros"] and "$" not in inner and vocab["distros"]:
            add(number, "warning", f"no distribution “{inner}” in the project's layers", ", ".join(difflib.get_close_matches(inner, list(vocab["distros"]), 3, 0.5)) or "create it with Studio → Distribution")
        if base in ("IMAGE_FEATURES", "EXTRA_IMAGE_FEATURES") and vocab["image_features"]:
            for word in inner.split():
                if "$" not in word and word not in vocab["image_features"]:
                    close = difflib.get_close_matches(word, list(vocab["image_features"]), 1, 0.7)
                    add(number, "warning", f"“{word}” is not an image feature of this release", f"did you mean “{close[0]}”?" if close else "see IMAGE_FEATURES[validitems] and FEATURE_PACKAGES_*")
    if in_function > 0:
        add(len(lines), "error", "a function's { is never closed", "add the closing }")
    return problems
