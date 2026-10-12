"""Web dashboard: authentication, Host checks, the shared service and Toaster-style reports."""
import asyncio
import json
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

from bitloom.cli import make_demo
from bitloom.daemon import rpc
from bitloom.web import Dashboard, create_server


@pytest.fixture
def dashboard(tmp_path):
    board = Dashboard(make_demo(tmp_path / 'demo'), tmp_path / 'state', token='secret-token')
    server = create_server(board, '127.0.0.1', 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield board, f'http://127.0.0.1:{server.server_address[1]}'
    server.shutdown()
    server.server_close()
    # The service refuses to stop while jobs are active: cancel them first.
    try:
        for job in rpc(board.state, {'op': 'status'})['jobs']:
            if job['status'] in {'running', 'queued', 'cancelling'}:
                rpc(board.state, {'op': 'cancel', 'id': job['id']})
        rpc(board.state, {'op': 'stop'})
    except (OSError, ValueError):
        pass


def call(base, path, body=None, token='secret-token', host=None):
    request = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                     method='POST' if body is not None else 'GET')
    if token:
        request.add_header('X-Bitloom-Token', token)
    if host:
        request.add_header('Host', host)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def test_page_and_security_checks(dashboard):
    board, base = dashboard
    status, page = call(base, '/', token=None)
    assert status == 200 and b'bitloom' in page and b'innerHTML' not in page
    assert call(base, '/api/state', token=None)[0] == 401
    assert call(base, '/api/state', token='wrong')[0] == 401
    assert call(base, '/api/state', host='attacker.example:80')[0] == 421
    assert call(base, '/api/nothing')[0] == 404


def test_queue_follow_report_and_retry_through_shared_service(dashboard, tmp_path):
    board, base = dashboard
    status, body = call(base, '/api/actions')
    assert status == 200 and any(a['id'] == 'build' for a in json.loads(body))
    status, body = call(base, '/api/preview', {'action': 'build', 'values': {'target': 'demo-image'}})
    assert status == 200 and 'bitbake demo-image' in json.loads(body)['command']
    assert call(base, '/api/jobs', {'action': 'devshell', 'values': {'target': 'x'}})[0] == 400
    assert call(base, '/api/jobs', {'action': 'build', 'values': {'target': '-x'}})[0] == 400
    script = 'print("NOTE: Running task 1 of 2"); print("WARNING: odd"); print("Sstate summary: Wanted 4 Local 3 Mirrors 0 Missed 1 Current 0")'
    status, body = call(base, '/api/jobs', {'action': 'custom', 'values': {'command': f"{sys.executable} -c '{script}'"}})
    assert status == 200, body
    ident = json.loads(body)['id']
    for _ in range(100):
        state = json.loads(call(base, '/api/state')[1])
        row = next(r for r in state['history'] if r['id'] == ident)
        if row['status'] == 'success':
            break
        time.sleep(.1)
    assert row['status'] == 'success' and row['progress'] == [1, 2]
    log = json.loads(call(base, f'/api/jobs/{ident}/log?offset=0')[1])
    assert 'WARNING: odd' in log['text'] and log['offset'] == log['size']
    assert json.loads(call(base, f'/api/jobs/{ident}/log?offset={log["offset"]}')[1])['text'] == ''
    assert 'WARNING: odd' in json.loads(call(base, f'/api/jobs/{ident}/log?q=odd')[1])['text']
    report = json.loads(call(base, f'/api/jobs/{ident}/report')[1])
    assert '75.0%' in report['sstate'] and '1 × odd' in report['warnings']
    status, body = call(base, f'/api/jobs/{ident}/retry', {})
    assert status == 200 and json.loads(body)['id'] != ident
    assert call(base, '/api/jobs/unknown/log')[0] == 404


def test_read_only_views_and_task_log_confinement(dashboard, tmp_path):
    board, base = dashboard
    meta = json.loads(call(base, '/api/metadata?q=demo-agent')[1])
    assert meta['total'] == 1 and meta['rows'][0]['kind'] == 'bb'
    health = json.loads(call(base, '/api/health')[1])
    assert any(check['name'] == 'local.conf' and check['status'] == 'OK' for check in health['checks'])
    logs = json.loads(call(base, '/api/tasklogs')[1])['rows']
    assert logs and logs[0]['recipe'] == 'demo-agent'
    from urllib.parse import quote
    text = json.loads(call(base, '/api/tasklog?path=' + quote(logs[0]['path']) + '&errors=1')[1])['text']
    assert 'oe_runmake failed' in text
    secret = tmp_path / 'demo/build/conf/local.conf'
    assert call(base, '/api/tasklog?path=' + quote(str(secret)))[0] == 404
    assert call(base, '/api/tasklog?path=' + quote(logs[0]['path'] + '/../../../../conf/local.conf'))[0] == 404


def test_console_builds_are_listed_and_confined(dashboard, tmp_path):
    from urllib.parse import quote
    board, base = dashboard
    rows = json.loads(call(base, '/api/console')[1])['rows']
    assert rows and rows[0]['status'] == 'failed' and rows[0]['machine'] == 'qemux86-64'
    path = quote(rows[0]['path'])
    assert 'oe_runmake failed' in json.loads(call(base, f'/api/console/log?path={path}&errors=1')[1])['text']
    assert 'Errors: 2' in json.loads(call(base, f'/api/console/report?path={path}')[1])['summary']
    assert call(base, '/api/console/log?path=' + quote(str(tmp_path / 'demo/build/conf/local.conf')))[0] == 404


def test_malformed_requests_get_json_answers(dashboard):
    board, base = dashboard
    profile = None  # the active profile
    status, body = call(base, '/api/jobs', {'profile': profile, 'action': 'build', 'values': 'core-image-minimal'})
    assert status == 400 and b'object of strings' in body          # used to drop the connection
    status, body = call(base, '/api/preview', {'profile': profile, 'action': 'build', 'values': {'target': 'a; id'}})
    assert status == 400 and b'Not a BitBake target' in body
    request = urllib.request.Request(base + '/api/state', method='DELETE', headers={'X-Bitloom-Token': 'secret-token'})
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=10)
    assert error.value.code == 405 and json.loads(error.value.read())['error']


def test_browser_opening_never_takes_over_the_terminal(monkeypatch):
    """On WSL Python fell back to lynx (www-browser), which took over the terminal running --web."""
    import subprocess
    import webbrowser
    import bitloom.infra as infra
    import bitloom.web as web
    launched = []
    monkeypatch.setattr(subprocess, 'Popen', lambda argv, **kwargs: launched.append(argv))
    monkeypatch.setattr(infra, 'wsl', lambda: True)
    monkeypatch.setattr(web.shutil, 'which', lambda name: '/x/powershell.exe' if name == 'powershell.exe' else None)
    assert web.open_in_browser('http://127.0.0.1:9000/#token=abc') == 'the Windows browser'
    assert launched[0][0] == 'powershell.exe' and "Start-Process 'http://127.0.0.1:9000/#token=abc'" in launched[0][-1]
    monkeypatch.setattr(infra, 'wsl', lambda: False)
    text = webbrowser.GenericBrowser('www-browser')
    monkeypatch.setattr(webbrowser, 'get', lambda: text)
    monkeypatch.setattr(text, 'open', lambda url: launched.append(['lynx']) or True)
    assert web.open_in_browser('http://127.0.0.1:9000/') == '' and ['lynx'] not in launched
