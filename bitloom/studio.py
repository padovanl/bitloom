"""Studio: create a product layer, your own distribution, machines, images and
recipes from explained, release-aware forms. Files are written into the project
checkout (never overwriting) and registered through bitbake-layers or a kas overlay."""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .models import Profile
from .versions import ORDER

UPSTREAM = {"meta", "meta-poky", "meta-yocto-bsp", "meta-selftest", "meta-skeleton", "meta-yocto"}
NAME = re.compile(r"[a-z][a-z0-9-]*")


@dataclass(frozen=True)
class Field:
    id: str
    label: str
    kind: str = "text"            # text | choice | multi | bool
    default: str = ""
    choices: tuple[str, ...] = ()
    info: str = ""
    required: bool = False


KINDS = {
    "layer": ("Product layer", "A layer for your company's metadata: distro, machines, images and recipes live here."),
    "distro": ("Distribution", "Your own DISTRO instead of poky: identity, init system, features, hardening and SBOM policy."),
    "machine": ("Machine", "A MACHINE derived from a reference board, with your features and console settings."),
    "image": ("Image recipe", "A product image: base packages, developer access, extra packages and filesystem types."),
    "recipe": ("Application recipe", "A licensed sample application built with CMake, Meson, Make, Python or Rust."),
    "append": ("Recipe append", "A .bbappend that adds your files or configuration to an existing recipe."),
}
DISTRO_FEATURES = ("systemd", "usrmerge", "pam", "seccomp", "ipv6", "wifi", "bluetooth", "x11", "wayland", "opengl", "vulkan",
                   "polkit", "zeroconf", "nfs", "ptest", "sota")
MACHINE_FEATURES = ("serial", "usbhost", "usbgadget", "wifi", "bluetooth", "screen", "keyboard", "pci", "rtc", "efi", "vfat", "ext2", "alsa")
BASE_MACHINES = ("qemux86-64", "qemuarm64", "qemuarm", "qemuriscv64", "genericx86-64", "beaglebone-yocto")


def newer(series, than):
    return series in ORDER and ORDER[series] >= ORDER[than]


def product_layers(entries, profile: Profile) -> list[Path]:
    """Writable product layers: everything except upstream layers and fetched repositories."""
    result = []
    for entry in entries or []:
        if entry.kind != "layer" or entry.name in UPSTREAM:
            continue
        parts = set(entry.path.parts)
        if parts & {"poky", "openembedded-core", "bitbake", "meta-openembedded"}:
            continue
        result.append(entry.path)
    return sorted(set(result))


