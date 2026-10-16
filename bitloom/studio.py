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
    label: str                    # plain words; the BitBake variable goes in var
    kind: str = "text"            # text | choice | multi | bool
    default: str = ""
    choices: tuple[str, ...] = ()
    info: str = ""
    required: bool = False
    section: str = ""             # Where · Identity · Contents · Policy
    var: str = ""                 # the variable it writes, shown next to the label and highlighted in the preview
    hints: tuple[tuple[str, str], ...] = ()   # (choice, what it means)
    placeholder: str = ""


class FieldError(ValueError):
    """A value the form must fix; field names the input to point at."""
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


KINDS = {
    "layer": ("Product layer", "A folder for your own metadata. Start here: distributions, machines, images and recipes you create go into it."),
    "distro": ("Distribution", "Your product's name, version and policies (init system, features, security, SBOM) instead of Poky's."),
    "machine": ("Machine", "Your board: a copy of a reference machine with your hardware features and serial console."),
    "image": ("Image", "What ends up on the device: a base image plus your packages, developer access and file system formats."),
    "recipe": ("Application recipe", "A working sample application with its source, license and build system, ready to replace with yours."),
    "append": ("Recipe append", "Change an existing recipe without editing it: add a file to /etc or set extra options."),
}
SECTIONS = {"where": "Where the files go", "identity": "Name and identity", "contents": "What goes in", "policy": "Policies"}

DISTRO_FEATURES = ("systemd", "usrmerge", "pam", "seccomp", "ipv6", "wifi", "bluetooth", "x11", "wayland", "opengl", "vulkan",
                   "polkit", "zeroconf", "nfs", "ptest", "sota")
FEATURE_HINTS = {
    "systemd": "systemd as the init system and service manager", "usrmerge": "/bin, /sbin and /lib are links into /usr (needed by systemd)",
    "pam": "pluggable authentication modules for logins", "seccomp": "system-call filtering for sandboxed services and containers",
    "ipv6": "IPv6 networking support", "wifi": "Wi-Fi tools and drivers", "bluetooth": "Bluetooth stack (BlueZ)",
    "x11": "the X11 graphical server", "wayland": "the Wayland graphical stack (Weston)", "opengl": "OpenGL / EGL 3D graphics",
    "vulkan": "Vulkan graphics API", "polkit": "PolicyKit privilege rules", "zeroconf": "Avahi zero-configuration networking (mDNS)",
    "nfs": "NFS client and server", "ptest": "package tests installable on the device", "sota": "software-over-the-air update hooks",
    "3g": "mobile broadband (ofono)", "nfc": "NFC (neard)", "pcmcia": "PCMCIA cards",
}
MACHINE_FEATURES = ("serial", "usbhost", "usbgadget", "wifi", "bluetooth", "screen", "keyboard", "pci", "rtc", "efi", "vfat", "ext2", "alsa")
MACHINE_HINTS = {
    "serial": "a serial console", "usbhost": "USB host ports", "usbgadget": "the board acts as a USB device", "wifi": "Wi-Fi hardware",
    "bluetooth": "Bluetooth hardware", "screen": "a display", "keyboard": "a keyboard", "pci": "a PCI bus", "rtc": "a real-time clock",
    "efi": "boots through UEFI", "vfat": "FAT boot partition", "ext2": "ext2/3/4 file systems", "alsa": "sound through ALSA",
}
BASE_MACHINES = ("qemux86-64", "qemuarm64", "qemuarm", "qemuriscv64", "genericx86-64", "beaglebone-yocto")
MACHINE_BASE_HINTS = {
    "qemux86-64": "64-bit x86 emulated by QEMU: fastest to try", "qemuarm64": "64-bit Arm emulated by QEMU",
    "qemuarm": "32-bit Arm emulated by QEMU", "qemuriscv64": "64-bit RISC-V emulated by QEMU",
    "genericx86-64": "real 64-bit PCs (needs meta-yocto-bsp)", "beaglebone-yocto": "BeagleBone Black (needs meta-yocto-bsp)",
}
IMAGE_HINTS = {
    "ssh-server-dropbear": "small SSH server", "ssh-server-openssh": "full OpenSSH server", "package-management": "keep the package manager on the device",
    "tools-debug": "gdb, strace and other debugging tools", "tools-profile": "perf, valgrind and other profilers", "dev-pkgs": "headers and development files",
    "read-only-rootfs": "mount the root file system read-only", "splash": "boot splash screen", "hwcodecs": "hardware video codecs",
    "debug-tweaks": "empty root password and root login (development only)", "allow-empty-password": "accounts may have an empty password (development only)",
    "empty-root-password": "root has no password (development only)", "allow-root-login": "root may log in over SSH (development only)",
}
FSTYPE_HINTS = {"ext4": "disk image for one partition", "tar.bz2": "compressed archive of the root file system", "tar.zst": "faster compressed archive",
                "wic": "complete partitioned disk image (boot + root), flash with dd or bmaptool", "wic.zst": "compressed wic", "squashfs": "compressed read-only file system",
                "cpio.gz": "initramfs archive"}


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


