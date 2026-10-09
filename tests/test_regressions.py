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
