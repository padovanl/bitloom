"""Advisory local coordination across Bitloom state directories."""
import fcntl
import hashlib
import os
from pathlib import Path

class BuildLease:
    def __init__(self, profile):
        identity=f'{profile.container_name}:{profile.build_path}'
        directory=Path('/tmp')/f'bitloom-leases-{os.getuid()}'
        directory.mkdir(mode=0o700,exist_ok=True)
        self.path=directory/(hashlib.sha256(identity.encode()).hexdigest()+'.lock')
        self.file=None
    def acquire(self):
        self.file=self.path.open('a+')
        try: fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            self.file.close(); self.file=None
            raise ValueError('Another Bitloom service owns this build directory; attach to that service')
        self.file.seek(0); self.file.truncate(); self.file.write(str(os.getpid())); self.file.flush()
    def close(self):
        if self.file: self.file.close(); self.file=None

class CacheLease:
    """Shared builder / exclusive maintenance lock on a host-visible cache."""
    def __init__(self, root, exclusive=False):
        self.root=Path(root); self.exclusive=exclusive; self.file=None
    def acquire(self):
        self.file=(self.root/'.bitloom-coordination.lock').open('a+')
        mode=fcntl.LOCK_EX if self.exclusive else fcntl.LOCK_SH
        try: fcntl.flock(self.file,mode|fcntl.LOCK_NB)
        except BlockingIOError:
            self.close()
            raise ValueError('Cache is in use by a cooperating builder or maintenance process')
    def close(self):
        if self.file: self.file.close(); self.file=None
    def __enter__(self): self.acquire(); return self
    def __exit__(self,*args): self.close()
