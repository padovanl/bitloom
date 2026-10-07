import asyncio
import json
import os
import sys
import time
from pathlib import Path

import pytest

from yoctotui.commands import BY_ID, arguments, invocation
from yoctotui.inspectors import Entry, cache_candidates, cache_path, metadata, prune_cache, search_log
from yoctotui.models import Profile, Settings
from yoctotui.runner import Job, Runner
from yoctotui.store import Store


def test_command_input_cannot_inject_shell(tmp_path):
    script = tmp_path / 'init.sh'
    script.write_text('mkdir -p "$1"\ncd "$1"\n')
    p = Profile(root=str(tmp_path), init_script=str(script))
    payload = 'recipe; touch /tmp/should-not-exist'
    inv = invocation(p, arguments(BY_ID['build'], {'target': payload}))
    assert "'recipe; touch /tmp/should-not-exist'" in inv.argv[-1]
    with pytest.raises(ValueError):
        arguments(BY_ID['build'], {'target': '-e'})
    assert arguments(BY_ID['task'], {'target': 'busybox', 'task': 'compile'}) == ['bitbake', 'busybox', '-c', 'compile']


@pytest.mark.parametrize('mode,first', [('kas', 'kas'), ('kas-container', 'kas-container')])
def test_kas_routes_all_tools(tmp_path, mode, first):
    p = Profile(root=str(tmp_path), mode=mode, kas_file='a.yml:b.yml')
    assert invocation(p, ['devtool', 'status']).argv == [first, 'shell', 'a.yml:b.yml', '-c', 'devtool status']
    assert invocation(p, ['kas', 'build']).argv == [first, 'build', 'a.yml:b.yml']


def test_container_mount_and_environment(tmp_path):
    p = Profile(root=str(tmp_path), mode='container', image='yocto:local', machine='qemuarm', environment={'FOO': 'a b'})
    inv = invocation(p, ['bitbake', 'busybox'])
    assert f'{tmp_path}:/work' in inv.argv
    assert 'MACHINE=qemuarm' in inv.argv
    assert 'FOO=a b' in inv.argv
    assert 'cd /work/build' in inv.argv[-1]
    p.build_dir = '/outside'
    with pytest.raises(ValueError):
        p.validate()


def test_settings_roundtrip(tmp_path):
    path = tmp_path / 'profiles.json'
    settings = Settings(path)
    settings.profiles = [Profile(name='one', root=str(tmp_path)), Profile(name='two', root=str(tmp_path), mode='kas')]
    settings.active = 'two'
    settings.save()
    assert Settings(path).profile.mode == 'kas'
    assert path.stat().st_mode & 0o777 == 0o600


async def test_runner_serial_history_failure(tmp_path):
    store = Store(tmp_path / 'state')
    events = []
    runner = Runner(store, lambda j, line: events.append((j.id, line)))
    p = Profile(root=str(tmp_path))
    first = runner.submit(p, 'first', [sys.executable, '-c', 'print("NOTE: Running task 1 of 2"); print("ERROR: example")'])
    second = runner.submit(p, 'second', [sys.executable, '-c', 'raise SystemExit(7)'])
    await runner.consumer
    assert first.status == 'success' and first.progress == (1, 2)
    assert second.status == 'failed' and second.code == 7
    assert first.finished <= second.started
    assert 'ERROR: example' in first.log.read_text()
    assert len(store.history()) == 2
    store.close()


async def test_cancel_running_and_queued(tmp_path):
    store = Store(tmp_path / 'state')
    runner = Runner(store, lambda *_: None)
    p = Profile(root=str(tmp_path))
    first = runner.submit(p, 'sleep', [sys.executable, '-c', 'import time; time.sleep(60)'])
    second = runner.submit(p, 'queued', [sys.executable, '-c', 'print("SHOULD NOT RUN")'])
    await asyncio.sleep(.1)
    await runner.cancel(second)
    await runner.cancel(first)
    await runner.consumer
    assert first.status == second.status == 'cancelled'
    assert not second.log.exists()
    store.close()


