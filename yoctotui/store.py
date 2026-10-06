from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.directory = directory
        self.db = sqlite3.connect(directory / "history.sqlite3")
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
            json.dumps({"profile": job.profile.__dict__, "action": job.action_id}),
        ))
        self.db.commit()

    def history(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM jobs ORDER BY started DESC LIMIT 500")]

    def close(self):
        self.db.close()