def fields(kind: str, series: str | None, layers: list[Path]) -> list[Field]:
    layer_choices = tuple(str(p) for p in layers) + ("new layer…",)
    target = Field("layer", "Target layer", "choice", layer_choices[0], layer_choices,
                   "Where the files go. Upstream layers are never modified; choose 'new layer…' to create one.")
    new_layer = Field("new_layer", "New layer name", "text", "meta-acme", info="Directory created under the project root, e.g. meta-acme.")
    if kind == "layer":
        return [Field("name", "Layer name", "text", "meta-acme", info="meta-<company or product>; becomes the directory name.", required=True),
                Field("collection", "Collection", "text", "acme", info="BBFILE_COLLECTIONS identifier used by LAYERDEPENDS of other layers.", required=True),
                Field("priority", "Priority", "choice", "7", ("5", "6", "7", "8", "9", "10"), "BBFILE_PRIORITY: higher wins when two layers provide the same recipe."),
                Field("depends", "Depends on", "multi", "core", ("core", "yocto", "yoctobsp", "openembedded-layer", "networking-layer"),
                      "LAYERDEPENDS: collections that must be present (core = OE-Core, yocto = meta-poky)."),
                Field("license", "Layer licence", "choice", "MIT", ("MIT", "Apache-2.0", "proprietary"), "Licence of your metadata (not of the software it builds)."),
                Field("owner", "Copyright owner", "text", "Acme Corp", required=True)]
    if kind == "distro":
        modern = newer(series, "wrynose")
        return [target, new_layer,
                Field("name", "DISTRO id", "text", "acme", info="Lowercase id used as DISTRO = \"…\" and conf/distro/<id>.conf.", required=True),
                Field("title", "DISTRO_NAME", "text", "Acme Linux", required=True),
                Field("version", "DISTRO_VERSION", "text", "1.0.0", info="Shown in /etc/os-release; bump it for every product release.", required=True),
                Field("base", "Based on", "choice", "poky", ("poky", "oe-core defaults"),
                      "poky: inherit Poky's policy and only change what differs (needs meta-poky). oe-core defaults: a standalone distro without meta-poky."),
                Field("init", "Init manager", "choice", "systemd" if modern else "sysvinit", ("systemd", "sysvinit", "mdev-busybox"),
                      "INIT_MANAGER selects the init system and its DISTRO_FEATURES. Wrynose defaults to systemd."),
                Field("features", "Add DISTRO_FEATURES", "multi", "ipv6 seccomp", DISTRO_FEATURES, "Features added to the base set."),
                Field("remove", "Remove DISTRO_FEATURES", "multi", "", DISTRO_FEATURES + ("3g", "nfc", "pcmcia", "zeroconf"), "Features your product must not carry."),
                Field("packages", "Package format", "choice", "package_ipk", ("package_ipk", "package_rpm", "package_deb"), "PACKAGE_CLASSES default for this distro."),
                Field("hardening", "Security flags", "bool", "1", info="Includes conf/distro/include/security_flags.inc (stack protector, FORTIFY, PIE)."),
                Field("sbom", "SBOM policy", "bool", "1", info="INHERIT create-spdx and supplier fields (SPDX 3 releases) for CRA-ready SBOMs."),
                Field("supplier", "Supplier for SBOMs", "text", "Acme Corp", info="SPDX_PACKAGE_SUPPLIER / SPDX_IMAGE_SUPPLIER on releases with SPDX 3."),
                Field("maintainer", "MAINTAINER", "text", "Acme Linux team <linux@acme.example>")]
    if kind == "machine":
        return [target, new_layer,
                Field("name", "MACHINE id", "text", "acme-board", info="conf/machine/<id>.conf; used as MACHINE = \"…\".", required=True),
                Field("title", "Description", "text", "Acme board (derived from the reference machine)"),
                Field("base", "Derived from", "choice", "qemux86-64", BASE_MACHINES, "Reference machine whose configuration is required; its overrides keep applying."),
                Field("features", "Add MACHINE_FEATURES", "multi", "serial usbhost", MACHINE_FEATURES),
                Field("console", "Serial console", "text", "115200;ttyS0", info="SERIAL_CONSOLES entries: baud;device, space separated."),
                Field("kernel", "Preferred kernel", "choice", "linux-yocto", ("linux-yocto", "linux-yocto-rt", "linux-yocto-tiny"), "PREFERRED_PROVIDER_virtual/kernel.")]
    if kind == "image":
        access = ("allow-empty-password", "empty-root-password", "allow-root-login") if newer(series, "styhead") else ("debug-tweaks",)
        return [target, new_layer,
                Field("name", "Image name", "text", "acme-image", info="recipes-core/images/<name>.bb; build it with bitbake <name>.", required=True),
                Field("summary", "Summary", "text", "Acme product image"),
                Field("base", "Starting point", "choice", "core-image", ("core-image", "core-image-minimal", "core-image-base"),
                      "core-image: an empty class-based image; or require an existing image and extend it."),
                Field("features", "IMAGE_FEATURES", "multi", "ssh-server-dropbear", ("ssh-server-dropbear", "ssh-server-openssh", "package-management",
                      "tools-debug", "tools-profile", "dev-pkgs", "read-only-rootfs", "splash", "hwcodecs") + access,
                      "Developer access features changed in 5.1: debug-tweaks was split into allow-empty-password, empty-root-password and allow-root-login."),
                Field("packages", "IMAGE_INSTALL additions", "text", "htop", info="Space-separated packages or packagegroups."),
                Field("fstypes", "IMAGE_FSTYPES", "multi", "ext4 tar.bz2", ("ext4", "tar.bz2", "tar.zst", "wic", "wic.zst", "squashfs", "cpio.gz")),
                Field("size", "Extra free space (KiB)", "text", "", info="IMAGE_ROOTFS_EXTRA_SPACE; empty keeps the default.")]
    if kind == "recipe":
        return [target, new_layer,
                Field("name", "Recipe name", "text", "acme-hello", info="Lowercase name; creates recipes-example/<name>/<name>_1.0.bb.", required=True),
                Field("system", "Build system", "choice", "cmake", ("cmake", "meson", "make", "python", "rust")),
                Field("owner", "Copyright owner", "text", "Acme Corp", required=True)]
    if kind == "append":
        return [target, new_layer,
                Field("recipe", "Recipe to extend", "text", "base-files", info="Recipe name (PN); the append matches every version (_%.bbappend).", required=True),
                Field("category", "Category directory", "text", "recipes-core", info="recipes-* directory mirroring the original recipe."),
                Field("file", "Add a file", "text", "motd", info="Created under files/ and installed into /etc by the append; empty for configuration only."),
                Field("config", "Extra lines", "text", "", info="Optional assignments, e.g. PACKAGECONFIG:append = \" foo\"")]
    raise ValueError("Unknown kind")


