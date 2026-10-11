"""Build and serve the documentation site locally.

Usage: python tools/serve_docs.py [--port 8000] [--host 127.0.0.1] [--no-build] [--open]
Rebuilds docs/*.html from the Markdown sources (needs markdown-it-py), then serves docs/.
"""
import argparse
import functools
import http.server
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--port', type=int, default=8000, help='port to listen on (0 picks a free one)')
    parser.add_argument('--host', default='127.0.0.1', help='address to bind (default: loopback only)')
    parser.add_argument('--no-build', action='store_true', help='serve the existing HTML without rebuilding it')
    parser.add_argument('--open', action='store_true', help='open the site in a browser')
    args = parser.parse_args()
    if not args.no_build:
        for tool in ('generate_reference.py', 'build_docs.py'):
            subprocess.run([sys.executable, str(ROOT / 'tools' / tool)], check=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / 'docs'))
    with http.server.ThreadingHTTPServer((args.host, args.port), handler) as server:
        url = f'http://{"127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host}:{server.server_address[1]}/'
        print(f'Serving the Bitloom documentation at {url} (Ctrl+C stops)')
        if args.open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
