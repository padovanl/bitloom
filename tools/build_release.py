"""Build versioned source, wheel and self-contained Debian release assets."""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def release_version(value: str) -> str:
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value):
        raise argparse.ArgumentTypeError('Use a stable version such as 1.2.3 (no v prefix).')
    return value


def set_version(source: Path, version: str) -> None:
    for filename, pattern in [('pyproject.toml', r'^version = ".*"$'),
                              ('yoctotui/__init__.py', r'^__version__ = ".*"$')]:
        path = source / filename
        replacement = f'version = "{version}"' if filename == 'pyproject.toml' else f'__version__ = "{version}"'
        text, count = re.subn(pattern, replacement, path.read_text(), flags=re.MULTILINE)
        if count != 1:
            raise RuntimeError(f'Expected exactly one version in {filename}')
        path.write_text(text)


def run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def build(version: str, output: Path) -> None:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    names = [f'yoctotui-{version}.tar.gz', f'yoctotui-{version}-py3-none-any.whl',
             f'bitloom_{version}_all.deb', 'SHA256SUMS']
    if any((output / name).exists() for name in names):
        raise RuntimeError('Release assets already exist in the output directory; use a fresh directory.')
    if not shutil.which('dpkg-deb'):
        raise RuntimeError('dpkg-deb is required (install dpkg on Debian/Ubuntu).')
    with tempfile.TemporaryDirectory(prefix='bitloom-release-') as directory:
        workspace = Path(directory)
        source = workspace / 'source'
        source.mkdir()
        # Copy project sources only: never include local state, caches or virtualenvs.
        for name in ('LICENSE', 'README.md', 'pyproject.toml', 'MANIFEST.in', 'setup-demo.sh',
                     'yoctotui', 'docs', 'tools', 'tests', 'examples', '.github'):
            origin, target = ROOT / name, source / name
            if origin.is_dir():
                shutil.copytree(origin, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            else:
                shutil.copy2(origin, target)
        set_version(source, version)
        assets = workspace / 'assets'
        run(sys.executable, '-m', 'build', '--sdist', '--wheel', '--no-isolation',
            '--outdir', str(assets), cwd=source)
        package = workspace / 'deb'
        library = package / 'opt/bitloom/lib'
        library.mkdir(parents=True)
        run(sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
            '--only-binary=:all:', '--no-compile', '--target', str(library),
            str(assets / names[1]))
        if any(p.suffix in {'.so', '.pyd'} for p in library.rglob('*')):
            raise RuntimeError('Native dependencies require architecture-specific Debian packaging.')
        shutil.rmtree(library / 'bin', ignore_errors=True)
        control = package / 'DEBIAN'
        control.mkdir()
        size = sum(p.stat().st_size for p in package.rglob('*') if p.is_file())
        (control / 'control').write_text(
            f'Package: bitloom\nVersion: {version}\nArchitecture: all\n'
            'Maintainer: Luca Padovan <padovan.93@gmail.com>\n'
            'Section: devel\nPriority: optional\nDepends: python3 (>= 3.10)\n'
            f'Installed-Size: {(size + 1023) // 1024}\n'
            'Description: Terminal cockpit for Yocto and BitBake development\n'
            ' Build monitoring, recipe development, layers, logs and cache utilities.\n'
            ' Python runtime dependencies are bundled under /opt/bitloom/lib.\n')
        binary = package / 'usr/bin'
        binary.mkdir(parents=True)
        launcher = binary / 'bitloom'
        launcher.write_text('#!/usr/bin/python3\nimport sys\nsys.path.insert(0, "/opt/bitloom/lib")\nfrom yoctotui.cli import main\nmain()\n')
        launcher.chmod(0o755)
        (binary / 'yoctotui').symlink_to('bitloom')
        documentation = package / 'usr/share/doc/bitloom'
        documentation.mkdir(parents=True)
        shutil.copy2(source / 'README.md', documentation / 'README.md')
        shutil.copy2(source / 'LICENSE', documentation / 'copyright')
        run('dpkg-deb', '--root-owner-group', '--build', str(package), str(assets / names[2]))
        for name in names[:-1]:
            shutil.copy2(assets / name, output / name)
        (output / 'SHA256SUMS').write_text(''.join(
            f'{hashlib.sha256((output / name).read_bytes()).hexdigest()}  {name}\n'
            for name in names[:-1]))
    print(f'Release assets ready in {output}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', type=release_version)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/release')
    args = parser.parse_args()
    build(args.version, args.output)


if __name__ == '__main__':
    main()
