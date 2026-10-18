"""Which recipe puts this in the image? Answers from what BitBake left on disk after a build (no BitBake run):
tmp/pkgdata/<machine>/runtime (packages, their recipe, files and runtime dependencies) and the image
manifests in tmp/deploy/images/<machine>. Answers "which package ships /etc/motd, from which recipe, in which
layer, which built images contain it, what pulls it in" and what to do to change it."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .inspectors import organize, recipe_name
from .models import Profile

_cache: dict[str, tuple[float, float, dict]] = {}


def _pkgdata_dirs(profile: Profile) -> list[Path]:
    build = profile.build_path
    return sorted(p for p in build.glob("tmp*/pkgdata/*/runtime") if p.is_dir())


def load(profile: Profile) -> dict:
    """Packages from pkgdata: {name: {pn, pv, renamed, files, depends}}, plus final name → package."""
    dirs = _pkgdata_dirs(profile)
    key = ":".join(str(d) for d in dirs)
    stamp = max((d.stat().st_mtime for d in dirs), default=0)
    cached = _cache.get(key)
    if cached and cached[0] == stamp and time.monotonic() - cached[1] < 120:
        return cached[2]
    packages, final = {}, {}
    for directory in dirs:
        for path in directory.iterdir():
            if path.suffix == ".packaged" or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
                continue
            try:
                text = path.read_text(errors="replace")
            except OSError:
                continue
            name = path.name
            info = {"pn": "", "pv": "", "renamed": name, "files": [], "depends": []}
            for line in text.splitlines():
                head, _, value = line.partition(": ")
                if head == "PN":
                    info["pn"] = value
                elif head == "PV":
                    info["pv"] = value
                elif head == f"PKG:{name}":
                    info["renamed"] = value
                elif head in (f"RDEPENDS:{name}", f"RRECOMMENDS:{name}"):
                    info["depends"] += re.sub(r"\([^)]*\)", "", value).split()
                elif head == f"FILES_INFO:{name}":
                    try:
                        info["files"] = list(json.loads(value))
                    except ValueError:
                        pass
            packages.setdefault(name, info)
            final.setdefault(info["renamed"], name)
    data = {"packages": packages, "final": final}
    _cache[key] = (stamp, time.monotonic(), data)
    return data


def manifests(profile: Profile) -> list[dict]:
    """Built images and their installed packages, newest manifest per image and machine."""
    found = {}
    for path in sorted(profile.build_path.glob("tmp*/deploy/images/*/*.manifest"), key=lambda p: p.stat().st_mtime if p.exists() else 0):
        machine = path.parent.name
        match = re.match(rf"^(.+?)-{re.escape(machine)}(\.rootfs)?(-\d{{14}})?\.manifest$", path.name)
        if not match:
            continue
        try:
            names = [line.split()[0] for line in path.read_text(errors="replace").splitlines() if line.strip()]
        except OSError:
            continue
        found[(match[1], machine)] = {"image": match[1], "machine": machine, "packages": set(names), "path": str(path)}
    return list(found.values())


def lookup(profile: Profile, query: str, entries=None, limit: int = 12) -> dict:
    query = query.strip()
    if not query:
        raise ValueError("Type a file on the device (/etc/motd), a package (libc6) or a recipe (busybox)")
    data = load(profile)
    packages, final = data["packages"], data["final"]
    if not packages:
        return {"query": query, "results": [], "note": "No package data yet: build an image (or the recipe) once, then ask again."}
    matches, how = [], ""
    if query.startswith("/"):
        matches = [name for name, info in packages.items() if query in info["files"]]
        how = "ships this file"
        if not matches:
            base = "/" + query.rstrip("/").rsplit("/", 1)[-1]
            matches = [name for name, info in packages.items() if any(f.endswith(base) for f in info["files"])]
            how = f"ships a file named {base.lstrip('/')} (not at that exact path)"
    else:
        name = final.get(query, query)
        if name in packages:
            matches, how = [name], "is this package"
        else:
            matches = [n for n, info in packages.items() if info["pn"] == query]
            how = "is built by this recipe"
            if not matches:
                matches = [n for n, info in packages.items() if any(f.endswith("/" + query) for f in info["files"])]
                how = f"ships a file named {query}"
    # Packages that end up on devices first; debug, source and development packages last.
    matches.sort(key=lambda n: (bool(re.search(r"-(dbg|src|dev|staticdev|doc|locale.*|ptest)$", n)), n))
    images = manifests(profile)
    entries = organize(list(entries)) if entries is not None else []
    from .studio import product_layers
    mine = {path.name for path in product_layers(entries, profile)}      # your layers: the ones to change
    recipes = {}
    for entry in entries:
        if entry.kind in ("bb", "bbappend"):
            recipes.setdefault(recipe_name(entry)[0], []).append(entry)
    results = []
    for name in matches[:limit]:
        info = packages[name]
        installed = info["renamed"]
        in_images = []
        for image in images:
            if installed in image["packages"]:
                pulled = sorted(other for other in image["packages"] if other != installed and name in packages.get(final.get(other, other), {}).get("depends", []))
                in_images.append({"image": image["image"], "machine": image["machine"], "pulled_in_by": pulled[:8]})
        files = [e for e in recipes.get(info["pn"], []) if e.kind == "bb"]
        appends = [e for e in recipes.get(info["pn"], []) if e.kind == "bbappend"]
        recipe = files[0] if files else None
        by_name = query.startswith("/") or how.startswith("ships a file named")
        wanted = "/" + query.rstrip("/").rsplit("/", 1)[-1]
        results.append({
            "package": name, "installed_as": installed, "recipe": info["pn"], "version": info["pv"],
            "files": [f for f in info["files"] if not by_name or f == query or f.endswith(wanted)][:5],
            "recipe_file": str(recipe.path) if recipe else "", "layer": recipe.layer if recipe else "", "group": recipe.group if recipe else "",
            "mine": bool(recipe and recipe.layer in mine),
            "appends": [{"path": str(e.path), "layer": e.layer, "mine": e.layer in mine} for e in appends], "images": in_images,
        })
    note = ""
    if not results:
        note = ("No package ships this file: it is made while the image is assembled, not installed from a package. "
                "Typical makers: useradd and groupadd (/etc/passwd, /etc/group, /etc/shadow), ldconfig (/etc/ld.so.cache), package "
                "post-install scripts, or the image recipe's ROOTFS_POSTPROCESS_COMMAND. Change it there: for example EXTRA_USERS_PARAMS "
                "in the image recipe for users, or a ROOTFS_POSTPROCESS_COMMAND function." if query.startswith("/") else
                "Nothing in the package data matches. Check the spelling, or build the image (or the recipe) again if it is new.")
    return {"query": query, "how": how, "results": results, "more": max(0, len(matches) - limit), "note": note}


def report(data: dict) -> str:
    """Text answer for the TUI and the command line."""
    lines = [f"WHICH RECIPE INSTALLS: {data['query']}", ""]
    if not data["results"]:
        return "\n".join(lines + [data.get("note") or "No match."])
    for row in data["results"]:
        lines.append(f"{row['package']} ({row['installed_as']}) {data['how']}")
        lines.append(f"  recipe   {row['recipe']} {row['version']}" + (f"   {row['recipe_file']}" if row["recipe_file"] else ""))
        if row["layer"]:
            lines.append(f"  layer    {row['layer']}" + ("  (yours)" if row["mine"] else "  (upstream)"))
        for path in row["files"]:
            lines.append(f"  file     {path}")
        for image in row["images"]:
            lines.append(f"  image    {image['image']} ({image['machine']})" + (f"  pulled in by {', '.join(image['pulled_in_by'])}" if image["pulled_in_by"] else ""))
        if not row["images"]:
            lines.append("  image    in no built image")
        for append in row["appends"]:
            lines.append(f"  append   {append['path']}" + ("  (yours)" if append["mine"] else ""))
        lines.append("  change   " + advice(row))
        lines.append("")
    if data.get("more"):
        lines.append(f"… {data['more']} more packages match; type a more precise path or name.")
    return "\n".join(lines).rstrip()


def advice(row: dict) -> str:
    """What to do to change it: your own append or recipe first; upstream recipes get a new append."""
    mine = [a for a in row["appends"] if a["mine"]]
    if mine:
        return f"edit your append {mine[0]['path']}"
    if row["mine"]:
        return f"edit {row['recipe_file']} (it is in your layer)"
    group = row["group"] if row["group"].startswith("recipes-") else "recipes-core"
    return f"add {group}/{row['recipe']}/{row['recipe']}_%.bbappend to your layer (Studio → Recipe append)"
