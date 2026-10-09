"""Real-browser smoke test for the static GitHub Pages documentation.

pip install playwright
PLAYWRIGHT_BROWSERS_PATH=/tmp/bitloom-browsers python -m playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=/tmp/bitloom-browsers python tools/check_docs.py
"""
import functools
import http.server
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def check():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / 'docs'))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
            failures = []
            page.on('pageerror', lambda exc: failures.append(str(exc)))
            page.on('response', lambda response: failures.append(f'{response.status} {response.url}') if response.status >= 400 else None)
            url = f'http://127.0.0.1:{server.server_port}'
            page.goto(url, wait_until='networkidle')
            page.locator('#feature-search').fill('sstate')
            assert page.locator('#feature-cards article:visible').count() == 1
            page.locator('#feature-search').fill('')
            page.locator('[data-runtime="kas-container"]').click()
            assert 'KAS_CONTAINER_ENGINE' in page.locator('#runtime-code').inner_text()
            page.locator('[data-image="assets/profiles.png"]').click()
            assert page.locator('#lightbox').is_visible()
            page.keyboard.press('Escape')
            assert not page.locator('#lightbox').is_visible()
            page.screenshot(path=str(ROOT / 'docs/assets/docs-site.png'), full_page=True)
            for name in ('guide', 'commands', 'validation', 'testbook'):
                page.goto(f'{url}/{name}.html', wait_until='networkidle')
                assert page.locator('h1').count() == 1
            page.set_viewport_size({'width': 390, 'height': 844})
            page.goto(url, wait_until='networkidle')
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.screenshot(path=str(ROOT / 'docs/assets/docs-mobile.png'), full_page=True)
            assert not failures, failures
            browser.close()
            print('PASS: feature filter, runtime switch, screenshot dialog, manual pages and mobile layout; no page errors or failed resources')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    check()
