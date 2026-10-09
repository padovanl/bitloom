"""Exercise force stop of one expendable, uniquely owned kas-container job.

Requires the profile prepared by tools/validate_developer.py. Does not interrupt
another job or build: the owned container only runs a READY marker and sleep.
"""
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bitloom.models import Settings
from bitloom.runner import Runner
from bitloom.store import Store


async def main():
    os.environ['PATH'] = str(ROOT / '.venv/bin') + os.pathsep + os.environ['PATH']
    profile = Settings(ROOT / '.developer-validation/profiles.json').profile
    ready = asyncio.Event()
    store = Store(ROOT / '.developer-validation' / ('stop-' + uuid.uuid4().hex[:8]))
    runner = Runner(store, lambda job, line: ready.set() if line == 'BITLOOM_STOP_READY' else None)
    job = runner.submit(profile, 'Owned kas-container stop validation',
                        ['python3','-c','import time; print("BITLOOM_STOP_READY",flush=True); time.sleep(300)'], 'shutdown-validation')
    try:
        await asyncio.wait_for(ready.wait(), 120)
        await runner.cancel(job)
        await runner.consumer
        saved = store.history()[0]
        metadata = json.loads(saved['metadata'])
        if not (job.status == 'cancelled' and job.stop_confirmed and metadata['stop_confirmed']):
            raise ValueError('Owned container shutdown was not confirmed: ' + str(job.log))
        evidence = {'job': job.id, 'status': job.status, 'stop_confirmed': job.stop_confirmed,
                    'observations': job.shutdown_evidence, 'log': str(job.log),
                    'scope': 'Real owned kas container with sleeping process; no BitBake task interruption claimed.'}
        (ROOT / '.developer-validation/stop-result.json').write_text(json.dumps(evidence, indent=2))
        print(json.dumps(evidence, indent=2))
    finally:
        await runner.shutdown(); store.close()


if __name__ == '__main__':
    asyncio.run(main())
