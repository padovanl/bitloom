"""Validate Developer workflows with real kas-container/BitBake and isolated state.

Uses a dedicated work directory. --build also builds a tiny dependency-free recipe;
--image additionally builds core-image-minimal. Hardware/IDE targets remain optional.
"""
import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bitloom import developer as dev
from bitloom.models import Profile, Settings
from bitloom.runner import Runner
from bitloom.runtime import request
from bitloom.store import Store
from tools.validate_kas import KAS_IMAGE


async def validate(args):
    directory = ROOT / '.developer-validation'
    directory.mkdir(exist_ok=True)
    args.work.mkdir(parents=True, exist_ok=True)
    os.environ['PATH'] = str(ROOT / '.venv/bin') + os.pathsep + os.environ['PATH']
    profile = Profile(name='developer-validation', root=str(ROOT), mode='kas-container', kas_file='tests/integration/kas-minimal.yml',
                      build_dir=str(args.work / 'build'), environment={'KAS_WORK_DIR':str(args.work), 'KAS_CONTAINER_IMAGE':KAS_IMAGE,
                      'KAS_CONTAINER_ENGINE':args.engine, 'KAS_CLONE_DEPTH':'1'})
    await dev.prepare_kas_work(profile)
    results = []

    async def probe(op, path='', **kwargs):
        result = await dev.inspect(profile, op, path, **kwargs)
        output = directory / (op + '.json')
        output.write_text(json.dumps(result, indent=2)); output.chmod(0o600)
        results.append({'operation':op, 'status':'PASS', 'evidence':str(output.relative_to(ROOT)), 'rows':len(result.get('rows', []))})
        print(op + ': PASS · ' + str(output.relative_to(ROOT)), flush=True)
        return result

    cap = await probe('capabilities', recipe='busybox')
    if not cap['task_probe_ok']: raise ValueError('BitBake tasks could not be evaluated')
    variable = await probe('variable', recipe='busybox', variable='SUMMARY')
    if not variable['fingerprints']: raise ValueError('Variable assignment origins missing')
    await probe('recipe', recipe='busybox')
    await probe('browse', '/work/poky/meta/recipes-core/busybox', query='.bb')
    await probe('ide', recipe='busybox')
    await probe('performance', build='.')
    await probe('upgrade', recipe='busybox')
    await probe('downloads', recipe='busybox')
    await probe('rebuild', '.', recipe='busybox')
    await probe('shutdown', '.')
    baseline = await probe('image', recipe='core-image-minimal')
    if args.build or args.image:
        ident = uuid.uuid4().hex[:8]
        layer = '/work/meta-bitloom-validation-' + ident
        name = 'bitloom-validation-hello'
        files = dev.scaffold_plan(name, 'bitloomvalidation', 'python', 'Bitloom validation fixture')
        recipe_path = 'recipes-example/' + name + '/' + name + '_1.0.bb'
        # A data-only package avoids rebuilding the cross-toolchain just for this probe.
        files[recipe_path] = ('SUMMARY = "Bitloom runtime validation"\nLICENSE = "CLOSED"\n'
                             'INHIBIT_DEFAULT_DEPS = "1"\nS = "${WORKDIR}"\n'
                             'do_install() {\n    install -d ${D}${datadir}/bitloom\n'
                             '    echo "Real kas-container recipe" > ${D}${datadir}/bitloom/message.txt\n}\n')
        await probe('scaffold', layer, files=files)
        relative = '.developer-validation/kas-' + ident + '.yml'
        config = ROOT / relative
        config.write_text(dev.kas_overlay(profile, layer, name, relative))
        profile.kas_file = relative
        settings = Settings(directory / 'profiles.json')
        settings.profiles = [profile]; settings.active = profile.name; settings.save()
        store = Store(directory / ('state-' + ident))
        runner = Runner(store, lambda job, line: print(line, flush=True) if line and ('ERROR' in line or 'Tasks Summary' in line) else None)
        async def build(title, argv):
            job = runner.submit(profile, title, argv, 'developer-validation')
            print('Running ' + title + ' · log ' + str(job.log), flush=True)
            await runner.consumer
            results.append({'operation':title, 'status':job.status, 'exit_code':job.code, 'log':str(job.log.relative_to(ROOT))})
            if job.status != 'success': raise ValueError('Build failed: ' + str(job.log))
            return job
        try:
            await build('Real generated recipe', ['bitbake', name])
            await probe('recipe', recipe=name)
            await probe('variable', recipe=name, variable='SUMMARY')
            await build('Prepare source mirrors', dev.runtime_command('offline', recipe=name, prepare=True))
            await build('Verify recipe fetch offline', dev.runtime_command('offline', recipe=name))
            await build('Verify recipe build offline', dev.runtime_command('offline', recipe=name, full=True))
            if args.image:
                await build('Real minimal image with generated recipe', ['bitbake', 'core-image-minimal'])
                after = await probe('image', recipe='core-image-minimal')
                diff = dev.compare_captures({'view':'image','data':baseline}, {'view':'image','data':after})
                (directory / 'image-diff.json').write_text(json.dumps(diff, indent=2))
            await probe('performance', build='.')
            append = layer + '/recipes-example/' + name + '/' + name + '_%.bbappend'
            await request(profile, 'create', append, text='do_install:append() {\n    bbfatal "Bitloom controlled task failure"\n}\n')
            job = runner.submit(profile, 'Controlled real task failure', ['bitbake','-f','-c','install',name], 'developer-validation')
            await runner.consumer
            if job.status != 'failed': raise ValueError('Controlled failure did not fail the actual BitBake task')
            await probe('failure', str(job.log), text=job.log.read_text())
            results.append({'operation':'Controlled task failure','status':'PASS','observed_status':job.status,'log':str(job.log.relative_to(ROOT))})
            old = await request(profile, 'read', append)
            await request(profile, 'write', append, sha256=old['sha256'], text='# Controlled failure restored.\n')
            await build('Restored generated recipe', ['bitbake',name])
        finally:
            await runner.shutdown(); store.close()
    report = {'runtime':'kas-container', 'image':KAS_IMAGE, 'work':str(args.work), 'results':results,
              'optional_unverified':['hardware deployment/console/labgrid', 'interactive IDE debugging', 'CVE database scan', 'kernel compilation'],
              'note':'Absent image/buildstats artifacts are recorded as unavailable; a probe PASS means the probe executed, not that a missing artifact exists.'}
    (directory / 'result.json').write_text(json.dumps(report, indent=2))
    print('Saved .developer-validation/result.json', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/tmp/bitloom-developer-validation'))
    parser.add_argument('--engine', choices=['docker','podman'], default='docker')
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--image', action='store_true')
    args = parser.parse_args()
    args.work = args.work.expanduser().resolve()
    asyncio.run(validate(args))


if __name__ == '__main__':
    main()