def _mit(owner):
    year = datetime.now(timezone.utc).year
    return (f"Copyright (c) {year} {owner}\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software "
            "and associated documentation files, to deal in the Software without restriction, subject to the following conditions: "
            "the above copyright notice and this permission notice shall be included in all copies or substantial portions of the "
            "Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND.\n")


def layer_files(name, collection, priority, depends, series, owner, licence="MIT"):
    files = {"conf/layer.conf": (
        'BBPATH .= ":${LAYERDIR}"\nBBFILES += "${LAYERDIR}/recipes-*/*/*.bb ${LAYERDIR}/recipes-*/*/*.bbappend"\n\n'
        f'BBFILE_COLLECTIONS += "{collection}"\nBBFILE_PATTERN_{collection} = "^${{LAYERDIR}}/"\nBBFILE_PRIORITY_{collection} = "{priority}"\n'
        f'LAYERDEPENDS_{collection} = "{depends}"\nLAYERSERIES_COMPAT_{collection} = "{series}"\n'),
        "README.md": f"# {name}\n\nProduct layer created with Bitloom Studio.\n\nDepends on: {depends}\n\nCompatible with: {series}\n"}
    if licence == "MIT":
        files["COPYING.MIT"] = _mit(owner)
    return files


def _check(name, label):
    if not NAME.fullmatch(name or ""):
        raise ValueError(f"{label} must be lowercase letters, digits and hyphens, starting with a letter")


