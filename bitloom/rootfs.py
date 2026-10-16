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
    entries = {"/": {"type": "dir", "size": 0, "mode": 0o755, "target": ""}}
    if path.is_dir():
        for item in path.rglob("*"):
            relative = "/" + str(item.relative_to(path))
            try:
                info = item.lstat()
            except OSError:
                continue
            kind = "link" if stat.S_ISLNK(info.st_mode) else "dir" if stat.S_ISDIR(info.st_mode) else "file"
            entries[relative] = {"type": kind, "size": info.st_size if kind == "file" else 0, "mode": stat.S_IMODE(info.st_mode),
                                 "target": str(item.readlink()) if kind == "link" else ""}
    else:
        with _open(path) as archive:
            for member in archive:
                name = "/" + member.name.lstrip("./").rstrip("/")
                if name == "/":
                    continue
                kind = "link" if member.issym() or member.islnk() else "dir" if member.isdir() else "file"
                entries[name] = {"type": kind, "size": member.size if kind == "file" else 0, "mode": member.mode, "target": member.linkname or ""}
    # Folders implied by paths, and their total size.
    for name in list(entries):
        parent = name.rsplit("/", 1)[0] or "/"
        while parent not in entries:
            entries[parent] = {"type": "dir", "size": 0, "mode": 0o755, "target": ""}
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