def _hints(table, choices):
    return tuple((c, table[c]) for c in choices if c in table)


def fields(kind: str, series: str | None, layers: list[Path]) -> list[Field]:
    layer_choices = tuple(str(p) for p in layers) + ("new layer…",)
    target = Field("layer", "Layer", "choice", layer_choices[0], layer_choices,
                   "Your layers are listed; upstream layers (Poky, OE-Core) are never modified." if layers else
                   "This project has no layer of its own yet, so a new one is created together with these files.",
                   section="where", hints=(("new layer…", "create a new layer next to the project and put the files there"),))
    new_layer = Field("new_layer", "New layer folder", "text", "meta-acme", info="Created in the project root; by convention meta-<company or product>.",
                      section="where", placeholder="meta-acme")
    if kind == "layer":
        return [Field("name", "Folder name", "text", "meta-acme", info="meta-<company or product>; created in the project root.", required=True, section="identity", placeholder="meta-acme"),
                Field("collection", "Short id", "text", "acme", info="Other layers name it in LAYERDEPENDS to say they need yours.", required=True, section="identity", var="BBFILE_COLLECTIONS"),
                Field("owner", "Copyright owner", "text", "Acme Corp", info="Written in the license file of the layer.", required=True, section="identity"),
                Field("priority", "Priority", "choice", "7", ("5", "6", "7", "8", "9", "10"), "When two layers provide the same recipe, the higher number wins. Poky's layers use 5.",
                      section="policy", var="BBFILE_PRIORITY"),
                Field("depends", "Needs these layers", "multi", "core", ("core", "yocto", "yoctobsp", "openembedded-layer", "networking-layer"),
                      "Layers that must be present for yours to parse.", section="policy", var="LAYERDEPENDS",
                      hints=(("core", "OE-Core (always needed)"), ("yocto", "meta-poky, needed by distributions based on Poky"), ("yoctobsp", "meta-yocto-bsp reference boards"),
                             ("openembedded-layer", "meta-oe from meta-openembedded"), ("networking-layer", "meta-networking"))),
                Field("license", "License of the metadata", "choice", "MIT", ("MIT", "Apache-2.0", "proprietary"), "Covers your recipes and configuration, not the software they build.", section="policy")]
    if kind == "distro":
        modern = newer(series, "wrynose")
        return [target, new_layer,
                Field("name", "Id", "text", "acme", info="Lowercase. Selecting it later means DISTRO = \"acme\".", required=True, section="identity", var="DISTRO", placeholder="acme"),
                Field("title", "Product name", "text", "Acme Linux", info="Shown in /etc/os-release and login banners.", required=True, section="identity", var="DISTRO_NAME"),
                Field("version", "Version", "text", "1.0.0", info="Bump it for every product release.", required=True, section="identity", var="DISTRO_VERSION"),
                Field("maintainer", "Maintainer", "text", "Acme Linux team <linux@acme.example>", section="identity", var="MAINTAINER"),
                Field("base", "Start from", "choice", "poky", ("poky", "oe-core defaults"), section="contents",
                      hints=(("poky", "inherit Poky's tested settings and change only what differs (needs meta-poky)"),
                             ("oe-core defaults", "a standalone distribution without meta-poky: you set everything"))),
                Field("init", "Init system", "choice", "systemd" if modern else "sysvinit", ("systemd", "sysvinit", "mdev-busybox"), section="contents", var="INIT_MANAGER",
                      hints=(("systemd", "full service manager; default from Wrynose"), ("sysvinit", "classic init scripts, smaller"),
                             ("mdev-busybox", "minimal BusyBox init for tiny systems"))),
                Field("features", "Add features", "multi", "ipv6 seccomp", DISTRO_FEATURES, "Added to the base distribution's features.", section="contents",
                      var="DISTRO_FEATURES", hints=_hints(FEATURE_HINTS, DISTRO_FEATURES)),
                Field("remove", "Remove features", "multi", "", DISTRO_FEATURES + ("3g", "nfc", "pcmcia", "zeroconf"), "Features your product must not carry.", section="contents",
                      var="DISTRO_FEATURES", hints=_hints(FEATURE_HINTS, DISTRO_FEATURES + ("3g", "nfc", "pcmcia"))),
                Field("packages", "Package format", "choice", "package_ipk", ("package_ipk", "package_rpm", "package_deb"), section="contents", var="PACKAGE_CLASSES",
                      hints=(("package_ipk", "opkg packages: small and fast, the Yocto default"), ("package_rpm", "RPM packages (dnf on the device)"),
                             ("package_deb", "Debian packages (apt on the device)"))),
                Field("hardening", "Compiler hardening", "bool", "1", info="Stack protector, FORTIFY_SOURCE and PIE for every package (security_flags.inc).", section="policy"),
                Field("sbom", "Software bill of materials", "bool", "1", info="An SPDX SBOM for every image, as the EU Cyber Resilience Act expects.", section="policy", var="create-spdx"),
                Field("supplier", "SBOM supplier", "text", "Acme Corp", info="The organisation named as supplier in the SBOM.", section="policy", var="SPDX_PACKAGE_SUPPLIER" if newer(series, "styhead") else "SPDX_SUPPLIER")]
    if kind == "machine":
        return [target, new_layer,
                Field("name", "Id", "text", "acme-board", info="Lowercase. Selecting it later means MACHINE = \"acme-board\".", required=True, section="identity", var="MACHINE", placeholder="acme-board"),
                Field("title", "Description", "text", "Acme board (derived from the reference machine)", section="identity", var="#@NAME"),
                Field("base", "Start from", "choice", "qemux86-64", BASE_MACHINES, "Its whole configuration is reused; you only add what differs.", section="contents",
                      var="require", hints=_hints(MACHINE_BASE_HINTS, BASE_MACHINES)),
                Field("features", "Hardware it has", "multi", "serial usbhost", MACHINE_FEATURES, "Recipes enable support only for hardware listed here.", section="contents",
                      var="MACHINE_FEATURES", hints=_hints(MACHINE_HINTS, MACHINE_FEATURES)),
                Field("console", "Serial console", "text", "115200;ttyS0", info="baud;device, several separated by spaces. Empty for none.", section="contents", var="SERIAL_CONSOLES"),
                Field("kernel", "Kernel", "choice", "linux-yocto", ("linux-yocto", "linux-yocto-rt", "linux-yocto-tiny"), section="contents", var="PREFERRED_PROVIDER_virtual/kernel",
                      hints=(("linux-yocto", "the standard Yocto kernel"), ("linux-yocto-rt", "with PREEMPT_RT real-time patches"), ("linux-yocto-tiny", "minimal configuration for small systems")))]
    if kind == "image":
        access = ("allow-empty-password", "empty-root-password", "allow-root-login") if newer(series, "styhead") else ("debug-tweaks",)
        features = ("ssh-server-dropbear", "ssh-server-openssh", "package-management", "tools-debug", "tools-profile", "dev-pkgs", "read-only-rootfs", "splash", "hwcodecs") + access
        fstypes = ("ext4", "tar.bz2", "tar.zst", "wic", "wic.zst", "squashfs", "cpio.gz")
        return [target, new_layer,
                Field("name", "Image name", "text", "acme-image", info="You build it with: bitbake acme-image.", required=True, section="identity", placeholder="acme-image"),
                Field("summary", "Summary", "text", "Acme product image", section="identity", var="SUMMARY"),
                Field("base", "Start from", "choice", "core-image", ("core-image", "core-image-minimal", "core-image-base"), section="contents",
                      hints=(("core-image", "an empty image: only what you add below"), ("core-image-minimal", "boots to a shell, plus what you add"),
                             ("core-image-base", "console image with hardware support for the machine, plus what you add"))),
                Field("packages", "Extra packages", "text", "htop", info="Space separated recipes or packagegroups, e.g. htop nano packagegroup-core-ssh-openssh.", section="contents", var="IMAGE_INSTALL"),
                Field("features", "Image features", "multi", "ssh-server-dropbear", features,
                      "Development access features were renamed in 5.1 (debug-tweaks became three separate ones)." if newer(series, "styhead") else "",
                      section="contents", var="IMAGE_FEATURES", hints=_hints(IMAGE_HINTS, features)),
                Field("fstypes", "Output formats", "multi", "ext4 tar.bz2", fstypes, "Files written to tmp/deploy/images.", section="contents", var="IMAGE_FSTYPES",
                      hints=_hints(FSTYPE_HINTS, fstypes)),
                Field("size", "Extra free space (KiB)", "text", "", info="Room left free in the root file system; empty keeps the default.", section="contents", var="IMAGE_ROOTFS_EXTRA_SPACE", placeholder="e.g. 102400")]
    if kind == "recipe":
        return [target, new_layer,
                Field("name", "Recipe name", "text", "acme-hello", info="Creates recipes-example/<name>/<name>_1.0.bb with its source; build it with bitbake <name>.", required=True, section="identity", var="PN", placeholder="acme-hello"),
                Field("owner", "Copyright owner", "text", "Acme Corp", info="Written in the MIT license of the sample source.", required=True, section="identity"),
                Field("system", "Build system", "choice", "cmake", ("cmake", "meson", "make", "python", "rust"), section="contents", var="inherit",
                      hints=(("cmake", "C program built with CMake"), ("meson", "C program built with Meson"), ("make", "C program with a plain Makefile"),
                             ("python", "Python package built with setuptools"), ("rust", "Rust program built with Cargo")))]
    if kind == "append":
        return [target, new_layer,
                Field("recipe", "Recipe to change", "text", "base-files", info="Its name without version (PN); the append applies to every version.", required=True, section="identity", placeholder="base-files"),
                Field("category", "Folder", "text", "recipes-core", info="Mirror the original's folder, e.g. recipes-core for base-files.", section="identity", placeholder="recipes-core"),
                Field("file", "Add a file to /etc", "text", "motd", info="Created under files/ and installed as /etc/<name>. Empty to only set options.", section="contents", var="SRC_URI"),
                Field("config", "Extra lines", "text", "", info="BitBake lines added as they are, e.g. PACKAGECONFIG:append = \" foo\".", section="contents", placeholder='PACKAGECONFIG:append = " foo"')]
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


