"""Bounded filesystem operations executed in the selected build runtime."""
from __future__ import annotations
import asyncio
import json
from .commands import invocation

AGENT = r'''
import os,sys,json,pathlib,hashlib,base64,shutil,subprocess,tempfile
request=json.loads(sys.argv[1]); op=request['op']; p=pathlib.Path(request.get('path','.'))
def git(path,*args):
 r=subprocess.run(['git','-C',str(path),*args],capture_output=True,text=True)
 return r.stdout.strip() if r.returncode==0 else None
if op=='read':
 if p.stat().st_size>2097152: raise ValueError('File exceeds 2 MiB preview limit')
 result={'path':str(p.resolve()),'text':p.read_text(errors='replace'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
elif op=='write':
 if p.is_symlink(): raise ValueError('Refusing a symlink edit')
 old=p.read_bytes()
 if hashlib.sha256(old).hexdigest()!=request['sha256']: raise ValueError('File changed since preview')
 data=request['text'].encode(); fd,name=tempfile.mkstemp(dir=p.parent)
 try:
  os.fchmod(fd,p.stat().st_mode & 0o777)
  with os.fdopen(fd,"wb") as stream: stream.write(data); stream.flush(); os.fsync(stream.fileno())
  backup=p.with_name(p.name+'.bitloom-backup-'+hashlib.sha256(old).hexdigest()[:12])
  if not backup.exists(): backup.write_bytes(old)
  os.replace(name,p)
 finally:
  if os.path.exists(name): os.unlink(name)
 result={'path':str(p),'backup':str(backup)}
elif op=='list':
 result=[]
 for f in sorted(p.iterdir()):
  if len(result)>=2000: break
  s=f.lstat(); result.append({'path':str(f),'directory':f.is_dir(),'symlink':f.is_symlink(),'size':s.st_size})
elif op=='preflight':
 existing=p
 while not existing.exists(): existing=existing.parent
 v=os.statvfs(existing); result={'path':str(p),'available_bytes':v.f_bavail*v.f_frsize,'available_inodes':v.f_favail,'writable':os.access(existing,os.W_OK),'exists':p.exists(),'mount_device':existing.stat().st_dev,'config':{n:(p/'conf'/n).exists() for n in ['local.conf','bblayers.conf']}}
elif op=='snapshot':
 result={'build':str(p.resolve()),'configs':{},'layers':[],'manifests':{},'artifacts':[],'package_sizes':{}}
 for f in (p/'conf').glob('*.conf'):
  if f.stat().st_size<2097152: result['configs'][f.name]=f.read_text(errors='replace')
 root=pathlib.Path(request.get('root',str(p.parent)))
 count=0
 for folder,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in ['tmp','downloads','sstate-cache','.venv','node_modules']]
  if '.git' in dirs or '.git' in files:
   dirs[:]=[d for d in dirs if d!='.git']; q=pathlib.Path(folder)
   result['layers'].append({'path':str(q),'commit':git(q,'rev-parse','HEAD'),'dirty':bool(git(q,'status','--porcelain')),'remote':git(q,'remote','get-url','origin')})
  count+=1
  if count>15000: result['scan_truncated']=True; break
 for f in (p/'tmp/deploy/images').glob('*/*.manifest'):
  if f.stat().st_size<2097152: result['manifests'][str(f)]=f.read_text(errors='replace')
 for f in (p/'tmp/deploy/images').glob('*/*'):
  if f.is_file() and not f.is_symlink(): result['artifacts'].append({'path':str(f),'size':f.stat().st_size})
 import re
 for f in (p/'tmp/pkgdata').glob('*/runtime/*'):
  if not f.is_file() or f.stat().st_size>2097152: continue
  match=re.search(r'^FILES_INFO:[^:]+: (.*)$',f.read_text(errors='replace'),re.M)
  if match:
   try: result['package_sizes'][f.parent.parent.name+'/'+f.name]=sum(json.loads(match.group(1)).values())
   except (ValueError,TypeError): pass
elif op=='provenance':
 import re,collections
 package=request['package']; image=request['image']
 evaluated=subprocess.run(['bitbake','-e',image],capture_output=True,text=True)
 if evaluated.returncode: raise ValueError(evaluated.stderr[-2000:])
 variables={}
 for line in evaluated.stdout.splitlines():
  match=re.match(r'^(?:export )?([A-Za-z0-9_:+.-]+)="(.*)"$',line)
  if match: variables[match[1]]=match[2]
 pkgdir=pathlib.Path(variables['PKGDATA_DIR'])/'runtime'; graph={}; owners={}; fileowners={}; sizes={}
 for f in pkgdir.iterdir():
  if not f.is_file() or f.stat().st_size>2097152: continue
  text=f.read_text(errors='replace'); pn=re.search(r'^PN: (.+)$',text,re.M)
  owners[f.name]=pn.group(1) if pn else None
  deps=[]
  for match in re.finditer(r'^R(?:DEPENDS|RECOMMENDS):[^:]+: (.*)$',text,re.M):
   deps.extend(re.sub(r'\([^)]*\)','',match.group(1)).split())
  graph[f.name]=deps
  match=re.search(r'^FILES_INFO:[^:]+: (.*)$',text,re.M)
  if match:
   try:
    files=json.loads(match.group(1)); sizes[f.name]=sum(files.values())
    if package.startswith('/') and package in files: fileowners[f.name]=package
   except (ValueError,TypeError): pass
 targets=list(fileowners) if package.startswith('/') else [package]
 roots=variables.get('PACKAGE_INSTALL',variables.get('IMAGE_INSTALL','')).split(); paths=[]
 for target in targets:
  queue=collections.deque([(root,[root]) for root in roots]); visited=set()
  while queue and len(visited)<20000:
   node,chain=queue.popleft()
   if node in visited: continue
   visited.add(node)
   if node==target: paths.append(chain); break
   queue.extend((dep,chain+[dep]) for dep in graph.get(node,[]))
 result={'image':image,'query':package,'owners':{k:owners.get(k) for k in targets},'sizes':{k:sizes.get(k) for k in targets},'inclusion_paths':paths,'direct_dependents':{target:[k for k,v in graph.items() if target in v] for target in targets},'image_install':variables.get('IMAGE_INSTALL'),'package_install':variables.get('PACKAGE_INSTALL'),'policy':'Edges include RDEPENDS and RRECOMMENDS; image features, exclusions and package-manager resolution can alter installation. No path is evidence of missing linkage, not proof of absence.'}
elif op=='devtool':
 result={'path':str(p),'commit':git(p,'rev-parse','HEAD'),'status':git(p,'status','--short'),'diff':git(p,'diff','--stat'),'commits':git(p,'log','-12','--oneline'),'patch_preview':git(p,'diff','--','.')}
else: raise ValueError('Unknown operation')
print('BITLOOM_JSON:'+json.dumps(result))
'''

async def request(profile, op: str, path: str, **values):
    inv = invocation(profile, ['python3', '-c', AGENT, json.dumps({'op':op,'path':path,**values})])
    proc = await asyncio.create_subprocess_exec(*inv.argv, cwd=inv.cwd, env=inv.env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, start_new_session=True)
    try:
        output, _ = await asyncio.wait_for(proc.communicate(), 120)
    except asyncio.TimeoutError:
        import os, signal
        os.killpg(proc.pid, signal.SIGTERM)
        await proc.wait()
        raise ValueError('Runtime request timed out')
    lines = output.decode(errors='replace').splitlines()
    for line in reversed(lines):
        if line.startswith('BITLOOM_JSON:') and proc.returncode == 0:
            return json.loads(line[len('BITLOOM_JSON:'):])
    raise ValueError('Runtime request failed: ' + '\n'.join(lines[-12:]))
