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
    return '\n'.join([f'Build report: {path}', f'Errors: {len(errors)} · Warnings: {len(warnings)}', '', *sstate, task, '', 'Failed tasks', *failed[-100:], '', 'Errors', *errors[-100:], '', 'Warnings', *warnings[-100:]])
