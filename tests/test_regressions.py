"""Regression tests for crash paths and state handling found during review."""
import json
import sys
from pathlib import Path

from textual.widgets import DataTable

from bitloom.app import BitloomApp
from bitloom.cli import make_demo
from bitloom.daemon import RemoteRunner
from bitloom.runner import Job, Runner
from bitloom.models import Profile


class _Store:
    def __init__(self, directory):
        self.directory = directory


def test_remote_tail_waits_for_complete_lines_and_split_utf8(tmp_path):
    seen = []
    runner = RemoteRunner(_Store(tmp_path), lambda job, line: seen.append(line))
    log = tmp_path / 'job.log'
    log.write_bytes(b'')
    raw = {'id': 'abc', 'title': 't', 'command': ['true'], 'action_id': 'custom', 'status': 'running',
           'started': '2026-01-01T00:00:00+00:00', 'finished': '', 'code': None, 'progress': [0, 0],
           'errors': [], 'failure_logs': [], 'cancel_requested': False, 'managed_container': '',
           'graceful_requested': False, 'stop_confirmed': False, 'shutdown_message': False,
           'active_recipe_tasks': {}, 'shutdown_evidence': {}, 'profile': Profile().__dict__,
           'log': str(log), 'at_risk': []}
    runner.update({'jobs': [raw], 'active': 'abc'})
    # First half of "é" plus an unterminated line: nothing may be emitted yet.
    log.write_bytes('NOTE: caf'.encode() + 'é'.encode()[:1])
    runner.update({'jobs': [raw], 'active': 'abc'})
    assert [line for line in seen if line] == []
    with log.open('ab') as stream:
        stream.write('é'.encode()[1:] + b' done\nsecond\n')
    runner.update({'jobs': [raw], 'active': 'abc'})
    assert [line for line in seen if line] == ['NOTE: café done', 'second']


def test_setscene_progress_is_tracked(tmp_path):
    job = Job(Profile(), 't', ['true'])
    runner = Runner.__new__(Runner)
    from bitloom.runner import SETSCENE, PROGRESS
    line = 'NOTE: Running setscene task 12 of 340 (/poky/meta/recipes-core/busybox/busybox_1.36.1.bb:do_package_setscene)'
    assert SETSCENE.search(line).groups() == ('12', '340')
    assert not PROGRESS.search(line)


async def test_history_selection_follows_job_and_retry_guard(tmp_path):
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    async with app.run_test(size=(140, 42)) as pilot:
        first = app.runner.submit(app.profile, 'first', [sys.executable, '-c', 'pass'])
        await app.runner.consumer
        await pilot.pause(.2)
        app.select_job(first.id, first.log)
        second = app.runner.submit(app.profile, 'second', [sys.executable, '-c', 'import time; time.sleep(1)'])
        await pilot.pause(.2)
        app.select_job(first.id, first.log)
        app.refresh_history()
        table = app.query_one('#history', DataTable)
        assert table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value == first.id
        # Retrying an active operation must not queue a duplicate.
        app.select_job(second.id, second.log)
        before = len(app.runner.jobs)
        app.retry_job()
        assert len(app.runner.jobs) == before
        await app.runner.consumer
    app.store.close()


async def test_failed_prune_and_stop_notify_instead_of_crashing(tmp_path):
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.2)
        await app.execute_prune(tmp_path / 'missing-cache', []).wait()
        job = Job(app.profile, 'kas job', ['kas', 'build'])
        job.status = 'running'

        async def refuse(_):
            raise ValueError('service refused')
        app.runner.graceful_stop = refuse
        await app.apply_stop(job, 'graceful').wait()
        await pilot.pause(.1)
        assert app.is_running
    app.store.close()


def test_profiles_from_other_versions_load(tmp_path):
    from bitloom.models import Settings
    config = tmp_path / 'profiles.json'
    config.write_text(json.dumps({'active': 'a', 'profiles': [{'name': 'a', 'root': str(tmp_path), 'future_field': 1}]}))
    settings = Settings(config)
    assert settings.profile.name == 'a' and settings.ignored_keys == ['future_field']
    assert Profile.from_dict({'name': 'b', 'launcher': ['x'], 'unknown': 2}).launcher == ['x']


async def test_output_written_while_hidden_is_rerendered(tmp_path):
    from textual.widgets import RichLog
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.3)
        await pilot.press('2')
        await pilot.pause(.2)
        job = app.runner.submit(app.profile, 'hidden', [sys.executable, '-c', 'print("a fairly long line of output written while Builds is hidden")'])
        app.select_job(job.id, job.log)
        await app.runner.consumer
        await pilot.pause(.4)
        await pilot.press('1')
        await pilot.pause(.5)
        lines = [line.text for line in app.query_one('#log', RichLog).lines]
        assert any('a fairly long line of output' in text for text in lines)
    app.store.close()


