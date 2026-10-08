"""Local build service. The UI detaches without interrupting the service."""
from __future__ import annotations
import asyncio
import json
import hashlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from .models import Profile
from .runner import Runner, Job
from .store import Store

def encode(job):
    keys=['id','title','command','action_id','status','started','finished','code','progress','errors','failure_logs','cancel_requested','managed_container','graceful_requested','stop_confirmed','shutdown_message','active_recipe_tasks']
    return {**{k:getattr(job,k) for k in keys},'profile':job.profile.__dict__,'log':str(job.log),'at_risk':sorted(job.at_risk)}

def socket_path(state):
    # Unix sockets are unsupported on common WSL /mnt/c workspaces.
    directory=Path('/tmp')/f'bitloom-services-{os.getuid()}'
    directory.mkdir(mode=0o700,exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid():
        raise ValueError('Unsafe service socket directory')
    directory.chmod(0o700)
    identity=hashlib.sha256(str(Path(state).resolve()).encode()).hexdigest()[:32]
    return directory/(identity+'.sock')

def rpc(state, payload):
    sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); sock.settimeout(60 if payload.get("op") == "cancel" else 5)
    try:
        sock.connect(str(socket_path(state)))
        sock.sendall(json.dumps(payload).encode()+b'\n')
        data=b''
        while not data.endswith(b'\n'):
            chunk=sock.recv(65536)
            if not chunk: raise ValueError('Build service disconnected')
            data+=chunk
            if len(data)>16*1024*1024: raise ValueError('Service response too large')
        result=json.loads(data)
        if 'error' in result: raise ValueError(result['error'])
        return result
    finally: sock.close()

def ensure_service(state):
    state=Path(state).resolve(); state.mkdir(parents=True,exist_ok=True)
    try: rpc(state,{'op':'status'}); return
    except (OSError,ValueError): pass
    with (state/'service.log').open('ab') as log:
        subprocess.Popen([sys.executable,'-m','bitloom.daemon',str(state)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    for _ in range(100):
        try: rpc(state,{'op':'status'}); return
        except (OSError,ValueError): time.sleep(.05)
    raise ValueError('Build service did not start; inspect service.log')

async def serve(state):
    store=Store(state); runner=Runner(store,lambda job,line:None)
    path=socket_path(state)
    if path.exists(): path.unlink()
    stop=asyncio.Event()
    async def handle(reader,writer):
        try:
            import struct
            peer=writer.get_extra_info('socket').getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12)
            if struct.unpack('3i',peer)[1]!=os.getuid(): raise ValueError('Different user rejected')
            payload=json.loads(await asyncio.wait_for(reader.readline(),5)); op=payload['op']
            if op=='submit': result={'job':encode(runner.submit(Profile(**payload['profile']),payload['title'],payload['command'],payload.get('action_id','custom')))}
            elif op in ['cancel','graceful']:
                job=next(j for j in runner.jobs if j.id==payload['id'])
                await (runner.cancel(job) if op=='cancel' else runner.graceful_stop(job)); result={'job':encode(job)}
            elif op=='stop':
                if runner.active or any(j.status=='queued' for j in runner.jobs): raise ValueError('Stop jobs explicitly before stopping service')
                stop.set(); result={'stopped':True}
            elif op=='status': result={'pid':os.getpid(),'jobs':[encode(j) for j in runner.jobs],'active':runner.active.id if runner.active else None}
            else: raise ValueError('Unknown operation')
        except Exception as exc: result={'error':str(exc)}
        writer.write(json.dumps(result).encode()+b'\n'); await writer.drain(); writer.close(); await writer.wait_closed()
    server=await asyncio.start_unix_server(handle,path=str(path),limit=1024*1024)
    os.chmod(path,0o600)
    try:
        async with server: await stop.wait()
    finally:
        await runner.shutdown(); store.close(); path.unlink(missing_ok=True)

class RemoteRunner:
    def __init__(self,store,callback):
        self.store=store; self.callback=callback; self.jobs=[]; self.active=None; self.offsets={}; self.poller=None
    def update(self,data):
        byid={j.id:j for j in self.jobs}
        for raw in data['jobs']:
            raw=dict(raw); profile=Profile(**raw.pop('profile')); raw['log']=Path(raw['log']); raw['at_risk']=set(raw['at_risk']); raw['progress']=tuple(raw['progress'])
            job=byid.get(raw['id']) or Job(profile,raw['title'],raw['command'])
            changed=job.status!=raw['status'] or job not in self.jobs
            for k,v in raw.items(): setattr(job,k,v)
            job.profile=profile
            if job not in self.jobs: self.jobs.append(job)
            if changed: self.callback(job,None)
            if job.log.exists():
                with job.log.open() as f:
                    if job.id not in self.offsets:
                        f.seek(0, 2)
                        self.offsets[job.id] = f.tell()
                    f.seek(self.offsets[job.id])
                    for line in f: self.callback(job,line.rstrip())
                    self.offsets[job.id]=f.tell()
        self.active=next((j for j in self.jobs if j.id==data['active']),None)
    async def poll(self):
        while True:
            try: self.update(await asyncio.to_thread(rpc,self.store.directory,{'op':'status'}))
            except (OSError,ValueError): pass
            await asyncio.sleep(.5)
    def start(self): self.poller=asyncio.create_task(self.poll())
    def submit(self,profile,title,command,action_id='custom'):
        raw=rpc(self.store.directory,{'op':'submit','profile':profile.__dict__,'title':title,'command':command,'action_id':action_id})['job']
        self.update({'jobs':[raw],'active':self.active.id if self.active else None})
        return next(j for j in self.jobs if j.id==raw['id'])
    async def control(self, op, job):
        result = await asyncio.to_thread(rpc,self.store.directory,{'op':op,'id':job.id})
        self.update({'jobs':[result['job']], 'active':self.active.id if self.active and result['job']['status'] in {'running','cancelling'} else None})
    async def cancel(self,job): await self.control('cancel',job)
    async def graceful_stop(self,job): await self.control('graceful',job)
    async def shutdown(self):
        if self.poller:
            self.poller.cancel()
            try: await self.poller
            except asyncio.CancelledError: pass

if __name__=='__main__': asyncio.run(serve(Path(sys.argv[1]).resolve()))
