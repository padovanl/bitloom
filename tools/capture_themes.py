"""Capture all Bitloom palettes from the running terminal, never a mockup."""
import asyncio
import sys
import os
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from yoctotui.app import YoctoApp
from yoctotui.cli import make_demo
from yoctotui.themes import THEMES
from terminal_capture import terminal_svg

async def main():
    import cairosvg
    from PIL import Image
    os.environ.pop("NO_COLOR", None)
    frames=[]
    with tempfile.TemporaryDirectory(prefix='bitloom-themes-') as work:
        root=Path(work); app=YoctoApp(make_demo(root/'demo'),root/'state')
        async with app.run_test(size=(120,36)) as pilot:
            await pilot.pause(.5)
            for name in THEMES:
                app.theme=name; app.title="Bitloom · " + name; app.refresh_theme_colors()
                await pilot.pause(.25)
                path=ROOT/'docs/assets'/('theme-'+name.lower().replace(' ','-')+'.svg')
                path.write_text(terminal_svg(app,'Bitloom · '+name+' · demo workspace'))
                cairosvg.svg2png(url=str(path),write_to=str(path.with_suffix('.png')),scale=.7)
                frames.append(Image.open(path.with_suffix('.png')).convert('RGB'))
        app.store.close()
    frames[0].save(ROOT/'docs/assets/themes.gif',save_all=True,append_images=frames[1:],duration=1200,loop=0)
    print('Captured all 12 terminal palettes')

if __name__=='__main__': asyncio.run(main())
