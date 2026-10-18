"""Argument-only command construction. User input is never interpolated as shell code."""
from __future__ import annotations

import os
import re
import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .models import Profile


@dataclass(frozen=True)
class Action:
    id: str
    group: str
    title: str
    tool: str
    args: tuple[str, ...] = ()
    inputs: tuple[str, ...] = ()
    help: str = ""
    interactive: bool = False
    task: str = ""      # optional runtime task probed before queueing (class/config dependent)
    needs: tuple[str, ...] = ()   # capabilities (bitloom/capabilities.py) the project's release must have
    instead: str = ""   # action id to suggest when this release lacks it


ACTIONS = [
    Action("build", "Build", "Build target", "bitbake", inputs=("target",)),
    Action("dry-run", "Build", "Dry run", "bitbake", ("-n",), ("target",)),
    Action("parse", "Build", "Parse metadata", "bitbake", ("-p",)),
    Action("fetch", "Downloads", "Fetch recipe sources", "bitbake", ("-c", "fetch"), ("target",)),
    Action("fetch-all", "Downloads", "Fetch all target dependencies", "bitbake", ("--runall=fetch",), ("target",)),
    Action("unpack", "Build", "Unpack recipe", "bitbake", ("-c", "unpack"), ("target",)),
    Action("patch", "Build", "Apply recipe patches", "bitbake", ("-c", "patch"), ("target",)),
    Action("configure", "Build", "Configure recipe", "bitbake", ("-c", "configure"), ("target",)),
    Action("compile", "Build", "Compile recipe", "bitbake", ("-c", "compile"), ("target",)),
    Action("force-compile", "Build", "Force compile", "bitbake", ("-f", "-c", "compile"), ("target",)),
    Action("install", "Build", "Install recipe", "bitbake", ("-c", "install"), ("target",)),
    Action("package", "Build", "Package recipe", "bitbake", ("-c", "package"), ("target",)),
    Action("rootfs", "Build", "Build root filesystem", "bitbake", ("-c", "rootfs"), ("target",)),
    Action("sdk", "Build", "Build SDK", "bitbake", ("-c", "populate_sdk"), ("target",)),
    Action("esdk", "Build", "Build extensible SDK", "bitbake", ("-c", "populate_sdk_ext"), ("target",)),
    Action("task", "Build", "Run custom task", "bitbake", inputs=("target", "task")),
    Action("clean", "Maintenance", "Clean recipe work directory", "bitbake", ("-c", "clean"), ("target",)),
    Action("cleansstate", "Maintenance", "Clean recipe + sstate", "bitbake", ("-c", "cleansstate"), ("target",), help="Removes this recipe's local shared state. Avoid with shared caches in active use."),
    Action("cleanall", "Maintenance", "Clean recipe + sstate + downloads", "bitbake", ("-c", "cleanall"), ("target",), help="Removes recipe sources and local shared state."),
    Action("environment", "Inspect", "Resolve recipe environment", "bitbake", ("-e",), ("target",)),
    Action("tasks", "Inspect", "List recipe tasks", "bitbake", ("-c", "listtasks"), ("target",)),
    Action("graph", "Inspect", "Generate dependency graph", "bitbake", ("-g",), ("target",)),
    Action("signatures", "Inspect", "Dump signatures", "bitbake", ("-S", "none"), ("target",)),
    Action("sig-diff", "Inspect", "Explain sstate differences", "bitbake", ("-S", "printdiff"), ("target",)),
    Action("layers", "Layers", "Show layers and priorities", "bitbake-layers", ("show-layers",)),
    Action("recipes", "Layers", "Show recipes", "bitbake-layers", ("show-recipes",)),
    Action("appends", "Layers", "Show recipe appends", "bitbake-layers", ("show-appends",)),
    Action("overlay", "Layers", "Show overlaid recipes", "bitbake-layers", ("show-overlayed",)),
    Action("layer-add", "Layers", "Add layer", "bitbake-layers", ("add-layer",), ("path",)),
    Action("layer-remove", "Layers", "Remove layer", "bitbake-layers", ("remove-layer",), ("path",)),
    Action("layer-create", "Layers", "Create layer", "bitbake-layers", ("create-layer",), ("path",)),
    Action("layer-depends", "Layers", "Show cross-layer dependencies", "bitbake-layers", ("show-cross-depends",)),
    Action("dev-status", "Devtool", "Workspace status", "devtool", ("status",)),
    Action("dev-modify", "Devtool", "Modify recipe", "devtool", ("modify",), ("target",)),
    Action("dev-add", "Devtool", "Add source as recipe", "devtool", ("add",), ("target", "path")),
    Action("dev-build", "Devtool", "Build workspace recipe", "devtool", ("build",), ("target",)),
    Action("dev-image", "Devtool", "Build image with workspace recipes", "devtool", ("build-image",), ("target",)),
    Action("dev-reset", "Devtool", "Reset workspace recipe", "devtool", ("reset",), ("target",)),
    Action("dev-finish", "Devtool", "Finish recipe into layer", "devtool", ("finish",), ("target", "path")),
    Action("dev-update", "Devtool", "Update recipe from source", "devtool", ("update-recipe",), ("target",)),
    Action("dev-upgrade", "Devtool", "Upgrade recipe", "devtool", ("upgrade",), ("target",)),
    Action("dev-latest", "Devtool", "Check upstream version", "devtool", ("latest-version",), ("target",)),
    Action("dev-deploy", "Devtool", "Deploy to device", "devtool", ("deploy-target",), ("target", "device")),
    Action("dev-undeploy", "Devtool", "Undeploy from device", "devtool", ("undeploy-target",), ("target", "device")),
    Action("dev-config", "Devtool", "Configure help", "devtool", ("configure-help",), ("target",)),
    Action("dev-upgrade-status", "Devtool", "Check recipe upgrade status", "devtool", ("check-upgrade-status",), ("target",)),
    Action("recipe-create", "Recipes", "Create recipe from URL/source", "recipetool", ("create",), ("source",)),
    Action("packages", "Packages", "List built packages", "oe-pkgdata-util", ("list-pkgs",)),
    Action("package-files", "Packages", "List package files", "oe-pkgdata-util", ("list-pkg-files",), ("target",)),
    Action("find-path", "Packages", "Find package owning a path", "oe-pkgdata-util", ("find-path",), ("path",)),
    Action("package-recipe", "Packages", "Find recipe for package", "oe-pkgdata-util", ("lookup-recipe",), ("target",)),
    Action("license", "Inspect", "Generate SPDX SBOM", "bitbake", ("-c", "create_spdx"), ("target",), help="Requires create-spdx in your image configuration.", task="do_create_spdx"),
    Action("testimage", "Testing", "Run image tests", "bitbake", ("-c", "testimage"), ("target",), help="Requires testimage configuration and suitable target runner.", task="do_testimage"),
    Action("ptest", "Testing", "Build ptest packages", "bitbake", ("-c", "compile_ptest_base"), ("target",), help="Recipe must inherit ptest and ptest must be enabled.", task="do_compile_ptest_base"),
    Action("devshell", "Terminal", "Open recipe development shell", "bitbake", ("-c", "devshell"), ("target",), interactive=True),
    Action("menuconfig", "Terminal", "Kernel menuconfig", "bitbake", ("-c", "menuconfig"), ("target",), interactive=True, task="do_menuconfig"),
    Action("qemu", "Terminal", "Boot image with QEMU", "runqemu", inputs=("target",), interactive=True),
    Action("kas-build", "Kas", "Build kas configuration", "kas", ("build",)),
    Action("kas-checkout", "Kas", "Checkout kas repositories", "kas", ("checkout",)),
    Action("kas-dump", "Kas", "Dump resolved kas configuration", "kas", ("dump",)),
    Action("kas-shell", "Kas", "Open kas shell", "kas", ("shell",), interactive=True),
    Action("custom", "Utility", "Custom command (argument list)", "", inputs=("command",), help="Parsed as argv. Shell operators are not interpreted."),
]
ACTIONS.extend([
    Action("getvar", "Inspect", "Resolve one BitBake variable", "bitbake-getvar", inputs=("variable",)),
    Action("dumpsig", "Inspect", "Read signature file", "bitbake-dumpsig", inputs=("path",)),
    Action("diffsigs", "Inspect", "Compare signature files", "bitbake-diffsigs", inputs=("path", "path2")),
    Action("kernel-diff", "Kernel", "Export kernel config changes", "bitbake", ("-c", "diffconfig"), ("target",), task="do_diffconfig"),
    Action("kernel-fragments", "Kernel", "Validate kernel config fragments", "bitbake", ("-c", "kernel_configcheck"), ("target",), task="do_kernel_configcheck"),
    Action("kernel-savedefconfig", "Kernel", "Save kernel defconfig", "bitbake", ("-c", "savedefconfig", "virtual/kernel"),
           help="Writes a minimal defconfig of the current kernel configuration to the kernel's build folder (${B}/defconfig): copy it to your layer as a starting point.",
           task="do_savedefconfig"),
    Action("uboot-menuconfig", "Bootloader", "U-Boot menuconfig", "bitbake", ("-c", "menuconfig", "virtual/bootloader"), interactive=True,
           help="Configures the machine's bootloader (PREFERRED_PROVIDER_virtual/bootloader, usually u-boot) in a terminal. Keep the result with U-Boot diffconfig.",
           task="do_menuconfig"),
    Action("uboot-diffconfig", "Bootloader", "Export U-Boot config changes", "bitbake", ("-c", "diffconfig", "virtual/bootloader"),
           help="Writes the changes made with menuconfig as a fragment.cfg in the bootloader's work folder: add it to SRC_URI in a u-boot append in your layer.",
           task="do_diffconfig"),
    Action("cve", "Security", "Run recipe CVE check (cve-check)", "bitbake", ("-c", "cve_check"), ("target",), help="Requires the cve-check class and CVE database. Removed in 6.0 Wrynose: use sbom-cve-check.",
           task="do_cve_check", needs=("cve-check",), instead="sbom-cve-recipe"),
    Action("kas-lock", "Kas", "Generate kas lock file", "kas", ("lock",)),
    Action("sbom-cve-recipe", "Security", "Recipe CVE analysis from its SBOM (sbom-cve-check)", "bitbake", ("-c", "sbom_cve_check_recipe"), ("target",),
           help="Analyses the recipe SBOM without building the software. The recipe must inherit sbom-cve-check-recipe; reports go to DEPLOY_DIR_IMAGE.",
           task="do_sbom_cve_check_recipe", needs=("sbom-cve-check-recipe",), instead="cve"),
    Action("recipe-sbom", "Security", "Create recipe SBOM (SPDX 3)", "bitbake", ("-c", "create_recipe_sbom"), ("target",),
           help="Recipe-level SBOM used by sbom-cve-check-recipe.", task="do_create_recipe_sbom", needs=("recipe-sbom",), instead="license"),
    Action("vex", "Security", "Generate VEX metadata", "bitbake", ("-c", "generate_vex"), ("target",),
           help='Requires INHERIT += "vex". Produces per-recipe and image VEX reports in DEPLOY_DIR_IMAGE.', task="do_generate_vex", needs=("vex",)),
    Action("sbom-cve-enable", "Security", "Enable sbom-cve-check for image builds", "bitbake-config-build", ("enable-fragment", "core/yocto/sbom-cve-check"),
           help="Every image build then analyses its SPDX 3 SBOM for CVEs. Reports go to DEPLOY_DIR_IMAGE.", needs=("sbom-cve-check", "fragments"), instead="cve"),
    Action("sbom-cve-disable", "Security", "Disable sbom-cve-check fragment", "bitbake-config-build", ("disable-fragment", "core/yocto/sbom-cve-check"), needs=("sbom-cve-check", "fragments")),
    # Configuration fragments and bitbake-setup: offered only when the project's BitBake ships the tool.
    Action("fragments", "Setup", "List configuration fragments", "bitbake-config-build", ("list-fragments",), needs=("fragments",),
           help="Fragments are named pieces of configuration (machine/…, distro/…, core/yocto/…) enabled in conf/toolcfg.conf."),
    Action("fragment-enable", "Setup", "Enable a configuration fragment", "bitbake-config-build", ("enable-fragment",), ("fragment",), needs=("fragments",),
           help="Appends the fragment to OE_FRAGMENTS in build/conf/toolcfg.conf, for example core/yocto/sstate-mirror-cdn."),
    Action("fragment-disable", "Setup", "Disable a configuration fragment", "bitbake-config-build", ("disable-fragment",), ("fragment",), needs=("fragments",)),
    Action("setup-status", "Setup", "bitbake-setup: compare with upstream", "bitbake-setup", ("status",), needs=("bitbake-setup",),
           help="Shows how this bitbake-setup workspace differs from its configuration template and upstream layers."),
    Action("setup-update", "Setup", "bitbake-setup: update layers and configuration", "bitbake-setup", ("update",), interactive=True, needs=("bitbake-setup",),
           help="Brings the workspace to its template: updates layer checkouts and, after asking, the build configuration."),
])
BY_ID = {a.id: a for a in ACTIONS}


