import asyncio
from pathlib import Path

from textual.widgets import Input, Select, TabbedContent, TextArea

from yoctotui.app import YoctoApp
from yoctotui.cli import make_demo
from yoctotui.screens import ActionScreen, ProfilesScreen


async def test_app_tabs_modals_filters_and_demo(tmp_path):
    config = make_demo(tmp_path / 'demo')
    app = YoctoApp(config, tmp_path / 'state')
    async with app.run_test(size=(150, 48)) as pilot:
        await pilot.pause(.8)
        assert len(app.entries) >= 3
        assert len(app.logs) == 1
        await pilot.press('f2')
        await pilot.pause()
        assert isinstance(app.screen, ActionScreen)
        app.screen.query_one('#action', Select).value = 'dev-status'
        await pilot.pause()
        assert not app.screen.query_one('#field-target', Input).display
        await pilot.press('escape')
        await pilot.press('f4')
        await pilot.pause()
        assert isinstance(app.screen, ProfilesScreen)
        assert 'demo' in app.screen.query_one('#json', TextArea).text
        await pilot.press('escape')
        app.query_one('#workspace', TabbedContent).active = 'metadata'
        app.query_one('#metadata-search', Input).value = 'demo-agent'
        await pilot.pause()
        assert app.query_one('#metadata-table').row_count == 1
        app.query_one('#workspace', TabbedContent).active = 'caches'
        app.scan_cache()
        await pilot.pause(.4)
        assert len(app.cache_entries) == 1
    app.store.close()


async def test_ui_job_and_error_search(tmp_path):
    import sys
    config = make_demo(tmp_path / 'demo')
    app = YoctoApp(config, tmp_path / 'state')
    async with app.run_test(size=(140, 44)) as pilot:
        await pilot.pause(.4)
        job = app.runner.submit(app.profile, 'test failure', [sys.executable, '-c', 'print("ERROR: compiler failed"); exit(3)'])
        app.select_job(job.id, job.log)
        await app.runner.consumer
        await pilot.pause(.4)
        assert job.status == 'failed'
        assert job.id in app.history_rows
        app.query_one('#log-search', Input).value = 'compiler'
        await pilot.pause(.3)
        assert app.selected_log == job.log
    app.store.close()
