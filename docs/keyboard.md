# Keyboard reference

Bitloom is fully usable without a mouse. Section keys work while a table, tree or log has focus; typing in a field never triggers them.

## Everywhere

| Key | Action |
| --- | --- |
| `1…9, 0` | Jump to a section (also Alt+number) |
| `[ / ]  F8 / F9` | Previous / next section |
| `Tab / Shift+Tab` | Move focus between fields, tables and logs |
| `/  or  Ctrl+W` | Focus the filter or search field of this section (nano: Where Is) |
| `Esc` | Leave a field and return to the section list |
| `Enter` | Open / select the highlighted row; run from a field |
| `↑ ↓  j / k` | Move down / up in tables, trees and logs |
| `Ctrl+Y / Ctrl+V` | Page up / page down (nano) |
| `t` | Edit the build target (when no section uses t) |
| `b` | Build the target (outside Recipes) |
| `P` | Switch profile |
| `F2` | Command center (every operation, filtered as you type) |
| `F3` | Refresh metadata, logs and diagnostics |
| `F4` | Edit profiles |
| `F5 / F6` | Stop / retry the selected job |
| `F7` | Themes |
| `F10` | Developer workbench |
| `Ctrl+L` | Search the build log |
| `Ctrl+P` | Command palette: sections, actions, operations |
| `?  F1  Ctrl+G` | This keyboard reference (nano: Get Help) |
| `Ctrl+Q / Ctrl+X` | Detach (service keeps running) / exit |

## 1 · Builds

| Key | Action |
| --- | --- |
| `s` | Stop |
| `r` | Retry |
| `e` | Errors |
| `p` | Pause |
| `x` | Export |
| `i` | Summary |
| `d` | Compare |
| `f` | Failed log |
| `c` | Console builds |

## 2 · Recipes

| Key | Action |
| --- | --- |
| `b` | Build |
| `m` | Modify |
| `l` | Layers |
| `n` | New file |
| `o` | Open |
| `t` | Tree |
| `c` | Studio |

## 3 · Task logs

| Key | Action |
| --- | --- |
| `o` | Open |
| `f` | Failed log |

## 4 · Environment

| Key | Action |
| --- | --- |
| `t` | Env/graph |
| `l` | Load |
| `r` | Resolve |
| `d` | Diff |
| `g` | Graph |
| `w` | Why |
| `h` | History |
| `a` | Audit |
| `o` | Report |
| `m` | Timings |

## 5 · Caches

| Key | Action |
| --- | --- |
| `s` | Scan |
| `t` | DL/sstate |
| `p` | Prune plan |
| `a` | Fetch all |
| `w` | tmp/work usage |

## 6 · Artifacts

| Key | Action |
| --- | --- |
| `o` | Open |
| `i` | Rootfs |
| `m` | Image matrix |
| `s` | SBOM quality |
| `v` | Vulnerabilities |

## 7 · Analysis

| Key | Action |
| --- | --- |
| `t` | Type |
| `a` | Analyze |
| `x` | Export |

## 8 · Developer

| Key | Action |
| --- | --- |
| `v` | View |
| `i` | Inspect |
| `o` | Open |
| `u` | Operation |
| `r` | Run |
| `c` | Capture |
| `d` | Compare |
| `n` | New layer |
| `l` | Clone |
| `h` | Devices |

## 9 · Configuration

| Key | Action |
| --- | --- |
| `l` | local.conf |
| `y` | bblayers |
| `e` | bitbake -e |
| `d` | devtool |
| `v` | Versions |
| `n` | Network |
| `s` | SBOM settings |
| `c` | CRA readiness |
| `w` | Projects |
| `o` | Notifications |

## Dialogs

| Key | Action |
| --- | --- |
| `Esc / Ctrl+X` | Close or cancel the dialog; in editors ^X asks before discarding changes |
| `Ctrl+O` | Write out: save files and profiles, confirm forms (Ctrl+S also works) |
| `Ctrl+W / Alt+W` | Editors: where is (search) / find next |
| `Ctrl+K / Ctrl+U` | Editors: cut the current line / uncut (paste) |
| `Ctrl+G` | Keyboard reference |
| `Enter` | Command center: queue the selected operation |
| `↑ / ↓` | Command center filter: choose the operation |
| `f / g / k` | Interruption dialog: finish, graceful stop, force |
