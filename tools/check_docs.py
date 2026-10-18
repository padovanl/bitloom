"""Real-browser smoke test for the static GitHub Pages documentation.

pip install playwright
PLAYWRIGHT_BROWSERS_PATH=/tmp/bitloom-browsers python -m playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=/tmp/bitloom-browsers python tools/check_docs.py
"""
import tempfile
import functools
import http.server
import threading
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
# Full-page review captures are not documentation: keep them out of docs/assets (and the release archive).
SHOTS = Path(tempfile.gettempdir()) / 'bitloom-docs-check'
SHOTS.mkdir(exist_ok=True)


def check_links():
    class Links(HTMLParser):
        def __init__(self):
            super().__init__(); self.references = []; self.ids = set()
        def handle_starttag(self, tag, attributes):
            values = dict(attributes)
            if values.get('id'): self.ids.add(values['id'])
            self.references += [values[key] for key in ('href', 'src', 'data-image') if values.get(key)]
    pages = {}
    for path in (ROOT / 'docs').glob('*.html'):
        page = Links(); page.feed(path.read_text()); pages[path.resolve()] = page
    count = 0
    for path, page in pages.items():
        for reference in page.references:
            url = urlsplit(reference)
            if url.scheme or url.netloc: continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            assert target.exists(), f'Missing local link: {path.name} → {reference}'
            if url.fragment and target in pages:
                assert unquote(url.fragment) in pages[target].ids, f'Missing anchor: {path.name} → {reference}'
            count += 1
    print(f'PASS: {count} local documentation links and anchors')


def check():
    check_links()
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
            page.locator('#feature-search').fill('developer')
            assert page.locator('#feature-cards article:visible').count() == 1
            page.locator('#feature-search').fill('')
            page.locator('[data-runtime="kas-container"]').click()
            assert 'KAS_CONTAINER_ENGINE' in page.locator('#runtime-code').inner_text()
            page.locator('[data-image="assets/profiles.png"]').click()
            assert page.locator('#lightbox').is_visible()
            page.keyboard.press('Escape')
            assert not page.locator('#lightbox').is_visible()
            page.screenshot(path=str(SHOTS / 'docs-site.png'), full_page=True)
            for name in ('guide', 'commands', 'validation', 'testbook', 'roadmap', 'developer'):
                page.goto(f'{url}/{name}.html', wait_until='networkidle')
                assert page.locator('h1').count() == 1
                assert page.locator('.sidebar a[aria-current="page"]').count() == 1
            page.locator('#search-input').fill('sbom-cve-check')
            page.wait_for_selector('#search-results a')
            assert page.locator('#search-results a').count() > 1
            page.keyboard.press('Escape')
            page.set_viewport_size({'width': 390, 'height': 844})
            page.goto(url, wait_until='networkidle')
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.screenshot(path=str(SHOTS / 'docs-mobile.png'), full_page=True)
            assert not failures, failures
            browser.close()
            print('PASS: feature filter, runtime switch, screenshot dialog, manual pages with navigation and search, mobile layout; no page errors or failed resources')
            print(f'Full-page captures for review: {SHOTS}')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    check()
