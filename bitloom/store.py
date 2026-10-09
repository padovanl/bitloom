from __future__ import annotations

import json
import fcntl
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, directory: Path, readonly=False):
        directory.mkdir(parents=True, exist_ok=True)
        self.directory = directory
        self.lock = None
        if readonly:
            self.db = sqlite3.connect(f"file:{directory.resolve() / 'history.sqlite3'}?mode=ro", uri=True)
            self.db.row_factory = sqlite3.Row
            return
        self.lock = (directory / "session.lock").open("a")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            if self.lock:
                self.lock.close()
            raise ValueError("Another Bitloom session is using this state directory") from exc
        self.db = sqlite3.connect(directory / "history.sqlite3")
        (directory / "history.sqlite3").chmod(0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, profile TEXT, title TEXT, argv TEXT, status TEXT,
            started TEXT, finished TEXT, code INTEGER, log TEXT, metadata TEXT)""")
        self.db.execute("UPDATE jobs SET status='interrupted' WHERE status IN ('running','queued','cancelling')")
        self.db.commit()

    def put(self, job) -> None:
        self.db.execute("INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)", (
            job.id, job.profile.name, job.title, json.dumps(job.command), job.status,
            job.started, job.finished, job.code, str(job.log),
            json.dumps({"profile": job.profile.__dict__, "action": job.action_id, "failure_logs": job.failure_logs, "progress": job.progress,
                        "shutdown_evidence": getattr(job, 'shutdown_evidence', {}), "stop_confirmed": job.stop_confirmed}),
        ))
        self.db.commit()

    def history(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM jobs ORDER BY started DESC LIMIT 500")]

    def close(self):
        self.db.close()
        if self.lock:
            self.lock.close()
