"""Add a layer to the project: from the OpenEmbedded Layer Index by name, or from any Git URL (your mirror
included), with its dependencies, on the branch of the project's release.

How it is added follows how the project builds: with kas (and launcher scripts, which run kas), a repos entry
in the kas file, so kas fetches it on the next run; with BitBake on the machine or in a container, a clone next
to the other layers and bitbake-layers add-layer through the profile's runtime."""
from __future__ import annotations

import difflib
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .models import Profile

INDEX = "https://layers.openembedded.org/layerindex/api"
_cache: dict[str, tuple[float, object]] = {}


@dataclass
class Layer:
    name: str
    url: str
    subdir: str = ""            # the layer's folder inside the repository ("" = the repository is the layer)
    branch: str = ""
    collection: str = ""
    summary: str = ""
    present: bool = False       # the project already has it
    required_by: list[str] = field(default_factory=list)

    @property
    def repo(self) -> str:
        return re.sub(r"\.git$", "", self.url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1])


def _get(path: str, timeout: float = 20):
    url = f"{INDEX}/{path}"
    hit = _cache.get(url)
    if hit and time.monotonic() - hit[0] < 3600:
        return hit[1]
    request = urllib.request.Request(url, headers={"Accept": "application/json"})   # the index refuses unknown user agents
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read())
    _cache[url] = (time.monotonic(), data)
    return data


def search(text: str, limit: int = 20) -> list[dict]:
    """Layers whose name contains the text, from the Layer Index."""
    text = text.strip()
    if len(text) < 2:
        return []
    items = _get("layerItems/?filter=" + urllib.parse.quote(f"name__icontains:{text}"))
    items.sort(key=lambda i: (not i["name"].startswith(text), i["name"] != text, len(i["name"]), i["name"]))
    return [{"name": i["name"], "summary": i.get("summary", ""), "url": i.get("vcs_url", ""), "type": i.get("layer_type", "")} for i in items[:limit]]


def _branch_id(series: str) -> tuple[int, str]:
    branches = {b["name"]: b["id"] for b in _get("branches/")}
    if series in branches:
        return branches[series], series
    return branches["master"], "master"


def resolve(name: str, series: str, collections: set[str]) -> list[Layer]:
    """The layer and every required dependency on this release, in the order to add them (dependencies first)."""
    branch_id, branch_name = _branch_id(series)
    items_by_id: dict[int, dict] = {}
    order: list[Layer] = []
    seen: set[int] = set()

    def item(ident=None, layer_name=None):
        if ident in items_by_id:
            return items_by_id[ident]
        found = _get(f"layerItems/?filter=id:{ident}") if ident is not None else _get("layerItems/?filter=" + urllib.parse.quote(f"name:{layer_name}"))
        if not found:
            raise LookupError(f"{layer_name or ident} is not in the OpenEmbedded Layer Index: add it by URL")
        items_by_id[found[0]["id"]] = found[0]
        return found[0]

    def visit(entry, required_by):
        if entry["id"] in seen:
            next((l for l in order if l.name == entry["name"]), Layer("", "")).required_by.append(required_by) if required_by else None
            return
        seen.add(entry["id"])
        branches = _get(f"layerBranches/?filter=layer:{entry['id']}")
        mine = next((b for b in branches if b["branch"] == branch_id), None)
        if mine is None:
            raise LookupError(f"{entry['name']} has no {series} branch in the Layer Index: it may not support this release yet")
        for dep in _get(f"layerDependencies/?filter=layerbranch:{mine['id']}"):
            if dep.get("required", True):
                visit(item(dep["dependency"]), entry["name"])
        order.append(Layer(entry["name"], entry["vcs_url"], mine.get("vcs_subdir", ""), mine.get("actual_branch") or branch_name,
                           mine.get("collection", ""), entry.get("summary", ""), mine.get("collection", "") in collections,
                           [required_by] if required_by else []))
    visit(item(layer_name=name), "")
    return order


def from_url(url: str, subdir: str, branch: str, name: str = "") -> list[Layer]:
    url = url.strip()
    if not re.fullmatch(r"(https://|ssh://|git://|file://|git@)[\w.~:/@+%-]+", url):
        raise ValueError("Enter an https://, ssh://, git://, file:// or git@ URL")
    if subdir and (subdir.startswith(("/", "-")) or ".." in Path(subdir).parts):
        raise ValueError("The layer folder must be relative, inside the repository")
    layer = Layer(name or (Path(subdir).name if subdir else ""), url, subdir.strip("/"), branch)
    layer.name = layer.name or layer.repo
    return [layer]


