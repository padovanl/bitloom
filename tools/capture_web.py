"""Capture the real web dashboard with Playwright on the labelled demo workspaces.

Run: python tools/capture_web.py   (requires playwright with Chromium, pillow)
Jobs are real subprocesses with sample output; nothing claims a Yocto build.
"""
import json
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bitloom.cli import prepare_demo
from bitloom.daemon import rpc
from bitloom.models import Settings
from bitloom.web import Dashboard, create_server


def main():
    from PIL import Image
    from playwright.sync_api import sync_playwright
    output = ROOT / 'docs/assets'
    work = Path(tempfile.mkdtemp(prefix='bitloom-web-'))
    config = prepare_demo(work / 'state')
    settings = Settings(config)
    settings.active = 'demo-wrynose'
    settings.save()
    board = Dashboard(config, work / 'state', token='docs')
    server = create_server(board, '127.0.0.1', 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_address[1]}'

    def post(path, body):
        request = urllib.request.Request(base + path, json.dumps(body).encode(), {'X-Bitloom-Token': 'docs', 'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(request).read())
    failing = work / 'sample_failure.py'
    failing.write_text('print("NOTE: Demo sample output, not a real build")\nprint("WARNING: demo-agent: QA issue sample")\n'
                       'print("NOTE: Sstate summary: Wanted 40 Local 31 Mirrors 0 Missed 9 Current 12")\nprint("ERROR: oe_runmake failed")\nexit(1)\n')
    running = work / 'sample_running.py'
    running.write_text('import time\nprint("NOTE: Demo sample output, not a real build")\nprint("NOTE: Running setscene task 120 of 300")\n'
                       'for i in range(1, 400):\n    print(f"NOTE: Running task {i} of 400 (/demo/r{i}.bb:do_compile)", flush=True)\n'
                       '    print(f"NOTE: recipe demo-r{i}-1.0-r0: task do_compile: Started", flush=True)\n    time.sleep(.2)\n')
    post('/api/jobs', {'action': 'custom', 'values': {'command': f'{sys.executable} {failing}'}})
    time.sleep(1.5)
    live = post('/api/jobs', {'action': 'custom', 'values': {'command': f'{sys.executable} {running}'}})['id']
    frames = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={'width': 1440, 'height': 900}, color_scheme='dark')
            page.goto(base + '/#token=docs')
            page.wait_for_timeout(6000)

            def shot(name, full=False, tour=True):
                path = output / f'{name}.png'
                page.screenshot(path=str(path), full_page=full)
                if tour:
                    frames.append(Image.open(path).convert('RGB').resize((1152, 720)))
            shot('web-builds')
            page.keyboard.press('u'); page.wait_for_timeout(900); shot('web-summary')
            page.keyboard.press('o')
            page.keyboard.press('4'); page.wait_for_timeout(1800); shot('web-compliance')
            page.keyboard.press('5'); page.wait_for_timeout(1500); shot('web-studio')
            page.keyboard.press('Control+k'); page.wait_for_timeout(300); page.keyboard.type('sbom'); page.wait_for_timeout(500); shot('web-palette')
            page.keyboard.press('Escape')
            page.keyboard.press('6'); page.wait_for_timeout(1200); shot('web-health', tour=False)
            mobile = browser.new_page(viewport={'width': 390, 'height': 844}, color_scheme='light')
            mobile.goto(base + '/#token=docs'); mobile.wait_for_timeout(3000)
            mobile.screenshot(path=str(output / 'web-mobile.png'))
            browser.close()
        frames[0].save(output / 'web-tour.gif', save_all=True, append_images=frames[1:], duration=2400, loop=0, optimize=True)
    finally:
        server.shutdown()
        try:
            rpc(board.state, {'op': 'cancel', 'id': live})
            rpc(board.state, {'op': 'stop'})
        except (OSError, ValueError):
            pass
    print(f'Captured {len(frames)} web views and web-tour.gif in {output}')


if __name__ == '__main__':
    main()