def availability(action: Action, series: str | None, profile=None) -> tuple[bool | None, str]:
    """Whether the project's release has what the operation needs (bitloom/capabilities.py), with a pointer
    to the operation this release offers instead."""
    from .capabilities import check_all
    ok, reason = check_all(action.needs, series, profile)
    if ok is False and action.instead in BY_ID:
        reason += f"; the operation for this release is “{BY_ID[action.instead].title}”"
    return ok, reason


def arguments(action: Action, values: dict[str, str]) -> list[str]:
    if not isinstance(values, dict) or any(not isinstance(v, str) for v in values.values()):
        raise ValueError("values must be an object of strings")
    for key in action.inputs:
        if not values.get(key, "").strip():
            raise ValueError(f"{key} is required")
    if action.id == "custom":
        argv = shlex.split(values["command"])
        if not argv:
            raise ValueError("Command is empty")
        return argv
    argv = [action.tool, *action.args]
    for key in action.inputs:
        value = values[key].strip()
        if value.startswith("-"):
            raise ValueError(f"{key} must not start with '-'")
        if key == "target":
            # Several targets may be given, separated by spaces (bitbake image1 image2).
            targets = value.split()
            bad = [t for t in targets if not TARGET.fullmatch(t)]
            if bad:
                raise ValueError(f"Not a BitBake target: {bad[0]!r} (recipe, image, virtual/… or mc:…:…)")
            argv += targets
        elif key == "task":
            if not TASK.fullmatch(value):
                raise ValueError(f"Not a task name: {value!r} (for example compile or do_compile)")
            argv += ["-c", value]
        elif key == "fragment" and not FRAGMENT.fullmatch(value):
            raise ValueError(f"Not a fragment name: {value!r} (for example core/yocto/sstate-mirror-cdn or machine/qemuarm64)")
        elif key == "variable" and not VARIABLE.fullmatch(value):
            raise ValueError(f"Not a variable name: {value!r} (for example IMAGE_INSTALL or SRC_URI:pn-busybox)")
        else:
            argv.append(value)
    return argv


