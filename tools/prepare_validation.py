"""Create a TUI profile for the existing or a new isolated kas test workspace."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bitloom.models import Profile, Settings
from tools.validate_kas import KAS_IMAGE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, help='Linux build workspace; defaults to the recorded validation workspace')
    parser.add_argument('--engine', choices=['docker', 'podman'], default='docker')
    args = parser.parse_args()
    state = ROOT / '.validation'
    work = args.work
    if work is None:
        result = state / 'result.json'
        if result.exists():
            work = Path(json.loads(result.read_text())['work'])
        else:
            work = Path('/tmp/bitloom-kas-validation')
    work = work.expanduser().resolve()
    settings = Settings(state / 'profiles.json')
    existing = settings.profiles if settings.path.exists() else []
    profile = Profile(
        name='kas-integration', root=str(ROOT), mode='kas-container',
        kas_file='tests/integration/kas-minimal.yml', machine='qemux86-64', distro='poky',
        targets=['core-image-minimal'], environment={
            'KAS_WORK_DIR':str(work), 'KAS_CONTAINER_ENGINE':args.engine,
            'KAS_CONTAINER_IMAGE':KAS_IMAGE,
        },
    )
    settings.profiles = [p for p in existing if p.name != profile.name] + [profile]
    settings.active = 'kas-integration'
    settings.save()
    print(f'Profile: {settings.path}')
    print(f'Runtime workspace: {work} (container daemon filesystem)')
    print('Launch from the repository with the virtual environment activated:')
    print('bitloom --config .validation/profiles.json --state .validation')
    print('This only writes the profile; it does not start a build or change workspace ownership.')


if __name__ == '__main__':
    main()