def plan(kind: str, values: dict, profile: Profile, series: str | None) -> dict:
    """Files to create, where, and how to activate them. Pure: nothing is written."""
    values = {k: (v.strip() if isinstance(v, str) else v) for k, v in values.items()}
    compat = series or values.get("series") or "scarthgap"
    notes, activate = [], {}
    if kind == "layer":
        _check(values.get("name"), "Layer name")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", values.get("collection", "")):
            raise ValueError("Collection must contain letters, digits, underscores or hyphens")
        root = profile.root_path / values["name"]
        files = layer_files(values["name"], values["collection"], values.get("priority", "7"), values.get("depends", "core") or "core",
                            compat, values.get("owner") or "Unknown", values.get("license", "MIT"))
        return {"kind": kind, "layer": str(root), "new_layer": True, "files": files, "activate": activate,
                "notes": [f"LAYERSERIES_COMPAT = {compat} (detected release)" if series else "Release not detected: set LAYERSERIES_COMPAT to your release."]}
    choice = values.get("layer", "")
    if not choice or choice.startswith("new layer"):
        _check(values.get("new_layer"), "New layer name")
        root, new = profile.root_path / values["new_layer"], True
    else:
        root, new = Path(choice), False
    files = {}
    if new:
        collection = re.sub(r"^meta-", "", values["new_layer"]).replace("-", "_")
        files.update(layer_files(values["new_layer"], collection, "7", "core yocto" if values.get("base") == "poky" else "core",
                                 compat, values.get("owner") or values.get("maintainer") or "Unknown"))
    if kind == "distro":
        _check(values.get("name"), "DISTRO id")
        lines = [f"# {values.get('title') or values['name']}: created with Bitloom Studio", ""]
        if values.get("base", "poky") == "poky":
            lines += ["require conf/distro/poky.conf", ""]
            notes.append("Requires meta-poky (collection 'yocto') in bblayers.")
        else:
            lines += ["require conf/distro/include/no-static-libs.inc", "require conf/distro/include/yocto-uninative.inc", "INHERIT += \"uninative\"", ""]
        lines += [f'DISTRO = "{values["name"]}"', f'DISTRO_NAME = "{values.get("title") or values["name"]}"',
                  f'DISTRO_VERSION = "{values.get("version") or "1.0"}"', f'DISTRO_CODENAME = "{compat}"',
                  f'MAINTAINER = "{values.get("maintainer") or "unknown"}"', f'TARGET_VENDOR = "-{values["name"]}"',
                  f'SDK_VENDOR = "-{values["name"]}sdk"', f'SDK_NAME = "${{DISTRO}}-${{TCLIBC}}-${{SDKMACHINE}}-${{IMAGE_BASENAME}}-${{TUNE_PKGARCH}}-${{MACHINE}}"', "",
                  f'INIT_MANAGER = "{values.get("init") or "systemd"}"', f'PACKAGE_CLASSES ?= "{values.get("packages") or "package_ipk"}"']
        if values.get("features"):
            lines.append(f'DISTRO_FEATURES:append = " {values["features"]}"')
        if values.get("remove"):
            lines.append(f'DISTRO_FEATURES:remove = "{values["remove"]}"')
        if values.get("hardening") in {"1", True, "true"}:
            lines += ["", "require conf/distro/include/security_flags.inc"]
        if values.get("sbom") in {"1", True, "true"}:
            lines += ["", "# SBOM policy (EU CRA): machine-readable SPDX for every image", 'INHERIT += "create-spdx"']
            supplier = (values.get("supplier") or "").replace('"', "'")
            if supplier and newer(series, "styhead"):
                lines += [f'SPDX_PACKAGE_SUPPLIER_name = "{supplier}"', 'SPDX_PACKAGE_SUPPLIER_type = "organization"',
                          f'SPDX_IMAGE_SUPPLIER_name = "{supplier}"', 'SPDX_IMAGE_SUPPLIER_type = "organization"']
            elif supplier:
                # SPDX 2.2 releases: replace the 'Organization: OpenEmbedded ()' placeholder.
                lines.append(f'SPDX_SUPPLIER = "Organization: {supplier}"')
        files[f"conf/distro/{values['name']}.conf"] = "\n".join(lines) + "\n"
        activate["distro"] = values["name"]
    elif kind == "machine":
        _check(values.get("name"), "MACHINE id")
        base = values.get("base") or "qemux86-64"
        lines = ["#@TYPE: Machine", f"#@NAME: {values.get('title') or values['name']}", f"#@DESCRIPTION: Derived from {base} with Bitloom Studio", "",
                 f"require conf/machine/{base}.conf", f'MACHINEOVERRIDES =. "{base}:"', ""]
        if values.get("features"):
            lines.append(f'MACHINE_FEATURES:append = " {values["features"]}"')
        if values.get("console"):
            lines.append(f'SERIAL_CONSOLES = "{values["console"]}"')
        if values.get("kernel"):
            lines.append(f'PREFERRED_PROVIDER_virtual/kernel ?= "{values["kernel"]}"')
        if base == "genericx86-64" or base == "beaglebone-yocto":
            notes.append(f"{base} lives in meta-yocto-bsp; keep that layer in bblayers.")
        files[f"conf/machine/{values['name']}.conf"] = "\n".join(lines) + "\n"
        activate["machine"] = values["name"]
    elif kind == "image":
        _check(values.get("name"), "Image name")
        base = values.get("base") or "core-image"
        lines = [f'SUMMARY = "{values.get("summary") or values["name"]}"', 'LICENSE = "MIT"', ""]
        lines += ["inherit core-image"] if base == "core-image" else [f"require recipes-core/images/{base}.bb"]
        features = values.get("features", "")
        if "debug-tweaks" in features.split() and newer(series, "styhead"):
            raise ValueError("debug-tweaks was removed in 5.1 Styhead; use allow-empty-password, empty-root-password and allow-root-login")
        if features:
            lines.append(f'IMAGE_FEATURES += "{features}"')
        if values.get("packages"):
            lines.append(f'IMAGE_INSTALL:append = " {values["packages"]}"')
        if values.get("fstypes"):
            lines.append(f'IMAGE_FSTYPES = "{values["fstypes"]}"')
        if values.get("size"):
            if not values["size"].isdigit():
                raise ValueError("Extra free space must be a number of KiB")
            lines.append(f'IMAGE_ROOTFS_EXTRA_SPACE = "{values["size"]}"')
        files[f"recipes-core/images/{values['name']}.bb"] = "\n".join(lines) + "\n"
        activate["target"] = values["name"]
    elif kind == "recipe":
        from .developer import scaffold_plan
        _check(values.get("name"), "Recipe name")
        generated = scaffold_plan(values["name"], "studio", values.get("system") or "cmake", values.get("owner") or "Unknown", compat)
        files.update({k: v for k, v in generated.items() if k != "conf/layer.conf"})
        activate["target"] = values["name"]
    elif kind == "append":
        _check(values.get("recipe"), "Recipe")
        category = values.get("category") or "recipes-core"
        if not re.fullmatch(r"recipes-[a-z0-9-]+", category):
            raise ValueError("Category must look like recipes-<name>")
        base = f"{category}/{values['recipe']}"
        lines = ['FILESEXTRAPATHS:prepend := "${THISDIR}/files:"', ""]
        name = values.get("file", "")
        if name:
            if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
                raise ValueError("File name may contain letters, digits, dots, underscores and hyphens")
            lines += [f'SRC_URI += "file://{name}"', "", "do_install:append() {", "    install -d ${D}${sysconfdir}",
                      f"    install -m 0644 ${{UNPACKDIR}}/{name} ${{D}}${{sysconfdir}}/{name}" if newer(series, "styhead") else
                      f"    install -m 0644 ${{WORKDIR}}/{name} ${{D}}${{sysconfdir}}/{name}", "}"]
            files[f"{base}/files/{name}"] = f"Installed by {root.name} (Bitloom Studio)\n"
            notes.append("Files are read from UNPACKDIR on 5.1+ and WORKDIR before; the append uses the detected release.")
        if values.get("config"):
            lines += ["", values["config"]]
        files[f"{base}/{values['recipe']}_%.bbappend"] = "\n".join(lines) + "\n"
    else:
        raise ValueError("Unknown kind")
    return {"kind": kind, "layer": str(root), "new_layer": new, "files": files, "activate": activate, "notes": notes}


