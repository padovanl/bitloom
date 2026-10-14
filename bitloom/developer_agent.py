"""Portable standard-library probes executed inside the selected Yocto runtime.

This file is sent as source to containers; it deliberately imports no Bitloom modules.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

LIMIT = 32 * 1024 * 1024


def read(path, limit=2 * 1024 * 1024):
    path = Path(path)
    if path.stat().st_size > limit:
        raise ValueError(f'{path}: exceeds {limit} byte read limit')
    return path.read_text(errors='replace')


def run(argv, timeout=90):
    with tempfile.TemporaryFile() as output:
        try:
            process = subprocess.run(argv, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {'argv': argv, 'exit_code': -1, 'output': str(exc)}
        output.seek(0)
        data = output.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise ValueError('Runtime command output exceeds 32 MiB; narrow the query')
        return {'argv': argv, 'exit_code': process.returncode, 'output': data.decode(errors='replace')}


def checked(argv):
    result = run(argv)
    if result['exit_code']:
        raise ValueError(result['output'][-4000:])
    return result['output']


def target(value):
    if not re.fullmatch(r'(?:mc:[A-Za-z0-9_.-]+:)?(?:virtual/)?[A-Za-z0-9][A-Za-z0-9+_.-]*', value):
        raise ValueError('Enter one recipe or mc:CONFIG:RECIPE target')
    return value


def values(text):
    return dict(re.findall(r'^(?:export )?([A-Za-z0-9_:+.-]+)="(.*?)"(?=\n|$)', text, re.M | re.S))


def evaluated(recipe):
    return values(checked(['bitbake', '-e', target(recipe)]))


def stamp(path, hashes=True):
    path = Path(path)
    try:
        stat = path.stat()
        return {'path': str(path), 'mtime_ns': stat.st_mtime_ns, 'size': stat.st_size,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest() if hashes and path.is_file() and stat.st_size <= 2097152 else None}
    except OSError:
        return {'path': str(path), 'missing': True}


def report(title, rows=(), text='', **data):
    return {'title': title, 'rows': list(rows), 'text': text, 'captured': time.time(), **data}


def origins(text):
    entries = []
    for line in text.splitlines():
        if not line.lstrip().startswith('#'):
            continue
        match = re.search(r'(/[^\n]+?):(\d+)(?:\s|$)', line)
        if match:
            entries.append({'name': line.lstrip('# ').split(' /', 1)[0], 'value': line.lstrip('# '),
                            'path': match[1], 'line': int(match[2])})
    return entries


def variable(recipe, name):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_:+.-]*', name):
        raise ValueError('Enter one variable or task function name')
    if recipe.startswith('mc:') or not shutil.which('bitbake-getvar'):
        # Older getvar/tinfoil versions do not accept mc:CONFIG:RECIPE in -r.
        complete = checked(['bitbake', '-e'] + ([target(recipe)] if recipe else []))
        lines = complete.splitlines()
        start = next((i for i, line in enumerate(lines) if re.match(r'^# \$' + re.escape(name) + r'(?:\s|$)', line)), None)
        if start is None:
            output = name + '=' + json.dumps(values(complete).get(name, 'unavailable'))
        else:
            end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('# $')), len(lines))
            output = '\n'.join(lines[start:end])
        overrides = values(complete).get('OVERRIDES')
    else:
        argv = ['bitbake-getvar'] + (['-r', target(recipe)] if recipe else []) + [name]
        output = checked(argv)
        override = run(['bitbake-getvar'] + (['-r', recipe] if recipe else []) + ['OVERRIDES'])
        overrides = values(override['output']).get('OVERRIDES')
    rows = [{'name': name, 'value': values(output).get(name, 'See raw evaluated output')}]
    rows += origins(output)
    active_overrides = set((overrides or '').split(':'))
    for row in rows:
        condition = re.search(r'override\[([^]]+)\]', row['name'])
        if condition:
            row['active_override_context'] = set(condition[1].split(':')).issubset(active_overrides)
            row['name'] = ('active ' if row['active_override_context'] else 'inactive ') + row['name']
    rows += [{'name': 'OVERRIDES', 'value': overrides or 'unavailable'},
             {'name': 'Datastore', 'value': recipe or '(global)'}]
    return report('VARIABLE ASSIGNMENT HISTORY', rows, output,
                  variable=name, recipe=recipe or '(global)', overrides=overrides,
                  fingerprints=[stamp(p) for p in sorted({r['path'] for r in rows if 'path' in r})],
                  context='Recipe datastore; task functions may have task-specific overrides. Global and recipe values are separate.')


def append_paths(output, filename):
    selected = False
    paths = []
    for line in output.splitlines():
        if line and not line[0].isspace() and '.bb' in line:
            selected = Path(filename).name in line
        if selected:
            paths += re.findall(r'(/[^\n]+\.bbappend)\s*$', line)
    return paths


def recipe_context(recipe):
    env = evaluated(recipe)
    appends = run(['bitbake-layers', 'show-appends'])
    paths = env.get('__BBAPPEND', '').split() or append_paths(appends['output'], env.get('FILE', ''))
    rows = []
    for name in ('PN', 'PV', 'PR', 'FILE', 'MACHINE', 'DISTRO', 'BB_CURRENT_MC', 'DL_DIR', 'SSTATE_DIR', 'BUILDHISTORY_DIR', 'PKGDATA_DIR', 'BBLAYERS', 'WORKDIR', 'S', 'B', 'T',
                 'RECIPE_SYSROOT', 'RECIPE_SYSROOT_NATIVE', 'SRC_URI', 'SRCREV', 'LICENSE', 'OVERRIDES'):
        value = env.get(name, 'unavailable')
        rows.append({'name': name, 'value': value, **({'path': value} if value.startswith('/') and name != 'SRC_URI' else {})})
    rows += [{'name': 'active append', 'value': p, 'path': p} for p in paths]
    temp = Path(env.get('T', '/nonexistent'))
    if temp.is_dir():
        rows += [{'name': 'task evidence', 'value': p.name, 'path': str(p)}
                 for p in sorted(temp.iterdir(), key=lambda p: p.lstat().st_mtime, reverse=True)[:100]
                 if p.name.startswith(('log.do_', 'run.do_'))]
    providers = run(['bitbake-layers', 'show-recipes', recipe.split(':')[-1]])
    return report('EVALUATED RECIPE CONTEXT', rows, providers['output'] + '\nACTIVE APPENDS\n' + appends['output'],
                  recipe=recipe, identity={k: env.get(k) for k in ('PN', 'PV', 'MACHINE', 'DISTRO', 'BB_CURRENT_MC')},
                  fingerprints=[stamp(p) for p in [env.get('FILE', ''), *paths] if p])


def browse(path, query=''):
    folder = Path(path).resolve()
    rows = [{'name': '..', 'value': 'parent directory', 'path': str(folder.parent), 'directory': True}]
    truncated = False
    if query:
        iterator = folder.rglob('*')
    else:
        iterator = sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    scanned = 0
    for entry in iterator:
        scanned += 1
        if scanned > 20000 or len(rows) >= 2000:
            truncated = True
            break
        if query and query.lower() not in str(entry.relative_to(folder)).lower():
            continue
        stat = entry.lstat()
        rows.append({'name': str(entry.relative_to(folder)), 'value': f'{stat.st_size} bytes',
                     'path': str(entry), 'directory': entry.is_dir(), 'symlink': entry.is_symlink()})
    return report('RUNTIME FILE BROWSER', rows, 'Enter a row to descend or open the runtime editor.',
                  path=str(folder), truncated=truncated, fingerprint_hashes=False,
                  fingerprints=[stamp(p, False) for p in dict.fromkeys([str(folder), *[r['path'] for r in rows]])])


def capabilities(recipe):
    tools = {name: shutil.which(name) for name in ('bitbake', 'bitbake-getvar', 'bitbake-layers', 'devtool',
                                                 'runqemu', 'git', 'cmake', 'gdb', 'kas')}
    version = run(['bitbake', '--version'])
    tasks = run(['bitbake', '-c', 'listtasks', target(recipe)]) if tools['bitbake'] else version
    task_names = sorted(set(re.findall(r'^\s*(do_[A-Za-z0-9_]+)\s', tasks['output'], re.M)))
    ide = run(['devtool', 'ide-sdk', '--help']) if tools['devtool'] else {'exit_code': -1, 'output': 'devtool unavailable'}
    env = evaluated(recipe) if tasks['exit_code'] == 0 else {}
    rows = [{'name': name, 'value': path or 'unavailable'} for name, path in tools.items()]
    rows += [{'name': 'task', 'value': name} for name in task_names]
    rows += [{'name': 'IDE bridge', 'value': 'available' if ide['exit_code'] == 0 else 'unavailable'},
             {'name': 'DISPLAY', 'value': os.environ.get('DISPLAY', 'unset')},
             {'name': '/dev/kvm', 'value': 'accessible' if os.access('/dev/kvm', os.R_OK | os.W_OK) else 'unavailable'},
             {'name': 'Yocto release', 'value': env.get('DISTRO_VERSION', 'unknown')}]
    return report('RUNTIME CAPABILITIES', rows, version['output'] + '\n' + tasks['output'], tools=tools,
                  tasks=task_names, task_probe_ok=tasks['exit_code'] == 0, ide_sdk=ide['exit_code'] == 0,
                  recipe=recipe, identity={k: env.get(k) for k in ('MACHINE', 'DISTRO', 'DISTRO_VERSION')},
                  multiconfig=env.get('BBMULTICONFIG', '').split(), terminal='Interactive operations also require the local real terminal.')


def rebuild(recipe, build):
    env = evaluated(recipe)
    stamps = Path(env.get('STAMPS_DIR', str(Path(build) / 'tmp/stamps')))
    groups = {}
    for count, path in enumerate(stamps.rglob('*.sigdata.*')):
        if count >= 20000:
            break
        if recipe.split(':')[-1] not in path.parts:
            continue
        groups.setdefault((str(path.parent), path.name.split('.sigdata.')[0]), []).append(path)
    rows, pairs = [], []
    for (_, task), paths in sorted(groups.items()):
        paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        if len(paths) < 2:
            rows.append({'name': task, 'value': 'Only one signature; baseline unavailable', 'path': str(paths[0])})
            continue
        result = run(['bitbake-diffsigs', str(paths[1]), str(paths[0])])
        changes = re.findall(r'Variable ([A-Za-z0-9_:+.-]+)', result['output'])
        rows.append({'name': task, 'value': ', '.join(changes) or result['output'][:180], 'path': str(paths[0]), 'evidence':result['output']})
        pairs.append({'task': task, 'before': str(paths[1]), 'after': str(paths[0]), **result})
        if len(pairs) >= 100:
            break
    difference = run(['bitbake', '-S', 'printdiff', target(recipe)])
    graph = run(['bitbake', '-g', recipe])
    edges = []
    graph_path = Path('task-depends.dot')
    if graph['exit_code'] == 0 and graph_path.is_file():
        edges = re.findall(r'"([^"]+)"\s*->\s*"([^"]+)"', read(graph_path, LIMIT))[:20000]
    impacted = {pair['task'] for pair in pairs if pair['exit_code'] == 0 and pair['output'].strip() and 'No differences' not in pair['output']}
    nodes = {a for a, _ in edges if any(a.endswith('.' + task) and recipe.split(':')[-1] in a for task in impacted)}
    dependents = set(nodes)
    for _ in range(200):
        added = {a for a, b in edges if b in dependents} - dependents
        if not added or len(dependents) > 2000:
            break
        dependents |= added
    rows += [{'name': 'dependent task', 'value': node} for node in sorted(dependents - nodes)[:200]]
    rows += [{'name': name, 'value': env.get(name, 'unset')} for name in ('SSTATE_DIR', 'SSTATE_MIRRORS', 'BB_HASHSERVE')]
    signatures = {Path(pair['after']).name.split('.sigdata.')[-1] for pair in pairs}
    local = {signature: [] for signature in signatures}
    cache = Path(env.get('SSTATE_DIR', '/nonexistent'))
    scanned = 0
    for file in cache.rglob('*.siginfo'):
        scanned += 1
        if scanned > 20000: break
        for signature in signatures:
            if signature in file.name: local[signature].append(str(file))
    rows += [{'name': 'local signature ' + signature[:12], 'value': f'{len(paths)} candidate references' if paths else 'not seen in bounded scan; remote/equivalent reuse unknown'} for signature, paths in local.items()]
    return report('REBUILD SIGNATURE EVIDENCE', rows,
                  difference['output'] + '\nMissing pairs are incomplete evidence. Dependencies show possible impact, not a guaranteed execution count.',
                  recipe=recipe, pairs=pairs, printdiff=difference, dependency_nodes=sorted(dependents)[:2000], local_cache_candidates=local, cache_scan_truncated=scanned>20000,
                  values={name: env.get(name) for pair in pairs for name in re.findall(r'Variable ([A-Za-z0-9_:+.-]+)', pair['output'])})


def failure(path, text=None):
    text = read(path, LIMIT) if text is None else text
    log_paths = list(dict.fromkeys(re.findall(r'Logfile of failure stored in:\s*(\S+)', text)))[:10]
    rows, evidence = [], []
    for name in log_paths or [path]:
        log = Path(name)
        if not log.is_file() and not (name == path and not log_paths):
            rows.append({'name': 'unavailable task log', 'value': name})
            continue
        data = read(log) if log.is_file() else text
        rows.append({'name': 'task log', 'value': name, 'path': name})
        script = log.with_name(log.name.replace('log.do_', 'run.do_', 1))
        if script.exists():
            rows.append({'name': 'executed script', 'value': str(script), 'path': str(script)})
        lines = data.splitlines()
        for i, line in enumerate(lines):
            match = re.search(r'([^\s:]+\.(?:c|cpp|cc|h|rs|py)):(\d+)(?::\d+)?:.*(?:error|fatal)', line)
            if match:
                source = Path(match[1])
                # Relative compiler locations need an evaluated build directory; never invent a path.
                rows.append({'name': 'source diagnostic', 'value': line, 'path': str(source) if source.is_absolute() else '', 'line': int(match[2])})
            if re.search(r'(error:|fatal:|ERROR:|FAILED|QA Issue)', line, re.I):
                evidence.append({'log': name, 'line': i + 1, 'context': '\n'.join(lines[max(0, i-3):i+7])})
                if len(evidence) >= 30:
                    break
    return report('FAILED TASK INVESTIGATION', rows, '\n\n'.join(e['context'] for e in evidence) or text[-12000:],
                  diagnostics=evidence, log_paths=log_paths, first_diagnostic_is_root_cause=False)


def resources(build):
    rows = []
    for name in ('cpu.max', 'memory.max', 'memory.current', 'memory.events', 'cpu.stat'):
        path = Path('/sys/fs/cgroup') / name
        rows.append({'name': 'cgroup ' + name, 'value': read(path).strip() if path.is_file() else 'unavailable'})
    for kind in ('cpu', 'memory', 'io'):
        path = Path('/proc/pressure') / kind
        rows.append({'name': 'pressure ' + kind, 'value': read(path).strip() if path.is_file() else 'unavailable'})
    path = Path(build)
    while not path.exists() and path != path.parent:
        path = path.parent
    stat = os.statvfs(path)
    rows += [{'name': 'runtime free bytes', 'value': str(stat.f_bavail * stat.f_frsize)},
             {'name': 'runtime free inodes', 'value': str(stat.f_favail)},
             {'name': 'runtime hostname', 'value': socket.gethostname()}]
    return rows


def performance(path, build):
    root = Path(path) if path else Path(build) / 'tmp/buildstats'
    sessions = sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True) if root.is_dir() else []
    def tasks(candidate, cap=10):
        return sum(1 for _ in zip(range(cap), candidate.glob('*/do_*')))
    # "Latest" means the latest real build: probes and parse-only runs leave sessions with no or few tasks.
    session = (next((s for s in sessions if tasks(s) >= 10), None) or next((s for s in sessions if tasks(s, 1)), None)
               or (sessions[0] if sessions else root)) if sessions and not any(p.name.startswith('do_') for p in root.glob('*/*')) else root
    entries = []
    for count, file in enumerate(session.rglob('do_*')):
        if count >= 10000:
            break
        if not file.is_file():
            continue
        text = read(file)
        fields = dict(re.findall(r'^([^:\n]+):\s*(.*)$', text, re.M))
        def number(key):
            try:
                return float(fields.get(key, '').split()[0])
            except (ValueError, IndexError):
                return None
        started, ended = number('Started'), number('Ended')
        duration = number('Elapsed time')
        if duration is None and started is not None and ended is not None:
            duration = ended - started
        entries.append({'task': str(file.relative_to(session)), 'path': str(file), 'seconds': duration,
                        'started': started, 'ended': ended, 'fields': fields})
    entries.sort(key=lambda e: e['seconds'] or 0, reverse=True)
    rows = [{'name': e['task'], 'value': f"{e['seconds']:.2f}s" if e['seconds'] is not None else 'duration unavailable', 'path': e['path']} for e in entries[:300]]
    rows += resources(build)
    starts = [e['started'] for e in entries if e['started'] is not None]
    ends = [e['ended'] for e in entries if e['ended'] is not None]
    wall = max(ends) - min(starts) if starts and ends else None
    timeline = []
    if wall and wall > 0:
        for entry in sorted(entries, key=lambda e: e['started'] or 0)[:200]:
            if entry['started'] is None or entry['ended'] is None:
                continue
            offset = int((entry['started'] - min(starts)) / wall * 40)
            length = max(1, int((entry['ended'] - entry['started']) / wall * 40))
            timeline.append(' ' * max(0, offset) + '━' * length + ' ' + entry['task'])
    return report('BUILD PERFORMANCE AND RUNTIME LIMITS', rows,
                  f'Stats: {session}\nObserved task span: {f"{wall:.1f} seconds" if wall is not None else "unavailable (no complete task timestamps)"}\n' + '\n'.join(timeline) +
                  '\nTask durations overlap. These limits apply to the probe runtime, not automatically to other jobs. No automatic tuning.',
                  buildstats=entries, wall_seconds=wall, available=bool(entries), session=str(session))


def image(recipe):
    env = evaluated(recipe)
    history = Path(env.get('BUILDHISTORY_DIR', 'buildhistory')) / 'images'
    matches = sorted(history.glob('**/' + recipe.split(':')[-1] + '/installed-package-sizes.txt'), key=lambda p: p.stat().st_mtime, reverse=True)
    machine = env.get('MACHINE_ARCH', env.get('MACHINE'))
    matching = [p for p in matches if (not machine or machine in p.parts) and (not env.get('TCLIBC') or env['TCLIBC'] in p.parts)]
    explicit = Path(env['BUILDHISTORY_DIR_IMAGE']) / 'installed-package-sizes.txt' if env.get('BUILDHISTORY_DIR_IMAGE') else None
    path = explicit if explicit and explicit.is_file() else matching[0] if matching else None
    packages, files = {}, {}
    if path:
        for line in read(path).splitlines():
            match = re.match(r'\s*(\d+)\s+(?:(KiB|MiB|B)\s+)?(\S+)', line)
            if match:
                packages[match[3]] = int(match[1]) * {'KiB':1024, 'MiB':1048576, 'B':1, None:1}[match[2]]
        listing = path.parent / 'files-in-image.txt'
        if listing.exists():
            for line in read(listing, LIMIT).splitlines():
                # Buildhistory uses an ls-style inventory; preserve complete descriptors.
                match = re.search(r'\s(\./[^\n]+|/[^\n]+)$', line)
                if match:
                    filename = match[1].split(' -> ', 1)[0]
                    files[filename] = line
    pkgdir = Path(env.get('PKGDATA_DIR', '/nonexistent')) / 'runtime'
    owners, size_sources = {}, {package:'buildhistory (rounded KiB normalized to bytes)' for package in packages}
    for package in packages:
        file = pkgdir / package
        if not file.is_file(): file = pkgdir.parent / 'runtime-reverse' / package
        if file.is_file():
            text = read(file)
            match = re.search(r'^PN: (.+)$', text, re.M)
            owners[package] = match[1] if match else None
            size = re.search(r'^PKGSIZE(?::[^:]+)?: (\d+)$', text, re.M)
            if size:
                packages[package] = int(size[1])
                size_sources[package] = 'pkgdata (exact bytes)'
    rows = [{'name': name, 'value': f'{size} bytes · {owners.get(name) or "recipe unavailable"}'}
            for name, size in sorted(packages.items(), key=lambda p: p[1], reverse=True)]
    return report('IMAGE REGRESSION BASELINE', rows,
                  'Capture, change the image, inspect again, then Compare with the saved capture.\n' +
                  ('Buildhistory: ' + str(path.parent) if path else 'Buildhistory image sizes unavailable; enable buildhistory and rebuild.'),
                  packages=packages, files=files, owners=owners, size_sources=size_sources, evidence_stamp=stamp(path,False) if path else None,
                  identity={key: env.get(key) for key in ('MACHINE', 'DISTRO', 'TCLIBC', 'BB_CURRENT_MC')}, image=recipe,
                  image_install=env.get('IMAGE_INSTALL'), available=bool(path))


def kernel(recipe, fragment, config):
    env = evaluated(recipe)
    config = config or str(Path(env['B']) / '.config')
    if not fragment:
        raise ValueError('Enter the requested kernel fragment path')
    def settings(text):
        result = dict(re.findall(r'^(CONFIG_\w+)=(.*)$', text, re.M))
        result.update({name: 'n' for name in re.findall(r'^# (CONFIG_\w+) is not set$', text, re.M)})
        return result
    requested, actual = settings(read(fragment)), settings(read(config))
    rows = [{'name': name, 'value': f'requested {value} · actual {actual.get(name, "absent")} · ' + ('MATCH' if actual.get(name) == value else 'MISMATCH'),
             'path': fragment} for name, value in sorted(requested.items())]
    return report('KERNEL FRAGMENT REVIEW', rows, 'Use kernel_configcheck for dependency/selection explanations.',
                  requested=requested, actual={name: actual.get(name) for name in requested}, recipe=recipe, config=config,
                  fingerprints=[stamp(fragment), stamp(config)])


def upgrade(recipe):
    result = recipe_context(recipe)
    env = evaluated(recipe)
    result['title'] = 'RECIPE AND LAYER UPGRADE BASELINE'
    result['version'] = {key: env.get(key) for key in ('PV', 'PR', 'SRCREV', 'SRC_URI', 'LICENSE', 'FILE', 'OVERRIDES')}
    result['layers'] = []
    for layer in env.get('BBLAYERS', '').split()[:100]:
        commit = run(['git', '-C', layer, 'rev-parse', 'HEAD'])
        branch = run(['git', '-C', layer, 'branch', '--show-current'])
        dirty = run(['git', '-C', layer, 'status', '--short'])
        entry = {'path': layer, 'commit': commit['output'].strip() if not commit['exit_code'] else None,
                 'branch': branch['output'].strip() if not branch['exit_code'] else None, 'changes': dirty['output'] if not dirty['exit_code'] else 'unavailable'}
        result['layers'].append(entry)
        result['rows'].append({'name': 'layer revision', 'value': layer + ' · ' + str(entry['commit']), 'path': layer, 'directory': True})
    result['patches'] = [uri for uri in env.get('SRC_URI', '').split() if '.patch' in uri or '.diff' in uri]
    result['text'] += '\nDEVTOOL WORKSPACE\n' + run(['devtool', 'status'])['output']
    for row in result['rows']:
        if row['name'] == 'S' and Path(row['value']).is_dir():
            result['source_changes'] = run(['git', '-C', row['value'], 'diff', '--stat'])
    return result


def downloads(recipe, log, text=None):
    env = evaluated(recipe)
    rows = [{'name': name, 'value': env.get(name, 'unset')} for name in
            ('DL_DIR', 'SRC_URI', 'PREMIRRORS', 'MIRRORS', 'BB_NO_NETWORK', 'BB_FETCH_PREMIRRORONLY', 'BB_GENERATE_MIRROR_TARBALLS')]
    text = text if text is not None else read(log, LIMIT) if log else ''
    patterns = [('checksum', r'checksum.*(mismatch|failed|does not match)'),
                ('DNS', r'(unable to resolve|name or service not known|temporary failure in name resolution)'),
                ('TLS', r'(certificate.*(failed|invalid|expired)|SSL.*(error|failed))'),
                ('access', r'(401 Unauthorized|403 Forbidden|Permission denied)'),
                ('missing source', r'(404 Not Found|repository.*not found|Unable to find file file://)'),
                ('proxy', r'(proxy.*(failed|refused|error))')]
    observations = []
    next_steps = {
        'checksum': 'Compare the fetched bytes with the authoritative upstream release; fix SRC_URI/checksum only after verifying the intended source. Never disable checksum validation.',
        'DNS': 'Check name resolution inside this build runtime and its proxy/network settings; host resolution may differ.',
        'TLS': 'Check runtime clock, trusted CA certificates and proxy CA configuration. Preserve TLS verification.',
        'access': 'Verify source URL permissions and credentials in the build runtime; keep secrets out of shared reports.',
        'missing source': 'Verify the release/tag/path and matching FILESEXTRAPATHS for local sources; inspect PREMIRRORS/MIRRORS for retained artifacts.',
        'proxy': 'Check the actual runtime proxy configuration and reachability, then retry the fetch explicitly.',
    }
    for name, pattern in patterns:
        lines = [line for line in text.splitlines() if re.search(pattern, line, re.I)][:10]
        if lines:
            observations.append({'category': name, 'evidence': lines, 'next_step': next_steps[name]})
            rows += [{'name': name, 'value': line} for line in lines]
            rows.append({'name': name + ' · next step', 'value': next_steps[name]})
    for uri in env.get('SRC_URI', '').split()[:100]:
        parsed = urlsplit(uri.split(';', 1)[0])
        if parsed.hostname:
            try:
                addresses = sorted({item[4][0] for item in socket.getaddrinfo(parsed.hostname, None)})
                rows.append({'name': parsed.hostname, 'value': 'DNS: ' + ', '.join(addresses)})
            except OSError as exc:
                rows.append({'name': parsed.hostname, 'value': 'DNS unavailable: ' + str(exc)})
    return report('FETCH AND MIRROR INVESTIGATION', rows,
                  'Mirror rules are evaluated metadata; DNS success alone does not prove authentication, TLS or artifact availability.\n'
                  'Prepare mirrors fetches with generated mirror tarballs. Verify offline disables BitBake network for fetch; Verify offline build checks the complete target. kas bootstrap may still need network.',
                  observations=observations, recipe=recipe, proxy_keys=[k for k in os.environ if k.lower().endswith('_proxy')])


def offline(recipe, full=False, prepare=False):
    # An ephemeral -R file changes only this invocation, including kas-container.
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as stream:
        stream.write('BB_GENERATE_MIRROR_TARBALLS = "1"\n' if prepare else 'BB_NO_NETWORK = "1"\n')
        name = stream.name
    try:
        argv = ['bitbake', '-R', name] + ([] if full else ['--runall=fetch']) + [target(recipe)]
        result = run(argv, timeout=3600)
        return report('SOURCE MIRROR PREPARATION' if prepare else 'OFFLINE VERIFICATION', text=result['output'],
                      exit_code=result['exit_code'], argv=argv, recipe=recipe, full_build=full, prepare=prepare)
    finally:
        Path(name).unlink(missing_ok=True)


def security(path):
    data = json.loads(read(path, LIMIT))
    if not isinstance(data, dict) or not any(key in data for key in ('package', 'packages', 'spdxVersion')):
        raise ValueError('Unsupported CVE/SPDX JSON report; select an actual supported report')
    packages = data.get('package', data.get('packages', []))
    if isinstance(packages, dict):
        packages = [{'name': name, **value} for name, value in packages.items()]
    issues, components = [], []
    for package in packages:
        name = package.get('name', package.get('package_name', 'unknown'))
        components.append({'name': name, 'version': package.get('version', package.get('versionInfo')),
                           'license': package.get('licenseDeclared', package.get('license'))})
        for issue in package.get('issue', package.get('issues', [])):
            issues.append({'package': name, 'id': issue.get('id', issue.get('cve', 'unknown')),
                           'status': issue.get('status', 'unknown'), 'summary': issue.get('summary', ''), 'link': issue.get('link')})
    rows = [{'name': e['package'] + ' · ' + e['id'], 'value': e['status'] + ' · ' + e['summary'], 'issue': e} for e in issues]
    rows += [{'name': e['name'], 'value': f"{e['version']} · {e['license']}"} for e in components]
    return report('IMAGE CVE AND SBOM REVIEW', rows,
                  'Report findings require product/platform/configuration review; status does not establish exploitability.\n'
                  'Recorded dispositions do not change upstream vulnerability status.',
                  issues=issues, components=components, source=stamp(path),
                  report_metadata={k: data.get(k) for k in ('version', 'spdxVersion', 'creationInfo', 'date', 'database_version') if k in data},
                  recognized=bool(packages), fingerprints=[stamp(path)])


def ide(recipe):
    env = evaluated(recipe)
    help_result = run(['devtool', 'ide-sdk', '--help'])
    source = Path(env.get('S', '/nonexistent'))
    rows = [{'name': key, 'value': env.get(key, 'unavailable'), **({'path': env[key]} if env.get(key, '').startswith('/') else {})}
            for key in ('S', 'B', 'RECIPE_SYSROOT', 'RECIPE_SYSROOT_NATIVE', 'CC', 'CXX', 'TARGET_ARCH')]
    if source.is_dir():
        for pattern in ('.vscode/*.json', '*Presets.json', 'compile_commands.json'):
            rows += [{'name': 'IDE configuration', 'value': str(p), 'path': str(p)} for p in source.glob(pattern)]
    database = Path(env.get('B', '/nonexistent')) / 'compile_commands.json'
    if database.is_file(): rows.append({'name': 'Compile database', 'value': str(database), 'path': str(database)})
    return report('IDE AND SDK BRIDGE', rows, help_result['output'], recipe=recipe,
                  ide_sdk=help_result['exit_code'] == 0, source=str(source), architecture=env.get('TARGET_ARCH'))


def scaffold(path, files):
    destination = Path(path)
    if not destination.is_absolute() or destination.exists() or destination.is_symlink():
        raise ValueError('Choose a new absolute layer directory; existing paths are preserved')
    if not files or len(files) > 50:
        raise ValueError('Scaffold requires 1–50 files')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.bitloom-layer-', dir=destination.parent))
    try:
        for name, text in files.items():
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts or len(text.encode()) > 2097152:
                raise ValueError('Invalid scaffold file')
            file = temporary / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text)
        # Linux renameat2 is unnecessary: mkdir reserves the destination without overwriting.
        destination.mkdir()
        try:
            for file in temporary.iterdir():
                file.rename(destination / file.name)
        except Exception:
            shutil.rmtree(destination)
            raise
        return report('LAYER SCAFFOLD CREATED', [{'name': name, 'value': str(destination / name), 'path': str(destination / name)} for name in files],
                      'Register through the previewed kas overlay or bitbake-layers add-layer, then Parse/build.', path=str(destination))
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def shutdown(build):
    path = Path(build)
    rows = []
    for name in ('bitbake.lock', 'bitbake-cookerdaemon.log', 'bitbake.sock'):
        file = path / name
        rows.append({'name': name, 'value': 'present' if file.exists() else 'absent', 'path': str(file) if file.is_file() else ''})
    processes = run(['ps', '-eo', 'pid,ppid,args'])
    lines = [line for line in processes['output'].splitlines() if re.search(r'bitbake|cooker', line) and 'python3 -c' not in line][:100]
    return report('RUNTIME SHUTDOWN OBSERVATIONS', rows, '\n'.join(lines) or 'No matching process was visible to this probe.',
                  process_query_ok=processes['exit_code'] == 0, visible_processes=lines,
                  shutdown_confirmed=False, note='A new kas shell has its own namespace. Absence here does not establish shutdown of another container/server.')


def execute(request):
    op = request['op'].removeprefix('dev-')
    path, recipe = request.get('path', ''), request.get('recipe', '')
    if op == 'variable': return variable(recipe, request['variable'])
    if op == 'recipe': return recipe_context(target(recipe))
    if op == 'browse': return browse(path or '.', request.get('query', ''))
    if op == 'fingerprints': return [stamp(p, request.get('hashes', True)) for p in request['paths'][:2000]]
    if op == 'capabilities': return capabilities(target(recipe))
    if op == 'rebuild': return rebuild(target(recipe), path or '.')
    if op == 'failure': return failure(path, request.get('text'))
    if op == 'performance': return performance(path, request.get('build', '.'))
    if op == 'image': return image(target(recipe))
    if op == 'kernel': return kernel(target(recipe), path, request.get('config', ''))
    if op == 'upgrade': return upgrade(target(recipe))
    if op == 'downloads': return downloads(target(recipe), path, request.get('text'))
    if op == 'offline': return offline(target(recipe), request.get('full', False), request.get('prepare', False))
    if op == 'security': return security(path)
    if op == 'ide': return ide(target(recipe))
    if op == 'scaffold': return scaffold(path, request['files'])
    if op == 'shutdown': return shutdown(path or '.')
    raise ValueError('Unknown developer operation')


if __name__ == '__main__':
    request = json.loads(sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read())
    result = execute(request)
    print('BITLOOM_JSON:' + json.dumps(result))
    if request.get('execute'):
        sys.exit(1 if result.get('exit_code', 0) else 0)