def _check(name, label, field="name"):
    if not NAME.fullmatch(name or ""):
        raise FieldError(field, f"{label} must be lowercase letters, digits and hyphens, starting with a letter")


def plan(kind: str, values: dict, profile: Profile, series: str | None) -> dict:
    """Files to create, where, and how to activate them. Pure: nothing is written."""
    values = {k: (v.strip() if isinstance(v, str) else v) for k, v in values.items()}
    compat = series or values.get("series") or "scarthgap"
    notes, activate = [], {}
    if kind == "layer":
        _check(values.get("name"), "Folder name")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", values.get("collection", "")):
            raise FieldError("collection", "Short id must contain letters, digits, underscores or hyphens")
        root = profile.root_path / values["name"]
        files = layer_files(values["name"], values["collection"], values.get("priority", "7"), values.get("depends", "core") or "core",
                            compat, values.get("owner") or "Unknown", values.get("license", "MIT"))
        return {"kind": kind, "layer": str(root), "new_layer": True, "files": files, "activate": activate, "main": "conf/layer.conf",
                "notes": [f"LAYERSERIES_COMPAT = {compat} (detected release)" if series else "Release not detected: set LAYERSERIES_COMPAT to your release."]}
    choice = values.get("layer", "")
    if not choice or choice.startswith("new layer"):
        _check(values.get("new_layer"), "New layer folder", "new_layer")
        root, new = profile.root_path / values["new_layer"], True
    else:
        root, new = Path(choice), False
    files = {}
    if new:
        collection = re.sub(r"^meta-", "", values["new_layer"]).replace("-", "_")
        files.update(layer_files(values["new_layer"], collection, "7", "core yocto" if values.get("base") == "poky" else "core",
                                 compat, values.get("owner") or values.get("maintainer") or "Unknown"))
    if kind == "distro":
        _check(values.get("name"), "Id")
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
        _check(values.get("name"), "Id")
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
            raise FieldError("features", "debug-tweaks was removed in 5.1 Styhead; use allow-empty-password, empty-root-password and allow-root-login")
        if features:
            lines.append(f'IMAGE_FEATURES += "{features}"')
        if values.get("packages"):
            lines.append(f'IMAGE_INSTALL:append = " {values["packages"]}"')
        if values.get("fstypes"):
            lines.append(f'IMAGE_FSTYPES = "{values["fstypes"]}"')
        if values.get("size"):
            if not values["size"].isdigit():
                raise FieldError("size", "Extra free space must be a number of KiB")
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
        _check(values.get("recipe"), "Recipe", "recipe")
        category = values.get("category") or "recipes-core"
        if not re.fullmatch(r"recipes-[a-z0-9-]+", category):
            raise FieldError("category", "Folder must look like recipes-<name>")
        base = f"{category}/{values['recipe']}"
        lines = ['FILESEXTRAPATHS:prepend := "${THISDIR}/files:"', ""]
        name = values.get("file", "")
        if name:
            if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
                raise FieldError("file", "File name may contain letters, digits, dots, underscores and hyphens")
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
    main = next((name for name in files if name.startswith(("conf/distro/", "conf/machine/", "recipes-core/images/")) or name.endswith((".bb", ".bbappend"))), next(iter(files)))
    return {"kind": kind, "layer": str(root), "new_layer": new, "files": files, "activate": activate, "notes": notes, "main": main}


