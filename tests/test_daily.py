"""Daily helpers: notifications, ETA, run comparison and tmp/work usage."""
import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import pytest

from bitloom import notify
from bitloom.insights import compare, eta, human, previous_runs, work_usage, work_report
from bitloom.models import Profile


def job(status='success', seconds=600, **extra):
    start = datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)
    return SimpleNamespace(id='j1', title='Build core-image-minimal', status=status, code=0 if status == 'success' else 1,
                           profile=SimpleNamespace(name='kas-wrynose'), started=start.isoformat(), finished=(start + timedelta(seconds=seconds)).isoformat(),
                           command=['kas', 'build'], log='/tmp/x.log', failure_logs=['/w/temp/log.do_compile.1'], action_id='kas-build', **extra)


class Hook(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        Hook.received.append((dict(self.headers), body))
        self.send_response(200); self.end_headers()

    def log_message(self, *args):
        pass


def test_notification_settings_and_formats(tmp_path, monkeypatch):
    assert notify.load(tmp_path)['on'] == ['success', 'failed']
    for bad in ({'webhook': 'ftp://x'}, {'format': 'xml'}, {'on': ['maybe']}):
        with pytest.raises(ValueError):
            notify.save(tmp_path, bad)
    server = HTTPServer(('127.0.0.1', 0), Hook)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_address[1]}/topic'
    monkeypatch.setattr(notify, 'desktop', lambda title, body: 'fake-desktop')
    try:
        notify.save(tmp_path, {'webhook': url, 'format': 'ntfy', 'min_seconds': 300})
        assert (tmp_path / 'notifications.json').stat().st_mode & 0o777 == 0o600
        assert notify.send(tmp_path, job(seconds=60)) == []                       # too short
        assert notify.send(tmp_path, job('failed')) == ['fake-desktop', 'webhook']
        for _ in range(50):
            if Hook.received:
                break
            threading.Event().wait(.05)
        headers, body = Hook.received[-1]
        assert headers['Priority'] == 'high' and b'kas-wrynose' in body and b'log.do_compile.1' in body
        notify.save(tmp_path, {'webhook': url, 'format': 'json', 'min_seconds': 0})
        request = notify.webhook_request(notify.load(tmp_path), *notify.message(job()), job())
        assert json.loads(request.data)['status'] == 'success'
        notify.save(tmp_path, {'webhook': url, 'format': 'slack'})
        assert 'text' in json.loads(notify.webhook_request(notify.load(tmp_path), 't', 'b', job()).data)
    finally:
        server.shutdown()


def test_eta_from_history_and_progress():
    now = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)
    started = (now - timedelta(minutes=10)).isoformat()
    history = [{'profile': 'p', 'argv': '["kas", "build"]', 'status': 'success',
                'started': (now - timedelta(days=d)).isoformat(), 'finished': (now - timedelta(days=d) + timedelta(minutes=30)).isoformat()}
               for d in (1, 2, 3)]
    only_history = eta(history, 'p', ['kas', 'build'], started, (0, 0), now)
    assert round(only_history['remaining']) == 20 * 60 and 'previous runs' in only_history['basis']
    both = eta(history, 'p', ['kas', 'build'], started, (500, 1000), now)
    assert round(both['remaining']) == round((20 * 60 + 10 * 60) / 2)
    assert eta([], 'p', ['kas', 'build'], started, (5, 1000), now) is None      # too early to trust the rate
    assert len(previous_runs(history, 'p', '["kas", "build"]')) == 3 and human(3725) == '1h 02m'


