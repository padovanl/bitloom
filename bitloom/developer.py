"""Developer workflow evidence, scaffolding, profile and device utilities."""
from __future__ import annotations

import copy
import difflib
import hashlib
import json
import os
import re
import shlex
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import Profile
from .workflows import SECRET, redact

VIEWS = [
    ('Variable history', 'variable'), ('Recipe context', 'recipe'), ('Runtime browser', 'browse'),
    ('Rebuild evidence', 'rebuild'), ('Failure investigation', 'failure'), ('IDE / SDK bridge', 'ide'),
    ('Image regressions', 'image'), ('Build performance', 'performance'), ('Resolved kas / multiconfig', 'config'),
    ('Downloads / offline', 'downloads'), ('CVE / SBOM review', 'security'), ('Kernel fragments', 'kernel'),
    ('Upgrade baseline', 'upgrade'), ('Board laboratory', 'board'), ('Runtime capabilities', 'capabilities'),
    ('Shutdown evidence', 'shutdown'),
]

HINTS = {
    'variable': ('Variable (SUMMARY, PACKAGECONFIG, do_install…)', 'Recipe in top target; clear target for global context'),
    'recipe': ('Optional runtime path to browse', 'Evaluated paths and appends; Enter opens a row'),
    'browse': ('Absolute runtime directory', 'Filename search (recursive, bounded)'),
    'rebuild': ('Runtime build directory (blank uses profile)', 'Latest signature pairs plus printdiff; Capture for comparison'),
    'failure': ('Runtime task log or local selected build log', 'Original job/profile is retained when selected log is used'),
    'ide': ('Image recipe (core-image-minimal)', 'SSH target, optional; Generate SDK uses devtool ide-sdk'),
    'image': ('Image recipe (blank uses the build target)', 'Capture baseline, rebuild, then Compare capture'),
    'performance': ('Runtime buildstats directory (blank uses latest)', 'Container limits and pressure are measured in this probe'),
    'config': ('Recipe for multiconfig probe (blank uses the recipe above)', 'Resolved kas dump; Clone creates a separate build directory'),
    'downloads': ('Optional local or runtime fetch failure log', 'Prepare mirrors / verify fetch offline / verify full build offline'),
    'security': ('Runtime CVE or SPDX JSON report', 'Database/report dates; select an issue to record a disposition'),
    'kernel': ('Runtime kernel fragment path', 'Final .config path (blank resolves recipe B/.config)'),
    'upgrade': ('Recipe (blank uses the recipe above)', 'Capture before an upgrade, inspect after, Compare'),
    'board': ('Device profile name', 'Artifact exported on host; hash is recorded with device jobs'),
    'capabilities': ('Recipe (blank uses the recipe above)', 'Probe tasks, tools, release, IDE and runtime devices'),
    'shutdown': ('Runtime build directory (blank uses profile)', 'Client, container and server observations remain distinct'),
}


def runtime_build(profile):
    if profile.mode in {'kas', 'kas-container', 'wrapper'}:
        return '.'
    if profile.mode == 'container':
        return str(Path(profile.container_root) / profile.build_path.relative_to(profile.root_path))
    return str(profile.build_path)


async def inspect(profile, operation, path='', **parameters):
    from .leases import BuildLease
    from .runtime import request
    lease = BuildLease(profile)
    lease.acquire()
    try:
        return await request(profile, 'dev-' + operation, path, **parameters)
    finally:
        lease.close()


