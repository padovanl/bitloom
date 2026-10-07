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
    return '\n'.join(line.rstrip() for line in ET.tostring(root, encoding='unicode').splitlines()) + '\n'
