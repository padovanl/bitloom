"""Build standalone HTML manuals for the GitHub Pages site from Markdown sources."""
import html
import re
from pathlib import Path
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


def heading_open(tokens, idx, options, env):
    title = tokens[idx + 1].content
    slug = re.sub(r'[^\w\s-]', '', title.lower()).replace(' ', '-')
    tokens[idx].attrSet('id', slug)
    return f'<{tokens[idx].tag} id="{html.escape(slug)}">'


def build():
    md = MarkdownIt('commonmark').enable('table')
    md.renderer.rules['heading_open'] = heading_open
    for name in ('guide', 'commands', 'validation'):
        source = DOCS / f'{name}.md'
        if not source.exists():
            continue
        content = md.render(source.read_text())
        content = re.sub(r'href="([^"#]+)\.md([#"][^"]*)', r'href="\1.html\2', content)
        title = source.read_text().splitlines()[0].lstrip('# ')
        page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)} — Bitloom</title><link rel="stylesheet" href="style.css"></head>
<body><header><a class="brand" href="index.html">B▸ Bitloom</a><nav aria-label="Documentation navigation"><a href="guide.html">Guide</a><a href="commands.html">Commands</a><a href="validation.html">Validation</a></nav></header><main class="manual"><article class="doc">{content}</article></main><footer><a href="index.html">← Back to the cockpit</a><a href="{name}.md">Markdown source</a></footer></body></html>'''
        (DOCS / f'{name}.html').write_text(page)
        print(f'Built {name}.html')


if __name__ == '__main__':
    build()
