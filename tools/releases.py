"""The two real validation workspaces: Scarthgap (5.0 LTS, poky) and Wrynose (6.0 LTS, split repositories)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bitloom.models import Profile

KAS_IMAGE = 'ghcr.io/siemens/kas/kas@sha256:fef6f850106a6823e65e133ed8157a847431dea4aa2de3a636c11f65e9977476'
RELEASES = {
    'scarthgap': {'profile': 'kas-scarthgap', 'kas_file': 'tests/integration/kas-minimal.yml', 'tag': 'yocto-5.0.8',
                  'result': 'result.json', 'work': Path('/tmp/bitloom-kas-validation'),
                  'note': 'Poky combined repository; SPDX 2.2 SBOMs by default; cve-check available'},
    'wrynose': {'profile': 'kas-wrynose', 'kas_file': 'tests/integration/kas-wrynose.yml', 'tag': 'yocto-6.0.2',
                'result': 'result-wrynose.json', 'work': Path('/tmp/bitloom-kas-wrynose'),
                'note': 'bitbake, openembedded-core and meta-yocto repositories; SPDX 3 SBOMs with VEX; sbom-cve-check'},
}
LEGACY_PROFILE = 'kas-integration'  # name used before the release split


def profile(release, work, engine='docker', clone_depth=False):
    spec = RELEASES[release]
    environment = {'KAS_WORK_DIR': str(Path(work).expanduser().resolve()), 'KAS_CONTAINER_ENGINE': engine, 'KAS_CONTAINER_IMAGE': KAS_IMAGE}
    if clone_depth:
        environment['KAS_CLONE_DEPTH'] = '1'
    return Profile(name=spec['profile'], root=str(ROOT), mode='kas-container', kas_file=spec['kas_file'], build_dir='build',
                   machine='qemux86-64', distro='poky', targets=['core-image-minimal'], environment=environment)


def add_arguments(parser, both=False):
    choices = ['scarthgap', 'wrynose', 'both'] if both else ['scarthgap', 'wrynose']
    parser.add_argument('--release', choices=choices, default='both' if both else 'scarthgap',
                        help='Yocto release workspace: scarthgap 5.0 LTS (poky) or wrynose 6.0 LTS (split repositories)')
