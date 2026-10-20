"""Render the actual terminal grid without Rich's decorative desktop-window frame."""
import re
import xml.etree.ElementTree as ET


def terminal_svg(app, title: str) -> str:
    svg = app.export_screenshot(title=title)
    root = ET.fromstring(svg)
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    ET.register_namespace('', ns['svg'])
    clip = next(e for e in root.findall('.//svg:clipPath', ns) if e.get('id', '').endswith('-clip-terminal'))
    rect = clip.find('svg:rect', ns)
    grid = next(e for e in root.findall('svg:g', ns) if e.get('clip-path', '').endswith('-clip-terminal)'))
    coords = re.findall(r'[\d.]+', grid.get('transform', ''))
    root.set('viewBox', f'{coords[0]} {coords[1]} {rect.get("width")} {rect.get("height")}')
    for child in list(root):
        if child.tag.endswith('rect') or child.get('class', '').endswith('-title') or child.find('svg:circle', ns) is not None:
            root.remove(child)
    style = root.find('svg:style', ns)
    style.text = re.sub(r'@font-face\s*\{.*?\}', '', style.text, flags=re.S).replace('Fira Code, monospace', '"DejaVu Sans Mono", monospace')
    desc = ET.SubElement(root, f'{{{ns["svg"]}}}desc')
    desc.text = title
    return private('\n'.join(line.rstrip() for line in ET.tostring(root, encoding='unicode').splitlines()) + '\n')


def private(text: str) -> str:
    """Captures are published: the checkout's folder and the home folder of whoever runs the capture become neutral
    paths of the same length (each piece of text has a fixed width in the image)."""
    from pathlib import Path

    names = ["bitloom", "bitloom-src", "bitloom-main", "bitloom-clone", "bitloom-master", "bitloom-checkout", "bitloom-workspace",
             "bitloom-development", "bitloom-main-checkout", "bitloom-current-checkout", "bitloom-workspace-current",
             "bitloom-workspace-checkout", "bitloom-development-checkout", "bitloom-workspace-main-checkout"]

    def fit(prefix: str, filler: str, length: int) -> str:
        exact = next((n for n in names if len(prefix + n) == length), None) if filler.startswith("bitloom") else None
        if exact:
            return prefix + exact
        while len(prefix + filler) < length:
            filler += "-copy"
        return (prefix + filler)[:length]
    checkout = str(Path(__file__).resolve().parents[1])
    home = str(Path.home())
    for real, neutral in ((checkout, fit("/home/user/src/", "bitloom-workspace-checkout", len(checkout))),
                          (home, fit("/home/", "user", len(home)))):
        if len(real) > 4:
            text = re.sub(re.escape(real), neutral, text, flags=re.IGNORECASE)
    return text
