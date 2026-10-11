import asyncio
from pathlib import Path

from textual.widgets import Input, Select, TabbedContent, TextArea

from bitloom.app import BitloomApp
from bitloom.cli import make_demo
from bitloom.screens import ActionScreen, ProfilesScreen


async def eventually(pilot, condition, timeout=20):
    """Poll instead of fixed sleeps: timers and workers are slower on a loaded machine."""
    for _ in range(int(timeout / .25)):
        if condition():
            return True
        await pilot.pause(.25)
    return condition()


async def test_app_tabs_modals_filters_and_demo(tmp_path):
    config = make_demo(tmp_path / 'demo')
    app = BitloomApp(config, tmp_path / 'state')
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
    app = BitloomApp(config, tmp_path / 'state')
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
    app = BitloomApp(config, tmp_path / 'state')
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
        assert str(app.query_one('#log-follow', Button).label).endswith('Resume')
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
    app = BitloomApp(config, tmp_path / 'state')
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
    app = BitloomApp(config, tmp_path / 'state')
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
    app = BitloomApp(config, tmp_path / 'state')
    async with app.run_test(size=(140, 42)) as pilot:
        assert await eventually(pilot, lambda: len(app.entries) >= 3)   # metadata scan finished
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
    from bitloom.daemon import rpc
    config=make_demo(tmp_path/'demo'); state=tmp_path/'persistent'
    app=BitloomApp(config,state,persistent=True)
    async with app.run_test(size=(140,42)) as pilot:
        await pilot.pause(.3)
        job=app.runner.submit(app.profile,'Detached UI probe',[sys.executable,'-c','import time; time.sleep(1); print("completed without UI")'])
        app.action_quit()
        await pilot.pause(.3)
    await asyncio.sleep(1)
    reopened=BitloomApp(config,state,persistent=True)
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

async def test_all_themes_preview_cancel_and_persist(tmp_path):
    import json
    from bitloom.themes import THEMES
    from bitloom.screens import ThemeScreen
    from textual.widgets import Button
    config=make_demo(tmp_path/'demo'); state=tmp_path/'state'
    app=BitloomApp(config,state)
    async with app.run_test(size=(140,42)) as pilot:
        await pilot.pause(.3)
        await pilot.press('f7'); await pilot.pause(.2)
        assert isinstance(app.screen,ThemeScreen)
        assert len(THEMES)>=10
        backgrounds=set()
        for name in THEMES:
            app.screen.query_one('#theme-choice',Select).value=name
            await pilot.pause(.08)
            assert app.theme==name
            for selector in ('#log', '#analysis-output'):
                pane=app.screen_stack[0].query_one(selector)
                assert pane.styles.scrollbar_background==app.screen_stack[0].query_one("#toolbar").styles.background
                assert pane.styles.background==app.screen_stack[0].styles.background
            backgrounds.add(app.screen_stack[0].styles.background.hex)
        assert len(backgrounds)>=10
        await pilot.press('escape'); await pilot.pause(.2)
        assert app.theme=='Bitloom'
        await pilot.press('f7'); await pilot.pause(.1)
        app.screen.query_one('#theme-choice',Select).value='Paper'
        await pilot.pause(.2)
        app.screen.query_one('#theme-save',Button).press()
        await pilot.pause(.2)
        assert app.theme=='Paper'
        assert json.loads((state/'appearance.json').read_text())['theme']=='Paper'
    app.store.close()
    restored=BitloomApp(config,state)
    assert restored.theme=='Paper'
    restored.store.close()

async def test_responsive_terminal_sizes_preserve_log_and_navigation(tmp_path):
    from textual.widgets import RichLog, Button
    app=BitloomApp(make_demo(tmp_path/'demo'),tmp_path/'state')
    async with app.run_test(size=(160,50)) as pilot:
        await pilot.pause(.3)
        for width,height in [(160,50),(120,36),(90,28),(80,24),(60,20),(140,20),(160,50)]:
            await pilot.resize_terminal(width,height)
            await pilot.pause(.2)
            log=app.query_one('#log',RichLog)
            assert log.region.width>15 and log.region.height>=3, (width,height,log.region)
            build=app.query_one('#build',Button)
            assert build.region.right<=width and build.region.bottom<=height
            if (width,height)==(60,20):
                from textual.containers import Vertical
                for shortcut in ('f2','f4','f7'):
                    await pilot.press(shortcut)
                    await pilot.pause(.1)
                    dialog=app.screen.query_one(Vertical).region
                    assert dialog.x>=0 and dialog.right<=width
                    assert dialog.y>=0 and dialog.bottom<=height
                    await pilot.press('escape')
                    await pilot.pause(.1)
            if width<75 or height<22:
                assert not app.query_one('#history-panel').display
                assert not app.query_one('#metrics').display
            elif height>=30 and width>=105:
                assert app.query_one('#rail').display
            await pilot.press('alt+2'); await pilot.pause(.1)
            assert app.query_one('#workspace',TabbedContent).active=='metadata'
            await pilot.press('alt+1'); await pilot.pause(.1)
        assert app.query_one('#history-panel').display
        assert app.query_one('#metrics').display
    app.store.close()