def test_tools_next_to_bitloom_are_found_without_an_activated_virtualenv(tmp_path, monkeypatch):
    """A build service started by another client inherited a bare PATH: kas-container in the
    virtualenv was not found and the build failed with FileNotFoundError."""
    import os
    import sys
    from pathlib import Path
    from bitloom.commands import invocation, which
    from bitloom.models import Profile
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    venv = str(Path(sys.executable).parent)
    profile = Profile(name="p", root=str(tmp_path), mode="host")
    path = invocation(profile, ["bitbake", "busybox"]).env["PATH"].split(os.pathsep)
    assert path[:2] == ["/usr/bin", "/bin"] and path[-1] == venv  # system tools keep precedence
    assert which(Path(sys.executable).name)


async def test_failed_start_stops_progress_and_explains(tmp_path):
    """A command that never started left the progress bar animating and only said 'exit -1'."""
    from bitloom.progress import TaskProgress
    from bitloom.cli import prepare_demo
    app = BitloomApp(prepare_demo(tmp_path / 'state'), tmp_path / 'state')
    notes = []
    original = app.notify
    app.notify = lambda message, *a, **k: (notes.append(str(message)), original(message, *a, **k))[1]
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.5)
        job = app.runner.submit(app.profile, 'Build target · demo-image', ['definitely-not-a-command-xyz', 'demo-image'], 'build')
        app.select_job(job.id, job.log)
        await app.runner.consumer
        await pilot.pause(.5)
        bar = app.query_one('#progress', TaskProgress)
        assert bar.status == 'failed' and bar.fraction() is None and not bar.timer._active.is_set()   # no animation after the end
        assert any('definitely-not-a-command-xyz not found' in n for n in notes)
        # Jobs carry their target; rows of other profiles name their profile.
        await pilot.press('P'); await pilot.pause(.3); await pilot.press('down', 'enter'); await pilot.pause(1)
        title = str(app.query_one('#history').get_row_at(0)[0])
        assert 'demo-image' in title and title.rstrip().endswith('demo')


def test_build_report_names_empty_sections(tmp_path):
    from bitloom.reports import build_summary
    log = tmp_path / 'build.log'
    log.write_text('NOTE: nothing happened\n')
    text = build_summary(log)
    assert 'Failed tasks\n  none' in text and 'Warnings\n  none' in text


async def test_reconnecting_does_not_announce_old_job_ends(tmp_path):
    """Reopening the TUI on a running service announced every finished job again."""
    from bitloom.runner import Job
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    notes = []
    original = app.notify
    app.notify = lambda message, *a, **k: (notes.append(str(message)), original(message, *a, **k))[1]
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.5)
        old = Job(id='old1', profile=app.profile, title='Old build', command=['bitbake', 'x'], log=tmp_path / 'old.log',
                  status='failed', started='2020-01-01T00:00:00+00:00', finished='2020-01-01T00:10:00+00:00', code=1)
        app.job_update(old, None)
        await pilot.pause(.2)
        assert not any('Old build' in n for n in notes)


async def test_runner_splits_glued_messages_and_counts_noexec(tmp_path):
    """BitBake prints 'Initialising tasks...WARNING: x' and ends with 'Running noexec task N of N'."""
    import sys
    from bitloom.models import Profile
    from bitloom.runner import Runner
    from bitloom.store import Store
    script = tmp_path / 'out.py'
    script.write_text('print("Initialising tasks...WARNING: tainted from a forced run")\n'
                      'print("NOTE: Running task 1244 of 1250 (x.bb:do_compile)")\n'
                      'print("NOTE: Running noexec task 1250 of 1250 (x.bb:do_build)")\n')
    store = Store(tmp_path / 'state')
    runner = Runner(store, lambda job, line: None)
    job = runner.submit(Profile(name='p', root=str(tmp_path)), 'glued', [sys.executable, str(script)])
    await runner.consumer
    lines = job.log.read_text().splitlines()
    assert 'Initialising tasks...' in lines and 'WARNING: tainted from a forced run' in lines
    assert job.progress == (1250, 1250)
    store.close()


def test_console_builds_leave_out_bitloom_jobs(tmp_path):
    """Builds Bitloom started appeared again under 'console builds · started outside Bitloom'."""
    from datetime import datetime, timedelta, timezone
    from bitloom.inspectors import console_logs
    from bitloom.models import Profile
    profile = Profile(name='p', root=str(tmp_path))
    cooker = profile.build_path / 'tmp/log/cooker/qemux86-64'
    cooker.mkdir(parents=True)
    start = datetime(2026, 10, 18, 1, 35, 10, tzinfo=timezone.utc)
    ours_utc = cooker / (start + timedelta(seconds=7)).strftime('%Y%m%d%H%M%S.log')                       # container clock in UTC
    ours_local = cooker / (start + timedelta(seconds=9)).astimezone().strftime('%Y%m%d%H%M%S.log')        # host clock
    outside = cooker / (start - timedelta(hours=3)).strftime('%Y%m%d%H%M%S.log')
    for path in (ours_utc, ours_local, outside):
        path.write_text('NOTE: Tasks Summary: Attempted 1 tasks of which 0 didn\'t need to be rerun and all succeeded.\n')
    jobs = [(start.isoformat(), (start + timedelta(seconds=40)).isoformat())]
    assert [e.path for e in console_logs(profile, jobs=jobs)] == [outside]
    assert len(console_logs(profile)) == 3
