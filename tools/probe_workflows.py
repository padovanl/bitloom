"""Verify new workflows and a reconnectable warm build in the real kas runtime."""
import asyncio
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bitloom.daemon import ensure_service,rpc
from bitloom.models import Profile
from bitloom.runtime import request
from bitloom.workflows import bundle,compare,preflight_report

async def main():
    evidence=json.loads((ROOT/'.validation/result.json').read_text())
    if not evidence.get('artifact_verified'): raise ValueError('Verified real build required')
    p=Profile(name='kas-scarthgap',root=str(ROOT),mode='kas-container',kas_file='tests/integration/kas-minimal.yml',targets=['core-image-minimal'],environment={'KAS_WORK_DIR':evidence['work'],'KAS_CONTAINER_ENGINE':'docker','KAS_CONTAINER_IMAGE':'ghcr.io/siemens/kas/kas@sha256:fef6f850106a6823e65e133ed8157a847431dea4aa2de3a636c11f65e9977476'})
    report={}
    report['preflight']=preflight_report(await request(p,'preflight','/work/build'))
    snapshot=await request(p,'snapshot','/work/build')
    report['snapshot']={'repositories':len(snapshot['layers']),'manifests':len(snapshot['manifests']),'package_sizes':len(snapshot['package_sizes']),'artifacts':len(snapshot['artifacts'])}
    report['provenance']=await request(p,'provenance','/work/build',package='/bin/sh',image='core-image-minimal')
    (ROOT/'.validation/reproducibility.json').write_text(json.dumps(bundle(p,snapshot,p.environment['KAS_CONTAINER_IMAGE']),indent=2))
    assert report['provenance']['owners']['busybox']=='busybox'
    assert ['packagegroup-core-boot','busybox'] in report['provenance']['inclusion_paths']
    assert report['snapshot']['package_sizes']>0
    assert 'unchanged' in compare(snapshot,snapshot)
    state=ROOT/'.validation/persistent'
    await asyncio.to_thread(ensure_service,state)
    jobs=[]
    for title,argv in [('Signature explanation',['bitbake','-S','printdiff','busybox']),('Persistent warm image build',['bitbake','core-image-minimal'])]:
        response=await asyncio.to_thread(rpc,state,{'op':'submit','profile':p.__dict__,'title':title,'command':argv})
        jobs.append(response['job']['id'])
    # Connections have closed. Independent service owns both queued operations.
    print('Disconnected from build service; reconnecting to observe results',flush=True)
    for _ in range(240):
        await asyncio.sleep(1)
        status=await asyncio.to_thread(rpc,state,{'op':'status'})
        completed=[j for j in status['jobs'] if j['id'] in jobs]
        if all(j['status'] in {'success','failed','cancelled'} for j in completed): break
    report['persistent_jobs']=[{'id':j['id'],'title':j['title'],'status':j['status'],'code':j['code'],'log':j['log']} for j in completed]
    (ROOT/'.validation/workflows.json').write_text(json.dumps(report,indent=2))
    await asyncio.to_thread(rpc,state,{'op':'stop'})
    print(json.dumps(report,indent=2),flush=True)
    if not all(j['status']=='success' for j in completed): raise ValueError('Real workflow probe failed')

if __name__=='__main__': asyncio.run(main())
