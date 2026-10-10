"""Team features: CI runs, shared profiles, setup/infrastructure checks, image matrix, fleet."""
import argparse
import asyncio
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from bitloom.cli import make_demo
from bitloom.models import Profile, Settings


def ci_args(tmp_path, config, specs, profiles=None, **extra):
    return argparse.Namespace(config=config, state=tmp_path / 'ci-state', ci=specs, profile=profiles, junit=str(tmp_path / 'junit.xml'),
                              summary=str(tmp_path / 'summary.json'), annotations='github', fail_fast=extra.get('fail_fast', False))


def test_ci_matrix_reports_and_annotations(tmp_path, capsys):
    from bitloom.ci import main
    config = make_demo(tmp_path / 'demo')
    data = json.loads(config.read_text())
    data['profiles'].append(dict(data['profiles'][0], name='second'))
    config.write_text(json.dumps(data))
    code = main(ci_args(tmp_path, config, ['parse'], ['demo', 'second']))
    out = capsys.readouterr().out
    assert code == 1  # bitbake is not installed here: both jobs fail, reports are still written
    assert out.count('::group::') == 2 and '::error title=demo: Parse metadata failed' in out
    suites = ET.parse(tmp_path / 'junit.xml').getroot()
    assert suites.get('tests') == '2' and {s.get('name') for s in suites} == {'demo', 'second'}
    summary = json.loads((tmp_path / 'summary.json').read_text())
    assert not summary['ok'] and len(summary['jobs']) == 2


def test_ci_facts_and_spec_validation(tmp_path):
    from bitloom.ci import log_facts, parse_spec
    log = tmp_path / 'job.log'
    log.write_text('$ bitbake x\nWARNING: a\nWARNING: a\nERROR: Task (/x/foo_1.0.bb:do_compile) failed with exit code 1\n'
                   'NOTE: Sstate summary: Wanted 10 Local 8 Mirrors 1 Missed 1 Current 0\n')
    facts = log_facts(log)
    assert facts['warnings'] == 2 and facts['failed_tasks'] == ['/x/foo_1.0.bb:do_compile'] and facts['sstate']['hit_rate'] == 0.9
    assert parse_spec('build:core-image-minimal')[1] == ['bitbake', 'core-image-minimal']
    assert parse_spec('kas-build')[1] == ['kas', 'build']
    for spec in ('devshell:x', 'diffsigs', 'nope', 'build:-x'):
        with pytest.raises(ValueError):
            parse_spec(spec)


async def test_ci_success_path_produces_images(tmp_path, monkeypatch):
    from bitloom.ci import Output, run
    import io
    config = make_demo(tmp_path / 'demo')
    build = tmp_path / 'demo/build'
    script = tmp_path / 'fake-bitbake'
    script.write_text('#!/bin/sh\nmkdir -p tmp/deploy/images/qemux86-64\necho img > tmp/deploy/images/qemux86-64/demo-image-qemux86-64.rootfs.wic\n'
                      'echo "NOTE: Sstate summary: Wanted 4 Local 4 Mirrors 0 Missed 0 Current 0"\n')
    script.chmod(0o755)
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    (bindir / 'bitbake').symlink_to(script)
    import os
    monkeypatch.setenv('PATH', f'{bindir}:{os.environ["PATH"]}')
    stream = io.StringIO()
    results = await run(config, tmp_path / 'ci-state', ['build:demo-image'], [], Output('plain', stream))
    assert results[0]['status'] == 'success' and results[0]['sstate']['hit_rate'] == 1.0
    assert results[0]['images'] == [{'machine': 'qemux86-64', 'file': 'demo-image-qemux86-64.rootfs.wic', 'size': 4}]
    assert '==> [1/1] demo: Build target · demo-image' in stream.getvalue()


def test_team_profiles_are_shared_read_only(tmp_path):
    team = tmp_path / 'nfs/team.json'
    team.parent.mkdir()
    team.write_text(json.dumps({'profiles': [{'name': 'product-a', 'root': str(tmp_path), 'mode': 'kas', 'kas_file': 'a.yml'},
                                             {'name': 'mine', 'root': str(tmp_path)}]}))
    config = tmp_path / 'home/profiles.json'
    config.parent.mkdir()
    config.write_text(json.dumps({'active': 'product-a', 'include': ['../nfs/team.json', '../missing.json'],
                                  'profiles': [{'name': 'mine', 'root': str(tmp_path)}]}))
    settings = Settings(config)
    assert settings.profile.name == 'product-a' and settings.shared == {'product-a': str(team)}
    assert any('already defined' in w for w in settings.include_warnings) and any('missing.json' in w for w in settings.include_warnings)
    settings.save()
    saved = json.loads(config.read_text())
    assert [p['name'] for p in saved['profiles']] == ['mine'] and saved['include'] == ['../nfs/team.json', '../missing.json']


def test_filesystem_and_network_checks(tmp_path):
    from bitloom.infra import endpoints, filesystem, filesystem_checks, probe
    table = [('/mnt/nfs', 'nfs4'), ('/', 'ext4')]
    assert filesystem(Path('/mnt/nfs/sstate/ab'), table) == 'nfs4'
    profile = Profile(root=str(tmp_path), build_dir='/mnt/nfs/build')
    rows = {name: (status, detail) for status, name, detail in filesystem_checks(profile, table)}
    assert rows['TMPDIR filesystem'][0] == 'WARN' and rows['DL_DIR filesystem'][0] == 'INFO'
    conf = tmp_path / 'build/conf'
    conf.mkdir(parents=True)
    (conf / 'local.conf').write_text('SSTATE_MIRRORS = "file://.* file:///nonexistent/sstate/PATH"\nBB_HASHSERVE = "127.0.0.1:1"\nPRSERV_HOST = "localhost:0"\n')
    found = endpoints(Profile(root=str(tmp_path)))
    assert ('SSTATE_MIRRORS', 'file:///nonexistent/sstate') in found and ('BB_HASHSERVE', '127.0.0.1:1') in found
    assert probe('file:///nonexistent/sstate')[0] == 'WARN'
    assert probe('127.0.0.1:1', timeout=.5)[0] == 'WARN'
    assert probe('localhost:0')[0] == 'OK'


def test_image_matrix_and_fleet(tmp_path):
    from bitloom.reports import image_matrix
    from bitloom.fleet import fleet_report, fleet_status
    profile = Profile(root=str(tmp_path))
    for machine in ('board-a', 'board-b'):
        folder = tmp_path / 'build/tmp/deploy/images' / machine
        folder.mkdir(parents=True)
        (folder / f'img-{machine}.rootfs.wic.zst').write_bytes(b'x' * 10)
        (folder / f'img-{machine}.rootfs.manifest').write_text('busybox core2_64 1.36\nbase-files qemux86_64 3.0\n')
    text = image_matrix(profile)
    assert 'board-a  ·  1 image files' in text and '2 packages' in text
    devices = tmp_path / 'devices.json'
    devices.write_text(json.dumps({'devices': [{'name': 'no-ssh'}, {'name': 'lab', 'labgrid_place': 'place-1'}]}))
    rows = asyncio.run(fleet_status(devices))
    assert {r['device']: r['status'] for r in rows}['no-ssh'] == 'unconfigured'
    assert 'Fleet status' in fleet_report(rows)
