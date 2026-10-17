"""Animated clips of the web dashboard in action, for the landing page and the docs.

Run: python tools/capture_web_clips.py                      (labelled demo workspace; needs playwright + pillow)
     python tools/capture_web_clips.py --real CONFIG PROFILE (adds web-clip-build.gif: a real force compile of busybox)
     python tools/capture_web_clips.py --image CONFIG PROFILE (web-image.png and web-clip-image.gif from a built image)

The demo clips use sample metadata and sample command output, labelled as such; nothing claims a Yocto build.
The real clip runs an actual BitBake task through the given profile and records it as it happens.
"""
import argparse
import io
import json
import os
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(Path.home() / '.cache/ms-playwright'))  # browsers stay in the real home
if '--only-real' not in sys.argv and '--image' not in sys.argv:
    os.environ['HOME'] = '/home/developer'   # paths shown in demo clips must not reveal the author's account
sys.path.insert(0, str(ROOT))
from bitloom.cli import prepare_demo
from bitloom.daemon import rpc
from bitloom.models import Settings
from bitloom.web import Dashboard, create_server

OUTPUT = ROOT / 'docs/assets'
VIEWPORT = {'width': 1440, 'height': 900}

# A few more sample layers and recipes so the Recipes view shows its structure (labelled sample metadata).
SAMPLE = {
    'meta-sample-bsp/conf/layer.conf': 'BBFILE_COLLECTIONS += "sample-bsp"\nLAYERSERIES_COMPAT_sample-bsp = "wrynose"\n',
    'meta-sample-bsp/recipes-kernel/linux/linux-yocto_%.bbappend': 'FILESEXTRAPATHS:prepend := "${THISDIR}/files:"\n',
    'meta-sample-bsp/recipes-bsp/u-boot/u-boot_%.bbappend': '# sample\n',
    'meta-sample-bsp/recipes-bsp/firmware/sample-firmware_1.2.bb': 'SUMMARY = "Sample board firmware"\nLICENSE = "MIT"\n',
    'meta-demo/recipes-core/images/demo-image-dev.bb': 'SUMMARY = "Demo image with developer tools"\nrequire recipes-core/images/demo-image.bb\n',
    'meta-demo/recipes-core/images/demo-image-minimal.bb': 'SUMMARY = "Smallest bootable demo image"\nLICENSE = "MIT"\ninherit core-image\n',
    'meta-demo/recipes-connectivity/demo-gateway/demo-gateway_2.4.bb': 'SUMMARY = "Sample gateway daemon"\nLICENSE = "MIT"\n',
    'meta-demo/recipes-connectivity/mosquitto/mosquitto_%.bbappend': '# sample\n',
    'meta-demo/recipes-support/demo-certs/demo-certs_1.0.bb': 'SUMMARY = "Sample CA bundle"\nLICENSE = "MIT"\n',
    'meta-demo/recipes-graphics/demo-ui/demo-ui_0.9.bb': 'SUMMARY = "Sample kiosk UI"\nLICENSE = "MIT"\n',
    'meta-demo/classes/demo-signing.bbclass': '# sample class\n',
}
FAILURE = ('import time\nprint("NOTE: Sample output for the documentation, not a real build", flush=True)\n'
           'for i in range(1, 9):\n    print(f"NOTE: Running task {i * 40} of 400 (/demo/meta-demo/recipes-apps/demo-agent/demo-agent_1.0.bb:do_compile)", flush=True); time.sleep(.25)\n'
           'print("| main.c:42:10: fatal error: telemetry.h: No such file or directory")\n'
           'print("| make: *** [Makefile:12: main.o] Error 1")\n'
           'print("ERROR: demo-agent-1.0-r0 do_compile: oe_runmake failed")\n'
           'print("ERROR: Logfile of failure stored in: /demo/build/tmp/work/core2-64-poky-linux/demo-agent/1.0-r0/temp/log.do_compile.4711")\n'
           'print("ERROR: Task (/demo/meta-demo/recipes-apps/demo-agent/demo-agent_1.0.bb:do_compile) failed with exit code \'1\'")\n'
           'raise SystemExit(1)\n')


