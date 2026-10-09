import json
import os
from pathlib import Path

import pytest

from bitloom import developer as dev
from bitloom import developer_agent as agent
from bitloom.models import Profile, Settings
from bitloom.runtime import request


def test_device_operations_require_their_actual_backend(tmp_path):
    with pytest.raises(ValueError, match='labgrid_place'):
        dev.board_command({'name': 'board', 'test_argv': ['true']}, 'power')
    with pytest.raises(ValueError, match='SSH'):
        dev.board_command({'ssh': '-bad'}, 'status')
    with pytest.raises(ValueError, match='place'):
        dev.board_command({'labgrid_place': '-bad'}, 'acquire')
    path = tmp_path / 'devices.json'
    path.write_text(json.dumps({'devices': [{'name': 'bad', 'ssh': '-option'}]}))
    with pytest.raises(ValueError, match='SSH'): dev.load_devices(path)


def test_image_comparison_rejects_other_machine_and_tracks_bytes_and_modes():
    before = {'view': 'image', 'data': {'identity': {'MACHINE': 'a'}, 'image': 'minimal', 'packages': {'app': 100}, 'files': {'./bin/app': '-rwxr-xr-x app'}, 'owners': {'app': 'app-recipe'}}}
    after = {'view': 'image', 'data': {'identity': {'MACHINE': 'a'}, 'image': 'minimal', 'packages': {'app': 130, 'new': 5}, 'files': {'./bin/app': '-rwsr-xr-x app'}, 'owners': {'app': 'app-recipe'}}}
    result = dev.compare_captures(before, after)
    assert any('+30 bytes' in r['value'] and 'app-recipe' in r['value'] for r in result['rows'])
    assert any(r['name'] == './bin/app' and r['value'] == 'metadata changed' for r in result['rows'])
    after['data']['identity']['MACHINE'] = 'other'
    with pytest.raises(ValueError, match='Machine'): dev.compare_captures(before, after)


def test_upgrade_comparison_allows_version_change_in_same_machine():
    before = {'view': 'upgrade', 'data': {'identity': {'MACHINE': 'qemu', 'PV': '1'}, 'version': {'PV': '1'}}}
    after = {'view': 'upgrade', 'data': {'identity': {'MACHINE': 'qemu', 'PV': '2'}, 'version': {'PV': '2'}}}
    assert '+    "PV": "2"' in dev.compare_captures(before, after)['text']


def test_clone_kas_profile_is_independent_and_rejects_shared_build(tmp_path):
    settings = Settings(tmp_path / 'profiles.json')
    settings.profiles = [Profile(name='base', root=str(tmp_path), mode='kas-container', environment={'KAS_WORK_DIR': str(tmp_path / 'work')})]
    settings.active = 'base'
    with pytest.raises(ValueError, match='separate'): dev.clone_profile(settings, 'bad', str(settings.profile.build_path))
    clone = dev.clone_profile(settings, 'debug', str(tmp_path / 'debug/build'), 'qemuarm')
    assert clone.environment['KAS_WORK_DIR'] == str(tmp_path / 'debug')
    clone.environment['EXTRA'] = 'new'
    assert 'EXTRA' not in settings.profiles[0].environment
    assert Settings(settings.path).active == 'debug'


def test_variable_history_preserves_order_and_file_line():
    text = '# $SUMMARY [2 operations]\n#   set /work/meta/a.bb:1\n#   append /work/meta/b.bbappend:3\nSUMMARY="first second"\n'
    rows = agent.origins(text)
    assert [r['line'] for r in rows] == [1, 3]
    assert rows[-1]['path'] == '/work/meta/b.bbappend'
    assert agent.values(text)['SUMMARY'] == 'first second'
    assert agent.values('SRC_URI="first\nsecond"\n')['SRC_URI'] == 'first\nsecond'


@pytest.mark.parametrize('name', ['busybox', 'mc:debug:busybox', 'libfoo-native', 'virtual/kernel', 'mc:debug:virtual/kernel'])
def test_multiconfig_targets_are_preserved(name):
    assert agent.target(name) == name


@pytest.mark.parametrize('name', ['-c clean', 'busybox;rm', 'mc::busybox', 'two targets'])
def test_target_injection_is_rejected(name):
    with pytest.raises(ValueError): agent.target(name)


