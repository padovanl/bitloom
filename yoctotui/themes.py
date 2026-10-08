"""Bitloom palettes; semantic colors adapt the entire terminal workspace."""
from textual.theme import Theme

# name, background, surface, foreground, accent, secondary, dark
PALETTES = [
    ('Bitloom', '#0b1115', '#111b22', '#bdcbd2', '#84c9c0', '#81bdcf', True),
    ('Soft Slate', '#252a30', '#2b3138', '#c4cbd0', '#98b9b2', '#a2b3c6', True),
    ('Linen', '#eeeae2', '#e4dfd5', '#424740', '#52786e', '#687d96', False),
    ('Nord', '#2e3440', '#3b4252', '#eceff4', '#88c0d0', '#b48ead', True),
    ('Dracula', '#282a36', '#343746', '#f8f8f2', '#bd93f9', '#8be9fd', True),
    ('Tokyo Night', '#1a1b26', '#24283b', '#c0caf5', '#7aa2f7', '#bb9af7', True),
    ('Catppuccin Mocha', '#1e1e2e', '#313244', '#cdd6f4', '#cba6f7', '#89b4fa', True),
    ('Gruvbox', '#282828', '#3c3836', '#ebdbb2', '#b8bb26', '#fabd2f', True),
    ('Solarized Dark', '#002b36', '#073642', '#93a1a1', '#2aa198', '#268bd2', True),
    ('Ocean', '#071b2b', '#102c42', '#d4e9f5', '#52d6db', '#82baff', True),
    ('Forest', '#101b15', '#1c3024', '#dce9d9', '#94d69c', '#d5c28b', True),
    ('Ember', '#211611', '#35241c', '#f0dcc9', '#f3a661', '#db8374', True),
    ('Paper', '#f5f3ed', '#e7e3d8', '#292f35', '#176f65', '#345b91', False),
    ('High Contrast', '#000000', '#161616', '#ffffff', '#00ffff', '#ffff00', True),
]
THEMES = {
    name: Theme(name=name, primary=accent, accent=accent, secondary=secondary,
                background=background, surface=surface, panel=surface,
                foreground=foreground, dark=dark,
                success='#8fdbc3' if dark else '#246441',
                warning='#dfbe77' if dark else '#815300',
                error='#f08b87' if dark else '#a32121')
    for name, background, surface, foreground, accent, secondary, dark in PALETTES
}


def syntax_theme(name):
    return 'friendly' if not THEMES.get(name, THEMES['Bitloom']).dark else 'nord' if name in {'Nord','Bitloom','Ocean'} else 'monokai'
