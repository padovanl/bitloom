"""Read-only daily diagnostics for metadata, image manifests and build logs."""
from collections import Counter
from pathlib import Path
import re


def metadata_search(entries, query: str, limit: int = 1000) -> str:
    if not query.strip():
        raise ValueError('Enter a literal search phrase')
    matches, skipped, checked = [], 0, set()
    needle = query.casefold()
    for entry in entries:
        path = entry.path / 'conf/layer.conf' if entry.kind == 'layer' else entry.path
        if path in checked:
            continue
        checked.add(path)
        try:
            if path.stat().st_size > 2_000_000:
                skipped += 1
                continue
            with path.open(errors='replace') as source:
                for number, line in enumerate(source, 1):
                    if needle in line.casefold():
                        matches.append(f'{path}:{number}: {line.rstrip()[:300]}')
                        if len(matches) >= limit:
                            return '\n'.join([f'Metadata search: {query}', f'Result limit reached: {limit}', *matches])
        except OSError:
            skipped += 1
    return '\n'.join([f'Metadata search: {query}', f'Matches: {len(matches)} · files considered: {len(checked)} · skipped: {skipped}', 'Local indexed metadata, including inactive layers; literal case-insensitive search.', '', *matches])


def read_manifest(path: Path) -> dict[tuple[str, str], str]:
    packages = {}
    with path.open(errors='replace') as source:
        for number, line in enumerate(source, 1):
            if number > 100000:
                raise ValueError('Manifest exceeds the 100,000-line limit')
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            fields = line.split()
            if len(fields) not in {2, 3}:
                raise ValueError(f'Invalid manifest row at {path}:{number}; expected package [architecture] version')
            name, architecture, version = (fields[0], fields[1], fields[2]) if len(fields) == 3 else (fields[0], '', fields[1])
            key = (name, architecture)
            if key in packages and packages[key] != version:
                raise ValueError(f'Conflicting versions for {name} / {architecture} at {path}:{number}')
            packages[key] = version
    return packages


def manifest_diff(before: Path, after: Path) -> str:
    old, new = read_manifest(before), read_manifest(after)
    added, removed = new.keys()-old.keys(), old.keys()-new.keys()
    changed = [key for key in old.keys() & new.keys() if old[key] != new[key]]
    def label(key):
        return key[0] + (f' [{key[1]}]' if key[1] else '')
    return '\n'.join([f'Image manifest comparison\nBefore: {before}\nAfter: {after}', f'Added: {len(added)} · Removed: {len(removed)} · Version changes: {len(changed)}', '', 'ADDED', *[f'+ {label(k)} {new[k]}' for k in sorted(added)], '', 'REMOVED', *[f'- {label(k)} {old[k]}' for k in sorted(removed)], '', 'VERSION CHANGES', *[f'~ {label(k)} {old[k]} -> {new[k]}' for k in sorted(changed)], '', 'Package architecture is part of identity. An architecture change appears as removal/addition.'])


def sstate_report(path: Path) -> str:
    summaries = []
    pattern = re.compile(r'Sstate summary:\s*Wanted (\d+) Local (\d+) Mirrors (\d+) Missed (\d+)(?: Current (\d+))?')
    with path.open(errors='replace') as source:
        for line in source:
            if line.startswith('$ '):
                continue
            match = pattern.search(line)
            if not match:
                continue
            wanted, local, mirrors, missed = map(int, match.groups()[:4])
            current = int(match[5]) if match[5] is not None else None
            hit = f'{100*(local+mirrors)/wanted:.1f}%' if wanted else 'n/a (no wanted tasks)'
            coverage = f'{100*(local+mirrors+current)/(wanted+current):.1f}%' if current is not None and wanted+current else 'n/a'
            summaries.append(f'Wanted {wanted} · Local {local} · Mirrors {mirrors} · Missed {missed} · Current {current if current is not None else "unreported"}\n  Wanted-task cache hit rate: {hit}\n  Coverage including current tasks: {coverage}')
    return '\n\n'.join([f'Shared-state analysis: {path}', *summaries[-100:], 'No sstate summary found.' if not summaries else 'Rates derive from reported task counts. This report does not determine cache reachability or estimate saved build time.'])


def warning_report(path: Path) -> str:
    warnings = Counter()
    with path.open(errors='replace') as source:
        for line in source:
            if not line.startswith('$ ') and 'WARNING:' in line:
                warnings[line.split('WARNING:', 1)[1].strip()] += 1
    return '\n'.join([f'Warning groups: {path}', f'Occurrences: {sum(warnings.values())} · distinct messages: {len(warnings)}', 'Exact messages are grouped after removing timestamp/logger prefixes.', '', *[f'{count:5} × {message}' for message, count in warnings.most_common(200)]])
