#!/usr/bin/env bash
# Prepare an isolated Bitloom demo from a fresh checkout; never install Yocto.
set -euo pipefail
DEMO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEMO_LAUNCH=1
DEMO_DEV=0
DEMO_PYTHON="${PYTHON:-python3}"
while (($#)); do
    case "$1" in
        --no-launch) DEMO_LAUNCH=0 ;;
        --dev) DEMO_DEV=1 ;;
        --python) shift; DEMO_PYTHON="${1:?--python requires an executable}" ;;
        --help|-h)
            printf 'Usage: ./setup-demo.sh [--no-launch] [--dev] [--python EXECUTABLE]\nCreates .venv, installs Bitloom, prepares sample data and launches the demo.\nRequires Python 3.10+ with venv support and internet access for dependencies.\n'
            exit 0 ;;
        *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done
command -v "$DEMO_PYTHON" >/dev/null || { printf 'Python not found. Install Python 3.10+ and venv support, then rerun.\n' >&2; exit 1; }
"$DEMO_PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else "Python 3.10+ is required")'
cd -- "$DEMO_ROOT"
if [[ -e .venv && ! -f .venv/pyvenv.cfg ]]; then
    printf 'Refusing to replace .venv: it is not a virtual environment.\n' >&2
    exit 1
fi
if [[ ! -f .venv/pyvenv.cfg ]]; then
    "$DEMO_PYTHON" -m venv .venv || { printf 'Cannot create .venv. Install your distribution Python venv support and rerun.\n' >&2; exit 1; }
fi
DEMO_VENV_PYTHON="$DEMO_ROOT/.venv/bin/python"
if [[ ! -x "$DEMO_VENV_PYTHON" ]]; then
    printf 'Existing .venv has no working Python executable. Recreate it for this machine and rerun.\n' >&2
    exit 1
fi
"$DEMO_VENV_PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else "Existing .venv needs Python 3.10+")'
DEMO_PACKAGE="$DEMO_ROOT"
if ((DEMO_DEV)); then DEMO_PACKAGE="$DEMO_ROOT[dev]"; fi
"$DEMO_VENV_PYTHON" -m pip --disable-pip-version-check install -e "$DEMO_PACKAGE"
"$DEMO_VENV_PYTHON" -c 'import sys; from pathlib import Path; from bitloom.cli import make_demo; make_demo(Path(sys.argv[1]) / "demo")' "$DEMO_ROOT/.bitloom"
export PATH="$DEMO_ROOT/.venv/bin:$PATH"
printf '\nDemo ready. Sample data is under .bitloom/demo; no Yocto image was built.\n'
if ((DEMO_LAUNCH)); then
    exec "$DEMO_VENV_PYTHON" -m bitloom --demo --state "$DEMO_ROOT/.bitloom"
fi
printf 'Launch: cd %q && .venv/bin/bitloom --demo\n' "$DEMO_ROOT"