def subject(action: Action, values: dict[str, str]) -> str:
    """What an operation acts on, for job titles: 'busybox', 'img1 img2', 'busybox · do_compile'."""
    return " · ".join(" ".join(values.get(key, "").split()) for key in action.inputs if key not in {"command"})


TARGET = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+:@/-]*")
TASK = re.compile(r"[A-Za-z0-9_]+")
FRAGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]*(/[A-Za-z0-9][A-Za-z0-9_.+-]*)+")
VARIABLE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_:.+/@${}\[\]-]*")


@dataclass
class Invocation:
    argv: list[str]
    cwd: Path
    env: dict[str, str]

    @property
    def display(self) -> str:
        return shlex.join(self.argv)


def search_path(path: str | None = None) -> str:
    """PATH plus Bitloom's own bin directory, last: kas and kas-container installed in Bitloom's
    virtualenv work even when it is not activated (a service started by another client or a
    desktop launcher inherits a bare PATH)."""
    path = os.environ.get("PATH", "") if path is None else path
    tools = str(Path(sys.executable).parent)
    return path if tools in path.split(os.pathsep) else os.pathsep.join(filter(None, [path, tools]))


def which(name: str) -> str | None:
    return shutil.which(name, path=search_path())


def invocation(profile: Profile, argv: list[str], managed_name: str = "") -> Invocation:
    profile.validate()
    env = os.environ.copy()
    env["PATH"] = search_path(env.get("PATH", ""))
    env.update(profile.environment)
    root = profile.root_path
    # MACHINE/DISTRO are passed through BitBake's explicit allow-list.
    for key, value in (("MACHINE", profile.machine), ("DISTRO", profile.distro)):
        if value:
            env[key] = value
    passthrough = set(env.get("BB_ENV_PASSTHROUGH_ADDITIONS", "").split())
    passthrough.update(profile.environment)
    passthrough.update(k for k, v in (("MACHINE", profile.machine), ("DISTRO", profile.distro)) if v)
    env["BB_ENV_PASSTHROUGH_ADDITIONS"] = " ".join(sorted(passthrough))
    if profile.mode == "wrapper":
        # The project script owns the kas configuration (often via environment).
        if argv[0] == "kas":
            return Invocation([*profile.launcher, *argv[1:]], root, env)
        command = shlex.join(argv)
        return Invocation([*profile.launcher, *(part.replace("{command}", command) for part in profile.launcher_shell)], root, env)
    if profile.mode in {"kas", "kas-container"}:
        if profile.machine:
            env["KAS_MACHINE"] = profile.machine
        if profile.distro:
            env["KAS_DISTRO"] = profile.distro
    if argv[0] == "kas" and profile.mode != "container":
        executable = "kas-container" if profile.mode == "kas-container" else "kas"
        prefix = [executable]
        if profile.mode == "kas-container" and managed_name:
            if not re.fullmatch(r'bitloom-[a-f0-9]+', managed_name): raise ValueError('Invalid managed container name')
            prefix += ['--runtime-args', '--name ' + managed_name + ' --label io.bitloom.owner=' + managed_name]
        return Invocation([*prefix, *argv[1:], profile.kas_file], root, env)
    if profile.mode in {"kas", "kas-container"}:
        executable = "kas-container" if profile.mode == "kas-container" else "kas"
        prefix = [executable]
        if profile.mode == "kas-container" and managed_name:
            if not re.fullmatch(r'bitloom-[a-f0-9]+', managed_name): raise ValueError('Invalid managed container name')
            prefix += ['--runtime-args', '--name ' + managed_name + ' --label io.bitloom.owner=' + managed_name]
        return Invocation([*prefix, "shell", profile.kas_file, "-c", shlex.join(argv)], root, env)
    script = profile.init_script
    if not script:
        for candidate in ("oe-init-build-env", "poky/oe-init-build-env"):
            if (root / candidate).exists():
                script = candidate
                break
    if profile.mode == "container":
        relative_build = profile.build_path.relative_to(root)
        build = str(Path(profile.container_root) / relative_build)
        container_script = script
        if script and Path(script).is_absolute():
            container_script = str(Path(profile.container_root) / Path(script).relative_to(root))
        if argv[0] == "kas":
            command = f"cd {shlex.quote(profile.container_root)} && exec {shlex.join([*argv, profile.kas_file])}"
        else:
            command = shell_command(argv, container_script, build, profile.container_root)
        if profile.container_name:
            prefix = [profile.engine, "exec", "-i", "-w", profile.container_root]
        else:
            prefix = [profile.engine, "run", "--rm", "-i", "--init", "-v", f"{root}:{profile.container_root}", "-w", profile.container_root]
            if managed_name:
                prefix += ["--name", managed_name]
            if hasattr(os, "getuid"):
                prefix += ["--user", f"{os.getuid()}:{os.getgid()}"]
        for key in sorted(passthrough | {"BB_ENV_PASSTHROUGH_ADDITIONS"}):
            if key in env:
                prefix += ["-e", f"{key}={env[key]}"]
        prefix += profile.container_args
        prefix += [profile.container_name or profile.image, "bash", "-c", command]
        return Invocation(prefix, root, env)
    if script:
        return Invocation(["bash", "-c", shell_command(argv, script, str(profile.build_path), str(root))], root, env)
    return Invocation(argv, profile.build_path if profile.build_path.exists() else root, env)


def shell_command(argv: list[str], script: str, build: str, root: str) -> str:
    # oe-init-build-env takes the build directory; bitbake-setup's build/init-build-env already knows it.
    target = "" if Path(script or "").name == "init-build-env" else " " + shlex.quote(build)
    setup = f"source {shlex.quote(script)}{target} >/dev/null && " if script else f"cd {shlex.quote(build)} && "
    return f"cd {shlex.quote(root)} && {setup}exec {shlex.join(argv)}"
