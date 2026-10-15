"""Projects: new projects, clones and recent folders in the TUI and the web dashboard."""
import json
import subprocess

import pytest

from bitloom.projects import Recent, clone_argv, create_project, default_destination, new_project_plan


def test_new_project_plans_are_release_specific(tmp_path):
    old = new_project_plan(str(tmp_path / 'a'), 'acme', 'scarthgap', 'qemuarm64', 'poky', 'core-image-base', True, 'Acme')
    assert 'url: https://git.yoctoproject.org/poky' in old['files']['kas.yml'] and 'machine: qemuarm64' in old['files']['kas.yml']
    assert 'meta-acme/conf/layer.conf' in old['files'] and 'path: meta-acme' in old['files']['kas.yml']
    new = new_project_plan(str(tmp_path / 'b'), 'acme', 'wrynose', 'qemux86-64', 'poky', 'core-image-minimal', False, '')
    text = new['files']['kas.yml']
    assert 'build_system: openembedded' in text and 'openembedded-core' in text and 'poky' not in text.split('repos:')[1].split('meta-yocto')[0].replace('meta-poky', '')
    assert 'commit: acfe02fa38b5da9e6a36c6cedcf91d4fcbefbfbd' in text and '.: disabled' in text
    for bad in [('relative', 'acme'), (str(tmp_path / 'c'), 'Bad Name')]:
        with pytest.raises(ValueError):
            new_project_plan(bad[0], bad[1], 'scarthgap', 'qemux86-64', 'poky', 'core-image-minimal', False, '')
    (tmp_path / 'full').mkdir(); (tmp_path / 'full/x').write_text('x')
    with pytest.raises(ValueError, match='not empty'):
        new_project_plan(str(tmp_path / 'full'), 'acme', 'scarthgap', 'qemux86-64', 'poky', 'core-image-minimal', False, '')


def test_create_project_and_recent(tmp_path):
    plan = new_project_plan(str(tmp_path / 'p'), 'acme', 'scarthgap', 'qemux86-64', 'poky', 'core-image-minimal', True, 'Acme')
    profile = create_project(plan, 'kas-container', tmp_path / 'work')
    assert (tmp_path / 'p/kas.yml').exists() and (tmp_path / 'p/.git').is_dir() and (tmp_path / 'work/acme').is_dir()
    assert profile.mode == 'kas-container' and profile.kas_file == 'kas.yml' and profile.targets == ['core-image-minimal']
    recent = Recent(tmp_path / 'state')
    recent.add(tmp_path / 'p', 'acme', 'created'); recent.add(tmp_path / 'q'); recent.add(tmp_path / 'p', 'acme', 'opened')
    assert [i['root'] for i in recent.load()] == [str(tmp_path / 'p'), str(tmp_path / 'q')]


def test_clone_arguments_are_validated(tmp_path):
    assert clone_argv('https://github.com/org/prod.git', str(tmp_path / 'prod'), 'main') == \
        ['git', 'clone', '--progress', '--branch', 'main', '--', 'https://github.com/org/prod.git', str(tmp_path / 'prod')]
    assert default_destination('git@github.com:org/prod.git', tmp_path) == str(tmp_path / 'prod')
    for url, dest, branch in [('--upload-pack=x', str(tmp_path / 'a'), ''), ('https://x/y', 'relative', ''),
                              ('https://x/y', str(tmp_path), ''), ('https://x/y', str(tmp_path / 'b'), '-x')]:
        with pytest.raises(ValueError):
            clone_argv(url, dest, branch)


def origin(tmp_path):
    source = tmp_path / 'origin'
    source.mkdir()
    (source / 'kas.yml').write_text('header:\n  version: 14\nmachine: qemux86-64\ntarget: core-image-minimal\nrepos:\n  poky:\n')
    for argv in (['git', 'init', '-q'], ['git', 'add', '.'], ['git', '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-qm', 'init']):
        subprocess.run(argv, cwd=source, check=True)
    return source


