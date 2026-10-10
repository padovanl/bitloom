"""Create a TUI profile for the existing or a new isolated kas test workspace."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bitloom.models import Profile, Settings
from tools.releases import LEGACY_PROFILE, RELEASES, add_arguments, profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser, both=True)
    parser.add_argument('--work', type=Path, help='Scarthgap workspace; defaults to the recorded validation workspace')
    parser.add_argument('--wrynose-work', type=Path, help='Wrynose workspace; defaults to the recorded one or /tmp/bitloom-kas-wrynose')
    parser.add_argument('--engine', choices=['docker', 'podman'], default='docker')
    args = parser.parse_args()
    state = ROOT / '.validation'
    settings = Settings(state / 'profiles.json')
    existing = settings.own_profiles if settings.path.exists() else []
    # Profiles created before the release split keep their settings under the new name.
    for item in existing:
        if item.name == LEGACY_PROFILE:
            item.name = RELEASES['scarthgap']['profile']
    wanted = ['scarthgap', 'wrynose'] if args.release == 'both' else [args.release]
    created = []
    for release in wanted:
        spec = RELEASES[release]
        work = args.work if release == 'scarthgap' else args.wrynose_work
        if work is None:
            result = state / spec['result']
            work = Path(json.loads(result.read_text())['work']) if result.exists() else spec['work']
        created.append(profile(release, work, args.engine))
    names = {p.name for p in created}
    settings.profiles = [p for p in existing if p.name not in names] + created
    settings.active = created[0].name
    settings.save()
    print(f'Profiles: {settings.path}')
    for item, release in zip(created, wanted):
        print(f'  {item.name:15} {RELEASES[release]["tag"]:12} {item.environment["KAS_WORK_DIR"]}  ({RELEASES[release]["note"]})')
    print('Launch from the repository with the virtual environment activated:')
    print('bitloom --config .validation/profiles.json --state .validation   # P switches between the releases')
    print('This only writes profiles; it does not start a build or change workspace ownership.')


if __name__ == '__main__':
    main()