class Clip:
    """Frames of one page region, saved as a looping GIF with an adaptive palette."""
    def __init__(self, page, locator=None, box=None, fps=7, width=1100):
        self.page, self.locator, self.box, self.fps, self.width, self.frames = page, locator, box, fps, width, []

    def region(self):
        if self.box:
            return self.box
        b = self.locator.bounding_box()
        size = self.page.viewport_size
        return {'x': max(0, b['x'] - 8), 'y': max(0, b['y'] - 8), 'width': min(size['width'], b['width'] + 16), 'height': min(size['height'] - max(0, b['y'] - 8), b['height'] + 16)}

    def hold(self, seconds):
        from PIL import Image
        end = time.monotonic() + seconds
        while True:
            image = Image.open(io.BytesIO(self.page.screenshot(clip=self.region()))).convert('RGB')
            if image.width > self.width:
                image = image.resize((self.width, round(image.height * self.width / image.width)), Image.LANCZOS)
            self.frames.append(image)
            if time.monotonic() >= end:
                return
            self.page.wait_for_timeout(1000 / self.fps)

    def type(self, selector, text):
        for char in text:
            self.page.type(selector, char)
            self.hold(.09)

    def save(self, name, tail=1.6):
        from PIL import Image
        palette = self.frames[len(self.frames) // 2].quantize(colors=200, method=Image.Quantize.MEDIANCUT)
        frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in self.frames]
        durations = [round(1000 / self.fps)] * len(frames)
        durations[-1] = int(tail * 1000)
        path = OUTPUT / f'{name}.gif'
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True, disposal=1)
        print(f'{path.name}: {len(frames)} frames, {path.stat().st_size // 1024} KiB')


