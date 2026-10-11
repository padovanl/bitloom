import asyncio
import json
import sys
from pathlib import Path
import pytest
from bitloom.models import Profile
from bitloom.runtime import request
from bitloom.workflows import bundle, compare, diagnose, cache_plan
from bitloom.leases import BuildLease
from bitloom.daemon import ensure_service, rpc

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

def test_shared_cache_coordination(tmp_path):
    from bitloom.leases import CacheLease
    a=CacheLease(tmp_path); b=CacheLease(tmp_path); maintenance=CacheLease(tmp_path,exclusive=True)
    a.acquire(); b.acquire()
    try:
        with pytest.raises(ValueError,match='in use'): maintenance.acquire()
    finally: a.close(); b.close()
    with maintenance:
        with pytest.raises(ValueError,match='in use'): a.acquire()

@pytest.mark.asyncio
async def test_runtime_binary_export_is_exact_and_never_overwrites(tmp_path):
    from bitloom.runtime import download
    source=tmp_path/'artifact.bin'; source.write_bytes(bytes(range(256))*900)
    destination=tmp_path/'export.bin'; profile=Profile(root=str(tmp_path))
    result=await download(profile,str(source),destination)
    assert result['size']==source.stat().st_size
    assert destination.read_bytes()==source.read_bytes()
    with pytest.raises(ValueError,match='exists'): await download(profile,str(source),destination)
    assert not list(tmp_path.glob('*.part-*'))

def test_provenance_report_keeps_chain_and_owner_evidence():
    from bitloom.workflows import provenance_report
    text=provenance_report({'image':'minimal','query':'/bin/sh','owners':{'busybox':'busybox'},'sizes':{'busybox':100},'inclusion_paths':[['packagegroup-core-boot','busybox']],'direct_dependents':{'busybox':['packagegroup-core-boot']},'image_install':'packagegroup-core-boot','package_install':'packagegroup-core-boot','policy':'Evidence is bounded.'})
    assert 'packagegroup-core-boot → busybox' in text
    assert 'busybox → busybox · 100' in text

@pytest.mark.asyncio
async def test_signature_pairs_are_kept_in_their_task_variant(tmp_path):
    import os
    stamps=tmp_path/'build/tmp/stamps/arch/busybox/version'; stamps.mkdir(parents=True)
    first=stamps/'do_compile.sigdata.before'; second=stamps/'do_compile.sigdata.after'
    first.touch(); second.touch(); os.utime(first,(10,10)); os.utime(second,(20,20))
    (stamps/'do_install.sigdata.only-one').touch()
    tools=tmp_path/'bin'; tools.mkdir()
    binary=tools/'bitbake-diffsigs'; binary.write_text('#!/bin/sh\nprintf "Variable CFLAGS value changed\\n"\n'); binary.chmod(0o755)
    profile=Profile(root=str(tmp_path),environment={'PATH':str(tools)+':'+os.environ['PATH']})
    result=await request(profile,'signature-context',str(tmp_path/'build'),recipe='busybox')
    assert len(result['comparisons'])==1
    assert result['comparisons'][0]['before']==str(first)
    assert result['comparisons'][0]['after']==str(second)
    assert 'CFLAGS' in result['comparisons'][0]['evidence']

def test_snapshot_comparison_normalizes_manifest_timestamps():
    first={'manifests':{'/old/image.rootfs-20260101010101.manifest':'busybox arch 1.0'},'package_sizes':{'arch/busybox':100}}
    second={'manifests':{'/new/image.rootfs-20260202020202.manifest':'busybox arch 1.1'},'package_sizes':{'arch/busybox':120}}
    text=compare(first,second)
    assert '-busybox arch 1.0' in text and '+busybox arch 1.1' in text
    assert 'arch/busybox: 100 → 120' in text
    assert '202601' not in text

async def test_create_runtime_file_is_atomic_and_never_overwrites(tmp_path):
    profile=Profile(name='local',root=str(tmp_path))
    path=tmp_path/'new-layer'/'recipes-example'/'hello_1.0.bb'
    result=await request(profile,'create',str(path),text='SUMMARY = "Hello"\n')
    assert result['path']==str(path)
    assert path.read_text()=='SUMMARY = "Hello"\n'
    with pytest.raises(ValueError):
        await request(profile,'create',str(path),text='overwrite')
    assert path.read_text()=='SUMMARY = "Hello"\n'
    link=tmp_path/'dangling.bb'
    link.symlink_to(tmp_path/'missing.bb')
    with pytest.raises(ValueError):
        await request(profile,'create',str(link),text='overwrite')
    assert link.is_symlink() and not (tmp_path/'missing.bb').exists()


def test_diagnosis_points_at_root_causes():
    # Shapes taken from a real kas-container perl failure and common build failures.
    perl = ('WARNING: Setting ABSTRACT via file failed\nWriting Makefile for Perl::OSType\n==> Your Makefile has been rebuilt. <==\n'
            '==> Please rerun the make command.  <==\nfalse\nmake[2]: *** [Makefile:738: Makefile] Error 1\n'
            "ERROR: Task (/work/poky/meta/recipes-devtools/perl/perl_5.38.2.bb:do_compile) failed with exit code '1'\n")
    report = diagnose(perl)
    assert 'Category: race' in report and 'Your Makefile has been rebuilt' in report and 'Setting ABSTRACT' not in report
    assert 'perl_5.38.2.bb:do_compile' in report and 'Retry the task' in report
    oom = 'x86_64-poky-linux-g++: fatal error: Killed signal terminated program cc1plus\nmake: *** [all] Error 1\n'
    assert 'Category: resources' in diagnose(oom) and 'PARALLEL_MAKE' in diagnose(oom)
    fetch = 'WARNING: Failed to fetch URL https://x/y.tar.gz\nERROR: Fetcher failure: Unable to find revision\n'
    assert 'Category: fetch' in diagnose(fetch)
    assert 'Category: link' in diagnose('foo.o: undefined reference to `bar\'\ncollect2: error: ld returned 1 exit status\n')


def test_diagnosis_reads_kas_errors():
    log = ('2026-10-12 02:07:04 - INFO     - kas 4.8.1 started\n'
           '2026-10-12 02:07:17 - ERROR    - Provided tag "yocto-6.0.2" ("acfe02fa") does not match provided commit "178b3931" in repository "bitbake"\n')
    report = diagnose(log)
    assert 'Category: configuration' in report and 'Provided tag' in report and "refs/tags/TAG^{}" in report


def test_diagnosis_recognises_interrupted_builds():
    # From a real Wrynose build interrupted by a WSL restart: zero-byte objects in binutils' ld.
    log = ("2026-10-12 08:24:21 - ERROR    - ERROR: binutils-2.46.1-r0 do_compile: oe_runmake failed\n"
           "/usr/src/debug/glibc/2.43+git/csu/../sysdeps/x86_64/start.S:103:(.text+0x1b): undefined reference to `main'\n"
           "ldgram.y:395:(.text+0xf0c): undefined reference to `input_flags'\n"
           "2026-10-12 08:24:21 - ERROR    - ERROR: Task (/work/build/../openembedded-core/meta/recipes-devtools/binutils/binutils_2.46.bb:do_compile) failed with exit code '1'\n")
    report = diagnose(log)
    assert 'Category: interrupted' in report and 'bitbake -c clean binutils' in report
