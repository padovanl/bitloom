"""Guided project setup: detection, checks, saving and live reload in TUI and web."""
import json
import os

from bitloom.models import Profile, Settings
from bitloom.setup import check, detect, save


def project(tmp_path):
    root = tmp_path / 'product'
    (root / 'boards').mkdir(parents=True)
    (root / 'boards/board-a.yml').write_text('header:\n  version: 14\nmachine: qemuarm64\ntarget: product-image\nrepos:\n  meta-product:\n')
    (root / 'boards/common.yml').write_text('header:\n  version: 14\nrepos:\n  poky:\n    url: https://git.yoctoproject.org/poky\n')
    script = root / 'run_build.sh'
    script.write_text('#!/bin/bash\n# Project launcher\nkas-container "$1" "${YML}"\n')
    script.chmod(0o755)
    (root / 'poky').mkdir()
    (root / 'poky/oe-init-build-env').write_text('# init\n')
    (root / 'build/conf').mkdir(parents=True)
    (root / 'build/conf/local.conf').write_text('MACHINE = "qemux86-64"\n')
    return root


def test_detects_launchers_kas_files_and_host_builds(tmp_path):
    root = project(tmp_path)
    candidates = detect(root)
    modes = [c.mode for c in candidates]
    assert modes[0] == 'wrapper' and 'host' in modes and any(m in {'kas', 'kas-container'} for m in modes)
    wrapper = candidates[0].profile
    assert wrapper['launcher'] == ['./run_build.sh'] and wrapper['environment'] == {'YML': 'boards/board-a.yml'}
    kas = next(c for c in candidates if c.mode in {'kas', 'kas-container'})
    assert kas.profile['kas_file'] == 'boards/board-a.yml' and kas.profile['machine'] == 'qemuarm64' and kas.profile['targets'] == ['product-image']
    host = next(c for c in candidates if c.mode == 'host')
    assert host.profile['init_script'] == 'poky/oe-init-build-env' and host.profile['machine'] == 'qemux86-64'
    rows = dict((m, s) for s, m in check(Profile.from_dict(wrapper)))
    assert rows['launcher ./run_build.sh'] == 'OK' and rows['YML=boards/board-a.yml'] == 'OK'
    bad = check(Profile(name='x', root=str(root), mode='kas-container', kas_file='missing.yml'))
    assert ('ERR', 'kas file missing.yml') in bad and ('ERR', 'set KAS_WORK_DIR to a separate directory') in bad


def test_save_replaces_first_run_default(tmp_path, monkeypatch):
    root = project(tmp_path)
    monkeypatch.chdir(root)
    settings = Settings(tmp_path / 'state/profiles.json')
    assert [p.name for p in settings.profiles] == ['default']
    save(settings, Profile.from_dict(detect(root)[0].profile))
    saved = json.loads((tmp_path / 'state/profiles.json').read_text())
    assert [p['name'] for p in saved['profiles']] == ['product-run-build'] and saved['active'] == 'product-run-build'


async def test_tui_wizard_saves_and_reloads(tmp_path, monkeypatch):
    from textual.widgets import Input
    from bitloom.app import BitloomApp
    from bitloom.screens import SetupScreen
    root = project(tmp_path)
    monkeypatch.chdir(root)
    app = BitloomApp(tmp_path / 'state/profiles.json', tmp_path / 'state')
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause(.8)
        assert isinstance(app.screen, SetupScreen)          # first run opens the wizard
        screen = app.screen
        assert screen.candidates[0].mode == 'wrapper'
        await pilot.press('down')                           # second proposal
        await pilot.pause(.2)
        assert screen.query_one('#setup-name', Input).value == screen.candidates[1].profile['name']
        await pilot.press('up')
        await pilot.pause(.2)
        await pilot.press('ctrl+o')
        await pilot.pause(.6)
        assert not isinstance(app.screen, SetupScreen)
        assert app.profile.name == 'product-run-build' and app.profile.mode == 'wrapper'
        assert app.main_query('#profile').value == 'product-run-build'
        from bitloom.screens import ProjectsScreen
        await pilot.press('9', 'w')                          # projects hub from Configuration
        await pilot.pause(.5)
        assert isinstance(app.screen, ProjectsScreen)
        await pilot.press('o')
        app.screen.query_one('#open-dir', Input).value = str(root)
        await pilot.press('enter')
        await pilot.pause(.5)
        # The folder already has a profile: Bitloom switches to it instead of asking again.
        assert not isinstance(app.screen, SetupScreen) and app.profile.name == 'product-run-build'
    app.store.close()


def test_web_setup_endpoints(tmp_path):
    import threading
    import urllib.request
    from bitloom.cli import make_demo
    from bitloom.web import Dashboard, create_server
    root = project(tmp_path)
    board = Dashboard(make_demo(tmp_path / 'demo'), tmp_path / 'state', token='t')
    server = create_server(board, '127.0.0.1', 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_address[1]}'

    def call(path, body=None):
        request = urllib.request.Request(base + path, json.dumps(body).encode() if body is not None else None, {'X-Bitloom-Token': 't', 'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(request).read())
    try:
        found = call('/api/setup/scan?dir=' + str(root))['candidates']
        assert found[0]['mode'] == 'wrapper'
        checks = call('/api/setup/check', {'profile': found[0]['profile']})['checks']
        assert all(row['status'] != 'ERR' for row in checks)
        assert call('/api/setup/save', {'profile': found[0]['profile']}) == {'active': 'product-run-build'}
        assert Settings(board.config).active == 'product-run-build'
    finally:
        server.shutdown()


def test_kas_work_directory_of_a_profile_is_recognised(tmp_path):
    """Scanning a kas work directory offered a plain host build; it now names the profile that owns it."""
    from bitloom.models import Profile
    from bitloom.setup import detect
    work = tmp_path / 'work'
    (work / 'openembedded-core').mkdir(parents=True)
    (work / 'openembedded-core/oe-init-build-env').write_text('# init\n')
    (work / 'build/conf').mkdir(parents=True)
    (work / 'build/conf/local.conf').write_text('MACHINE = "qemux86-64"\n')
    owner = Profile(name='product', root=str(tmp_path), mode='kas-container', kas_file='kas.yml', environment={'KAS_WORK_DIR': str(work)})
    host = next(c for c in detect(work, [owner]) if c.mode == 'host')
    assert 'kas work directory of profile product' in host.evidence[0] and host.score == 1 and host.hints
    assert 'kas work directory' not in detect(work)[0].evidence[0]