def mirror(layers: list[Layer], base: str) -> list[Layer]:
    """Your mirror instead of the original servers: <base>/<repository name> for every repository."""
    base = base.strip().rstrip("/")
    if base:
        if not re.fullmatch(r"(https://|ssh://|git://|file://|git@)[\w.~:/@+%-]+", base):
            raise ValueError("The mirror must be an https://, ssh://, git://, file:// or git@ address")
        for layer in layers:
            layer.url = f"{base}/{layer.repo}" + (".git" if layer.url.endswith(".git") else "")
    return layers


def branch_exists(url: str, branch: str, timeout: float = 30) -> bool | None:
    """True/False when the remote answered, None when it could not be asked (network, credentials)."""
    try:
        result = subprocess.run(["git", "ls-remote", "--heads", "--tags", "--", url, branch], capture_output=True, text=True, timeout=timeout,
                                env={"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/bin:/bin:/usr/local/bin"})
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return bool(result.stdout.strip())


def project_collections(entries) -> set[str]:
    from .models import read_assignments
    found = set()
    for entry in entries:
        if entry.kind == "layer":
            found.update(read_assignments(entry.path / "conf/layer.conf").get("BBFILE_COLLECTIONS", "").split())
    return found


# --- plans per runtime -----------------------------------------------------------------------------------------

def _repo_blocks(lines: list[str]) -> tuple[int, int, dict[str, tuple[int, int, str]]]:
    """(start, end) of the repos: section and each repository block: name -> (first, last line index, url)."""
    start = next((i for i, l in enumerate(lines) if re.match(r"^repos:\s*$", l)), -1)
    if start < 0:
        return -1, -1, {}
    end = start + 1
    while end < len(lines) and (not lines[end].strip() or lines[end][0].isspace() or lines[end].lstrip().startswith("#")):
        end += 1
    blocks, i = {}, start + 1
    while i < end:
        m = re.match(r"^  ([\w.\-]+):\s*$", lines[i])
        if m:
            j = i + 1
            while j < end and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip()) > 2):
                j += 1
            body = "\n".join(lines[i + 1:j])
            url = re.search(r"^\s+url:\s*['\"]?([^'\"\s]+)", body, re.M)
            blocks[m[1]] = (i, j, url[1] if url else "")
            i = j
        else:
            i += 1
    return start, end, blocks


def kas_plan(profile: Profile, layers: list[Layer]) -> dict:
    """The kas file with the new repositories (or new layers in a repository it already has)."""
    from .setup import profile_kas_files
    files = profile_kas_files(profile)
    main = next((p for p in files if re.search(r"^repos:", p.read_text(errors="replace"), re.M)), files[0] if files else None)
    if main is None:
        raise ValueError("This profile has no kas file to add the layer to")
    text = main.read_text(errors="replace")
    lines = text.splitlines()
    start, end, blocks = _repo_blocks(lines)
    if start < 0:
        lines += ["repos:"]
        start, end, blocks = len(lines) - 1, len(lines), {}
    notes = []
    same = lambda a, b: re.sub(r"(\.git)?/?$", "", a.split("://")[-1].split("@")[-1]) == re.sub(r"(\.git)?/?$", "", b.split("://")[-1].split("@")[-1])
    inserts: dict[int, list[str]] = {}
    new_repos: dict[str, dict] = {}            # repositories this plan adds, written at the end of repos:
    for layer in (l for l in layers if not l.present):
        pending = next((key for key, repo in new_repos.items() if same(repo["url"], layer.url)), None)
        if pending:
            if layer.subdir and layer.subdir not in new_repos[pending]["layers"]:
                new_repos[pending]["layers"].append(layer.subdir)
                notes.append(f"{layer.name}: added to the layers of {pending}")
            continue
        existing = next((name for name, (_, _, url) in blocks.items() if url and same(url, layer.url)), None)
        if existing:
            first, last, _ = blocks[existing]
            body = lines[first + 1:last]
            if not layer.subdir:
                notes.append(f"{layer.name}: already in repos as {existing}")
                continue
            if any(re.match(rf"^\s+{re.escape(layer.subdir)}:\s*$", l) for l in body):
                notes.append(f"{layer.name}: {existing} already lists it")
                continue
            layers_line = next((first + 1 + k for k, l in enumerate(body) if re.match(r"^\s+layers:\s*$", l)), None)
            if layers_line is None:
                inserts.setdefault(last, []).extend(["    layers:", f"      {layer.subdir}:"])
            else:
                k = layers_line + 1
                while k < last and len(lines[k]) - len(lines[k].lstrip()) > 4:
                    k += 1
                inserts.setdefault(k, []).append(f"      {layer.subdir}:")
            notes.append(f"{layer.name}: added to the layers of {existing}")
            continue
        key, n = layer.repo, 2
        while key in blocks or key in new_repos:
            key, n = f"{layer.repo}-{n}", n + 1
        new_repos[key] = {"url": layer.url, "branch": layer.branch, "layers": [layer.subdir] if layer.subdir else []}
        notes.append(f"{layer.name}: new repository {key} ({layer.url}, branch {layer.branch})")
    additions = []
    for key, repo in new_repos.items():
        additions += [f"  {key}:", f"    url: {repo['url']}", f"    branch: {repo['branch']}"]
        if repo["layers"]:
            additions += ["    layers:", *[f"      {sub}:" for sub in repo["layers"]]]
    new_lines = list(lines)
    if additions:
        new_lines[end:end] = additions          # after every existing repository: inserts below sit above it
    for index in sorted(inserts, reverse=True):
        new_lines[index:index] = inserts[index]
    new_text = "\n".join(new_lines) + ("\n" if text.endswith("\n") or not text else "")
    return {"kind": "kas", "path": str(main), "name": main.name, "text": new_text, "notes": notes, "changed": new_text != text,
            "diff": "\n".join(difflib.unified_diff(text.splitlines(), new_text.splitlines(), fromfile=main.name, tofile=main.name, lineterm="", n=2))}