def explain(profile: Profile, result: dict, use: bool, shared: bool = False) -> list[str]:
    """What Create will do, in order, so nothing happens by surprise (mirrors register())."""
    root = Path(result["layer"])
    steps = [f"Write {len(result['files'])} new {'file' if len(result['files']) == 1 else 'files'} into "
             + (f"a new layer {root.name} (in {root.parent})" if result["new_layer"] else root.name) + "; existing files are never overwritten."]
    activate = result["activate"]
    selected = ", ".join(f"{k.upper() if k != 'target' else 'build target'} {v}" for k, v in activate.items() if k != "target")
    if profile.mode in {"kas", "kas-container", "wrapper"} and (result["new_layer"] or activate):
        name = kas_overlay(profile, result)[0]
        what = " and ".join(filter(None, ["adds the layer" if result["new_layer"] else "", f"selects {selected}" if selected else "",
                                          f"builds {activate['target']} by default" if activate.get("target") else ""]))
        if profile.mode == "wrapper":
            steps.append(f"Write {name}, which {what}; add it to the configuration your launcher passes to kas.")
        elif shared:
            steps.append(f"Write {name}, which {what}; this is a team profile, so clone it and append {name} to kas_file.")
        else:
            steps.append(f"Write {name}, which {what}, and add it to this profile's kas files: the next build uses it.")
    else:
        if result["new_layer"]:
            steps.append("Queue bitbake-layers add-layer so BitBake reads the new layer.")
        if activate.get("distro") or activate.get("machine"):
            if use:
                steps.append(f"Set {selected} in profile {profile.name}: the next build uses it.")
            else:
                assignments = " and ".join(f'{k.upper()} = "{v}"' for k, v in activate.items() if k != "target")
                steps.append(f"Nothing selects it yet: set {assignments} in conf/local.conf when you want it.")
    if activate.get("target"):
        steps.append(f"Offer to build {activate['target']} right away.")
    elif result["kind"] == "append":
        recipe = Path(result["main"]).name.split("_")[0]
        steps.append(f"Rebuild {recipe} (or an image containing it) to apply the change.")
    return steps


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


# --- Where the files go, for the web Studio -------------------------------------------------------------

SKIP_DIRS = {".git", "__pycache__", ".bitloom"}


def layer_list(entries, profile: Profile) -> list[dict]:
    """Every layer of the workspace for the explorer: your layers first and editable, upstream ones read-only."""
    writable = set(product_layers(entries, profile))
    rows = [{"name": e.name, "path": str(e.path), "writable": e.path in writable} for e in entries if e.kind == "layer"]
    return sorted(rows, key=lambda r: (not r["writable"], r["name"] in {"meta-selftest", "meta-skeleton"}, r["name"]))


def list_layer_files(layer: Path, limit: int = 4000) -> list[str]:
    """Files of one layer, relative to it, folders first in walk order; capped for very large layers."""
    found = []
    for directory, dirs, files in os.walk(layer):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        base = Path(directory)
        for name in sorted(files):
            path = base / name
            if not path.is_symlink():
                found.append(str(path.relative_to(layer)))
                if len(found) >= limit:
                    return found
    return found