async def test_tui_new_project_and_clone(tmp_path, monkeypatch):
    from textual.widgets import Input
    from bitloom.app import BitloomApp
    from bitloom.cli import make_demo
    from bitloom.screens import CloneScreen, NewProjectScreen, ProjectsScreen, SetupScreen
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause(.5)
        await pilot.press('9', 'w')
        await pilot.pause(.3)
        assert isinstance(app.screen, ProjectsScreen)
        await pilot.press('n')
        await pilot.pause(.4)
        assert isinstance(app.screen, NewProjectScreen)
        app.screen.query_one('#np-dir', Input).value = str(tmp_path / 'projects/acme')
        app.screen.query_one('#np-name', Input).value = 'acme'
        app.screen.query_one('#np-dir', Input).value = str(tmp_path / 'projects/acme')
        await pilot.pause(.2)
        await pilot.press('ctrl+o')
        await pilot.pause(.6)
        assert app.profile.name == 'acme' and (tmp_path / 'projects/acme/kas.yml').exists()
        assert json.loads((tmp_path / 'state/projects.json').read_text())[0]['how'] in {'created', 'set up'}
        source = origin(tmp_path)
        await pilot.press('9', 'w', 'g')
        await pilot.pause(.4)
        assert isinstance(app.screen, CloneScreen)
        app.screen.query_one('#clone-url', Input).value = 'file://' + str(source)
        await pilot.pause(.2)
        assert app.screen.query_one('#clone-dest', Input).value.endswith('/yocto/origin')   # auto-filled from the URL
        app.screen.query_one('#clone-dest', Input).value = str(tmp_path / 'projects/cloned')
        await pilot.pause(.2)
        app.screen.query_one('#clone-url', Input).value = 'file://' + str(source) + '/'
        await pilot.pause(.2)
        assert app.screen.query_one('#clone-dest', Input).value == str(tmp_path / 'projects/cloned')  # user choice kept
        await pilot.pause(.2)
        await pilot.press('ctrl+o')
        await app.runner.consumer
        await pilot.pause(.8)
        assert (tmp_path / 'projects/cloned/kas.yml').exists()
        assert isinstance(app.screen, SetupScreen)            # guided setup on the clone
        assert app.screen.query_one('#setup-dir', Input).value == str(tmp_path / 'projects/cloned')
        assert app.screen.candidates and app.screen.candidates[0].profile['kas_file'] == 'kas.yml'
    app.store.close()


def test_web_projects(tmp_path, monkeypatch):
    import threading
    import time
    import urllib.request
    from bitloom.cli import make_demo
    from bitloom.daemon import rpc
    from bitloom.models import Settings
    from bitloom.web import Dashboard, create_server
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    board = Dashboard(make_demo(tmp_path / 'demo'), tmp_path / 'state', token='t')
    server = create_server(board, '127.0.0.1', 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_address[1]}'

    def call(path, body=None):
        request = urllib.request.Request(base + path, json.dumps(body).encode() if body is not None else None, {'X-Bitloom-Token': 't', 'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(request).read())
    try:
        info = call('/api/projects')
        assert 'wrynose' in info['releases'] and 'qemuarm64' in info['machines']
        body = {'name': 'webby', 'dir': str(tmp_path / 'p/webby'), 'release': 'wrynose', 'machine': 'qemux86-64', 'distro': 'poky',
                'target': 'core-image-minimal', 'runtime': 'kas-container', 'layer': True, 'owner': 'Acme'}
        assert 'kas.yml' in call('/api/projects/preview', body)['files']
        assert call('/api/projects/create', body)['active'] == 'webby'
        assert Settings(board.config).active == 'webby'
        source = origin(tmp_path)
        clone = call('/api/projects/clone', {'url': 'file://' + str(source), 'dest': str(tmp_path / 'p/cloned')})
        for _ in range(100):
            row = next(r for r in call('/api/state')['history'] if r['id'] == clone['id'])
            if row['status'] == 'success':
                break
            time.sleep(.1)
        assert row['status'] == 'success' and (tmp_path / 'p/cloned/kas.yml').exists()
    finally:
        server.shutdown()
        try:
            rpc(board.state, {'op': 'stop'})
        except (OSError, ValueError):
            pass


def test_one_root_with_several_profiles(tmp_path):
    """YML=a.yml / YML=b.yml on the same launcher: one project row naming both, active when either is."""
    from bitloom.models import Profile, Settings
    from bitloom.projects import Recent, project_rows
    settings = Settings(tmp_path / 'profiles.json')
    settings.profiles = [Profile(name=n, root=str(tmp_path), mode='wrapper', launcher=['./run_kas.sh']) for n in ('alpha', 'beta')]
    settings.active = 'beta'
    rows = project_rows(settings, Recent(tmp_path / 'state'))
    assert len(rows) == 1 and rows[0]['profiles'] == ['alpha', 'beta'] and rows[0]['profile'] == 'beta' and rows[0]['active']
