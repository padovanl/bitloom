"""Capture actual Developer views from saved real kas-container validation reports.

Run tools/validate_developer.py --build first. No fabricated report content is used.
The wizard capture is a preview only and does not create a layer.
"""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bitloom.app import BitloomApp
from bitloom.developer_ui import DeveloperPanel, ScaffoldScreen
from bitloom.models import Settings
from textual.widgets import Input, Select
from terminal_capture import terminal_svg


async def capture():
    import cairosvg
    from PIL import Image
    evidence = ROOT / '.developer-validation'
    if not (evidence / 'result.json').is_file():
        raise ValueError('Run python tools/validate_developer.py --build successfully first')
    result = json.loads((evidence / 'result.json').read_text())
    if not any(r['operation'] == 'Restored generated recipe' and r['status'] == 'success' for r in result['results']):
        raise ValueError('Successful real recipe validation and recovery evidence is required')
    os.environ.pop('NO_COLOR', None)
    frames = []
    output = ROOT / 'docs/assets'
    with tempfile.TemporaryDirectory(prefix='bitloom-developer-captures-') as temporary:
        directory = Path(temporary)
        settings = Settings(evidence / 'profiles.json')
        identity = json.loads((evidence / 'capabilities.json').read_text())['identity']
        settings.profile.machine = identity.get('MACHINE') or settings.profile.machine
        settings.profile.distro = identity.get('DISTRO') or settings.profile.distro
        settings.path = directory / 'profiles.json'; settings.save()
        app = BitloomApp(settings.path, directory / 'state')
        async with app.run_test(size=(140,44)) as pilot:
            await pilot.pause(.5)
            app.theme = 'Soft Slate'
            await pilot.press('f10')
            panel = app.query_one(DeveloperPanel)
            async def shot(name, description, animated=True):
                await pilot.pause(.3)
                svg = output / (name + '.svg')
                svg.write_text(terminal_svg(app, 'Bitloom · ' + description))
                cairosvg.svg2png(url=str(svg), write_to=str(svg.with_suffix('.png')), scale=.8)
                if animated: frames.append(Image.open(svg.with_suffix('.png')).convert('RGB'))
            for view, first in [('variable', 'SUMMARY'), ('recipe', ''), ('browse', '/work/poky/meta/recipes-core/busybox'),
                                ('performance', ''), ('failure', '')]:
                app.query_one('#dev-view', Select).value = view
                await pilot.pause(.1)
                data = json.loads((evidence / (view + '.json')).read_text())
                app.query_one('#dev-recipe', Input).value = 'bitloom-validation-hello' if view in {'variable','recipe','failure'} else 'busybox'
                app.query_one('#dev-first', Input).value = first
                panel.display_report(data, settings.profile, view)
                await shot('developer-' + ('browser' if view == 'browse' else view), 'real kas-container ' + view + ' evidence')
            app.query_one('#dev-view', Select).value = 'browse'
            await pilot.pause(.1)
            app.query_one('#dev-first', Input).value = '/work/poky/meta/recipes-core/busybox'
            panel.display_report(json.loads((evidence / 'browse.json').read_text()), settings.profile, 'browse')
            await pilot.resize_terminal(80,24)
            await shot('developer-compact', 'real runtime browser · 80 × 24', animated=False)
            await pilot.resize_terminal(140,44)
            app.push_screen(ScaffoldScreen(settings.profile))
            await pilot.pause(.2)
            app.screen.preview()
            await shot('developer-scaffold', 'actual licensed CMake wizard preview · no files created')
            await pilot.press('escape')
        app.store.close()
    size = frames[0].size
    frames = [frame.resize(size) for frame in frames]
    frames[0].save(output / 'developer-tour.gif', save_all=True, append_images=frames[1:], duration=2400, loop=0)
    print('Captured real Developer evidence, compact browser and actual wizard preview')


if __name__ == '__main__':
    asyncio.run(capture())
