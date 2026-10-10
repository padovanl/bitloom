"""Run a genuine kas-container build through Bitloom's own Runner.

Usage: PATH="$PWD/.venv/bin:$PATH" python tools/validate_kas.py --work /tmp/yoctotui-kas
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
from yoctotui.models import Profile
from yoctotui.runner import Runner
from yoctotui.store import Store


KAS_IMAGE = 'ghcr.io/siemens/kas/kas@sha256:fef6f850106a6823e65e133ed8157a847431dea4aa2de3a636c11f65e9977476'


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
        report = json.loads((state / 'result.json').read_text())
        evidence = await asyncio.to_thread(collect_evidence, args)
        report['artifact_evidence'] = evidence
        report['artifacts'] = [str(Path('.validation/artifacts') / item['name']) for item in evidence]
        report['artifact_verified'] = bool(evidence) and all(a['has_shell'] for a in evidence)
        (state / 'result.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        return 0 if report['status'] == 'success' and report['artifact_verified'] else 1
    store = Store(state)
    profile = Profile(
        name='kas-integration', root=str(ROOT), mode='kas-container',
        kas_file='tests/integration/kas-minimal.yml', build_dir='build',
        environment={'KAS_WORK_DIR': str(args.work.resolve()), 'KAS_CONTAINER_ENGINE': args.engine, 'KAS_CLONE_DEPTH': '1', 'KAS_CONTAINER_IMAGE': KAS_IMAGE},
    )
    def event(job, line):
        if line is not None:
            print(line, flush=True)
    runner = Runner(store, event)
    job = runner.submit(profile, 'Integration: core-image-minimal (kas container)', ['kas', 'build'], 'kas-build')
    try:
        await runner.consumer
    except asyncio.CancelledError:
        await runner.shutdown()
        raise
    report = {'status': job.status, 'exit_code': job.code, 'started': job.started, 'finished': job.finished, 'log': str(job.log.relative_to(ROOT)), 'work': str(args.work), 'target': 'core-image-minimal', 'machine': 'qemux86-64', 'release_tag': 'yocto-5.0.8', 'runtime': 'kas-container', 'artifacts': [str(p) for p in args.work.glob('build/tmp/deploy/images/qemux86-64/*.tar.bz2')]}
    if job.status == 'success':
        try:
            report['artifact_evidence'] = await asyncio.to_thread(collect_evidence, args)
            report['artifacts'] = [str(Path('.validation/artifacts') / item['name']) for item in report['artifact_evidence']]
            report['artifact_verified'] = bool(report['artifact_evidence']) and all(a['has_shell'] for a in report['artifact_evidence'])
        except Exception as exc:
            report['artifact_verified'] = False
            report['verification_error'] = str(exc)
    (state / 'result.json').write_text(json.dumps(report, indent=2))
    store.close()
    print(json.dumps(report, indent=2))
    return 0 if job.status == 'success' and report.get('artifact_verified') else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', type=Path, default=Path('/tmp/yoctotui-kas-validation'))
    parser.add_argument('--verify-only', action='store_true', help='Verify/export artifacts from a completed recorded build')
    parser.add_argument('--engine', choices=['docker', 'podman'], default='docker')
    raise SystemExit(asyncio.run(validate(parser.parse_args())))
