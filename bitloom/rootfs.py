"""Explore a built image like a file manager: its root filesystem from the deploy directory's archive (or the
rootfs folder in tmp/work while it still exists), with every file's size and the package and recipe that
installs it, folder sizes, the biggest packages, and the content of small text files."""
from __future__ import annotations

import re
import shutil
import stat
import subprocess
import tarfile
import time
from pathlib import Path

from .models import Profile

ARCHIVES = (".tar.bz2", ".tar.gz", ".tar.xz", ".tar", ".tar.zst")     # preference order for the same build


def _zstd_available() -> bool:
    try:
        import compression.zstd  # noqa: F401  (Python 3.14+)
        return True
    except ImportError:
        return bool(shutil.which("zstd"))
TEXT_LIMIT = 256 * 1024
_cache: dict[str, tuple[float, float, dict]] = {}


def built_images(profile: Profile) -> list[dict]:
    """Images with something to explore: a rootfs archive in deploy/images/<machine>, or the rootfs folder."""
    found = {}
    for path in sorted(profile.build_path.glob("tmp*/deploy/images/*/*"), key=lambda p: p.name):
        machine = path.parent.name
        suffix = next((s for s in ARCHIVES if path.name.endswith(s)), None)
        if not suffix or (suffix == ".tar.zst" and not _zstd_available()):
            continue
        match = re.match(rf"^(.+?)-{re.escape(machine)}(\.rootfs)?(-\d{{14}})?{re.escape(suffix)}$", path.name)
        if not match:
            continue
        try:
            real = path.resolve()
            if not real.is_file():
                continue
            mtime, size = real.stat().st_mtime, real.stat().st_size
        except OSError:
            continue
        key = (match[1], machine)
        rank = (int(mtime), -ARCHIVES.index(suffix))
        # The newest archive per image and machine; for one build, the format Python reads directly.
        if key not in found or rank > found[key]["rank"]:
            found[key] = {"image": match[1], "machine": machine, "source": str(real), "kind": "archive", "size": size, "mtime": mtime, "rank": rank}
    archived = {image for image, _ in found}
    for rootfs in profile.build_path.glob("tmp*/work/*/*/*/rootfs"):
        image = rootfs.parent.parent.name
        # The rootfs folder (kept when rm_work is off) helps only for images without an archive.
        if (rootfs / "etc").is_dir() and image not in archived:
            machine = rootfs.parent.parent.parent.name.split("-")[0].replace("_", "-")
            found.setdefault((image, machine), {"image": image, "machine": machine, "source": str(rootfs), "kind": "folder", "size": 0, "mtime": rootfs.stat().st_mtime})
    return [{k: v for k, v in row.items() if k != "rank"} for row in sorted(found.values(), key=lambda r: -r["mtime"])]


