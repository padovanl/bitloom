"""Generate the complete command reference from the executable action catalog."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yoctotui.commands import ACTIONS
lines = ['# Command reference', '', 'All actions use the selected profile/runtime. Required inputs appear in the command dialog.', 'Commands may require classes or options supplied by your selected Yocto release.', '', '| ID | Group | Operation | Required input | Tool / arguments |', '| --- | --- | --- | --- | --- |']
for a in ACTIONS:
    tool = ' '.join([a.tool, *a.args]).strip() or 'custom argv'
    lines.append(f'| `{a.id}` | {a.group} | {a.title} | {", ".join(a.inputs) or "—"} | `{tool}` |')
lines += ['', 'Interactive commands hand off to a real terminal and are not stored as queued build logs.', 'Custom task adds `-c TASK` after the target. kas commands append the selected kas_file.', '', '## Action-specific requirements', '']
for a in ACTIONS:
    if a.help:
        lines.append(f'- **{a.title}:** {a.help}')
(ROOT / 'docs/commands.md').write_text('\n'.join(lines) + '\n')
print(f'Documented {len(ACTIONS)} actions')
