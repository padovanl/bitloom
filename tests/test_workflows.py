import asyncio
import json
import sys
from pathlib import Path
import pytest
from yoctotui.models import Profile
from yoctotui.runtime import request
from yoctotui.workflows import bundle, compare, diagnose, cache_plan
from yoctotui.leases import BuildLease
from yoctotui.daemon import ensure_service, rpc

def test_credentials_and_config_are_redacted():
    p=Profile(environment={'MY_TOKEN':'sensitive','MACHINE':'qemu'},image='registry/image@sha256:abc')
    result=bundle(p,{'configs':{'local.conf':'PASSWORD = "secret"\nSRC_URI = "https://bob:pass@example.com/a"'}})
    serialized=json.dumps(result)
    assert 'sensitive' not in serialized and 'bob:pass' not in serialized and '"secret"' not in serialized
    assert result['profile']['environment']['MACHINE']=='qemu'

def test_evidence_reports_and_conservative_cache(tmp_path):
    assert 'Category: compile' in diagnose('a.c:4: error: missing declaration\nERROR: do_compile failed')
    assert 'before/local.conf' in compare({'configs':{'local.conf':'MACHINE="old"'}},{'configs':{'local.conf':'MACHINE="new"'}})
    cache=tmp_path/'cache'; stamps=tmp_path/'stamps'; cache.mkdir(); stamps.mkdir()
    signature='a'*64
    (cache/f'sstate-{signature}.tgz').write_text('data'); (stamps/f'x.sigdata.{signature}').touch()
    plan=cache_plan(cache,stamps)
    assert plan['entries'][0]['classification']=='referenced' and not plan['deletion_allowed']

def test_build_lease_conflict(tmp_path):
    profile=Profile(root=str(tmp_path)); a=BuildLease(profile); b=BuildLease(profile)
    a.acquire()
    try:
        with pytest.raises(ValueError,match='owns'): b.acquire()
    finally: a.close()
    b.acquire(); b.close()

@pytest.mark.asyncio
async def test_runtime_read_edit_conflict_and_snapshot(tmp_path):
    build=tmp_path/'build'; (build/'conf').mkdir(parents=True)
    path=build/'conf/local.conf'; path.write_text('MACHINE="qemu"')
    p=Profile(root=str(tmp_path))
    data=await request(p,'read',str(path))
    path.write_text('external edit')
    with pytest.raises(ValueError,match='changed'): await request(p,'write',str(path),sha256=data['sha256'],text='replacement')
    data=await request(p,'read',str(path))
    edit=await request(p,'write',str(path),sha256=data['sha256'],text='replacement')
    assert Path(edit['backup']).read_text()=='external edit'
    snapshot=await request(p,'snapshot',str(build))
    assert snapshot['configs']['local.conf']=='replacement'

@pytest.mark.asyncio
async def test_service_survives_client_disconnect(tmp_path):
    state=tmp_path/'state'
    await asyncio.to_thread(ensure_service,state)
    profile=Profile(root=str(tmp_path))
    result=await asyncio.to_thread(rpc,state,{'op':'submit','profile':profile.__dict__,'title':'persistent probe','command':[sys.executable,'-c','import time; print("before",flush=True); time.sleep(1); print("after")']})
    job=result['job']
    # Each RPC connection closes; the independent owner continues execution.
    for _ in range(60):
        status=await asyncio.to_thread(rpc,state,{'op':'status'})
        current=next(j for j in status['jobs'] if j['id']==job['id'])
        if current['status'] in {'success','failed'}: break
        await asyncio.sleep(.1)
    assert current['status']=='success'
    assert 'after' in Path(current['log']).read_text()
    await asyncio.to_thread(rpc,state,{'op':'stop'})
