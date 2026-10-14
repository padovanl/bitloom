"""Structured analysis of real outputs, independent of BitBake Python internals."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .models import Profile
from .store import Store


VARIABLE = re.compile(r'^(?:export )?([A-Za-z_][\w:.-]*)="(.*)"$')


def environment(path: Path) -> dict[str, str]:
    result = {}
    with path.open(errors='replace') as source:
        for line in source:
            match = VARIABLE.match(line.rstrip('\n'))
            if match:
                result[match[1]] = match[2]
    return result


def environment_jobs(store: Store, profile: Profile, target: str = '') -> list[dict]:
    result = []
    for job in store.history():
        data = json.loads(job['metadata'])
        argv = json.loads(job['argv'])
        if job['profile'] == profile.name and data.get('action') == 'environment' and job['status'] == 'success' and (not target or target in argv):
            result.append(job)
    return result


def env_diff(first: dict[str, str], second: dict[str, str]) -> str:
    lines = []
    for key in sorted(first.keys() | second.keys()):
        if first.get(key) != second.get(key):
            lines += [key, f"  - {first.get(key, '<unset>')}", f"  + {second.get(key, '<unset>')}", '']
    return '\n'.join(lines) or 'No changed literal environment variables.'


def dependencies(path: Path) -> list[tuple[str, str]]:
    edges = []
    with path.open(errors='replace') as source:
        for line in source:
            if line.startswith("$ "):
                continue
            match = re.search(r'"([^"\n]+)"\s*->\s*"([^"\n]+)"', line)
            if match:
                edges.append(match.groups())
            if len(edges) >= 20000:
                break
    return edges


def build_history(profile: Profile) -> str:
    path = profile.build_path / 'buildhistory'
    if not path.is_dir():
        return 'No buildhistory directory. Enable INHERIT += "buildhistory" and BUILDHISTORY_COMMIT = "1" in local.conf.'
    lines = [f'Build history: {path}', '']
    for args in (['log', '-5', '--oneline', '--stat'], ['diff', 'HEAD~1', 'HEAD', '--']):
        try:
            result = subprocess.run(['git', '-C', str(path), *args], text=True, capture_output=True, timeout=20)
            lines.append(result.stdout if result.returncode == 0 else result.stderr)
        except (OSError, subprocess.TimeoutExpired) as exc:
            lines.append(str(exc))
    return '\n'.join(lines)


def download_audit(root: Path, entries) -> str:
    files = {e.path for e in entries}
    orphan = [e.path for e in entries if e.name.endswith('.done') and e.path.with_name(e.name[:-5]) not in files and not e.path.with_name(e.name[:-5]).exists()]
    locks = [e.path for e in entries if e.name.endswith('.lock')]
    partial = [e.path for e in entries if e.name.endswith(('.tmp', '.part'))]
    lines = [f'Download inventory audit: {root}', f'Indexed files: {len(entries)} (bounded inventory)', '', 'This is a structural audit. Run bitbake -c fetch RECIPE for authoritative SRC_URI checksum validation.', 'Lock file presence does not prove a lock is currently held.', '', f'Orphan completion markers: {len(orphan)}', *map(str, orphan[:100]), '', f'Lock files: {len(locks)}', *map(str, locks[:100]), '', f'Possible partial downloads: {len(partial)}', *map(str, partial[:100])]
    return '\n'.join(lines)


def build_summary(path: Path) -> str:
    errors, warnings, failed, sstate = [], [], [], []
    task = ''
    with path.open(errors='replace') as source:
        for line in source:
            line = line.rstrip()
            if 'ERROR:' in line:
                errors.append(line)
            if 'WARNING:' in line:
                warnings.append(line)
            if 'failed with exit code' in line:
                failed.append(line)
            if 'Sstate summary:' in line:
                sstate.append(line)
            if 'Tasks Summary:' in line:
                task = line
    def section(title, lines):
        return ['', title, *(lines[-100:] or ['  none'])]
    head = [f'Build report: {path}', f'Errors: {len(errors)} · Warnings: {len(warnings)}']
    if sstate or task:
        head += ['', *sstate, *([task] if task else [])]
    return '\n'.join(head + section('Failed tasks', failed) + section('Errors', errors) + section('Warnings', warnings))


def dependency_context(edges: list[tuple[str, str]], node: str, limit: int = 200) -> str:
    """Walk both directions without looping on cycles in BitBake DOT graphs."""
    from collections import defaultdict, deque
    forward, reverse = defaultdict(set), defaultdict(set)
    for parent, dependency in edges:
        forward[parent].add(dependency)
        reverse[dependency].add(parent)
    if node not in forward and node not in reverse:
        raise ValueError('Enter an exact task/node name from the loaded graph')

    def walk(graph):
        queue = deque([(node, 0)])
        seen, result = {node}, []
        while queue and len(result) < limit:
            current, depth = queue.popleft()
            for child in sorted(graph[current]):
                if child not in seen:
                    seen.add(child)
                    result.append(f'{depth+1:>3}  {child}')
                    queue.append((child, depth+1))
        return result
    return '\n'.join([f'Dependency context: {node}', 'Numbers indicate shortest graph distance. Each direction is bounded.', '', 'REQUIRES / transitive dependencies', *walk(forward), '', 'REQUIRED BY / reverse dependencies', *walk(reverse)])


def image_contents(path: Path, limit: int = 20000) -> str:
    """Inspect tar rootfs metadata without extracting or following archive links."""
    import tarfile
    try:
        with tarfile.open(path, 'r:*') as archive:
            lines, total, count = [], 0, 0
            for item in archive:
                count += 1
                if count > limit:
                    lines.append(f'Inventory truncated at {limit} entries')
                    break
                total += item.size if item.isfile() else 0
                kind = 'dir' if item.isdir() else 'link' if item.issym() or item.islnk() else 'file' if item.isfile() else 'special'
                link = f' -> {item.linkname}' if item.issym() or item.islnk() else ''
                lines.append(f'{kind:7} {item.mode:04o} {item.uid:5}:{item.gid:<5} {item.size:10} {item.name}{link}')
    except tarfile.TarError as exc:
        raise ValueError('Select a tar rootfs archive (.tar, .tar.gz, .tar.bz2, .tar.xz)') from exc
    return '\n'.join([f'Root filesystem: {path}', f'Indexed entries: {min(count, limit)} · regular-file bytes: {total}', 'Read-only archive inspection; nothing was extracted.', '', 'TYPE    MODE UID:GID           BYTES PATH', *lines])


def task_timings(path: Path) -> str:
    """Use observed timestamps; never infer durations from line positions."""
    from datetime import datetime
    running, complete = {}, []
    with path.open(errors='replace') as source:
        for line in source:
            stamp = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            event = re.search(r'recipe (\S+): task (\S+): (Started|Succeeded|Failed)', line)
            if not stamp or not event:
                continue
            timestamp = datetime.strptime(stamp[1], '%Y-%m-%d %H:%M:%S')
            key = (event[1], event[2])
            if event[3] == 'Started':
                running[key] = timestamp
            elif key in running:
                seconds = (timestamp-running.pop(key)).total_seconds()
                if seconds >= 0:
                    complete.append((seconds, *key, event[3]))
    if not complete:
        return 'No completed timestamped task pairs found. kas timestamped output is supported. Plain BitBake output does not provide timings; enable buildstats and inspect its artifacts.'
    rows = [f'{seconds:9.0f}s  {recipe:45} {task:30} {status}' for seconds, recipe, task, status in sorted(complete, reverse=True)[:200]]
    return '\n'.join([f'Observed task timings: {path}', f'Completed pairs: {len(complete)} · unmatched starts: {len(running)}', 'Sorted by wall duration. Tasks overlap; summed durations are not build elapsed time.', '', *rows])


IMAGE_SUFFIXES = (".wic", ".wic.gz", ".wic.bz2", ".wic.xz", ".wic.zst", ".ext4", ".ext3", ".ext2", ".tar.bz2", ".tar.gz", ".tar.xz",
                  ".tar.zst", ".squashfs", ".squashfs-xz", ".ubi", ".ubifs", ".jffs2", ".cpio.gz", ".iso", ".hddimg", ".sdimg", ".rpi-sdimg",
                  ".swu", ".fitImage", ".itb")


def image_matrix(profile: Profile) -> str:
    """Every image of every MACHINE in tmp/deploy/images, newest first, with package counts."""
    from datetime import datetime
    from .inspectors import human_size
    root = profile.build_path / 'tmp/deploy/images'
    if not root.is_dir():
        return f'No deployed images under {root}. Build an image for at least one MACHINE first.'
    lines = [f'Image matrix: {root}', 'One block per MACHINE. Symlinks are the stable names BitBake points at the newest build.', '']
    machines = sorted(p for p in root.iterdir() if p.is_dir())
    for machine in machines:
        images, manifests = [], {}
        for path in machine.iterdir():
            if path.name.endswith('.manifest') and not path.is_symlink():
                try:
                    manifests[path.name[:-9]] = sum(1 for line in path.read_text(errors='replace').splitlines() if line.strip())
                except OSError:
                    pass
            elif path.name.endswith(IMAGE_SUFFIXES) and path.is_file() and not path.is_symlink():
                images.append(path)
        images.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        lines.append(f'{machine.name}  ·  {len(images)} image file{"s" if len(images) != 1 else ""}  ·  {len(manifests)} manifest{"s" if len(manifests) != 1 else ""}')
        for path in images[:40]:
            stat = path.stat()
            stem = next((name for name in manifests if path.name.startswith(name)), '')
            packages = f'{manifests[stem]} packages' if stem else ''
            lines.append(f'  {datetime.fromtimestamp(stat.st_mtime):%Y-%m-%d %H:%M}  {human_size(stat.st_size):>10}  {path.name}  {packages}')
        lines.append('')
    sdk = profile.build_path / 'tmp/deploy/sdk'
    if sdk.is_dir():
        installers = sorted(p for p in sdk.iterdir() if p.name.endswith('.sh') and p.is_file())
        lines.append(f'SDK installers: {len(installers)}')
        lines += [f'  {human_size(p.stat().st_size):>10}  {p.name}' for p in installers[:20]]
    return '\n'.join(lines)
