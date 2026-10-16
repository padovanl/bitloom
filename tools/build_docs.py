"""Build standalone HTML manuals for the GitHub Pages site from Markdown sources.

Every manual page gets the documentation layout (docs.css, docs.js): a sidebar with all
pages, an "On this page" table of contents, previous/next links, a theme switch and a
client-side search over docs/search.json, which this script also writes."""
import html
import json
import re
from pathlib import Path
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
REPOSITORY = 'https://github.com/padovanl/bitloom'

# Sidebar groups, in reading order (previous/next follow this order).
NAV = [
    ('Get started', [('quickstart', 'Quickstart'), ('guide', 'User guide'), ('projects', 'Projects and setup'), ('keyboard', 'Keyboard')]),
    ('Features', [('web', 'Web dashboard'), ('image', 'Image explorer'), ('compliance', 'SBOM, CRA and releases'), ('studio', 'Studio'),
                  ('practices', 'Best practices'),                   ('teams', 'Teams and CI/CD'), ('developer', 'Developer workbench')]),
    ('Reference', [('commands', 'Command reference'), ('validation', 'Validation'), ('testbook', 'Manual testbook'),
                   ('roadmap', 'Research map')]),
]
PAGES = [(name, title, group) for group, items in NAV for name, title in items]


def slugify(title):
    return re.sub(r'[^\w\s-]', '', title.lower()).replace(' ', '-')


def heading_open(tokens, idx, options, env):
    title = tokens[idx + 1].content
    slug = slugify(title)
    tokens[idx].attrSet('id', slug)
    return f'<{tokens[idx].tag} id="{html.escape(slug)}">'


def heading_close(tokens, idx, options, env):
    tag = tokens[idx].tag
    if tag in ('h2', 'h3'):
        slug = tokens[idx - 2].attrGet('id')
        return f'<a class="anchor" href="#{html.escape(slug)}" aria-label="Link to this section">#</a></{tag}>\n'
    return f'</{tag}>\n'


SHOT = re.compile(r'<p><img src="([^"]+)" alt="([^"]*)"\s*/?></p>')


def expandable_images(content):
    """Screenshots collapse into animated <details>; images load only when opened."""
    def replace(match):
        source, alt = match[1], match[2]
        kind = 'Animation' if source.endswith('.gif') else 'Screenshot'
        return (f'<details class="shot"><summary><span>{kind}</span> {alt}</summary>'
                f'<div class="shot-body"><img src="{source}" alt="{alt}" loading="lazy" decoding="async"></div></details>')
    return SHOT.sub(replace, content)


TAGS = re.compile(r'<[^>]+>')


BLOCK_END = re.compile(r'</(p|li|h\d|td|th|tr|pre|div|summary|ul|ol|table|blockquote)>|<br\s*/?>')


def plain(fragment):
    # Block ends become spaces; inline tags (code, strong, a) vanish without adding spaces.
    return re.sub(r'\s+', ' ', html.unescape(TAGS.sub('', BLOCK_END.sub(' ', fragment)))).strip()


def sections(content, page_title, name):
    """Search entries: one per page introduction and per h2/h3 section."""
    parts = re.split(r'(<h[23] id="[^"]+">.*?</h[23]>)', content)
    entries = [{'page': page_title, 'title': page_title, 'url': f'{name}.html', 'text': plain(parts[0])[:1500]}]
    for heading, body in zip(parts[1::2], parts[2::2]):
        anchor = re.search(r'id="([^"]+)"', heading)[1]
        title = plain(re.sub(r'<a class="anchor".*?</a>', '', heading))
        entries.append({'page': page_title, 'title': title, 'url': f'{name}.html#{anchor}', 'text': plain(body)[:1500]})
    return entries


def toc(content):
    links = []
    for level, anchor, inner in re.findall(r'<h([23]) id="([^"]+)">(.*?)</h[23]>', content):
        text = plain(re.sub(r'<a class="anchor".*?</a>', '', inner))
        css = ' class="sub"' if level == '3' else ''
        links.append(f'<a href="#{anchor}"{css}>{html.escape(text)}</a>')
    return '<h4>On this page</h4>' + ''.join(links) if links else ''


