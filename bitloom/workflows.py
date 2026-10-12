"""Evidence-based reports, portable snapshots and cooperative cache plans."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

SECRET = re.compile(r'(?i)(password|passwd|token|secret|credential|private.key|authorization|access.?key|api.?key|netrc)')
URL_AUTH = re.compile(r'((?:https?|ftp|git|ssh)://)[^/\s@]+@')

def redact(value):
    if isinstance(value, dict):
        return {k: '<redacted>' if SECRET.search(k) else redact(v) for k,v in value.items()}
    if isinstance(value, list): return [redact(v) for v in value]
    if isinstance(value, str):
        value = URL_AUTH.sub(r'\1<redacted>@', value)
        return '\n'.join('<redacted configuration line>' if SECRET.search(line) else line for line in value.split('\n'))
    return value

def bundle(profile, snapshot, image_identity=None):
    data = {'schema':1,'profile':profile.__dict__, 'snapshot':snapshot, 'container_identity':image_identity,
            'limitations':['Dirty repositories require separate patch export.', 'Redacted credentials must be supplied separately.', 'A tag without an image digest is not an exact container pin.']}
    safe_env = {'MACHINE','DISTRO','BB_NUMBER_THREADS','PARALLEL_MAKE','BB_ENV_PASSTHROUGH_ADDITIONS','KAS_WORK_DIR','KAS_BUILD_DIR','KAS_MACHINE','KAS_DISTRO','KAS_CONTAINER_ENGINE','KAS_CONTAINER_IMAGE','KAS_CLONE_DEPTH'}
    data['profile'] = dict(profile.__dict__)
    data['omitted_environment_keys'] = sorted(set(profile.environment) - safe_env)
    data['profile']['environment'] = {k:v for k,v in profile.environment.items() if k in safe_env}
    data['profile']['container_args'] = []
    if profile.container_args: data['limitations'].append('Custom container arguments omitted because they may contain credentials; reconfigure them separately.')
    return redact(data)

def compare(before, after):
    before = {**before.get('snapshot',before), 'container_identity':before.get('container_identity')}
    after = {**after.get('snapshot',after), 'container_identity':after.get('container_identity')}
    lines=['BUILD SNAPSHOT COMPARISON']
    def manifests(values):
        normalized={}
        for path,text in sorted((values or {}).items()):
            name=re.sub(r'-[0-9]{14}(?=\.manifest$)','',Path(path).name)
            normalized[name]=text
        return normalized
    for section in ['configs','layers','manifests','artifacts','container_identity','metrics','package_sizes']:
        a,b=before.get(section),after.get(section)
        if section=='manifests': a,b=manifests(a),manifests(b)
        if section=='layers': a={row['path']:row for row in a or []}; b={row['path']:row for row in b or []}
        if section=='artifacts': a={row['path']:row['size'] for row in a or []}; b={row['path']:row['size'] for row in b or []}
        if a==b: lines.append(f'{section}: unchanged'); continue
        lines.append(f'{section}: changed')
        if section in {'configs','manifests'}:
            import difflib
            for name in sorted(set(a or {})|set(b or {})):
                lines.extend(difflib.unified_diff((a or {}).get(name,'').splitlines(),(b or {}).get(name,'').splitlines(),fromfile='before/'+name,tofile='after/'+name,lineterm=''))
        elif isinstance(a,dict) and isinstance(b,dict):
            keys=[key for key in sorted(a.keys()|b.keys()) if a.get(key)!=b.get(key)]
            for key in keys[:1000]: lines.append(f'{key}: {json.dumps(a.get(key),sort_keys=True)} → {json.dumps(b.get(key),sort_keys=True)}')
            if len(keys)>1000: lines.append(f'{len(keys)-1000} additional changes omitted; inspect exported JSON')
        else: lines.extend(['before: '+json.dumps(a,sort_keys=True),'after: '+json.dumps(b,sort_keys=True)])
    return '\n'.join(lines)

# Known causes, most specific first: (category, pattern, explanation and next step).
KNOWN_CAUSES = [
    ('configuration', r'Provided tag .* does not match provided commit',
     'kas: the pinned commit is not the commit of the tag. For annotated tags pin the peeled commit: '
     "git ls-remote URL 'refs/tags/TAG^{}'."),
    ('configuration', r'(Validation against the schema failed|Could not find file .*\.ya?ml|unknown option|LAYERSERIES_COMPAT|is not compatible with the core layer)',
     'The kas or layer configuration is invalid for this release. Check the named file, the kas header version and LAYERSERIES_COMPAT.'),
    ('resources', r'(Killed signal terminated program|fatal error: Killed|virtual memory exhausted|Cannot allocate memory|out of memory)',
     'The compiler was killed, usually by the out-of-memory killer. Lower PARALLEL_MAKE / BB_NUMBER_THREADS for this recipe '
     '(PARALLEL_MAKE:pn-<recipe> = "-j4"), add swap or memory, then retry.'),
    ('stale SBOM', r"sbom-cve-check: error: \[Errno 2\] No such file or directory: '[^']*\.spdx\.json'",
     'The image SBOM was reused from an earlier build, under that build\'s IMAGE_NAME timestamp, while sbom-cve-check looks for '
     'the name of this run. Rebuild the SBOM in the same run: bitbake <image> -C create_image_sbom_spdx (or a kas build after '
     'cleaning the image: bitbake -c cleansstate <image>).'),
    ('resources', r'No space left on device', 'The disk is full. Free space (Caches → prune plan, rm_work) and retry.'),
    ('interrupted', r"(undefined reference to [`']main'|file truncated|file format not recognized|is truncated|unexpected end of file)",
     'Object files were left empty or truncated by an interrupted build (killed container, power loss, WSL or machine restart); '
     'make sees them as up to date. Clean the recipe and build again: {clean}. Downloads and sstate are kept.'),
    ('race', r'Your Makefile has been rebuilt|Please rerun the make command',
     'ExtUtils::MakeMaker regenerated a Makefile during a parallel build (timestamp race, common in perl). Retry the task; '
     'if it repeats, check for clock skew or files with future timestamps in the work directory.'),
    ('race', r'(Text file busy|Resource temporarily unavailable)', 'A transient resource conflict. Retry the task; if it repeats, reduce parallelism.'),
    ('pseudo', r'pseudo: (path mismatch|inode mismatch)|pseudo abort',
     'The pseudo database no longer matches the work directory (files changed outside BitBake). Clean the recipe (bitbake -c clean) and rebuild.'),
    ('fetch', r'(Fetcher failure|Unable to fetch URL|unable to fetch|do_fetch.*failed|Checksum mismatch|checksums? (?:do|does) not match)',
     'Check the URL, proxy and PREMIRRORS/MIRRORS, and the SRC_URI checksums; run the fetch task alone before rebuilding.'),
    ('patch', r'(Applying patch .* failed|Patch .* does not apply|Hunk #\d+ FAILED|do_patch.*failed)',
     'A patch no longer applies to this source revision. Refresh it in a devtool workspace (devtool modify, rebase, devtool update-recipe).'),
    ('metadata', r'(Nothing PROVIDES|Nothing RPROVIDES|ParseError|ExpansionError|was skipped: )',
     'A recipe or provider is missing, or metadata does not parse. Check layer configuration (bitbake-layers show-layers) and the named variable.'),
    ('QA', r'(QA Issue|do_package_qa.*failed)', 'A packaging QA rule failed. Read the named rule; fix the recipe rather than relaxing ERROR_QA.'),
    ('rootfs', r'(do_rootfs.*failed|unable to install packages|Could not invoke dnf|nothing provides)',
     'The image package set cannot be installed. Inspect runtime dependencies and package feeds in the rootfs log.'),
    ('link', r'(undefined reference to|ld: cannot find|collect2: error)', 'Linking failed: a library or symbol is missing. Check DEPENDS and the link flags.'),
    ('compile', r'(:\d+:\d+: error:|:\d+: error:|fatal error: [^K]|error: )', 'Inspect the first compiler error and its include paths.'),
]
ROOT_SIGNALS = re.compile(r'(sbom-cve-check: error:| - ERROR +- |:\d+(?::\d+)?: (?:fatal )?error:|undefined reference to|Killed signal|No space left|Your Makefile has been rebuilt|'
                          r'Fetcher failure|Hunk #\d+ FAILED|Nothing PROVIDES|QA Issue|pseudo abort|make(?:\[\d+\])?: \*\*\* )')


# Start-up chatter that BitBake and kas print before any task: never evidence of a failure.
BITBAKE_CHATTER = re.compile(
    r'^(?:\d{4}-\d\d-\d\d \d\d:\d\d:\d\d - INFO\s+- )?'   # kas prefixes every line it relays
    r'(?:kas [\d.]+ started|Repository \S+ already contains \S+ as commit|Repository \S+ (?:checked out|cloned)\b.*|'
    r'(?:Cloning|Updating|Fetching) repository \S+.*|'
    r'NOTE: Reconnecting to bitbake server\.*|Loading cache\.\.\.done\.|Loaded \d+ entries from dependency cache\.|'
    r'Parsing recipes\.\.\.done\.|Parsing of \d+ \.bb files complete.*|NOTE: Retrying server connection.*|'
    r'NOTE: Started PRServer.*|Summary: There (?:was|were) \d+ WARNING messages?\.?)$')


def diagnose(text):
    """Point at the root cause, not the first line that mentions failure."""
    lines = [line for line in text.splitlines() if not BITBAKE_CHATTER.match(line.strip())]
    category, advice = 'unclassified', 'Open the reported task log; the build stream alone may omit the cause.'
    for name, pattern, hint in KNOWN_CAUSES:
        if re.search(pattern, text):
            category, advice = name, hint
            break
    anchor = next((i for i, line in enumerate(lines) if not line.startswith('$ ') and 'WARNING:' not in line and ROOT_SIGNALS.search(line)), None)
    if anchor is None:
        anchor = next((i for i, line in enumerate(lines) if not line.startswith('$ ') and re.search(r'\b(ERROR:|FAILED|fatal:)', line)), None)
    # The first make "***" line follows its cause; show the lines leading up to it.
    before = 10 if anchor is not None and '***' in lines[anchor] else 3
    evidence = [line for line in lines[max(0, anchor - before):anchor + 6] if 'WARNING:' not in line] if anchor is not None else []
    paths = list(dict.fromkeys(re.findall(r'Logfile of failure stored in:\s*(\S+)', text)))
    failed = sorted(set(re.findall(r'Task \(?([^)\s]+)\)? failed', text)))
    recipes = sorted({re.sub(r'_[^_/]*\.bb$', '', Path(task.split(':')[0]).name).removesuffix('.bb') for task in failed}) or \
        sorted(set(re.findall(r'ERROR: ([a-z0-9][a-z0-9+.-]*?)-\d[^ ]* do_\w+:', text)))
    advice = advice.replace('{clean}', ' '.join(f'bitbake -c clean {name}' for name in recipes) or 'bitbake -c clean <recipe>')
    return ('FAILURE DIAGNOSIS\nCategory: ' + category + '\nFailed tasks: ' + (', '.join(failed) or 'not reported') +
            '\nReported task logs: ' + (', '.join(paths) or 'none') + '\nRoot-cause context:\n' +
            '\n'.join(line[:400] for line in evidence or ['No diagnostic found.']) + '\nNext step: ' + advice)


def preflight_report(data):
    items=[]
    for level,name,ok,detail in [
        ('BLOCK','Permissions',data['writable'],'build directory must be writable'),
        ('BLOCK','Free disk',data['available_bytes']>1024**3,f"{data['available_bytes']/1024**3:.1f} GiB available; 1 GiB minimum guard"),
        ('WARN','Disk headroom',data['available_bytes']>30*1024**3,'30 GiB advisory threshold; image requirements vary'),
        ('BLOCK','Inodes',data['available_inodes']>1000,f"{data['available_inodes']} available"),
    ]: items.append(f"{'PASS' if ok else level}: {name}: {detail}")
    items.extend(f"{'PASS' if present else 'WARN'}: {name}: {'present' if present else 'not initialized'}" for name,present in data['config'].items())
    items.append('Mirror reachability and layer compatibility require evaluated BitBake metadata; run environment and layer inspection before trusting this check.')
    return '\n'.join(items)

def cache_plan(cache: Path, stamps: Path):
    """Conservative signature reference plan; never delete artifacts with unknown references."""
    if not cache.is_dir() or not stamps.is_dir(): raise ValueError('Both cache and stamps directories must exist')
    references=set()
    for p in stamps.rglob('*'):
        references.update(re.findall(r'(?<![a-f0-9])[a-f0-9]{64}(?![a-f0-9])',p.name))
    entries=[]
    for p in cache.rglob('*'):
        if p.is_file() and not p.is_symlink():
            hashes=re.findall(r'(?<![a-f0-9])[a-f0-9]{64}(?![a-f0-9])',p.name)
            entries.append({'path':str(p),'size':p.stat().st_size,'classification':'referenced' if any(h in references for h in hashes) else 'unproven','sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.stat().st_size<2097152 else None})
        if len(entries)>=20000: break
    return {'cache':str(cache.resolve()),'stamps':str(stamps.resolve()),'reference_hashes':len(references),'entries':entries,'deletion_allowed':False,'reason':'Absence from one build stamps directory does not prove absence from other builders. Coordinate all users; use the Yocto release cache-management script for removal.'}


def provenance_report(data):
    lines = ["IMAGE: " + data['image'], "QUERY: " + data['query'], "", "PACKAGE → RECIPE · FILE BYTES"]
    for package, recipe in data['owners'].items():
        lines.append(f"{package} → {recipe or 'unknown'} · {data['sizes'].get(package, 'unavailable')}")
    if not data['owners']: lines.append("No file owner was found in runtime pkgdata.")
    lines += ["", "INCLUSION CHAINS"]
    lines += [" → ".join(path) for path in data['inclusion_paths']] or ["No inclusion chain found; inspect providers and package-manager decisions."]
    lines += ["", "DIRECT DEPENDENTS"]
    for package, deps in data['direct_dependents'].items(): lines.append(package + " ← " + (", ".join(deps) or "none recorded"))
    lines += ["", "IMAGE_INSTALL: " + (data.get('image_install') or "unavailable"), "PACKAGE_INSTALL: " + (data.get('package_install') or "unavailable"), "", data['policy']]
    return "\n".join(lines)
