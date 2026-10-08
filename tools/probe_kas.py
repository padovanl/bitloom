"""Exercise non-destructive tools through the real kas-container Runner after validation."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bitloom.models import Profile
from bitloom.reports import environment, dependencies
from bitloom.runner import Runner
from bitloom.store import Store


async def probe():
    state = ROOT / '.validation'
    result = json.loads((state / 'result.json').read_text())
    if result['status'] != 'success' or not result.get('artifact_verified'):
        raise RuntimeError('Complete and verify the real image build before running probes')
    profile = Profile(name='kas-integration', root=str(ROOT), mode='kas-container', kas_file='tests/integration/kas-minimal.yml', environment={'KAS_WORK_DIR': result['work'], 'KAS_CONTAINER_ENGINE': 'docker', 'KAS_CLONE_DEPTH': '1', 'KAS_CONTAINER_IMAGE': 'ghcr.io/siemens/kas/kas@sha256:fef6f850106a6823e65e133ed8157a847431dea4aa2de3a636c11f65e9977476'})
    store = Store(state)
    runner = Runner(store, lambda job, line: print(f'{job.title}: {job.status}', flush=True) if line is None else None)
    commands = [
        ('Show evaluated layers', ['bitbake-layers', 'show-layers'], 'layers'),
        ('Find busybox recipe', ['bitbake-layers', 'show-recipes', 'busybox'], 'recipes'),
        ('Resolve busybox environment', ['bitbake', '-e', 'busybox'], 'environment'),
        ('Devtool workspace status', ['devtool', 'status'], 'dev-status'),
        ('Read config inside container', ['cat', '/work/build/conf/local.conf'], 'custom'),
        ('List built packages', ['oe-pkgdata-util', 'list-pkgs'], 'packages'),
        ('Generate real dependency graph', ['bitbake', '-g', 'core-image-minimal'], 'graph'),
        ('Read container-only graph', ['cat', 'task-depends.dot'], 'graph-read'),
    ]
    jobs = [runner.submit(profile, title, command, action) for title, command, action in commands]
    await runner.consumer
    results = [{'title': job.title, 'action': job.action_id, 'status': job.status, 'exit_code': job.code, 'log': str(job.log.relative_to(ROOT))} for job in jobs]
    env_job = next(j for j in jobs if j.action_id == 'environment')
    values = environment(env_job.log)
    checks = {'all_exit_zero': all(j.status == 'success' for j in jobs), 'machine': values.get('MACHINE'), 'recipe': values.get('PN'), 'environment_variables': len(values), 'dependency_edges': len(dependencies(jobs[-1].log))}
    report = {'jobs': results, 'checks': checks}
    (state / 'probes.json').write_text(json.dumps(report, indent=2))
    store.close()
    print(json.dumps(report, indent=2))
    return 0 if checks['all_exit_zero'] and checks['machine'] == 'qemux86-64' and checks['recipe'] == 'busybox' and checks['dependency_edges'] > 0 else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(probe()))