@pytest.mark.parametrize('system', ['cmake', 'meson', 'make', 'python', 'rust'])
async def test_scaffolding_creates_complete_licensed_layer_without_overwrite(tmp_path, system):
    layer = tmp_path / ('meta-' + system)
    files = dev.scaffold_plan('hello', 'hellolayer', system, 'Example Owner')
    result = await request(Profile(root=str(tmp_path)), 'dev-scaffold', str(layer), files=files)
    assert result['path'] == str(layer)
    recipe = layer / 'recipes-example/hello/hello_1.0.bb'
    assert 'LICENSE = "MIT"' in recipe.read_text()
    assert 'md5=' in recipe.read_text()
    assert 'Example Owner' in (recipe.parent / 'files/source/LICENSE').read_text()
    assert 'LAYERSERIES_COMPAT_hellolayer' in (layer / 'conf/layer.conf').read_text()
    with pytest.raises(ValueError): await request(Profile(root=str(tmp_path)), 'dev-scaffold', str(layer), files=files)
    assert recipe.read_text() == files['recipes-example/hello/hello_1.0.bb']


async def test_runtime_payload_larger_than_os_argument_limit(tmp_path):
    content = 'abcdef' * 100000
    profile = Profile(root=str(tmp_path))
    path = tmp_path / 'large.txt'
    await request(profile, 'create', str(path), text=content)
    assert (await request(profile, 'read', str(path)))['text'] == content


async def test_runtime_browser_search_and_external_staleness(tmp_path):
    source = tmp_path / 'meta/recipes/hello.bb'; source.parent.mkdir(parents=True); source.write_text('hello')
    profile = Profile(root=str(tmp_path))
    result = await request(profile, 'dev-browse', str(tmp_path), query='.bb')
    assert any(r['path'] == str(source) for r in result['rows'])
    old = await request(profile, 'dev-fingerprints', '', paths=[str(source)])
    source.write_text('world')
    new = await request(profile, 'dev-fingerprints', '', paths=[str(source)])
    assert old[0]['sha256'] != new[0]['sha256']


def test_buildstats_wall_time_is_not_sum_of_parallel_tasks(tmp_path):
    session = tmp_path / 'stats/20260101'
    for task, started, ended in [('a/do_compile', 10, 20), ('b/do_compile', 12, 22)]:
        file = session / task; file.parent.mkdir(parents=True); file.write_text(f'Started: {started}\nEnded: {ended}\nElapsed time: {ended-started}\n')
    result = agent.performance(str(tmp_path / 'stats'), str(tmp_path))
    assert result['wall_seconds'] == 12
    assert sum(e['seconds'] for e in result['buildstats']) == 20
    assert len(result['buildstats']) == 2


def test_security_delta_and_expiring_review_preserve_upstream_status(tmp_path):
    file = tmp_path / 'cve.json'
    file.write_text(json.dumps({'version': '1', 'package': [{'name': 'app', 'version': '1', 'issue': [{'id': 'CVE-TEST', 'status': 'Unpatched'}]}]}))
    result = agent.security(str(file))
    issue = result['issues'][0]
    reviews = dev.security_disposition(tmp_path / 'reviews.json', issue, 'Owner', 'Configuration reviewed', '2099-01-01')
    assert reviews['app/CVE-TEST']['upstream_status'] == 'Unpatched'
    assert agent.security(str(file))['issues'][0]['status'] == 'Unpatched'
    with pytest.raises(ValueError, match='Expiry'): dev.security_disposition(tmp_path / 'reviews.json', issue, 'Owner', 'Reason', '2000-01-01')
    second = dict(result, issues=[dict(issue, status='Patched')])
    diff = dev.compare_captures({'view':'security', 'data':result}, {'view':'security', 'data':second})
    assert diff['rows'][0]['value'] == 'Unpatched → Patched'


def test_compile_database_mapping_is_boundary_aware_and_preserves_arguments():
    entries = [{'directory':'/work/build', 'file':'/work/src/a.c', 'arguments':['cc', '-I/work/include', '--sysroot=/work/sysroot', '/worker/unrelated.c', '-DNAME=a b']}]
    mapped = dev.map_compile_database(entries, {'/work':'/home/dev/project'})
    assert mapped[0]['file'] == '/home/dev/project/src/a.c'
    assert mapped[0]['arguments'][1] == '-I/home/dev/project/include'
    assert mapped[0]['arguments'][3:] == ['/worker/unrelated.c', '-DNAME=a b']
    assert entries[0]['directory'] == '/work/build'


