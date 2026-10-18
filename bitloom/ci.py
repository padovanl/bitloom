"""Headless runs for CI/CD: the same serial queue, profiles and runtimes as the TUI,
with collapsible log sections, error annotations, JUnit XML and a JSON summary."""
from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .commands import BY_ID, arguments
from .models import Settings

SSTATE = re.compile(r'Sstate summary:\s*Wanted (\d+) Local (\d+) Mirrors (\d+) Missed (\d+)(?: Current (\d+))?')


def parse_spec(spec: str):
    """ACTION[:TARGET] → (action, values). Example: build:core-image-minimal, kas-build."""
    ident, _, target = spec.partition(':')
    action = BY_ID.get(ident)
    if action is None:
        raise ValueError(f'Unknown operation {ident!r}; see bitloom --list-actions')
    if action.interactive:
        raise ValueError(f'{ident} is interactive and cannot run in CI')
    extra = [name for name in action.inputs if name != 'target']
    if extra:
        raise ValueError(f'{ident} needs {", ".join(extra)}; use it from the TUI or as custom')
    values = {'target': target} if 'target' in action.inputs else {}
    return action, arguments(action, values)


def log_facts(path: Path) -> dict:
    warnings, errors, failed, sstate = Counter(), [], [], None
    with path.open(errors='replace') as stream:
        for line in stream:
            if line.startswith('$ '):
                continue
            if 'WARNING:' in line:
                warnings[line.split('WARNING:', 1)[1].strip()] += 1
            if 'ERROR:' in line:
                errors.append(line.split('ERROR:', 1)[1].strip())
            match = re.search(r'ERROR: Task \(?([^)\s]+)\)? failed', line)
            if match:
                failed.append(match[1])
            match = SSTATE.search(line)
            if match:
                wanted, local, mirrors, missed = map(int, match.groups()[:4])
                current = int(match[5]) if match[5] else None
                total = wanted + (current or 0)
                # hit_rate: wanted tasks served from sstate. reuse: everything BitBake did not have to run
                # (already current or from sstate), BitBake's "complete": a forced task makes hit_rate 0%
                # while 98% of the build was reused.
                sstate = {'wanted': wanted, 'local': local, 'mirrors': mirrors, 'missed': missed, 'current': current,
                          'hit_rate': round((local + mirrors) / wanted, 4) if wanted else None,
                          'reuse': round((local + mirrors + (current or 0)) / total, 4) if total else None}
    return {'warnings': sum(warnings.values()), 'distinct_warnings': [{'message': m, 'count': c} for m, c in warnings.most_common(20)],
            'errors': errors[-20:], 'failed_tasks': failed, 'sstate': sstate}


def deployed_images(profile, since: float) -> list[dict]:
    root = profile.build_path / 'tmp/deploy/images'
    from .reports import IMAGE_SUFFIXES
    found = []
    if root.is_dir():
        for machine in root.iterdir():
            if machine.is_dir():
                for path in machine.iterdir():
                    try:
                        if path.name.endswith(IMAGE_SUFFIXES) and path.is_file() and not path.is_symlink() and path.stat().st_mtime >= since:
                            found.append({'machine': machine.name, 'file': path.name, 'size': path.stat().st_size})
                    except OSError:
                        pass
    return sorted(found, key=lambda item: (item['machine'], item['file']))


class Output:
    """Collapsible sections and annotations for the CI service in use."""

    def __init__(self, style='auto', stream=None):
        if style == 'auto':
            style = 'github' if os.environ.get('GITHUB_ACTIONS') else 'gitlab' if os.environ.get('GITLAB_CI') else 'plain'
        self.style, self.stream, self.section = style, stream or sys.stdout, 0

    def write(self, text):
        self.stream.write(text + '\n')
        self.stream.flush()

    def start(self, title):
        self.section += 1
        if self.style == 'github':
            self.write(f'::group::{title}')
        elif self.style == 'gitlab':
            self.write(f'\x1b[0Ksection_start:{int(time.time())}:bitloom_{self.section}[collapsed=true]\r\x1b[0K{title}')
        else:
            self.write(f'==> {title}')

    def end(self):
        if self.style == 'github':
            self.write('::endgroup::')
        elif self.style == 'gitlab':
            self.write(f'\x1b[0Ksection_end:{int(time.time())}:bitloom_{self.section}\r\x1b[0K')

    def annotate(self, level, title, message):
        message = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        if self.style == 'github':
            self.write(f'::{level} title={title}::{message}')
        else:
            self.write(f'{level.upper()}: {title}: {message}')


def junit(results: list[dict]) -> bytes:
    suites = ET.Element('testsuites', name='bitloom', tests=str(len(results)), failures=str(sum(r['status'] not in {'success', 'skipped'} for r in results)))
    for profile in dict.fromkeys(r['profile'] for r in results):
        rows = [r for r in results if r['profile'] == profile]
        suite = ET.SubElement(suites, 'testsuite', name=profile, tests=str(len(rows)), skipped=str(sum(r['status'] == 'skipped' for r in rows)),
                              failures=str(sum(r['status'] not in {'success', 'skipped'} for r in rows)), time=f'{sum(r["seconds"] for r in rows):.1f}')
        for row in rows:
            case = ET.SubElement(suite, 'testcase', classname=f'bitloom.{profile}', name=row['title'], time=f'{row["seconds"]:.1f}')
            if row['status'] == 'skipped':
                ET.SubElement(case, 'skipped', message=row['reason'])
                continue
            if row['status'] != 'success':
                failure = ET.SubElement(case, 'failure', message=f'{row["status"]} (exit {row["code"]})', type=row['status'])
                failure.text = '\n'.join([*row['failed_tasks'], *row['errors'], *('Task log: ' + p for p in row['failure_logs'])])
            out = ET.SubElement(case, 'system-out')
            out.text = f'log: {row["log"]}\nwarnings: {row["warnings"]}\nsstate: {json.dumps(row["sstate"])}'
    return ET.tostring(suites, encoding='utf-8', xml_declaration=True)


