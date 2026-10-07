"""Capture a completed, genuine integration build from its persisted Runner history."""
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yoctotui.app import YoctoApp
from terminal_capture import terminal_svg
from yoctotui.models import Profile, Settings
from textual.widgets import Input, Select, TabbedContent


async def capture():
    import cairosvg
    state = ROOT / '.validation'
    report = json.loads((state / 'result.json').read_text())
    if report['status'] != 'success' or not report.get('artifact_verified'):
        raise RuntimeError('A successfully built and verified rootfs is required before making this capture')
    config = state / 'profiles.json'
    settings = Settings(config)
    settings.profiles = [Profile(name='kas-integration', root=str(ROOT), mode='kas-container', kas_file='tests/integration/kas-minimal.yml', machine='qemux86-64', distro='poky', environment={'KAS_WORK_DIR': report['work'], 'KAS_CONTAINER_ENGINE': 'docker'}, targets=['core-image-minimal'])]
    settings.active = 'kas-integration'
    settings.save()
    os.environ.pop('NO_COLOR', None)
    app = YoctoApp(config, state)
    async with app.run_test(size=(140, 44)) as pilot:
        await pilot.pause(.5)
        jobs = [r for r in app.history_rows.values() if r['status'] == 'success' and 'core-image-minimal' in r['title']]
        if not jobs:
            raise RuntimeError('No matching successful history record')
        job = jobs[0]
        app.select_job(job['id'], job['log'])
        app.query_one('#log-search', Input).value = 'Tasks Summary'
        await pilot.pause(.5)
        def shot(name, title):
            svg = ROOT / f'docs/assets/{name}.svg'
            svg.write_text(terminal_svg(app, title))
            cairosvg.svg2png(url=str(svg), write_to=str(svg.with_suffix('.png')), scale=.8)
        shot('real-kas-build', 'Bitloom · actual kas-container image build')
        app.query_one('#workspace', TabbedContent).active = 'workbench'
        app.query_one('#target', Input).value = 'busybox'
        app.query_one('#inspect-search', Input).value = 'MACHINE'
        app.load_inspection()
        await app.workers.wait_for_complete()
        await pilot.pause(.2)
        shot('real-kas-environment', 'Bitloom · evaluated busybox environment from kas-container')
        graph = next(r for r in app.history_rows.values() if json.loads(r['metadata']).get('action') == 'graph-read' and r['status'] == 'success')
        app.query_one('#inspect-kind', Select).value = 'graph'
        app.query_one('#inspect-search', Input).value = 'busybox'
        app.read_runtime_graph(Path(graph['log']))
        await app.workers.wait_for_complete()
        await pilot.pause(.2)
        shot('real-kas-dependencies', 'Bitloom · actual task dependency graph from kas-container')
    app.store.close()
    print('Captured verified real image build from persisted history')


if __name__ == '__main__':
    asyncio.run(capture())
