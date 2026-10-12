"""Capture the real Textual UI with Pilot; create SVG, PNG and animated GIF assets.

Run: python tools/capture_docs.py (requires pillow and cairosvg).
Demo screenshots are explicitly sample data, never a claimed Yocto build.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Neutral home directory in captures: paths shown in the docs must not reveal the author's account.
os.environ['HOME'] = '/home/developer'
sys.path.insert(0, str(ROOT))

from bitloom.app import BitloomApp
from terminal_capture import terminal_svg
from bitloom.cli import prepare_demo
from textual.widgets import Input, TabbedContent, Tree, DataTable


async def capture():
    import cairosvg
    from PIL import Image
    output = ROOT / 'docs/assets'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bitloom-docs-') as work:
        root = Path(work)
        os.environ.pop('NO_COLOR', None)
        app = BitloomApp(prepare_demo(root / 'workspace'), root / 'state')
        frames = []
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause(.8)
            idle_svg = output / 'welcome.svg'
            idle_svg.write_text(terminal_svg(app, 'Bitloom · idle demo workspace'))
            cairosvg.svg2png(url=str(idle_svg), write_to=str(output / 'welcome.png'), scale=.8)
            # Real subprocess output provides a controlled, labelled demo failure.
            script = root / 'sample_failure.py'
            script.write_text('print("NOTE: Running task 1 of 3")\nprint("NOTE: recipe demo-agent-1.0-r0: task do_compile: Started")\nprint("agent.c:12: error: unknown type telemetry_t")\nprint("ERROR: oe_runmake failed")\nprint("ERROR: Task demo-agent:do_compile failed with exit code 1")\nexit(1)\n')
            job = app.runner.submit(app.profile, 'Demo diagnostic — sample output', [sys.executable, str(script)])
            app.select_job(job.id, job.log)
            await app.runner.consumer
            await pilot.pause(.6)
            async def shot(name, include_in_tour=True):
                await pilot.pause(.25)
                svg = output / f'{name}.svg'
                svg.write_text(terminal_svg(app, 'Bitloom · demo workspace'))
                png = output / f'{name}.png'
                cairosvg.svg2png(url=str(svg), write_to=str(png), scale=.8)
                if include_in_tour:
                    frames.append(Image.open(png).convert('RGB'))
            await shot('builds')
            app.query_one('#log-search', Input).value = 'error'
            await shot('error-search')
            app.query_one('#workspace', TabbedContent).active = 'metadata'
            tree = app.query_one('#layer-tree', Tree)
            layer = next(n for n in tree.root.children if n.data and n.data.kind == 'layer')
            tree.select_node(layer)
            await pilot.pause(.2)
            app.query_one('#metadata-table', DataTable).move_cursor(row=1)
            await shot('layers-recipes')
            app.query_one('#workspace', TabbedContent).active = 'tasklogs'
            await shot('task-logs')
            app.query_one('#workspace', TabbedContent).active = 'caches'
            app.scan_cache()
            await pilot.pause(.4)
            await shot('caches')
            app.query_one('#workspace', TabbedContent).active = 'healthtab'
            await shot('health')
            app.query_one('#workspace', TabbedContent).active = 'workbench'
            from bitloom.models import read_assignments
            app.inspection_rows = sorted(read_assignments(app.profile.build_path / 'conf/local.conf').items())
            app.render_inspection()
            await shot('workbench')
            app.query_one('#workspace', TabbedContent).active = 'analysis'
            app.query_one('#analysis-query', Input).value = 'SRC_URI'
            app.run_analysis()
            await app.workers.wait_for_complete()
            await shot('analysis')
            from bitloom.runner import Job
            from bitloom.stop import StopScreen
            demo_stop = Job(app.profile, 'Demo: interruption options', ['bitbake', 'demo-image'], at_risk={'demo-agent'})
            app.push_screen(StopScreen(demo_stop))
            await shot('interruption')
            await pilot.press('escape')
            await pilot.press('f2')
            await shot('command-center')
            await pilot.press('escape')
            await pilot.press('f4')
            await shot('profiles')
            await pilot.press('escape')
            app.new_file()
            await pilot.pause(.2)
            app.screen.query_one('#new-path', Input).value = str(root / 'demo/meta-demo/recipes-example/hello/hello_1.0.bb')
            from textual.widgets import Select
            app.screen.query_one('#new-template', Select).value = 'recipe'
            await shot('file-creation')
            await pilot.press('escape')
            # Keyboard reference, profile switcher and builds started outside Bitloom.
            await pilot.press('1', 'question_mark')
            await shot('keys')
            await pilot.press('escape', 'P')
            await shot('profile-picker', include_in_tour=False)
            await pilot.press('escape', 'c')
            await pilot.pause(.4)
            await shot('console-builds')
            await pilot.press('enter')
            await pilot.pause(.4)
            await shot('console-build-log', include_in_tour=False)
            # Release-aware features on the Wrynose and Scarthgap sample workspaces.
            from textual.widgets import Select as ProfileSelect
            app.main_query('#profile', ProfileSelect).value = 'demo-wrynose'
            await pilot.pause(1.2)
            await pilot.press('2', 'c')
            await pilot.pause(.8)
            await shot('studio')
            await pilot.press('escape', '9', 's')
            await pilot.pause(.6)
            await shot('sbom-settings')
            await pilot.press('escape', '9', 'c')
            await pilot.pause(.8)
            await shot('cra-readiness')
            await pilot.press('escape', '6', 's')
            await pilot.pause(.8)
            await shot('sbom-quality')
            await pilot.press('escape', 'v')
            await pilot.pause(.8)
            await shot('vulnerabilities')
            await pilot.press('escape')
            # Projects: hub, new project form, guided setup of an existing folder.
            await pilot.press('9', 'w')
            await pilot.pause(.5)
            await shot('projects')
            await pilot.press('n')
            await pilot.pause(.6)
            await shot('new-project')
            await pilot.press('escape', '9', 'w', 'o')
            await pilot.pause(.3)
            app.screen.query_one('#open-dir', Input).value = str(root / 'workspace/demo-scarthgap')
            await pilot.press('enter')
            await pilot.pause(.4)
            await pilot.press('escape', '9', 'w', 'o')
            await pilot.pause(.3)
            launcher_root = root / 'launcher-project'
            (launcher_root / 'boards').mkdir(parents=True)
            (launcher_root / 'boards/board-a.yml').write_text('header:\n  version: 14\nmachine: qemuarm64\ntarget: core-image-minimal\nrepos:\n  meta-product:\n')
            (launcher_root / 'run_build.sh').write_text('#!/bin/bash\n# Sample project launcher (demo)\nkas-container "$1" "${YML}"\n')
            (launcher_root / 'run_build.sh').chmod(0o755)
            app.screen.query_one('#open-dir', Input).value = str(launcher_root)
            await pilot.press('enter')
            await pilot.pause(.8)
            await shot('setup-wizard')
            await pilot.press('escape')
            app.main_query('#profile', ProfileSelect).value = 'demo-scarthgap'
            await pilot.pause(1.2)
            await pilot.press('1', 'f2')
            await pilot.pause(.3)
            for key in 'sbom':
                await pilot.press(key)
            await pilot.press('down')
            await shot('release-gating')
            await pilot.press('escape')
            # Live job: spinner, indeterminate progress, then task counts.
            running = root / 'sample_running.py'
            running.write_text('import time\nprint("NOTE: Running setscene task 120 of 300")\ntime.sleep(1.5)\nfor i in range(1, 40):\n    print(f"NOTE: Running task {i} of 400 (/demo/r{i}.bb:do_compile)", flush=True)\n    print(f"NOTE: recipe demo-r{i}-1.0-r0: task do_compile: Started", flush=True)\n    time.sleep(.1)\n')
            live = app.runner.submit(app.profile, 'Demo running build — sample output', [sys.executable, str(running)])
            app.select_job(live.id, live.log)
            await pilot.pause(2.6)
            await shot('running')
            await app.runner.consumer
            app.main_query('#profile', ProfileSelect).value = 'demo'
            await pilot.pause(.8)
            app.query_one('#workspace', TabbedContent).active = 'builds'
            await pilot.resize_terminal(90, 28)
            await shot('compact', include_in_tour=False)
            await pilot.resize_terminal(60, 20)
            await shot('tiny', include_in_tour=False)
        app.store.close()
        # Stable dimensions; no invented terminal content.
        size = frames[0].size
        frames = [f.resize(size).quantize(colors=128) for f in frames]
        frames[0].save(output / 'tour.gif', save_all=True, append_images=frames[1:], duration=2200, loop=0, optimize=True)
        print(f'Captured {len(frames)} real UI views and tour.gif in {output}')


if __name__ == '__main__':
    asyncio.run(capture())
