"""Evidence-based reports, portable snapshots and cooperative cache plans."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

SECRET = re.compile(r'(?i)(password|passwd|token|secret|credential|private.key|authorization)')
URL_AUTH = re.compile(r'(https?://)[^/\s@]+@')

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
    return redact(data)

def compare(before, after):
    lines=['BUILD SNAPSHOT COMPARISON']
    for section in ['configs','layers','manifests','artifacts','container_identity','metrics','package_sizes']:
        a,b=before.get(section),after.get(section)
        if a==b: lines.append(f'{section}: unchanged'); continue
        lines.append(f'{section}: changed')
        if section=='configs':
            import difflib
            for name in sorted(set(a or {})|set(b or {})):
                lines.extend(difflib.unified_diff((a or {}).get(name,'').splitlines(),(b or {}).get(name,'').splitlines(),fromfile='before/'+name,tofile='after/'+name,lineterm=''))
        else:
            lines.extend(['before: '+json.dumps(a,sort_keys=True),'after: '+json.dumps(b,sort_keys=True)])
    return '\n'.join(lines)

def diagnose(text):
    lines=text.splitlines(); evidence=[]
    patterns=[('fetch',r'(fetcher failure|unable to fetch|do_fetch.*failed)'),('patch',r'(patch.*failed|hunk.*failed|do_patch.*failed)'),('QA',r'(QA Issue|do_package_qa.*failed)'),('rootfs',r'(do_rootfs.*failed|unable to install packages)'),('compile',r'(error:|undefined reference|do_compile.*failed)')]
    category='unclassified'
    for i,line in enumerate(lines):
        if line.startswith('$ '): continue
        if re.search(r'(error:|ERROR:|fatal:|FAILED|Hunk.*FAILED)',line,re.I):
            evidence=lines[max(0,i-3):i+8]; break
    for name,pattern in patterns:
        if re.search(pattern,text,re.I): category=name; break
    suggestions={'fetch':'Check the failing URL, proxy/mirror settings and checksums; retry fetch before rebuilding.', 'patch':'Inspect the rejected hunk and source revision; refresh patches in a devtool workspace.', 'QA':'Inspect the named QA rule and package contents before changing ERROR_QA.', 'rootfs':'Inspect package manager output and runtime dependency conflicts.', 'compile':'Inspect the compiler command, include paths and first source diagnostic.', 'unclassified':'Open the reported task log; the build stream alone may omit the cause.'}
    paths=re.findall(r'Logfile of failure stored in:\s*(\S+)',text)
    return f'FAILURE DIAGNOSIS\nCategory: {category}\nReported task logs: '+(', '.join(paths) or 'none')+'\nFirst diagnostic context:\n'+'\n'.join(evidence or ['No diagnostic found.'])+'\nNext step: '+suggestions[category]

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