def test_compare_runs_and_work_usage(tmp_path):
    old, new = tmp_path / 'old.log', tmp_path / 'new.log'
    old.write_text('NOTE: Running setscene task 1 of 900\nNOTE: Running task 1 of 100\nWARNING: busybox: QA issue 1\n'
                   'NOTE: Sstate summary: Wanted 1000 Local 900 Mirrors 0 Missed 100 Current 0\n')
    new.write_text('NOTE: Running setscene task 1 of 200\nNOTE: Running task 1 of 800\nWARNING: busybox: QA issue 2\nWARNING: openssh: new problem\n'
                   'ERROR: zlib do_compile failed\nNOTE: Sstate summary: Wanted 1000 Local 200 Mirrors 0 Missed 800 Current 0\n')
    row = lambda log, day, status: {'title': 'Build', 'log': str(log), 'status': status, 'started': f'2026-10-{day}T08:00:00+00:00', 'finished': f'2026-10-{day}T08:30:00+00:00'}
    text = compare(row(new, 12, 'failed'), row(old, 11, 'success'))
    assert 'NEW WARNINGS (1)' in text and 'openssh: new problem' in text and 'NEW ERRORS (1)' in text
    assert 'QA issue' not in text.split('NEW WARNINGS')[1].split('WARNINGS GONE')[0]   # numbers are normalised
    assert '90.0' in text and '20.0' in text
    work = tmp_path / 'build/tmp/work/core2-64-poky-linux'
    for name, size in (('big', 300_000), ('small', 10_000)):
        (work / name / '1.0').mkdir(parents=True)
        (work / name / '1.0/blob').write_bytes(b'x' * size)
    data = work_usage(Profile(root=str(tmp_path)))
    assert [r['recipe'] for r in data['rows']] == ['big', 'small'] and data['complete'] and not data['rm_work']
    assert 'INHERIT += "rm_work"' in work_report(Profile(root=str(tmp_path)), data) and 'bitbake -c clean big' in work_report(Profile(root=str(tmp_path)), data)


async def test_tui_daily_keys(tmp_path):
    import sys
    from textual.widgets import Input
    from bitloom.app import BitloomApp
    from bitloom.cli import make_demo
    from bitloom.screens import FileScreen, NotificationsScreen
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    async with app.run_test(size=(150, 46)) as pilot:
        await pilot.pause(.4)
        for _ in range(2):
            j = app.runner.submit(app.profile, 'twice', [sys.executable, '-c', 'print("WARNING: sample")'])
            await app.runner.consumer
        app.select_job(j.id, j.log)
        await pilot.pause(.3)
        await pilot.press('1', 'd')
        for _ in range(40):
            if isinstance(app.screen, FileScreen):
                break
            await pilot.pause(.1)
        assert isinstance(app.screen, FileScreen) and 'Compare runs of: twice' in app.screen.query_one('#content').text
        await pilot.press('escape', '9', 'o')
        await pilot.pause(.3)
        assert isinstance(app.screen, NotificationsScreen)
        app.screen.query_one('#nt-min', Input).value = '5'
        await pilot.press('ctrl+o')
        await pilot.pause(.2)
        assert json.loads((tmp_path / 'state/notifications.json').read_text())['min_seconds'] == 5
    app.store.close()


def test_web_compare_eta_and_notifications(tmp_path):
    import sys, time, urllib.request
    from bitloom.cli import make_demo
    from bitloom.daemon import rpc
    from bitloom.web import Dashboard, create_server
    board = Dashboard(make_demo(tmp_path / 'demo'), tmp_path / 'state', token='t')
    server = create_server(board, '127.0.0.1', 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_address[1]}'

    def call(path, body=None):
        request = urllib.request.Request(base + path, json.dumps(body).encode() if body is not None else None, {'X-Bitloom-Token': 't', 'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(request).read())
    try:
        ids = []
        for _ in range(2):
            ids.append(call('/api/jobs', {'action': 'custom', 'values': {'command': f'{sys.executable} -c "print(1)"'}})['id'])
            for _ in range(100):
                if next(r for r in call('/api/state')['history'] if r['id'] == ids[-1])['status'] == 'success':
                    break
                time.sleep(.1)
        assert 'Compare runs of' in call(f'/api/jobs/{ids[-1]}/compare')['text']
        assert 'No earlier run' in call(f'/api/jobs/{ids[0]}/compare')['text']
        call('/api/notifications', {'desktop': False, 'min_seconds': 0, 'on': ['failed'], 'webhook': '', 'format': 'json'})
        assert call('/api/notifications')['on'] == ['failed']
        assert 'tmp/work usage' in call('/api/workusage')['text']
    finally:
        server.shutdown()
        try:
            rpc(board.state, {'op': 'stop'})
        except (OSError, ValueError):
            pass