def serve(config, state, token):
    board = Dashboard(config, state, token=token)
    server = create_server(board, '127.0.0.1', 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_address[1]}'

    def post(path, body):
        request = urllib.request.Request(base + path, json.dumps(body).encode(), {'X-Bitloom-Token': token, 'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(request).read())
    return board, server, base, post


def demo_clips(browser):
    work = Path(tempfile.mkdtemp(prefix='bitloom-clips-'))
    config = prepare_demo(work / 'state')
    settings = Settings(config)
    settings.active = 'demo-wrynose'
    settings.save()
    root = next(p for p in settings.profiles if p.name == 'demo-wrynose').root_path
    for relative, text in SAMPLE.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text)
    # A launcher project with two products, for the guided setup clip.
    project = work / 'product'
    (project / 'kas').mkdir(parents=True)
    (project / 'kas/base.yml').write_text('header:\n  version: 14\nmachine: qemux86-64\ntarget: demo-image\nrepos:\n  poky:\n')
    (project / 'kas/gateway.yml').write_text('header:\n  version: 14\n  includes:\n    - kas/base.yml\n')
    (project / 'kas/panel.yml').write_text('header:\n  version: 14\n  includes:\n    - kas/base.yml\nmachine: qemuarm64\ntarget: demo-ui-image\n')
    launcher = project / 'run_kas.sh'
    launcher.write_text('#!/bin/bash\nexport KAS_WORK_DIR="${KAS_WORK_DIR:-$PWD/build-${YML%.yml}}"\ncmd=$1; shift\nexec kas-container "$cmd" "$@" "$YML"\n')
    launcher.chmod(0o755)
    board, server, base, post = serve(config, work / 'state', 'clips')
    failing = work / 'sample_failure.py'
    failing.write_text(FAILURE)
    try:
        page = browser.new_page(viewport=VIEWPORT, color_scheme='dark')
        page.goto(base + '/#token=clips')
        page.wait_for_timeout(3500)

        # Target picker: open, filter, choose.
        clip = Clip(page, box={'x': 560, 'y': 0, 'width': 560, 'height': 330})
        clip.hold(.6)
        page.keyboard.press('t')
        clip.hold(1.4)
        clip.type('#target', 'dev')
        clip.hold(1.0)
        page.keyboard.press('Enter')
        clip.hold(1.2)
        clip.save('web-clip-target')
        page.fill('#target', 'demo-image')
        page.keyboard.press('Escape'); page.keyboard.press('Escape')    # leave the field: t is a shortcut only outside it
        page.keyboard.press('t')
        page.wait_for_timeout(900)
        page.keyboard.press('Escape'); page.keyboard.press('Escape')

        # A failed sample job: the toast, then the summary opens on the diagnosis.
        # Framed on the build detail, where it happens: progress, toast, then the summary.
        detail = page.locator('#d-prog').locator('xpath=ancestor::div[contains(@class,"panel")][1]').bounding_box()
        clip = Clip(page, box={'x': detail['x'] - 6, 'y': 0, 'width': VIEWPORT['width'] - detail['x'] + 6, 'height': 640}, fps=6, width=900)
        post('/api/jobs', {'action': 'custom', 'values': {'command': f'{sys.executable} {failing}'}})
        clip.hold(5.5)
        page.keyboard.press('u')
        clip.hold(2.6)
        clip.save('web-clip-failure', tail=2.5)

        # Recipes: layers, kind filter, search.
        page.keyboard.press('Escape'); page.keyboard.press('2')
        page.wait_for_timeout(1800)
        clip = Clip(page, box={'x': 230, 'y': 205, 'width': 1210, 'height': 640})
        clip.hold(.8)
        page.locator('.layer-item', has_text='meta-demo').first.click()
        clip.hold(1.2)
        page.locator('#meta-kinds button', has_text='Images').click()
        clip.hold(1.2)
        page.locator('#meta-kinds button', has_text='All').click()
        page.locator('.layer-item').first.click()
        clip.hold(.6)
        page.locator('#meta-search').click()
        clip.type('#meta-search', 'demo-')
        clip.hold(1.4)
        clip.save('web-clip-recipes')
        page.fill('#meta-search', '')

        # Studio: pick what to create, walk the steps, review. The preview follows the focused field.
        page.keyboard.press('Escape'); page.keyboard.press('6')
        page.wait_for_timeout(1800)
        clip = Clip(page, box={'x': 230, 'y': 60, 'width': 1210, 'height': 840}, width=1100)
        clip.hold(1.2)
        page.locator('.sg-kind b', has_text='Image').first.click()
        clip.hold(1.4)
        page.locator('#sg-next').click()
        clip.hold(.6)
        page.fill('#sf-name', '')
        clip.type('#sf-name', 'gateway-image')
        clip.hold(.5)
        page.keyboard.press('Enter')
        clip.hold(.8)
        page.locator('#sf-packages').click()
        clip.type('#sf-packages', ' mosquitto')
        clip.hold(.6)
        page.locator('[data-field=features] .toggle', has_text='tools-debug').focus()
        page.locator('[data-field=features] .toggle', has_text='tools-debug').click()
        clip.hold(1.0)
        page.locator('#sg-next').click()
        clip.hold(2.4)
        clip.save('web-clip-studio', tail=2.5)
        page.locator('#sg-restart').click()

        # Guided setup on a launcher project with two products.
        page.keyboard.press('Escape'); page.keyboard.press('7')
        page.wait_for_timeout(1500)
        page.locator('#setup-dir').scroll_into_view_if_needed()
        page.fill('#setup-dir', '')
        box = page.locator('#setup-dir').locator('xpath=ancestor::div[contains(@class,"panel")][1]').bounding_box()
        clip = Clip(page, box={'x': box['x'] - 6, 'y': max(0, box['y'] - 6), 'width': box['width'] + 12, 'height': min(900 - max(0, box['y'] - 6), 760)})
        clip.hold(.5)
        page.locator('#setup-dir').click()
        page.keyboard.type(str(project))
        clip.hold(.4)
        page.keyboard.press('Enter')
        clip.hold(2.4)
        page.locator('#setup-found .row').nth(1).click()
        clip.hold(1.6)
        clip.save('web-clip-setup', tail=2.2)
        page.close()
    finally:
        server.shutdown()
        try:
            rpc(board.state, {'op': 'stop'})
        except (OSError, ValueError):
            pass


def real_clip(browser, config, profile, state):
    board, server, base, post = serve(Path(config), Path(state), 'clips')
    settings = Settings(Path(config))
    settings.active = profile
    settings.save()
    try:
        page = browser.new_page(viewport=VIEWPORT, color_scheme='dark')
        page.goto(base + '/#token=clips')
        page.wait_for_timeout(3500)
        page.select_option('#profile', profile)
        page.wait_for_timeout(1500)
        clip = Clip(page, box={'x': 230, 'y': 60, 'width': 1210, 'height': 840}, fps=3, width=1100)
        page.fill('#target', 'busybox')
        page.keyboard.press('Escape'); page.keyboard.press('Escape')    # close the image list, then leave the field
        page.keyboard.press('q'); page.wait_for_timeout(600)
        page.keyboard.type('Force compile'); page.wait_for_timeout(600)
        page.locator('#op-submit').click()
        started = time.monotonic()
        while time.monotonic() - started < 600:
            clip.hold(1.0)          # one frame a second, played at three: about three times real speed
            status = page.locator('#d-meta').first.inner_text()
            if any(word in status for word in ('success', 'failed', 'cancelled')):
                break
        page.keyboard.press('u')
        clip.hold(2.0)
        clip.save('web-clip-build', tail=3)
    finally:
        server.shutdown()


def image_clip(browser, config, profile, state):
    """The Image explorer on a real built image: the overview, /etc, a file, which recipe installs it, Change it."""
    board, server, base, post = serve(Path(config), Path(state), 'clips')
    try:
        page = browser.new_page(viewport=VIEWPORT, color_scheme='dark')
        page.goto(base + '/#token=clips')
        page.wait_for_timeout(3000)
        page.select_option('#profile', profile)
        page.wait_for_timeout(1500)
        page.keyboard.press('4')
        page.wait_for_timeout(4000)
        page.screenshot(path=str(OUTPUT / 'web-image.png'))
        print('web-image.png')
        page.click('#img-mode button[data-mode=services]')
        page.wait_for_timeout(4000)
        page.locator('#img-services .svc', has_text='syslog').first.click()
        page.wait_for_timeout(3000)
        page.evaluate("document.querySelector('#img-mode').closest('.panel').scrollIntoView({block: 'start'})")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUTPUT / 'web-image-services.png'))
        print('web-image-services.png')
        page.click('#img-mode button[data-mode=files]')
        page.wait_for_timeout(500)
        page.click('#img-mode button[data-mode=insights]')
        page.wait_for_timeout(6000)
        page.evaluate("document.querySelector('#img-insights').scrollIntoView({block: 'start'})")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUTPUT / 'web-image-insights.png'))
        print('web-image-insights.png')
        page.click('#img-mode button[data-mode=files]')
        page.wait_for_timeout(800)
        page.locator('#img-crumbs button').first.click()
        page.wait_for_timeout(1500)
        page.evaluate('window.scrollTo(0, 0)')
        clip = Clip(page, box={'x': 230, 'y': 50, 'width': 1210, 'height': 850}, fps=5, width=1100)
        clip.hold(1.5)
        page.locator('.ent.dir .n', has_text='etc').first.click()
        clip.hold(1.4)
        page.locator('.ent .n', has_text='motd').first.click()
        clip.hold(2.4)
        page.fill('#img-find', '')
        page.locator('#img-find').click()
        clip.type('#img-find', 'libc6')
        page.keyboard.press('Enter')
        clip.hold(2.2)
        page.locator('.ent .n', has_text='motd').first.click()
        clip.hold(1.2)
        page.locator('button', has_text='Change it with an append').first.click()
        clip.hold(3.0)
        clip.save('web-clip-image', tail=2.5)
    finally:
        server.shutdown()


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--real', nargs=2, metavar=('CONFIG', 'PROFILE'), help='also record a real force compile of busybox')
    parser.add_argument('--state', default=None, help='state directory for --real (default: next to CONFIG)')
    parser.add_argument('--only-real', action='store_true')
    parser.add_argument('--image', nargs=2, metavar=('CONFIG', 'PROFILE'), help='record the Image explorer on a profile with a built image')
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        if not args.only_real and not args.image:
            demo_clips(browser)
        if args.real:
            real_clip(browser, args.real[0], args.real[1], args.state or str(Path(args.real[0]).parent / 'state'))
        if args.image:
            image_clip(browser, args.image[0], args.image[1], args.state or str(Path(args.image[0]).parent / 'state'))
        browser.close()


if __name__ == '__main__':
    main()