def allowed_roots(profile: Profile) -> list[Path]:
    roots = [profile.root_path]
    if profile.environment.get("KAS_WORK_DIR"):
        roots.append(Path(profile.environment["KAS_WORK_DIR"]).expanduser().resolve())
    return roots


def create(profile: Profile, result: dict) -> list[Path]:
    """Write every file or none: refuses existing files and paths outside the project."""
    root = Path(result["layer"]).resolve()
    if not any(root == base or root.is_relative_to(base) for base in allowed_roots(profile)):
        raise ValueError("Studio writes only inside the project root (or KAS_WORK_DIR)")
    if result["new_layer"] and root.exists():
        raise ValueError(f"{root} already exists; choose another layer name or that layer")
    if not result["new_layer"] and not (root / "conf/layer.conf").is_file():
        raise ValueError(f"{root} is not a layer (conf/layer.conf missing)")
    targets = []
    for name in result["files"]:
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Invalid file name " + name)
        path = root / relative
        if path.exists():
            raise ValueError(f"{path} exists; Studio never overwrites files")
        targets.append(path)
    written = []
    try:
        for path, text in zip(targets, result["files"].values()):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x") as stream:
                stream.write(text)
            written.append(path)
    except OSError:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return written


def runtime_path(profile: Profile, host: Path) -> str:
    if profile.mode == "container":
        return str(Path(profile.container_root) / Path(host).relative_to(profile.root_path))
    return str(host)


