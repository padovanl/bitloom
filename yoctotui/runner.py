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
    errors: list[str] = field(default_factory=list)
    cancel_requested: bool = False


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
        job.status = "running"
        job.started = now()
        self.store.put(job)
        self.callback(job, None)
        try:
            inv = invocation(job.profile, job.command)
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
                    m = PROGRESS.search(line)
                    if m:
                        job.progress = (int(m[1]), int(m[2]))
                    if "ERROR:" in line or "FAILED" in line:
                        job.errors.append(line)
                        job.errors = job.errors[-200:]
                    self.callback(job, line)
                job.code = await job.process.wait()
            job.status = "cancelled" if job.cancel_requested else ("success" if job.code == 0 else "failed")
        except Exception as exc:
            job.status = "failed"
            job.code = -1
            message = f"ERROR: {type(exc).__name__}: {exc}"
            with job.log.open("a") as output:
                output.write(message + "\n")
            job.errors.append(message)
            self.callback(job, message)
        finally:
            job.finished = now()
            self.store.put(job)
            self.callback(job, None)

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
        self.store.put(job)
        self.callback(job, None)
        # Signal the process group, including children launched by BitBake.
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

    async def shutdown(self):
        for job in self.jobs:
            if job.status == "queued":
                await self.cancel(job)
        if self.active:
            await self.cancel(self.active)
        if self.consumer:
            await self.consumer