async def test_report_focus_keeps_background_stable(tmp_path):
    from textual.widgets import RichLog
    app=BitloomApp(make_demo(tmp_path/'demo'),tmp_path/'state')
    async with app.run_test(size=(120,36)) as pilot:
        for name in ('Bitloom','Soft Slate','Linen'):
            app.theme=name
            app.query_one('#workspace',TabbedContent).active='analysis'
            await pilot.pause(.1)
            pane=app.query_one('#analysis-output',RichLog)
            before=pane.styles.background
            pane.focus()
            await pilot.pause(.1)
            assert pane.has_focus
            assert pane.styles.background==before
            assert pane.styles.background_tint.a==0
            app.query_one('#target',Input).focus()
            await pilot.pause(.1)
    app.store.close()

async def test_live_elapsed_and_terminal_navigation(tmp_path):
    import sys
    from textual.widgets import DataTable
    from textual._xterm_parser import XTermParser
    app=BitloomApp(make_demo(tmp_path/'demo'),tmp_path/'state')
    async with app.run_test(size=(120,36)) as pilot:
        job=app.runner.submit(app.profile,'Timer regression',[sys.executable,'-c','import time; time.sleep(4)'])
        await pilot.pause(.3)
        table=app.query_one('#history',DataTable)
        column=list(table.columns)[2]
        initial=table.get_cell(job.id,column)
        await pilot.pause(1.7)
        assert table.get_cell(job.id,column)!=initial
        assert job.status=='running'
        # Feed real terminal escape sequences, rather than synthetic Alt events.
        for sequence,expected in [('\x1b[20~','metadata'),('\x1b[19~','builds')]:
            events=list(XTermParser().feed(sequence))
            assert len(events)==1
            await pilot.press(events[0].key)
            assert app.query_one('#workspace',TabbedContent).active==expected
        await app.runner.consumer
        await pilot.pause(.2)
        final=table.get_cell(job.id,column)
        await pilot.pause(1.2)
        assert table.get_cell(job.id,column)==final
    app.store.close()

async def test_create_recipe_from_tui_and_detect_external_file(tmp_path):
    from bitloom.screens import NewFileScreen
    from textual.widgets import Button
    app=BitloomApp(make_demo(tmp_path/'demo'),tmp_path/'state')
    async with app.run_test(size=(140,42)) as pilot:
        await pilot.pause(.3)
        app.query_one('#workspace',TabbedContent).active='metadata'
        app.query_one('#new-file',Button).press()
        await pilot.pause(.2)
        assert isinstance(app.screen,NewFileScreen)
        path=tmp_path/'demo/meta-demo/recipes-example/new/new_1.0.bb'
        app.screen.query_one('#new-path',Input).value=str(path)
        app.screen.query_one('#new-template',Select).value='recipe'
        await pilot.pause(.1)
        assert 'do_install' in app.screen.query_one('#new-content',TextArea).text
        app.screen.query_one('#create-file',Button).press()
        assert await eventually(pilot, path.exists)
        assert await eventually(pilot, lambda: any(e.path==path for e in app.entries))
        external=path.with_name('external_1.0.bb')
        external.write_text('SUMMARY = "Created externally"\n')
        assert await eventually(pilot, lambda: any(e.path==external for e in app.entries))
        previous=next(e.size for e in app.entries if e.path==external)
        external.write_text('SUMMARY = "Externally modified recipe content"\n')
        assert await eventually(pilot, lambda: next((e.size for e in app.entries if e.path==external), previous)!=previous)
        external.unlink()
        assert await eventually(pilot, lambda: not any(e.path==external for e in app.entries))
    app.store.close()

async def test_open_runtime_directory_refreshes_automatically(tmp_path):
    app=BitloomApp(make_demo(tmp_path/'demo'),tmp_path/'state')
    async with app.run_test(size=(120,36)) as pilot:
        await pilot.pause(.3)
        app.query_one('#workspace',TabbedContent).active='analysis'
        app.query_one('#analysis-kind',Select).value='runtime-list'
        app.query_one('#analysis-first',Input).value=str(tmp_path)
        await app.run_analysis().wait()
        assert 'external-runtime.conf' not in app.analysis_text
        (tmp_path/'external-runtime.conf').write_text('Changed outside Bitloom\n')
        await pilot.pause(15.5)
        assert 'external-runtime.conf' in app.analysis_text
    app.store.close()

async def test_new_generic_file_opens_containing_directory(tmp_path):
    from textual.widgets import Button
    app=BitloomApp(make_demo(tmp_path/'demo'),tmp_path/'state')
    async with app.run_test(size=(120,36)) as pilot:
        await pilot.pause(.2)
        app.new_file()
        await pilot.pause(.2)
        path=tmp_path/'demo/notes.txt'
        app.screen.query_one('#new-path',Input).value=str(path)
        app.screen.query_one('#new-content',TextArea).load_text('My notes\n')
        app.screen.query_one('#create-file',Button).press()
        assert await eventually(pilot, lambda: path.exists() and 'notes.txt' in app.analysis_text)
        assert path.read_text()=='My notes\n'
        assert app.query_one('#workspace',TabbedContent).active=='analysis'
    app.store.close()