def checkout_plan(profile: Profile, layers: list[Layer], entries) -> dict:
    """Clones next to the other layers, then bitbake-layers add-layer, for BitBake on the machine or in a container."""
    from .studio import runtime_path
    upstream = [e.path for e in entries if e.kind == "layer" and e.name in ("meta", "meta-poky")]
    top = None
    for path in upstream:
        try:
            root = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            root = ""
        if root:
            top = Path(root).parent
            break
    top = top or (profile.root_path / "layers" if (profile.root_path / "layers").is_dir() else profile.root_path)
    steps, notes = [], []
    cloned: dict[str, Path] = {}
    for layer in (l for l in layers if not l.present):
        destination = top / layer.repo
        if layer.url not in cloned:
            if destination.exists():
                notes.append(f"{destination} exists: using it as it is")
            else:
                steps.append({"title": f"Clone {layer.repo}", "argv": ["git", "clone", "--branch", layer.branch, "--", layer.url, str(destination)], "where": "host"})
            cloned[layer.url] = destination
        path = cloned[layer.url] / layer.subdir if layer.subdir else cloned[layer.url]
        steps.append({"title": f"Add {layer.name}", "argv": ["bitbake-layers", "add-layer", runtime_path(profile, path)], "where": "profile"})
    return {"kind": "checkout", "top": str(top), "steps": steps, "notes": notes}


def plan(profile: Profile, layers: list[Layer], entries) -> dict:
    if profile.mode in ("kas", "kas-container", "wrapper"):
        return kas_plan(profile, layers)
    return checkout_plan(profile, layers, entries)


def apply_kas(profile: Profile, state: Path, result: dict) -> dict:
    """Write the kas file; the original goes to the same backups as the migration's (one Undo for both)."""
    import shutil
    path = Path(result["path"]).resolve()
    if profile.root_path.resolve() not in path.parents:
        raise ValueError(f"{path} is outside the project: not changed")
    if path.read_text(errors="replace") == result["text"]:
        return {"written": [], "backup": ""}
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = Path(state) / "migration-backups" / stamp
    copy = backup / str(path).lstrip("/")
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, copy)
    temporary = path.with_name(path.name + ".bitloom-tmp")
    temporary.write_text(result["text"])
    temporary.chmod(path.stat().st_mode)
    temporary.replace(path)
    (backup / "manifest.json").write_text(json.dumps({"profile": profile.name, "files": [str(path)], "at": stamp, "why": "add layer"}, indent=2))
    return {"written": [str(path)], "backup": str(backup)}


def describe(layers: list[Layer]) -> list[dict]:
    return [{**asdict(l), "repo": l.repo} for l in layers]
