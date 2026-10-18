"""Generate the complete command reference from the executable action catalog."""
import os
import sys
from pathlib import Path
os.environ["BITLOOM_KEYS"] = "default"   # the documented keys are the defaults, whatever this machine customised
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bitloom.capabilities import CAPABILITIES
from bitloom.commands import ACTIONS
from bitloom.versions import INFO
lines = ['# Command reference', '', 'All actions use the selected profile/runtime. Required inputs appear in the command dialog.', 'Some operations need a capability of the project\'s Yocto release (see [Release capabilities](#release-capabilities)). Bitloom checks it in the project itself (the class in its layers, the tool in its BitBake) and falls back to the release number; where it is missing the TUI, the web dashboard and `--ci` refuse the operation, say why and name the one to use instead.', '', '| ID | Group | Operation | Required input | Tool / arguments | Needs |', '| --- | --- | --- | --- | --- | --- |']
for a in ACTIONS:
    tool = ' '.join([a.tool, *a.args]).strip() or 'custom argv'
    needs = ", ".join(f"[{n}](#release-capabilities)" for n in a.needs) or "any release"
    lines.append(f'| `{a.id}` | {a.group} | {a.title} | {", ".join(a.inputs) or "—"} | `{tool}` | {needs} |')
lines += ['', 'Interactive commands hand off to a real terminal and are not stored as queued build logs.', 'Custom task adds `-c TASK` after the target. kas commands append the selected kas_file.', '', '## Action-specific requirements', '']
for a in ACTIONS:
    if a.help:
        lines.append(f'- **{a.title}:** {a.help}')
def version(series):
    return f"{series} {INFO[series][0]}" if series in INFO else series


lines += ['', '## Release capabilities', '',
          'One registry (`bitloom/capabilities.py`) decides what the project\'s Yocto release can do. Operations, SBOM and CRA settings, '
          'the CRA checks and Studio all ask it. **Evidence** is looked for in the project first; the release window is used only when '
          'the layers or BitBake are not visible from Bitloom. Configuration shows the answer for the active project (web: *What this release can do*).', '',
          '| Capability | What it is | Releases | Evidence in the project | Otherwise use |', '| --- | --- | --- | --- | --- |']
for cap in CAPABILITIES.values():
    window = (f"{version(cap.since)}+" if cap.since and not cap.until else f"up to {version(cap.until)}" if cap.until and not cap.since
              else f"{version(cap.since)} to {version(cap.until)}" if cap.since else "where the tool exists")
    evidence = "; ".join(filter(None, [f"`{cap.bbclass}.bbclass` in its layers" if cap.bbclass else "", f"`{cap.tool}` in its BitBake" if cap.tool else "",
                                       "a bitbake-setup workspace" if cap.workspace else ""])) or "release only"
    lines.append(f"| `{cap.name}` | {cap.title}{' (' + cap.note + ')' if cap.note else ''} | {window} | {evidence} | {('`' + cap.instead + '`') if cap.instead else '—'} |")
(ROOT / 'docs/commands.md').write_text('\n'.join(lines) + '\n')
print(f'Documented {len(ACTIONS)} actions')
from bitloom.keys import reference_markdown
(ROOT / 'docs/keyboard.md').write_text(reference_markdown())
print('Documented the keyboard reference')