def sidebar(current):
    out = ['<a class="home" href="index.html">← Bitloom home</a>']
    for group, items in NAV:
        out.append(f'<h3>{html.escape(group)}</h3>')
        for name, title in items:
            mark = ' aria-current="page"' if name == current else ''
            out.append(f'<a href="{name}.html"{mark}>{html.escape(title)}</a>')
    return ''.join(out)


def pager(position):
    links = []
    if position > 0:
        name, title, _ = PAGES[position - 1]
        links.append(f'<a class="prev" href="{name}.html"><small>Previous</small>{html.escape(title)}</a>')
    if position + 1 < len(PAGES):
        name, title, _ = PAGES[position + 1]
        links.append(f'<a class="next" href="{name}.html"><small>Next</small>{html.escape(title)}</a>')
    return f'<nav class="pager" aria-label="Previous and next page">{"".join(links)}</nav>'


THEME_BOOT = ("<script>try{var t=localStorage.getItem('bitloom-docs-theme');"
              "if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}catch(e){}</script>")


def build():
    md = MarkdownIt('commonmark').enable('table')
    md.renderer.rules['heading_open'] = heading_open
    md.renderer.rules['heading_close'] = heading_close
    index = []
    for position, (name, nav_title, group) in enumerate(PAGES):
        source = ROOT / 'README.testbook.md' if name == 'testbook' else DOCS / f'{name}.md'
        if not source.exists():
            continue
        text = source.read_text()
        content = md.render(text)
        content = re.sub(r'href="([^"#]+)\.md([#"][^"]*)', r'href="\1.html\2', content)
        content = expandable_images(content)
        source_link = f'{REPOSITORY}/blob/main/README.testbook.md' if name == 'testbook' else f'{REPOSITORY}/blob/main/docs/{name}.md'
        title = text.splitlines()[0].lstrip('# ')
        index += sections(content, title, name)
        page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — Bitloom documentation</title>
<meta name="description" content="Bitloom documentation: {html.escape(title)}">
<link rel="icon" type="image/svg+xml" href="assets/bitloom-icon.svg"><link rel="icon" type="image/png" sizes="32x32" href="assets/favicon-32.png"><link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
{THEME_BOOT}<link rel="stylesheet" href="docs.css"></head>
<body>
<header class="topbar">
<button id="menu-toggle" class="icon-button" type="button" aria-label="Open the page list" aria-expanded="false" aria-controls="sidebar">☰</button>
<a class="brand" href="index.html"><img src="assets/bitloom-icon.svg" width="26" height="26" alt=""> Bitloom <small>docs</small></a>
<div class="search" role="search"><input id="search-input" type="search" placeholder="Search docs" aria-label="Search the documentation" autocomplete="off"><kbd>/</kbd><div id="search-results" class="search-results" role="listbox" hidden></div></div>
<span class="spacer"></span>
<a class="top-link" href="{REPOSITORY}">GitHub</a>
<button id="theme-toggle" class="icon-button" type="button" aria-label="Switch theme">☾</button>
</header>
<div class="layout">
<nav id="sidebar" class="sidebar" aria-label="Documentation pages">{sidebar(name)}</nav>
<main class="content">
<div class="breadcrumbs"><a href="index.html">Bitloom</a> › {html.escape(group)}</div>
<article class="doc">{content}</article>
{pager(position)}
<div class="page-meta"><a href="{source_link}">View the Markdown source</a><a href="{REPOSITORY}/issues">Report a problem</a></div>
</main>
<aside class="toc" aria-label="On this page">{toc(content)}</aside>
</div>
<script src="docs.js"></script>
</body></html>
'''
        (DOCS / f'{name}.html').write_text(page)
        print(f'Built {name}.html')
    (DOCS / 'search.json').write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')))
    print(f'Wrote search.json ({len(index)} sections)')


if __name__ == '__main__':
    build()