def _open(path: Path):
    """A streaming tar reader for any supported compression."""
    if path.name.endswith(".tar.zst"):
        try:
            import compression.zstd as zstd  # Python 3.14+
            return tarfile.open(fileobj=zstd.open(path), mode="r|")
        except ImportError:
            process = subprocess.Popen(["zstd", "-dc", str(path)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            return tarfile.open(fileobj=process.stdout, mode="r|")
    # bz2 from pbzip2 holds several streams: the seekable reader handles them, the streaming one stops at the first.
    return tarfile.open(path, mode="r:*")


def _entries(source: str) -> dict:
    """path → {type, size, mode, target}; directories aggregate the size of what they hold."""
    path = Path(source)
    stamp = path.stat().st_mtime
    cached = _cache.get(source)
    if cached and cached[0] == stamp:
        return cached[2]
    entries = {"/": {"type": "dir", "size": 0, "mode": 0o755, "target": "", "owner": ""}}
    if path.is_dir():
        for item in path.rglob("*"):
            relative = "/" + str(item.relative_to(path))
            try:
                info = item.lstat()
            except OSError:
                continue
            kind = "link" if stat.S_ISLNK(info.st_mode) else "dir" if stat.S_ISDIR(info.st_mode) else "file"
            # Owners in tmp/work are the builder's (pseudo keeps the real ones in its database): not shown.
            entries[relative] = {"type": kind, "size": info.st_size if kind == "file" else 0, "mode": stat.S_IMODE(info.st_mode),
                                 "target": str(item.readlink()) if kind == "link" else "", "owner": ""}
    else:
        with _open(path) as archive:
            for member in archive:
                name = "/" + member.name.lstrip("./").rstrip("/")
                if name == "/":
                    continue
                kind = "link" if member.issym() or member.islnk() else "dir" if member.isdir() else "file"
                entries[name] = {"type": kind, "size": member.size if kind == "file" else 0, "mode": member.mode, "target": member.linkname or "",
                                 "owner": f"{member.uname or ('root' if member.uid == 0 else member.uid)}:{member.gname or ('root' if member.gid == 0 else member.gid)}"}
    # Folders implied by paths, and their total size.
    for name in list(entries):
        parent = name.rsplit("/", 1)[0] or "/"
        while parent not in entries:
            entries[parent] = {"type": "dir", "size": 0, "mode": 0o755, "target": "", "owner": ""}
            parent = parent.rsplit("/", 1)[0] or "/"
    for name, info in list(entries.items()):
        if info["type"] == "file" and info["size"]:
            parent = name
            while parent != "/":
                parent = parent.rsplit("/", 1)[0] or "/"
                entries[parent]["size"] += info["size"]
    _cache[source] = (stamp, time.monotonic(), entries)
    return entries


def _find(profile: Profile, image: str, machine: str) -> dict:
    match = next((i for i in built_images(profile) if i["image"] == image and i["machine"] == machine), None)
    if match is None:
        raise LookupError(f"No built root filesystem for {image} ({machine}): build the image with a tar IMAGE_FSTYPES (tar.bz2, tar.zst…)")
    return match


def owners(profile: Profile) -> dict[str, tuple[str, str]]:
    """File path → (package, recipe), from the package data of the build."""
    from .whois import load
    data = load(profile)
    result = {}
    for name, info in data["packages"].items():
        if re.search(r"-(dbg|src|staticdev)$", name):
            continue
        for path in info["files"]:
            result.setdefault(path, (info["renamed"], info["pn"]))
    return result


def listing(profile: Profile, image: str, machine: str, directory: str = "/") -> dict:
    found = _find(profile, image, machine)
    entries = _entries(found["source"])
    directory = "/" + directory.strip("/") if directory.strip("/") else "/"
    if directory not in entries or entries[directory]["type"] != "dir":
        raise LookupError(f"{directory} is not a folder of {image}")
    owner = owners(profile)
    prefix = directory.rstrip("/") + "/"
    children = []
    for name, info in entries.items():
        if name != directory and name.startswith(prefix) and "/" not in name[len(prefix):]:
            package, recipe = owner.get(name, ("", ""))
            children.append({"name": name[len(prefix):], "path": name, **info, "package": package, "recipe": recipe})
    children.sort(key=lambda c: (c["type"] != "dir", c["name"]))
    return {"image": image, "machine": machine, "dir": directory, "size": entries[directory]["size"], "children": children, "source": found["kind"]}


def summary(profile: Profile, image: str, machine: str) -> dict:
    """Totals, the biggest packages and folders: where the space of the image goes."""
    found = _find(profile, image, machine)
    entries = _entries(found["source"])
    owner = owners(profile)
    by_package: dict[str, list] = {}
    files = 0
    for name, info in entries.items():
        if info["type"] == "file":
            files += 1
            package, recipe = owner.get(name, ("(not from a package)", ""))
            row = by_package.setdefault(package, [0, recipe, 0])
            row[0] += info["size"]
            row[2] += 1
    total = entries["/"]["size"]
    packages = sorted(({"package": p, "recipe": r[1], "size": r[0], "files": r[2]} for p, r in by_package.items()), key=lambda r: -r["size"])
    folders = sorted(({"path": n, "size": i["size"]} for n, i in entries.items() if i["type"] == "dir" and n.count("/") == 1 and n != "/"), key=lambda r: -r["size"])
    return {"image": image, "machine": machine, "source": found["source"], "kind": found["kind"], "built": found["mtime"],
            "total": total, "files": files, "packages": packages[:25], "package_count": len([p for p in by_package if not p.startswith("(")]),
            "folders": folders[:12]}


def _contents(source: str, paths: set[str], limit: int = 64 * 1024) -> dict[str, str]:
    """The text of several small files in one pass over the archive (unit files, rules, D-Bus descriptions)."""
    found: dict[str, str] = {}
    if not paths:
        return found
    root = Path(source)
    if root.is_dir():
        for path in paths:
            try:
                found[path] = (root / path.lstrip("/")).read_bytes()[:limit].decode(errors="replace")
            except OSError:
                pass
        return found
    with _open(root) as archive:
        for member in archive:
            name = "/" + member.name.lstrip("./").rstrip("/")
            if name in paths and member.isfile():
                stream = archive.extractfile(member)
                if stream:
                    found[name] = stream.read(limit).decode(errors="replace")
                if len(found) == len(paths):
                    break
    return found


def _resolve(entries: dict, path: str, depth: int = 0) -> str:
    """Follow symbolic links inside the image (absolute or relative) to the real path."""
    info = entries.get(path)
    if not info or info["type"] != "link" or depth > 8 or not info["target"]:
        return path
    target = info["target"] if info["target"].startswith("/") else str(Path(path).parent / info["target"])
    parts = []
    for part in target.split("/"):
        if part == "..":
            parts = parts[:-1]
        elif part and part != ".":
            parts.append(part)
    return _resolve(entries, "/" + "/".join(parts), depth + 1)


def _ini(text: str) -> dict[str, str]:
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if "=" in line and not line.startswith(("#", ";", "[")):
            key, _, value = line.partition("=")
            values.setdefault(key.strip(), value.strip())
    return values


UNIT_DIRS = ("/lib/systemd/system", "/usr/lib/systemd/system", "/etc/systemd/system")
UNIT_KINDS = (".service", ".socket", ".timer", ".mount", ".path", ".target")
RULE_DIRS = ("/lib/udev/rules.d", "/usr/lib/udev/rules.d", "/etc/udev/rules.d")
DBUS_DIRS = ("/usr/share/dbus-1/system-services", "/usr/share/dbus-1/system.d", "/etc/dbus-1/system.d", "/usr/share/dbus-1/services")


def services(profile: Profile, image: str, machine: str) -> dict:
    """What starts on the device and what reacts to it: the init system, systemd units (enabled or not) or SysV
    scripts with their runlevels, udev rules and D-Bus services, each with the package and recipe that installs it."""
    found = _find(profile, image, machine)
    entries = _entries(found["source"])
    owner = owners(profile)
    who = lambda path: dict(zip(("package", "recipe"), owner.get(path) or owner.get(_resolve(entries, path)) or ("", "")))
    exists = lambda path: path in entries
    init = ("systemd" if exists("/lib/systemd/systemd") or exists("/usr/lib/systemd/systemd")
            else "sysvinit" if exists("/etc/inittab") and exists("/etc/init.d") and any(n.startswith("/etc/rc") for n in entries)
            else "busybox init" if exists("/etc/inittab") else "unknown")
    units: dict[str, dict] = {}
    for directory in UNIT_DIRS:
        prefix = directory + "/"
        for name, info in entries.items():
            rest = name[len(prefix):] if name.startswith(prefix) else ""
            if not rest or "/" in rest or not rest.endswith(UNIT_KINDS) or info["type"] == "dir":
                continue
            if info["type"] == "link" and info["target"] == "/dev/null":
                units.setdefault(rest, {"name": rest, "path": name})["masked"] = True
                continue
            if rest not in units or directory == "/etc/systemd/system":
                units.setdefault(rest, {"name": rest})["path"] = name
    wanted: dict[str, list[str]] = {}
    for name, info in entries.items():
        folder, _, unit = name.rpartition("/")
        if folder.startswith("/etc/systemd/system/") and folder.endswith((".wants", ".requires")) and info["type"] == "link":
            wanted.setdefault(unit, []).append(folder.rsplit("/", 1)[1].rsplit(".", 1)[0])
    unit_paths = {_resolve(entries, u["path"]) for u in units.values() if u.get("path")}
    rule_files = [n for n in entries if n.rsplit("/", 1)[0] in RULE_DIRS and n.endswith(".rules")]
    dbus_files = [n for n in entries if n.rsplit("/", 1)[0] in DBUS_DIRS and n.endswith((".service", ".conf"))]
    text = _contents(found["source"], unit_paths | {_resolve(entries, n) for n in rule_files + dbus_files})
    rows = []
    for name, unit in sorted(units.items()):
        values = _ini(text.get(_resolve(entries, unit.get("path", "")), ""))
        alias_of = Path(_resolve(entries, unit["path"])).name if unit.get("path") else name
        rows.append({"name": name, "path": unit.get("path", ""), "kind": name.rsplit(".", 1)[1], "description": values.get("Description", ""),
                     "exec": values.get("ExecStart", "").lstrip("-@+!"), "enabled": sorted(set(wanted.get(name, []) + (wanted.get(alias_of, []) if alias_of != name else []))),
                     "masked": bool(unit.get("masked")), **who(unit.get("path", ""))})
    default = _resolve(entries, "/etc/systemd/system/default.target") if exists("/etc/systemd/system/default.target") else \
        _resolve(entries, "/lib/systemd/system/default.target") if exists("/lib/systemd/system/default.target") else ""
    sysv = []
    links = [(n.split("/")[2], n.rsplit("/", 1)[1], i) for n, i in entries.items() if re.fullmatch(r"/etc/rc[0-6S]\.d/[SK]\d\d.+", n)]
    for name, info in sorted(entries.items()):
        if name.startswith("/etc/init.d/") and name.count("/") == 3 and info["type"] != "dir":
            script = name.rsplit("/", 1)[1]
            starts = sorted({level[2] for level, link, li in links if link[0] == "S" and link[3:] == script}, key=lambda lvl: (lvl != "S", lvl))
            boot = [lvl for lvl in starts if lvl in "S12345"]
            order = next((link[1:3] for level, link, li in sorted(links, key=lambda l: (l[0][2] != "S", l[0])) if link[3:] == script and link[0] == "S"
                          and (not boot or level[2] in boot)), "")
            sysv.append({"name": script, "path": name, "runlevels": starts, "boot": bool(boot), "order": order, **who(name)})
    sysv.sort(key=lambda r: (not r["boot"], not r["runlevels"], "S" not in r["runlevels"], r["order"], r["name"]))
    rules = []
    for name in sorted(rule_files, key=lambda n: n.rsplit("/", 1)[1]):
        body = text.get(_resolve(entries, name), "")
        lines = [l for l in body.splitlines() if l.strip() and not l.lstrip().startswith("#")]
        comment = next((l.lstrip("# ").strip() for l in body.splitlines() if l.startswith("#") and len(l.strip("# ")) > 3), "")
        base = name.rsplit("/", 1)[1]
        masked = entries[name]["type"] == "link" and entries[name]["target"] == "/dev/null"
        overridden = not name.startswith("/etc/") and f"/etc/udev/rules.d/{base}" in entries
        rules.append({"name": base, "path": name, "rules": 0 if masked else len(lines), "comment": comment[:120], "local": name.startswith("/etc/"),
                      "masked": masked, "overridden": overridden, **who(name)})
    dbus = []
    for name in sorted(dbus_files):
        values = _ini(text.get(_resolve(entries, name), ""))
        kind = "activation" if name.endswith(".service") else "policy"
        dbus.append({"name": values.get("Name") or name.rsplit("/", 1)[1].rsplit(".", 1)[0], "path": name, "kind": kind,
                     "bus": "session" if "/services/" in name else "system", "exec": values.get("Exec", ""), "unit": values.get("SystemdService", ""), **who(name)})
    return {"image": image, "machine": machine, "init": init, "default_target": Path(default).name if default else "",
            "units": rows, "sysv": sysv, "udev": rules, "dbus": dbus,
            "starts": [u["name"] for u in rows if u["enabled"] and not u["masked"]] + [s["name"] for s in sysv if set(s["runlevels"]) & set("S12345")]}


def services_report(data: dict) -> str:
    lines = [f"SERVICES IN {data['image']} ({data['machine']})", "", f"init system  {data['init']}" + (f" · default target {data['default_target']}" if data["default_target"] else ""), ""]
    if data["units"]:
        lines.append("SYSTEMD UNITS")
        for u in data["units"]:
            state = "masked" if u["masked"] else ("enabled → " + ", ".join(u["enabled"])) if u["enabled"] else "installed"
            lines.append(f"  {'●' if u['enabled'] and not u['masked'] else '○'} {u['name']:<34} {state:<34} {u['package'] or '—'} ({u['recipe'] or '—'})")
            if u["description"]:
                lines.append(f"      {u['description']}")
        lines.append("")
    if data["sysv"]:
        lines.append("SYSV INIT SCRIPTS")
        for s in data["sysv"]:
            lines.append(f"  {'●' if s['runlevels'] else '○'} {s['name']:<28} {('runlevels ' + ''.join(s['runlevels']) + ' · order ' + s['order']) if s['runlevels'] else 'not started':<30} {s['package'] or '—'} ({s['recipe'] or '—'})")
        lines.append("")
    if data["udev"]:
        lines.append("UDEV RULES")
        for r in data["udev"]:
            state = "disabled in /etc" if r["masked"] else "replaced by /etc" if r["overridden"] else f"{r['rules']:>3} rules" + ("  · /etc" if r["local"] else "")
            lines.append(f"  {r['name']:<40} {state:<18} {r['package'] or 'not from a package'}")
        lines.append("")
    if data["dbus"]:
        lines.append("D-BUS")
        for d in data["dbus"]:
            lines.append(f"  {d['kind']:<10} {d['name']:<44} {d['bus']:<7} {d['unit'] or d['exec'] or ''}  {d['package'] or '—'}")
        lines.append("")
    lines.append("Change a service: an append to its recipe (SYSTEMD_AUTO_ENABLE, SYSTEMD_SERVICE, INITSCRIPT_PARAMS) or remove its package from the image.")
    return "\n".join(lines)


def read(profile: Profile, image: str, machine: str, path: str) -> dict:
    """A small text file of the image (configuration files, scripts), never a binary."""
    found = _find(profile, image, machine)
    entries = _entries(found["source"])
    path = "/" + path.strip("/")
    info = entries.get(path)
    if not info or info["type"] != "file":
        raise LookupError(f"{path} is not a file of {image}")
    if info["size"] > TEXT_LIMIT:
        raise ValueError("File larger than 256 KiB: not shown")
    source = Path(found["source"])
    if source.is_dir():
        data = (source / path.lstrip("/")).read_bytes()
    else:
        data = None
        with _open(source) as archive:
            for member in archive:
                if "/" + member.name.lstrip("./").rstrip("/") == path:
                    stream = archive.extractfile(member)
                    data = stream.read(TEXT_LIMIT + 1) if stream else None
                    break
        if data is None:
            raise LookupError(f"{path} is not a file of {image}")
    if b"\0" in data[:8192]:
        return {"path": path, "binary": True, "size": info["size"], "text": ""}
    return {"path": path, "binary": False, "size": info["size"], "text": data.decode(errors="replace")}