def kas_overlay(profile: Profile, result: dict) -> tuple[str, str]:
    """(file name, YAML) selecting the layer and the created distro/machine/image."""
    root = Path(result["layer"])
    name = "kas-studio-" + root.name + ".yml"
    # The overlay lives in the project; a kas repo with neither url nor path is "the repository holding this
    # file", so the layer resolves for kas and kas-container alike (a relative path would resolve against
    # KAS_WORK_DIR, where the layer does not exist). Layer paths are relative to that repository's top.
    top = next((d for d in (profile.root_path, *profile.root_path.parents) if (d / ".git").exists()), profile.root_path)
    try:
        relative = os.path.relpath(root, top)
    except ValueError:
        relative = str(root)
    lines = ["header:", "  version: 14"]
    for key in ("distro", "machine", "target"):
        if key in result["activate"]:
            lines.append(f"{key}: {result['activate'][key]}")
    if result["new_layer"]:
        # Existing layers are already part of the configuration; adding them again would duplicate them.
        lines += ["repos:", f"  {root.name.replace('-', '_')}:", "    layers:", f"      {json.dumps(relative)}:"]
    return name, "\n".join(lines) + "\n"


def register(settings, profile: Profile, result: dict, use: bool, submit) -> tuple[list[str], str | None]:
    """Make the created files effective; submit(profile, title, argv, action) queues commands.
    Returns (messages, build target to suggest)."""
    messages = []
    if profile.mode in {"kas", "kas-container", "wrapper"} and (result["new_layer"] or result["activate"]):
        name, text = kas_overlay(profile, result)
        path = profile.root_path / name
        if path.exists():
            messages.append(f"{name} exists; add the layer/selection to it by hand")
        else:
            path.write_text(text)
            if profile.mode == "wrapper":
                messages.append(f"add {name} to the configuration your launcher passes to kas")
            elif profile.name in settings.shared:
                messages.append(f"team profile: clone it and append {name} to kas_file")
            else:
                profile.kas_file = ":".join([*profile.kas_file.split(":"), name])
                settings.save()
                messages.append(f"kas_file is now {profile.kas_file}")
    else:
        if result["new_layer"]:
            submit(profile, "Register layer " + Path(result["layer"]).name, ["bitbake-layers", "add-layer", runtime_path(profile, result["layer"])], "layer-add")
            messages.append("queued bitbake-layers add-layer")
        if use and (result["activate"].get("distro") or result["activate"].get("machine")):
            profile.distro = result["activate"].get("distro", profile.distro)
            profile.machine = result["activate"].get("machine", profile.machine)
            settings.save()
            messages.append(f"profile now uses DISTRO={profile.distro or 'default'} MACHINE={profile.machine or 'default'}")
    target = result["activate"].get("target")
    if target:
        messages.append(f"build target: {target}")
    return messages, target
