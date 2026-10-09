"""wrapper mode: a project launcher script (e.g. YML=... ./script build) drives kas."""
import json
import sys

import pytest

from bitloom.commands import invocation
from bitloom.inspectors import diagnostics
from bitloom.models import Profile
from bitloom.runner import Runner
from bitloom.store import Store

LAUNCHER = '''#!/bin/bash
# Typical project wrapper: configuration from $YML, kas subcommand as arguments.
if [ "$1" = "shell" ] && [ "$2" = "-c" ]; then exec bash -c "$3"; fi
echo "launcher kas $* config=$YML"
'''


@pytest.fixture
def project(tmp_path):
    root = tmp_path / 'project'
    (root / 'scripts').mkdir(parents=True)
    script = root / 'scripts/kas-wrapper.sh'
    script.write_text(LAUNCHER)
    script.chmod(0o755)
    (root / 'build/conf').mkdir(parents=True)
    (root / 'build/conf/local.conf').write_text('MACHINE = "qemux86-64"\n')
    return Profile(name='wrapped', root=str(root), mode='wrapper', launcher=['./scripts/kas-wrapper.sh'],
                   environment={'YML': 'boards/product.yml'})


def test_wrapper_validation_and_mapping(project):
    assert invocation(project, ['kas', 'build']).argv == ['./scripts/kas-wrapper.sh', 'build']
    shell = invocation(project, ['bitbake', '-e', 'busybox']).argv
    assert shell == ['./scripts/kas-wrapper.sh', 'shell', '-c', 'bitbake -e busybox']
    assert invocation(project, ['kas', 'build']).env['YML'] == 'boards/product.yml'
    custom = Profile(**{**project.__dict__, 'launcher_shell': ['run', '--', '{command}']})
    assert invocation(custom, ['bitbake', 'core-image-minimal']).argv[-3:] == ['run', '--', 'bitbake core-image-minimal']
    with pytest.raises(ValueError):
        Profile(**{**project.__dict__, 'launcher': []}).validate()
    with pytest.raises(ValueError):
        Profile(**{**project.__dict__, 'launcher_shell': ['shell']}).validate()
    runtime = next(row for row in diagnostics(project) if row[1] == 'Runtime')
    assert runtime[0] == 'OK' and 'kas-wrapper.sh' in runtime[2]


async def test_wrapper_runs_builds_commands_and_runtime_probes(project, tmp_path):
    store = Store(tmp_path / 'state')
    runner = Runner(store, lambda job, line: None)
    build = runner.submit(project, 'kas build', ['kas', 'build'], 'kas-build')
    command = runner.submit(project, 'command', [sys.executable, '-c', 'print("through the launcher shell")'])
    await runner.consumer
    assert build.status == command.status == 'success'
    assert 'launcher kas build config=boards/product.yml' in build.log.read_text()
    assert 'through the launcher shell' in command.log.read_text()
    from bitloom.runtime import request
    listing = await request(project, 'list', str(project.root_path / 'build'))
    assert any(entry['path'].endswith('conf') for entry in listing)
    store.close()