def test_capture_redacts_secret_variable_value_and_keeps_immutable_files(tmp_path):
    path = dev.capture(tmp_path, Profile(), 'variable', {'title':'Variable', 'variable':'API_TOKEN', 'text':'super-sensitive', 'rows':[{'value':'super-sensitive'}]})
    assert 'super-sensitive' not in path.read_text()
    assert json.loads(path.read_text())['data']['redacted']
    assert path.stat().st_mode & 0o777 == 0o600


def test_board_arguments_are_explicit_and_artifact_identity_is_real(tmp_path):
    image = tmp_path / 'image.bin'; image.write_bytes(b'actual artifact')
    identity = dev.device_identity(str(image))
    assert identity['size'] == 15 and len(identity['sha256']) == 64
    device = {'name':'board', 'ssh':'root@192.0.2.1', 'test_argv':['test-runner', '{artifact}', '{device}']}
    argv = dev.board_command(device, 'test', str(image), 'hello')
    assert argv == ['test-runner', str(image), 'root@192.0.2.1']
    assert dev.board_command({'labgrid_place':'test-place'}, 'power') == ['labgrid-client','-p','test-place','power','cycle']
    with pytest.raises(ValueError): dev.device_identity(str(tmp_path / 'absent'))


def test_kernel_fragment_detects_disabled_and_missing_symbols(tmp_path, monkeypatch):
    fragment = tmp_path / 'fragment.cfg'; fragment.write_text('CONFIG_A=y\n# CONFIG_B is not set\nCONFIG_C=m\n')
    config = tmp_path / '.config'; config.write_text('CONFIG_A=y\nCONFIG_B=y\n')
    monkeypatch.setattr(agent, 'evaluated', lambda recipe: {'B':str(tmp_path)})
    result = agent.kernel('linux-yocto', str(fragment), '')
    assert 'MATCH' in result['rows'][0]['value']
    assert 'MISMATCH' in result['rows'][1]['value']
    assert result['actual']['CONFIG_C'] is None


def test_named_kas_container_uses_owned_runtime_argument(tmp_path):
    from bitloom.commands import invocation
    profile = Profile(root=str(tmp_path), mode='kas-container')
    argv = invocation(profile, ['bitbake','busybox'], 'bitloom-a123').argv
    assert argv[:3] == ['kas-container', '--runtime-args', '--name bitloom-a123 --label io.bitloom.owner=bitloom-a123']
    with pytest.raises(ValueError): invocation(profile, ['bitbake','busybox'], 'bad;name')


def test_real_buildhistory_kib_format_and_pkgdata_exact_bytes(tmp_path, monkeypatch):
    history = tmp_path / 'history/images/qemux86_64/glibc/minimal'
    history.mkdir(parents=True)
    (history / 'installed-package-sizes.txt').write_text('2\tKiB\tapp\n3\tKiB\tother\n')
    (history / 'files-in-image.txt').write_text('-rwxr-xr-x root root 1024 ./usr/bin/app\nlrwxrwxrwx root root 3 ./bin/app -> ../usr/bin/app\n')
    runtime = tmp_path / 'pkgdata/runtime'; runtime.mkdir(parents=True)
    (runtime / 'app').write_text('PN: app-recipe\nPKGSIZE: 1800\n')
    monkeypatch.setattr(agent, 'evaluated', lambda recipe: {'MACHINE':'qemux86-64','MACHINE_ARCH':'qemux86_64','TCLIBC':'glibc',
        'BUILDHISTORY_DIR':str(tmp_path/'history'),'PKGDATA_DIR':str(tmp_path/'pkgdata')})
    result = agent.image('minimal')
    assert result['packages'] == {'app':1800,'other':3072}
    assert result['owners']['app'] == 'app-recipe'
    assert result['files']['./bin/app'].endswith('-> ../usr/bin/app')
    monkeypatch.setattr(agent, 'evaluated', lambda recipe: {'MACHINE':'other-machine','MACHINE_ARCH':'other_machine','TCLIBC':'glibc','BUILDHISTORY_DIR':str(tmp_path/'history')})
    assert not agent.image('minimal')['available']