async def prepare_kas_work(profile):
    """Initialize an empty daemon-side work directory without touching its contents."""
    import asyncio
    work = Path(profile.environment.get('KAS_WORK_DIR', ''))
    if profile.mode != 'kas-container' or not work.is_absolute() or work == Path('/') or work == profile.root_path:
        raise ValueError('Configure a separate absolute KAS_WORK_DIR for container preparation')
    work.mkdir(parents=True, exist_ok=True)
    engine = profile.environment.get('KAS_CONTAINER_ENGINE', profile.engine)
    if engine not in {'docker', 'podman'}: raise ValueError('Unsupported container engine')
    image = profile.environment.get('KAS_CONTAINER_IMAGE')
    if not image: raise ValueError('Set an explicit KAS_CONTAINER_IMAGE before preparing the workspace')
    mounts = ['-v', str(work) + ':/work']
    paths = ['/work']
    build = profile.build_path
    if not build.is_relative_to(work):
        if build == profile.root_path or build == Path('/'):
            raise ValueError('Configure a separate build directory')
        build.mkdir(parents=True, exist_ok=True)
        mounts += ['-v', str(build) + ':/build']
        paths.append('/build')
    source = ('import os,pathlib,sys\nuid=int(sys.argv[1]); gid=int(sys.argv[2])\n'
              'for name in sys.argv[3:]:\n    p=pathlib.Path(name); s=p.stat()\n'
              '    if s.st_uid!=uid and any(p.iterdir()):\n        raise ValueError("Workspace contains files owned by another user; review ownership manually")\n'
              '    if s.st_uid!=uid:\n        os.chown(p,uid,gid)\n        os.chmod(p,0o775)\n'
              '    print("Prepared directory",name,"for UID",uid)')
    process = await asyncio.create_subprocess_exec(engine, 'run', '--rm', '--user', '0', '--entrypoint', 'python3',
        *mounts, image, '-c', source, str(os.getuid()), str(os.getgid()), *paths,
        env={**os.environ, **profile.environment}, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        output, _ = await asyncio.wait_for(process.communicate(), 120)
    finally:
        if process.returncode is None: process.kill(); await process.wait()
    if process.returncode: raise ValueError(output.decode(errors='replace')[-2000:])
    return output.decode(errors='replace')


def runtime_command(operation, **parameters):
    source = Path(__file__).with_name('developer_agent.py').read_text()
    return ['python3', '-c', source, json.dumps({'op': 'dev-' + operation, 'execute': True, **parameters})]


def capture(directory, profile, view, data, job=None):
    safe = redact(data)
    if view == 'variable' and SECRET.search(data.get('variable', '')):
        safe = {'title': data['title'], 'variable': data['variable'], 'redacted': True}
    result = {'schema': 1, 'view': view, 'profile': redact(asdict(profile)), 'data': safe,
              'job': job, 'captured_utc': datetime.now(timezone.utc).isoformat()}
    path = Path(directory) / 'exports' / f'developer-{view}-{datetime.now(timezone.utc):%Y%m%d-%H%M%S-%f}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        path.chmod(0o600)
        json.dump(result, stream, indent=2)
    return path


def compare_captures(before, after):
    from .developer_agent import report
    if before['view'] != after['view']:
        raise ValueError('Compare captures from the same Developer view')
    a, b = before['data'], after['data']
    view = before['view']
    identity_keys = ('MACHINE', 'DISTRO', 'TCLIBC', 'BB_CURRENT_MC')
    identity_a = {key: a.get('identity', {}).get(key) for key in identity_keys}
    identity_b = {key: b.get('identity', {}).get(key) for key in identity_keys}
    if view in {'image', 'upgrade'} and (identity_a != identity_b or a.get('image') != b.get('image')):
        raise ValueError('Machine, distro, libc, multiconfig and image must match for this comparison')
    rows, lines = [], []
    if view == 'image':
        for name in sorted(a.get('packages', {}).keys() | b.get('packages', {}).keys()):
            old, new = a.get('packages', {}).get(name), b.get('packages', {}).get(name)
            if old != new:
                state = 'added' if old is None else 'removed' if new is None else f'{new-old:+d} bytes'
                rows.append({'name': name, 'value': f'{old} → {new} · {state} · recipe {b.get("owners", {}).get(name) or a.get("owners", {}).get(name) or "unknown"}'})
        for name in sorted(a.get('files', {}).keys() | b.get('files', {}).keys()):
            old, new = a.get('files', {}).get(name), b.get('files', {}).get(name)
            if old != new:
                rows.append({'name': name, 'value': 'added' if old is None else 'removed' if new is None else 'metadata changed'})
                lines += [name, str(old), '→ ' + str(new)]
    elif view == 'security':
        old = {(e['package'], e['id']): e for e in a.get('issues', [])}
        new = {(e['package'], e['id']): e for e in b.get('issues', [])}
        for key in sorted(old.keys() | new.keys()):
            if old.get(key) != new.get(key):
                rows.append({'name': ' · '.join(key), 'value': f'{old.get(key, {}).get("status", "absent")} → {new.get(key, {}).get("status", "absent")}'})
        lines.append('Report/database metadata: ' + json.dumps(a.get('report_metadata')) + ' → ' + json.dumps(b.get('report_metadata')))
    elif view == 'performance':
        old = {e['task']: e['seconds'] for e in a.get('buildstats', [])}
        new = {e['task']: e['seconds'] for e in b.get('buildstats', [])}
        for task in sorted(old.keys() | new.keys()):
            x, y = old.get(task), new.get(task)
            rows.append({'name': task, 'value': f'{x} → {y} seconds' + (f' ({y-x:+.2f})' if x is not None and y is not None else '')})
        lines.append(f'Observed task span: {a.get("wall_seconds")} → {b.get("wall_seconds")} seconds; tasks overlap.')
    else:
        def stable(data):
            return {k: v for k, v in data.items() if k not in {'captured', 'fingerprints'}}
        lines = list(difflib.unified_diff(json.dumps(stable(a), indent=2, sort_keys=True).splitlines(),
                                        json.dumps(stable(b), indent=2, sort_keys=True).splitlines(),
                                        fromfile=before.get('captured_utc', 'before'), tofile=after.get('captured_utc', 'after'), lineterm=''))
        rows = [{'name': key, 'value': 'changed'} for key in sorted(a.keys() | b.keys()) if stable(a).get(key) != stable(b).get(key)]
    return report('CAPTURE COMPARISON · ' + view.upper(), rows[:2000], '\n'.join(lines) or 'No recorded changes.',
                  changes=len(rows), before=before.get('captured_utc'), after=after.get('captured_utc'))


def clone_profile(settings, name, build, machine='', distro=''):
    if any(p.name == name for p in settings.profiles):
        raise ValueError('Profile name already exists')
    path = Path(build).expanduser()
    if not path.is_absolute():
        raise ValueError('Choose an absolute, separate build directory')
    original = settings.profile
    if path.resolve() == original.build_path.resolve():
        raise ValueError('Cloned profile must have a separate build directory')
    profile = copy.deepcopy(original)
    profile.name, profile.build_dir = name, str(path)
    profile.machine, profile.distro = machine or original.machine, distro or original.distro
    if profile.mode in {'kas', 'kas-container', 'wrapper'}:
        # Keep local layer paths and source repositories from the original work
        # mount. kas-container forwards an external build directory as /build.
        profile.environment.setdefault('KAS_WORK_DIR', str(original.root_path))
        profile.environment['KAS_BUILD_DIR'] = str(path)
        path.parent.mkdir(parents=True, exist_ok=True)
    profile.validate()
    old_active = settings.active
    settings.profiles.append(profile)
    settings.active = name
    try:
        settings.save()
    except Exception:
        settings.profiles.remove(profile)
        settings.active = old_active
        raise
    return profile


MIT = '''MIT License

Copyright (c) {year} {owner}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''


def scaffold_plan(name, layer, system, owner, series='scarthgap'):
    if not re.fullmatch(r'[a-z][a-z0-9-]*', name):
        raise ValueError('Recipe name must be lowercase letters, digits and hyphens')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', layer):
        raise ValueError('Layer collection must contain letters, digits, underscores or hyphens')
    if not owner.strip() or '\n' in owner:
        raise ValueError('Enter a copyright owner on one line')
    if not re.fullmatch(r'[a-z0-9 -]+', series):
        raise ValueError('Enter space-separated layer series names')
    license_text = MIT.format(year=datetime.now(timezone.utc).year, owner=owner)
    source = {'LICENSE': license_text}
    c = f'#include <stdio.h>\nint main(void) {{ puts("Hello from {name}"); return 0; }}\n'
    if system == 'cmake':
        source.update({'main.c': c, 'CMakeLists.txt': f'cmake_minimum_required(VERSION 3.16)\nproject({name} C)\nadd_executable({name} main.c)\ninstall(TARGETS {name} DESTINATION bin)\n'})
        build = 'inherit cmake\n'
    elif system == 'meson':
        source.update({'main.c': c, 'meson.build': f"project('{name}', 'c', version: '1.0')\nexecutable('{name}', 'main.c', install: true)\n"})
        build = 'inherit meson\n'
    elif system == 'make':
        source.update({'main.c': c, 'Makefile': f'PREFIX ?= /usr\nall: {name}\n{name}: main.c\n\t$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $<\ninstall: {name}\n\tinstall -d $(DESTDIR)$(PREFIX)/bin\n\tinstall -m 0755 {name} $(DESTDIR)$(PREFIX)/bin/\n'})
        build = 'do_compile() {\n    oe_runmake\n}\ndo_install() {\n    oe_runmake DESTDIR="${D}" PREFIX="${prefix}" install\n}\n'
    elif system == 'python':
        source[name] = f'#!/usr/bin/python3\nprint("Hello from {name}")\n'
        build = f'RDEPENDS:${{PN}} += "python3-core"\ndo_install() {{\n    install -d ${{D}}${{bindir}}\n    install -m 0755 ${{S}}/{name} ${{D}}${{bindir}}/{name}\n}}\n'
    elif system == 'rust':
        source.update({'src/main.rs': f'fn main() {{ println!("Hello from {name}"); }}\n',
                       'Cargo.toml': f'[package]\nname = "{name}"\nversion = "1.0.0"\nedition = "2021"\n',
                       'Cargo.lock': f'version = 3\n\n[[package]]\nname = "{name}"\nversion = "1.0.0"\n'})
        build = 'inherit cargo\n'
    else:
        raise ValueError('Choose cmake, meson, make, python or rust')
    base = f'recipes-example/{name}'
    files = {f'{base}/files/source/{path}': text for path, text in source.items()}
    files[f'{base}/{name}_1.0.bb'] = (f'SUMMARY = "{name} developer fixture"\nLICENSE = "MIT"\n'
        f'LIC_FILES_CHKSUM = "file://LICENSE;md5={hashlib.md5(license_text.encode()).hexdigest()}"\n'
        'SRC_URI = "file://source"\nUNPACKDIR ??= "${WORKDIR}"\nS = "${UNPACKDIR}/source"\n' + build)
    files['conf/layer.conf'] = ('BBPATH .= ":${LAYERDIR}"\nBBFILES += "${LAYERDIR}/recipes-*/*/*.bb ${LAYERDIR}/recipes-*/*/*.bbappend"\n'
        f'BBFILE_COLLECTIONS += "{layer}"\nBBFILE_PATTERN_{layer} = "^${{LAYERDIR}}/"\n'
        f'BBFILE_PRIORITY_{layer} = "6"\nLAYERSERIES_COMPAT_{layer} = "{series}"\nLAYERDEPENDS_{layer} = "core"\n')
    return files


def kas_overlay(profile, layer_path, recipe, overlay_file=''):
    if profile.mode not in {'kas', 'kas-container'}:
        return None
    parent = (profile.root_path / overlay_file).parent if overlay_file else profile.root_path
    includes = '\n'.join('    - ' + json.dumps(os.path.relpath(profile.root_path / value, parent)) for value in profile.kas_file.split(':'))
    return ('header:\n  version: 14\n  includes:\n' + includes + '\nrepos:\n  bitloom_generated:\n'
            '    path: ' + json.dumps(layer_path) + '\nlocal_conf_header:\n  bitloom-generated: |\n'
            f'    IMAGE_INSTALL:append = " {recipe}"\n')


def load_devices(path):
    result = json.loads(Path(path).read_text()) if Path(path).exists() else {'devices': []}
    devices = result.get('devices', [])
    if not isinstance(devices, list) or any(not isinstance(d, dict) for d in devices):
        raise ValueError('devices must be an array of objects')
    if len({d.get('name') for d in devices}) != len(devices):
        raise ValueError('Device names must be unique')
    for device in devices:
        if not device.get('name'):
            raise ValueError('Device name is required')
        if device.get('ssh') and (device['ssh'].startswith('-') or not re.fullmatch(r'[A-Za-z0-9_.@:\[\]-]+', device['ssh'])):
            raise ValueError('Invalid SSH destination')
        for key in ('test_argv', 'console_argv'):
            if key in device and (not isinstance(device[key], list) or not device[key] or any(not isinstance(v, str) for v in device[key])):
                raise ValueError(key + ' must be a nonempty string argument array')
    return devices


def board_command(device, operation, artifact='', recipe=''):
    if operation not in {'deploy', 'undeploy', 'status', 'acquire', 'release', 'power', 'console', 'test'}:
        raise ValueError('Unknown device operation')
    if device.get('ssh', '').startswith('-'):
        raise ValueError('Invalid SSH destination')
    if operation in {'deploy', 'undeploy'}:
        if not device.get('ssh'):
            raise ValueError('Device needs an SSH destination')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9+_.-]*', recipe):
            raise ValueError('Enter the devtool recipe in the top target')
        return ['devtool', operation + '-target', recipe, device['ssh']]
    place = device.get('labgrid_place')
    if operation in {'status', 'acquire', 'release', 'power', 'console'} and place:
        if place.startswith('-') or not re.fullmatch(r'[A-Za-z0-9_+.-]+', place):
            raise ValueError('Invalid labgrid place')
        suffix = ['power', 'cycle'] if operation == 'power' else ['show'] if operation == 'status' else [operation]
        return ['labgrid-client', '-p', place, *suffix]
    if operation == 'status':
        if not device.get('ssh'):
            raise ValueError('Configure SSH or labgrid')
        return ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', device['ssh'], 'uname -a']
    if operation in {'acquire', 'release', 'power'}:
        raise ValueError('Configure a labgrid_place for ownership or power operations')
    argv = device.get('console_argv' if operation == 'console' else 'test_argv')
    if not argv:
        raise ValueError('Configure a console_argv or test_argv argument array for this operation')
    replacements = {'artifact': artifact, 'device': device.get('ssh', ''), 'recipe': recipe, 'place': place or ''}
    return [part.format_map(replacements) for part in argv]


def device_identity(path):
    file = Path(path).expanduser()
    if not file.is_file():
        raise ValueError('Export the tested artifact to a local file and enter its path')
    digest = hashlib.sha256()
    with file.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'path': str(file.resolve()), 'sha256': digest.hexdigest(), 'size': file.stat().st_size}


def read_reviews(path) -> dict:
    """Recorded dispositions keyed by package/CVE; ValueError when the file is damaged
    (never treated as empty, so saving cannot overwrite the reviews it holds)."""
    file = Path(path)
    if not file.exists():
        return {}
    try:
        entries = json.loads(file.read_text(errors='replace'))
    except ValueError as exc:
        raise ValueError(f'{file} is not valid JSON ({exc}); fix or move it away') from exc
    if not isinstance(entries, dict) or any(not isinstance(v, dict) for v in entries.values()):
        raise ValueError(f'{file} must map package/CVE to review objects; fix or move it away')
    return entries


def security_disposition(path, issue, owner, reason, expiry):
    if not owner.strip() or not reason.strip():
        raise ValueError('Owner and reason are required')
    date = datetime.strptime(expiry, '%Y-%m-%d').date()
    if date < datetime.now(timezone.utc).date():
        raise ValueError('Expiry must be today or later')
    file = Path(path)
    entries = read_reviews(file)
    entries[issue['package'] + '/' + issue['id']] = {'owner': owner, 'reason': reason, 'expires': expiry,
        'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'upstream_status': issue['status']}
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_suffix('.tmp')
    temporary.write_text(json.dumps(entries, indent=2))
    temporary.chmod(0o600)
    temporary.replace(file)
    return entries


def ide_mappings(profile):
    mappings = dict(profile.source_mappings)
    if profile.mode == 'container':
        mappings.setdefault(profile.container_root, str(profile.root_path))
    return mappings


def map_path(value, mappings):
    for runtime, host in sorted(mappings.items(), key=lambda p: len(p[0]), reverse=True):
        if value == runtime or value.startswith(runtime.rstrip('/') + '/'):
            return host.rstrip('/') + value[len(runtime.rstrip('/')):]
    return value


def map_compile_database(entries, mappings):
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get('file'), str):
            raise ValueError('Invalid compile_commands.json entry')
    result = copy.deepcopy(entries)
    def argument(value):
        for prefix in ('--sysroot=', '-I', '-L', '-isystem'):
            if value.startswith(prefix) and len(value) > len(prefix):
                return prefix + map_path(value[len(prefix):], mappings)
        return map_path(value, mappings)
    for entry in result:
        for key in ('file', 'directory', 'output'):
            if key in entry: entry[key] = map_path(entry[key], mappings)
        if 'arguments' in entry: entry['arguments'] = [argument(v) for v in entry['arguments']]
        if 'command' in entry: entry['command'] = shlex.join([argument(v) for v in shlex.split(entry['command'])])
    return result
