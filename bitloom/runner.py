from __future__ import annotations

import asyncio
import copy
import os
import re
import signal
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .commands import invocation
from .models import Profile
from .store import Store

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
PROGRESS = re.compile(r"Running task (\d+) of (\d+)")
SETSCENE = re.compile(r"Running setscene task (\d+) of (\d+)")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Job:
    profile: Profile
    title: str
    command: list[str]
    action_id: str = "custom"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "queued"
    started: str = field(default_factory=now)
    finished: str = ""
    code: int | None = None
    log: Path = Path()
    process: asyncio.subprocess.Process | None = None
    progress: tuple[int, int] = (0, 0)
    setscene: tuple[int, int] = (0, 0)
    errors: list[str] = field(default_factory=list)
    failure_logs: list[str] = field(default_factory=list)
    cancel_requested: bool = False
    managed_container: str = ""
    graceful_requested: bool = False
    stop_confirmed: bool = False
    shutdown_message: bool = False
    at_risk: set[str] = field(default_factory=set)
    active_recipe_tasks: dict[str, str] = field(default_factory=dict)
    shutdown_evidence: dict = field(default_factory=dict)


class Runner:
    """Serial queue avoids concurrent BitBake servers modifying a build directory."""
    def __init__(self, store: Store, callback: Callable[[Job, str | None], None]):
        self.store = store
        self.callback = callback
        self.jobs: list[Job] = []
        self.queue: asyncio.Queue[Job] = asyncio.Queue()
        self.consumer: asyncio.Task | None = None
        self.active: Job | None = None

    def submit(self, profile: Profile, title: str, command: list[str], action_id="custom") -> Job:
        # Resolve and validate before putting anything in the queue.
        invocation(profile, command)
        job = Job(copy.deepcopy(profile), title, list(command), action_id)
        job.log = self.store.directory / "logs" / f"{job.id}.log"
        job.log.parent.mkdir(exist_ok=True)
        self.jobs.append(job)
        self.store.put(job)
        self.queue.put_nowait(job)
        if self.consumer is None or self.consumer.done():
            self.consumer = asyncio.create_task(self.consume())
        self.callback(job, None)
        return job

    async def consume(self):
        while not self.queue.empty():
            job = await self.queue.get()
            try:
                if job.cancel_requested:
                    continue
                self.active = job
                await self.execute(job)
            finally:
                self.active = None
                self.queue.task_done()

    async def execute(self, job: Job):
        job.log.touch(mode=0o600)
        job.status = "running"
        job.started = now()
        self.store.put(job)
        self.callback(job, None)
        from .leases import BuildLease, CacheLease
        lease = BuildLease(job.profile)
        cache_leases = []
        try:
            lease.acquire()
            from .inspectors import cache_path
            for kind in ("downloads", "sstate"):
                root = cache_path(job.profile, kind)
                if root.is_dir():
                    cache_lease = CacheLease(root)
                    cache_lease.acquire()
                    cache_leases.append(cache_lease)
            if (job.profile.mode == "container" and not job.profile.container_name) or job.profile.mode == "kas-container":
                job.managed_container = f"bitloom-{job.id}"
            inv = invocation(job.profile, job.command, job.managed_container)
            with job.log.open("w", buffering=1) as output:
                output.write(f"$ {inv.display}\n")
                job.process = await asyncio.create_subprocess_exec(
                    *inv.argv, cwd=inv.cwd, env=inv.env,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                    start_new_session=True, limit=4 * 1024 * 1024,
                )
                if job.cancel_requested:
                    os.killpg(job.process.pid, signal.SIGINT)
                while True:
                    raw = await job.process.stdout.readline()
                    if not raw:
                        break
                    line = ANSI.sub("", raw.decode(errors="replace")).rstrip()
                    output.write(line + "\n")
                    if "Execution was interrupted" in line:
                        job.shutdown_message = True
                    failure = re.search(r"Logfile of failure stored in:\s*(.+)$", line)
                    if failure and failure[1] not in job.failure_logs:
                        job.failure_logs.append(failure[1].strip())
                    self.track_tasks(job, line)
                    m = PROGRESS.search(line)
                    if m:
                        job.progress = (int(m[1]), int(m[2]))
                    m = SETSCENE.search(line)
                    if m:
                        job.setscene = (int(m[1]), int(m[2]))
                    if "ERROR:" in line or "FAILED" in line:
                        job.errors.append(line)
                        job.errors = job.errors[-200:]
                    self.callback(job, line)
                job.code = await job.process.wait()
                if job.cancel_requested and job.shutdown_message and job.code >= 0:
                    job.stop_confirmed = True
            job.status = "cancelled" if job.cancel_requested else ("success" if job.code == 0 else "failed")
        except Exception as exc:
            job.status = "failed"
            job.code = -1
            message = f"ERROR: {type(exc).__name__}: {exc}"
            if isinstance(exc, FileNotFoundError) and exc.filename:
                message = (f"ERROR: {exc.filename} not found. The command never started: for a host profile set its init script "
                           f"(oe-init-build-env) or start Bitloom from an initialised shell; otherwise pick a kas, container or "
                           f"wrapper runtime. Configuration (9) shows the runtime check.")
            with job.log.open("a") as output:
                output.write(message + "\n")
            job.errors.append(message)
            self.callback(job, message)
        finally:
            for cache_lease in cache_leases:
                cache_lease.close()
            lease.close()
            job.finished = now()
            self.store.put(job)
            if self.active is job:
                self.active = None
            self.callback(job, None)

    @staticmethod
    def track_tasks(job: Job, line: str):
        # Standard knotty non-TTY output: recipe PN-VERSION: task do_x: Started/Succeeded.
        match = re.search(r"recipe (\S+): task (\S+): (Started|Succeeded|Failed)", line)
        if match:
            recipe_version, task, state = match.groups()
            recipe = re.sub(r"-[0-9].*$", "", recipe_version)
            key = f"{recipe_version}:{task}"
            if state == "Started":
                job.active_recipe_tasks[key] = recipe
            elif state == "Succeeded":
                job.active_recipe_tasks.pop(key, None)
            job.at_risk = set(job.active_recipe_tasks.values())

    async def graceful_stop(self, job: Job):
        if job.status == "queued":
            await self.cancel(job)
            return
        if job.graceful_requested:
            return  # Never send an accidental second SIGINT.
        supported = job.profile.mode == "host" or (job.profile.mode == "container" and bool(job.managed_container))
        if not supported or job.command[0] != "bitbake":
            raise ValueError("Graceful signalling requires a host or managed-container BitBake client")
        if not job.process or job.process.returncode is not None:
            return
        # Only the client receives SIGINT. Signalling the process group would
        # interrupt workers instead of allowing BitBake's normal shutdown.
        job.cancel_requested = True
        job.graceful_requested = True
        job.status = "cancelling"
        job.shutdown_evidence = {'client_pid': job.process.pid, 'runtime': job.profile.mode,
                                 'owned_container': job.managed_container or None, 'server_shutdown': 'unconfirmed'}
        self.store.put(job)
        self.callback(job, None)
        try:
            if job.managed_container:
                control = await asyncio.create_subprocess_exec(job.profile.engine, "kill", "--signal", "SIGINT", job.managed_container, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
                output, _ = await control.communicate()
                if control.returncode:
                    self.callback(job, "ERROR: Container signal failed: " + output.decode(errors="replace"))
            else:
                os.kill(job.process.pid, signal.SIGINT)
        except ProcessLookupError:
            pass

    async def cancel(self, job: Job):
        if job.status not in {"running", "queued", "cancelling"}:
            return
        job.cancel_requested = True
        if job.process is None:
            job.status = "cancelled"
            job.finished = now()
            self.store.put(job)
            self.callback(job, None)
            return
        job.status = "cancelling"
        job.shutdown_evidence.update(client_pid=job.process.pid, runtime=job.profile.mode,
                                     owned_container=job.managed_container or None, server_shutdown='unconfirmed')
        self.store.put(job)
        self.callback(job, None)
        if job.managed_container:
            engine = job.profile.environment.get('KAS_CONTAINER_ENGINE', job.profile.engine) if job.profile.mode == 'kas-container' else job.profile.engine
            control = await asyncio.create_subprocess_exec(engine, "stop", "--time", "10", job.managed_container, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            output, _ = await control.communicate()
            if control.returncode == 0:
                job.stop_confirmed = True
                job.shutdown_evidence.update(container_stop_code=0, server_shutdown='owned container stopped; namespace workers terminated')
            else:
                job.shutdown_evidence.update(container_stop_code=control.returncode, output=output.decode(errors='replace')[-2000:])
            if control.returncode:
                self.callback(job, "WARNING: Container stop: " + output.decode(errors="replace"))
        elif job.profile.mode != "host":
            self.callback(job, "WARNING: Stopping runtime client; check external container/server before recovery.")
        if job.profile.mode == "host" and job.command[0] == "bitbake" and job.process.returncode is None:
            # BitBake's first interrupt drains tasks; the second asks its server
            # to stop executing tasks. The daemon may be outside our process group.
            try:
                if not job.graceful_requested:
                    os.kill(job.process.pid, signal.SIGINT)
                    await asyncio.sleep(0.3)
                if job.process.returncode is None:
                    os.kill(job.process.pid, signal.SIGINT)
                await asyncio.wait_for(job.process.wait(), 15)
            except (ProcessLookupError, asyncio.TimeoutError):
                pass
        # Escalate remaining client/children; external servers are not assumed stopped.
        for sig, timeout in ((signal.SIGINT, 8), (signal.SIGTERM, 4), (signal.SIGKILL, 2)):
            if job.process.returncode is not None:
                break
            try:
                os.killpg(job.process.pid, sig)
            except ProcessLookupError:
                break
            try:
                await asyncio.wait_for(job.process.wait(), timeout)
            except asyncio.TimeoutError:
                pass
        job.shutdown_evidence.update(client_exit_code=job.process.returncode, interruption_log_observed=job.shutdown_message,
                                     recovery_allowed=job.stop_confirmed)
        self.store.put(job)

    async def shutdown(self):
        for job in self.jobs:
            if job.status == "queued":
                await self.cancel(job)
        if self.active:
            await self.cancel(self.active)
        if self.consumer:
            await self.consumer
