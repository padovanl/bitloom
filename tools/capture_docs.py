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
sys.path.insert(0, str(ROOT))

from yoctotui.app import YoctoApp
from terminal_capture import terminal_svg
from yoctotui.cli import make_demo
from textual.widgets import Input, TabbedContent, Tree, DataTable


async def capture():
    import cairosvg
    from PIL import Image
    output = ROOT / 'docs/assets'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='yoctotui-docs-') as work:
        root = Path(work)
        os.environ.pop('NO_COLOR', None)
        app = YoctoApp(make_demo(root / 'demo'), root / 'state')
        frames = []
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause(.8)
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
                svg.write_text(terminal_svg(app, 'YoctoTUI · demo workspace'))
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
            from yoctotui.models import read_assignments
            app.inspection_rows = sorted(read_assignments(app.profile.build_path / 'conf/local.conf').items())
            app.render_inspection()
            await shot('workbench')
            from yoctotui.runner import Job
            from yoctotui.stop import StopScreen
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
            app.query_one('#workspace', TabbedContent).active = 'builds'
            await pilot.resize_terminal(90, 28)
            await shot('compact', include_in_tour=False)
        app.store.close()
        # Stable dimensions; no invented terminal content.
        size = frames[0].size
        frames = [f.resize(size).quantize(colors=128) for f in frames]
        frames[0].save(output / 'tour.gif', save_all=True, append_images=frames[1:], duration=2200, loop=0, optimize=True)
        print(f'Captured {len(frames)} real UI views and tour.gif in {output}')


if __name__ == '__main__':
    asyncio.run(capture())
