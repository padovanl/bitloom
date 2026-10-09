import json
import time
from pathlib import Path

from textual.widgets import Button, DataTable, Input, Select, TabbedContent, TextArea

from bitloom.app import BitloomApp
from bitloom.cli import make_demo
from bitloom.developer_agent import report
from bitloom.developer_ui import DeveloperPanel, ScaffoldScreen, CloneProfileScreen
from bitloom.screens import ActionScreen


async def test_developer_runtime_browser_enter_editor_and_small_terminal(tmp_path):
    config = make_demo(tmp_path / 'demo')
    file = tmp_path / 'hello.bb'; file.write_text('SUMMARY = "hello"\n')
    app = BitloomApp(config, tmp_path / 'state')
    async with app.run_test(size=(140,42)) as pilot:
        await pilot.pause(.4)
        await pilot.press('f10')
        assert app.query_one('#workspace', TabbedContent).active == 'developer'
        panel = app.query_one(DeveloperPanel)
        app.query_one('#dev-view', Select).value = 'browse'
        await pilot.pause()
        app.query_one('#dev-first', Input).value = str(tmp_path)
        panel.load()
        await pilot.pause(.5)
        assert any(r.get('path') == str(file) for r in panel.rows)
        row = next(i for i,r in enumerate(panel.rows) if r.get('path') == str(file))
        app.query_one('#dev-rows', DataTable).move_cursor(row=row)
        panel.open_row()
        await pilot.pause(.5)
        assert app.screen.query_one('#content', TextArea).text == file.read_text()
        await pilot.press('escape')
        await pilot.resize_terminal(60,20)
        await pilot.pause()
        assert app.query_one('#dev-inspect', Button).region.right <= 60
        assert app.query_one('#dev-rows').region.bottom < 20
        assert app.query_one('#dev-detail').region.y >= app.query_one('#dev-rows').region.bottom
        assert app.query_one('#dev-open', Button).region.intersection(app.query_one('#dev-open', Button).parent.region).area > 0
        assert app.query_one('#dev-detail').region.height >= 3
        await pilot.resize_terminal(80,24)
        await pilot.pause()
        assert app.query_one('#dev-detail').region.height >= 3
    app.store.close()


async def test_optional_task_is_disabled_with_actual_missing_prerequisite(tmp_path):
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    async with app.run_test(size=(80,24)) as pilot:
        await pilot.pause(.3)
        app.capability_cache[(app.profile.name, 'busybox')] = {'captured': time.time(), 'tasks': ['do_compile']}
        app.push_screen(ActionScreen(app.profile, 'testimage', 'busybox'))
        await pilot.pause()
        assert app.screen.query_one('#submit', Button).disabled
        assert 'do_testimage' in str(app.screen.query_one('#preview').render())
        assert not app.runner.jobs
    app.store.close()


async def test_scaffold_dialog_preview_and_cancel_do_not_write(tmp_path):
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    async with app.run_test(size=(80,24)) as pilot:
        await pilot.pause(.3)
        app.push_screen(ScaffoldScreen(app.profile))
        await pilot.pause()
        screen = app.screen
        screen.query_one('#scaffold-path', Input).value = str(tmp_path / 'meta-new')
        screen.preview()
        assert 'LIC_FILES_CHKSUM' in screen.query_one('#scaffold-preview', TextArea).text
        assert not (tmp_path / 'meta-new').exists()
        assert not screen.query_one('#scaffold-create', Button).disabled
        await pilot.press('escape')
        assert not (tmp_path / 'meta-new').exists()
    app.store.close()


async def test_variable_capture_staleness_and_profile_clone(tmp_path):
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    async with app.run_test(size=(140,42)) as pilot:
        await pilot.pause(.3)
        panel = app.query_one(DeveloperPanel)
        panel.display_report(report('Example variable fixture', [{'name':'SUMMARY','value':'old'}], 'Test fixture'), view='variable')
        panel.capture()
        capture = Path(panel.field('baseline'))
        assert json.loads(capture.read_text())['view'] == 'variable'
        panel.mark_stale()
        panel.capture()
        assert len(list((app.store.directory / 'exports').glob('developer-*'))) == 1
        app.push_screen(CloneProfileScreen(app.settings))
        await pilot.pause()
        app.screen.query_one('#clone-name', Input).value = 'separate'
        app.screen.query_one('#clone-build', Input).value = str(tmp_path / 'separate/build')
        app.screen.save()
        await pilot.pause()
        assert app.settings.active == 'separate'
    app.store.close()