async def run(config: Path, state: Path, specs: list[str], profiles: list[str], output: Output, fail_fast=False) -> list[dict]:
    from .runner import Runner
    from .store import Store
    settings = Settings(config)
    chosen = profiles or [settings.active]
    known = {p.name: p for p in settings.profiles}
    missing = [name for name in chosen if name not in known]
    if missing:
        raise ValueError('Unknown profile: ' + ', '.join(missing))
    plan = [(known[name], *parse_spec(spec)) for name in chosen for spec in specs]
    store = Store(state)
    current = {}

    def stream(job, line):
        if line is not None and job.id == current.get('id'):
            output.write(line)
    runner = Runner(store, stream)
    results = []
    try:
        from .commands import availability
        from .versions import detect_release
        releases = {profile.name: detect_release(profile) for profile, _, _ in plan}
        for index, (profile, action, argv) in enumerate(plan, 1):
            title = f'{action.title} · {" ".join(argv[1 + len(action.args):])}' if action.inputs else action.title
            ok, reason = availability(action, releases[profile.name])
            if ok is False:
                # Do what this release can do: skip with the alternative instead of failing the matrix.
                output.annotate('warning', f'{profile.name}: {title} skipped', reason)
                results.append({'profile': profile.name, 'action': action.id, 'title': title, 'argv': argv, 'status': 'skipped',
                                'reason': reason, 'release': releases[profile.name], 'code': None, 'seconds': 0.0, 'log': '', 'progress': [0, 0],
                                'setscene': [0, 0], 'failure_logs': [], 'warnings': 0, 'distinct_warnings': [], 'errors': [],
                                'failed_tasks': [], 'sstate': None, 'images': []})
                continue
            output.start(f'[{index}/{len(plan)}] {profile.name}: {title}')
            started = time.time()
            job = runner.submit(profile, title, argv, action.id)
            current['id'] = job.id
            await runner.consumer
            output.end()
            facts = log_facts(job.log) if job.log.exists() else {'warnings': 0, 'distinct_warnings': [], 'errors': [], 'failed_tasks': [], 'sstate': None}
            row = {'profile': profile.name, 'action': action.id, 'title': title, 'argv': argv, 'status': job.status, 'code': job.code,
                   'seconds': round(time.time() - started, 1), 'log': str(job.log), 'progress': list(job.progress),
                   'setscene': list(job.setscene), 'failure_logs': job.failure_logs, **facts,
                   'images': deployed_images(profile, started) if job.status == 'success' else [], 'release': releases[profile.name]}
            results.append(row)
            if job.status != 'success':
                detail = '; '.join(row['failed_tasks'][:5]) or (row['errors'][-1] if row['errors'] else f'exit {job.code}')
                output.annotate('error', f'{profile.name}: {title} {job.status}', detail)
                if fail_fast:
                    break
            for warning in row['distinct_warnings'][:5]:
                output.annotate('warning', f'{profile.name}: {title}', f'{warning["count"]}× {warning["message"]}')
    finally:
        await runner.shutdown()
        store.close()
    return results


def main(args) -> int:
    output = Output(args.annotations)
    loop = asyncio.new_event_loop()
    task = loop.create_task(run(args.config, args.state, args.ci, args.profile or [], output, args.fail_fast))
    for sig in (signal.SIGTERM, signal.SIGINT):
        # CI cancellation: stop the running job cleanly, keep partial reports.
        loop.add_signal_handler(sig, task.cancel)
    try:
        results = loop.run_until_complete(task)
    except asyncio.CancelledError:
        output.write('Cancelled: the running job was stopped.')
        return 130
    except (ValueError, OSError) as exc:
        output.write(f'bitloom: {exc}')
        return 2
    finally:
        loop.close()
    summary = {'generated': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'ok': all(r['status'] in {'success', 'skipped'} for r in results),
               'jobs': results}
    if args.summary:
        Path(args.summary).write_text(json.dumps(summary, indent=2))
    if args.junit:
        Path(args.junit).write_bytes(junit(results))
    output.write('')
    for row in results:
        state = row['sstate'] or {}
        reuse = state.get('reuse', state.get('hit_rate'))
        if row['status'] == 'skipped':
            output.write(f'SKIP  {row["profile"]}: {row["title"]}  {row["reason"]}')
            continue
        output.write(f'{"PASS" if row["status"] == "success" else "FAIL"}  {row["profile"]}: {row["title"]}  '
                     f'{row["seconds"]:.0f}s  warnings {row["warnings"]}' + (f'  sstate reuse {100 * reuse:.0f}% (' + (f'{state["missed"]} of {state["wanted"]} wanted tasks rebuilt' if state["wanted"] else 'everything up to date') + ')' if reuse is not None else ''))
    return 0 if summary['ok'] and any(r['status'] == 'success' for r in results) else 1
