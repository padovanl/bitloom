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


async def test_terminal_navigation_preview_and_pause(tmp_path):
    from textual.widgets import Button, RichLog, Tree
    config = make_demo(tmp_path / 'demo')
    app = YoctoApp(config, tmp_path / 'state')
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.5)
        await pilot.press('alt+2')
        await pilot.pause(.3)
        assert app.query_one('#workspace', TabbedContent).active == 'metadata'
        assert app.query_one('#source-preview', RichLog).lines
        tree = app.query_one('#layer-tree', Tree)
        layer = next(node for node in tree.root.children if node.data and node.data.kind == 'layer')
        tree.select_node(layer)
        await pilot.pause(.3)
        assert app.query_one('#metadata-search', Input).value == str(layer.data.path)
        assert app.query_one('#metadata-table').row_count >= 2
        await pilot.press('alt+1')
        await pilot.click('#log-follow')
        assert not app.follow_log
        assert str(app.query_one('#log-follow', Button).label) == 'Resume'
        app.live_lines.append('saved output')
        app.flush_log()
        assert app.live_lines == ['saved output']
        await pilot.pause(.4)
        await pilot.click('#log-follow')
        await pilot.pause(.2)
        assert app.follow_log
        await pilot.resize_terminal(90, 28)
        await pilot.pause(.3)
        assert app.screen.has_class('narrow')
        assert app.query_one('#stop').region.x < 90
        assert app.query_one('#log-follow').region.x < 90
        assert app.query_one('#log-follow').region.y < 28
    app.store.close()


async def test_background_output_survives_command_dialog(tmp_path):
    import sys
    config = make_demo(tmp_path / 'demo')
    app = YoctoApp(config, tmp_path / 'state')
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.3)
        job = app.runner.submit(app.profile, 'background', [sys.executable, '-c', 'import time; time.sleep(.3); print("NOTE: background output"); time.sleep(.3)'])
        app.select_job(job.id, job.log)
        await pilot.press('f2')
        await app.runner.consumer
        app.update_telemetry()
        assert isinstance(app.screen, ActionScreen)
        assert job.status == 'success'
        await pilot.press('escape')
        await pilot.pause(.3)
        assert app.history_rows[job.id]['status'] == 'success'
    app.store.close()


async def test_runtime_graph_output_is_loaded_into_workbench(tmp_path):
    import sys
    config = make_demo(tmp_path / 'demo')
    app = YoctoApp(config, tmp_path / 'state')
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.3)
        app.query_one('#workspace', TabbedContent).active = 'workbench'
        app.query_one('#inspect-kind', Select).value = 'graph'
        job = app.runner.submit(app.profile, 'runtime graph', [sys.executable, '-c', 'print(\'"image.do_build" -> "busybox.do_compile";\')'], 'graph-read')
        await app.runner.consumer
        await pilot.pause(.4)
        assert job.status == 'success'
        assert app.inspection_rows == [('image.do_build', 'busybox.do_compile')]
        assert app.query_one('#inspect-table').row_count == 1
    app.store.close()


async def test_analysis_content_search_log_report_and_export(tmp_path):
    config = make_demo(tmp_path / 'demo')
    app = YoctoApp(config, tmp_path / 'state')
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.4)
        app.query_one('#workspace', TabbedContent).active = 'analysis'
        app.query_one('#analysis-query', Input).value = 'SRC_URI'
        app.run_analysis()
        await app.workers.wait_for_complete()
        assert 'file://agent.c' in app.analysis_text
        app.export_analysis()
        assert len(list((tmp_path/'state/exports').glob('analysis-*.txt'))) == 1
        log = tmp_path/'sstate.log'
        log.write_text('Sstate summary: Wanted 10 Local 5 Mirrors 0 Missed 5 Current 0\n')
        app.query_one('#analysis-kind', Select).value = 'sstate'
        app.query_one('#analysis-first', Input).value = str(log)
        await pilot.pause(.2)
        assert not app.query_one('#analysis-query', Input).display
        app.run_analysis()
        await app.workers.wait_for_complete()
        assert '50.0%' in app.analysis_text
    app.store.close()

async def test_persistent_tui_detaches_and_reconnects(tmp_path):
    import sys
    from yoctotui.daemon import rpc
    config=make_demo(tmp_path/'demo'); state=tmp_path/'persistent'
    app=YoctoApp(config,state,persistent=True)
    async with app.run_test(size=(140,42)) as pilot:
        await pilot.pause(.3)
        job=app.runner.submit(app.profile,'Detached UI probe',[sys.executable,'-c','import time; time.sleep(1); print("completed without UI")'])
        app.action_quit()
        await pilot.pause(.3)
    await asyncio.sleep(1)
    reopened=YoctoApp(config,state,persistent=True)
    try:
        async with reopened.run_test(size=(140,42)) as pilot:
            await pilot.pause(.8)
            current=next(j for j in reopened.runner.jobs if j.id==job.id)
            assert current.status=='success'
            assert reopened.history_rows[job.id]['status']=='success'
            reopened.action_quit()
            await pilot.pause(.3)
    finally:
        await asyncio.to_thread(rpc,state,{'op':'stop'})
