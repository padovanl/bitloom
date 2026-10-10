"""Run a genuine kas-container build through Bitloom's own Runner.

Usage: PATH="$PWD/.venv/bin:$PATH" python tools/validate_kas.py --work /tmp/bitloom-kas
Requires Docker or Podman and kas-container. Does not install Yocto on the host.
"""
import argparse
import asyncio
import json
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bitloom.models import Profile
from bitloom.runner import Runner
from bitloom.store import Store


from tools.releases import KAS_IMAGE, RELEASES, add_arguments, profile as release_profile


def collect_evidence(args):
    output = ROOT / '.validation/artifacts'
    output.mkdir(parents=True, exist_ok=True)
    # Inspect from the daemon's namespace too: Docker Snap may have private /tmp.
    code = r'''import hashlib, json, pathlib, shutil, tarfile
root = pathlib.Path('/work/build/tmp/deploy/images/qemux86-64')
artifacts = []
seen = set()
for p in sorted(root.glob('core-image-minimal*.tar.bz2')):
    p = p.resolve()
    if p in seen: continue
    seen.add(p)
    with p.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    with tarfile.open(p, 'r:bz2') as archive:
        names = {m.name.lstrip('./') for m in archive}
    destination = pathlib.Path('/out') / p.name
    shutil.copyfile(p, destination)
    artifacts.append({'name': p.name, 'bytes': p.stat().st_size, 'sha256': digest, 'has_shell': 'bin/sh' in names or 'usr/bin/sh' in names, 'rootfs_entries': len(names)})
for p in root.glob('core-image-minimal*.manifest'):
    if not p.is_symlink(): shutil.copyfile(p, pathlib.Path('/out') / p.name)
print(json.dumps(artifacts))'''
    result = subprocess.run([args.engine, 'run', '--rm', '--user', '0', '--entrypoint', 'python3', '-v', f'{args.work.resolve()}:/work:ro', '-v', f'{output}:/out', KAS_IMAGE, '-c', code], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return json.loads(result.stdout)


async def validate(args):
    args.work.mkdir(parents=True, exist_ok=True)
    state = ROOT / '.validation'
    if args.verify_only:
        report = json.loads((state / RELEASES[args.release]['result']).read_text())
        evidence = await asyncio.to_thread(collect_evidence, args)
        report['artifact_evidence'] = evidence
        report['artifacts'] = [str(Path('.validation/artifacts') / item['name']) for item in evidence]
        report['artifact_verified'] = bool(evidence) and all(a['has_shell'] for a in evidence)
        (state / RELEASES[args.release]['result']).write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        return 0 if report['status'] == 'success' and report['artifact_verified'] else 1
    store = Store(state)
    profile = release_profile(args.release, args.work, args.engine, clone_depth=True)
    def event(job, line):
        if line is not None:
            print(line, flush=True)
    runner = Runner(store, event)
    job = runner.submit(profile, f'Integration {args.release}: core-image-minimal (kas container)', ['kas', 'build'], 'kas-build')
    try:
        await runner.consumer
    except asyncio.CancelledError:
        await runner.shutdown()
        raise
    report = {'status': job.status, 'exit_code': job.code, 'started': job.started, 'finished': job.finished, 'log': str(job.log.relative_to(ROOT)), 'work': str(args.work), 'target': 'core-image-minimal', 'machine': 'qemux86-64', 'release': args.release, 'release_tag': RELEASES[args.release]['tag'], 'runtime': 'kas-container', 'artifacts': [str(p) for p in args.work.glob('build/tmp/deploy/images/qemux86-64/*.tar.bz2')]}
    if job.status == 'success':
        try:
            report['artifact_evidence'] = await asyncio.to_thread(collect_evidence, args)
            report['artifacts'] = [str(Path('.validation/artifacts') / item['name']) for item in report['artifact_evidence']]
            report['artifact_verified'] = bool(report['artifact_evidence']) and all(a['has_shell'] for a in report['artifact_evidence'])
        except Exception as exc:
            report['artifact_verified'] = False
            report['verification_error'] = str(exc)
    (state / RELEASES[args.release]['result']).write_text(json.dumps(report, indent=2))
    store.close()
    print(json.dumps(report, indent=2))
    return 0 if job.status == 'success' and report.get('artifact_verified') else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    parser.add_argument('--work', type=Path, help='Linux build workspace (default per release, see tools/releases.py)')
    parser.add_argument('--verify-only', action='store_true', help='Verify/export artifacts from a completed recorded build')
    parser.add_argument('--engine', choices=['docker', 'podman'], default='docker')
    arguments = parser.parse_args()
    arguments.work = arguments.work or RELEASES[arguments.release]['work']
    raise SystemExit(asyncio.run(validate(arguments)))