def test_task_tracking_preserves_hyphenated_recipe():
    job = Job(Profile(), 'build', ['bitbake', 'image'])
    Runner.track_tasks(job, 'NOTE: recipe gcc-cross-aarch64-13.2.0-r0: task do_compile: Started')
    assert job.at_risk == {'gcc-cross-aarch64'}
    Runner.track_tasks(job, 'NOTE: recipe gcc-cross-aarch64-13.2.0-r0: task do_compile: Succeeded')
    assert not job.at_risk


def test_prune_ignores_symlinks_changed_and_outside(tmp_path):
    root = tmp_path / 'cache'
    root.mkdir()
    old = root / 'old.tar'
    old.write_text('old')
    outside = tmp_path / 'outside'
    outside.write_text('keep')
    link = root / 'link'
    link.symlink_to(outside)
    changed = root / 'changed'
    changed.write_text('initial')
    entries = [Entry(p.name, '', p, p.stat().st_size, p.stat().st_mtime) for p in (old, outside, link, changed)]
    changed.write_text('changed now')
    assert prune_cache(root, entries)[0] == 1
    assert outside.exists() and changed.exists() and link.is_symlink()


def test_cache_config_and_metadata(tmp_path):
    conf = tmp_path / 'build/conf'
    conf.mkdir(parents=True)
    (conf / 'local.conf').write_text('DL_DIR = "${TOPDIR}/../../shared-downloads"\n')
    p = Profile(root=str(tmp_path))
    assert cache_path(p, 'downloads') == tmp_path / 'build/../../shared-downloads'
    layer = tmp_path / 'meta-app/conf'
    layer.mkdir(parents=True)
    (layer / 'layer.conf').write_text('')
    (layer.parent / 'hello_1.0.bb').write_text('')
    assert {e.kind for e in metadata(p)} == {'layer', 'bb'}


def test_log_search_context(tmp_path):
    log = tmp_path / 'log'
    log.write_text('before\nERROR: compile failed\nafter\n')
    result = search_log(log, 'compile', True)
    assert 'before' in result and 'after' in result


def test_complete_file_log_search_finds_early_error(tmp_path):
    log = tmp_path / 'large.log'
    log.write_text('ERROR: early issue\n' + 'fine\n' * 6000)
    assert 'early issue' in search_log(log, 'issue', True)


def test_prune_protects_git_checkout_and_sibling_lock(tmp_path):
    root = tmp_path / 'downloads'
    git = root / 'git2/repo/objects'
    git.mkdir(parents=True)
    p = git / 'object'
    p.write_text('git object')
    archive = root / 'source.tar.gz'
    archive.write_text('source')
    archive.with_name(archive.name + '.lock').touch()
    old = time.time() - 86400 * 60
    for file in (p, archive):
        os.utime(file, (old, old))
    entries = [Entry(file.name, '', file, file.stat().st_size, file.stat().st_mtime) for file in (p, archive)]
    assert cache_candidates(entries, 30) == []


def test_store_prevents_concurrent_sessions(tmp_path):
    first = Store(tmp_path)
    with pytest.raises(ValueError, match='Another'):
        Store(tmp_path)
    first.close()
    second = Store(tmp_path)
    second.close()


async def test_graceful_stop_sends_only_one_client_signal(tmp_path, monkeypatch):
    import signal
    store = Store(tmp_path / 'state')
    runner = Runner(store, lambda *_: None)
    job = Job(Profile(root=str(tmp_path)), 'image', ['bitbake', 'image'])
    class Process:
        pid = 12345
        returncode = None
    job.process = Process()
    job.status = 'running'
    calls = []
    monkeypatch.setattr(os, 'kill', lambda pid, sig: calls.append((pid, sig)))
    await runner.graceful_stop(job)
    await runner.graceful_stop(job)
    assert calls == [(12345, signal.SIGINT)]
    assert job.status == 'cancelling'
    store.close()


def test_kas_external_work_directory(tmp_path):
    p = Profile(root=str(tmp_path), mode='kas-container', environment={'KAS_WORK_DIR': '/tmp/separate-work'})
    p.validate()
    assert p.build_path == Path('/tmp/separate-work/build')
    p.environment['KAS_BUILD_DIR'] = '/tmp/custom-build'
    assert p.build_path == Path('/tmp/custom-build')
