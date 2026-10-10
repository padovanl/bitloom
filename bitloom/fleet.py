"""Fleet status: probe every configured device at once (devices, not builds, run in parallel)."""
from __future__ import annotations

import asyncio
import json
import shutil
import time
from pathlib import Path

from .developer import board_command, load_devices


async def probe(device, timeout=15) -> dict:
    started = time.monotonic()
    try:
        argv = board_command(device, 'status')
    except ValueError as exc:
        return {'device': device['name'], 'status': 'unconfigured', 'detail': str(exc), 'seconds': 0}
    if not shutil.which(argv[0]):
        return {'device': device['name'], 'status': 'unavailable', 'detail': argv[0] + ' is not installed on this host', 'seconds': 0}
    process = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, stdin=asyncio.subprocess.DEVNULL)
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return {'device': device['name'], 'status': 'timeout', 'detail': f'no answer within {timeout}s', 'seconds': timeout}
    text = output.decode(errors='replace').strip().splitlines()
    return {'device': device['name'], 'status': 'online' if process.returncode == 0 else 'offline',
            'detail': (text[-1] if text else f'exit {process.returncode}')[:200], 'seconds': round(time.monotonic() - started, 1),
            'via': 'labgrid' if device.get('labgrid_place') else 'ssh'}


async def fleet_status(devices_file: Path, limit=16) -> list[dict]:
    devices = load_devices(devices_file)
    gate = asyncio.Semaphore(limit)

    async def bounded(device):
        async with gate:
            return await probe(device)
    return list(await asyncio.gather(*(bounded(device) for device in devices)))


def fleet_report(rows: list[dict]) -> str:
    if not rows:
        return 'No devices configured. Add them in Developer → Devices (devices.json in the state directory).'
    counts = {}
    for row in rows:
        counts[row['status']] = counts.get(row['status'], 0) + 1
    lines = ['Fleet status · ' + ' · '.join(f'{count} {status}' for status, count in sorted(counts.items())), '',
             f'{"DEVICE":24} {"STATUS":12} {"TIME":>6}  DETAIL']
    for row in sorted(rows, key=lambda r: (r['status'] != 'online', r['device'])):
        lines.append(f'{row["device"][:24]:24} {row["status"]:12} {row["seconds"]:>5}s  {row["detail"]}')
    lines += ['', 'SSH probes use BatchMode (no password prompts) and a 10 s connect timeout; labgrid places use labgrid-client show.']
    return '\n'.join(lines)


def main(state: Path) -> int:
    rows = asyncio.run(fleet_status(Path(state) / 'devices.json'))
    print(fleet_report(rows))
    (Path(state) / 'fleet-status.json').write_text(json.dumps(rows, indent=2))
    return 0 if rows and all(row['status'] == 'online' for row in rows) else 1
