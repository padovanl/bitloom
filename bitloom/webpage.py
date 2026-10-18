"""Single-page web dashboard. Data is always inserted with textContent, never as HTML."""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bitloom dashboard</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22512%22 height=%22512%22 viewBox=%220 0 512 512%22 role=%22img%22 aria-labelledby=%22title description%22%3E %3Crect width=%22512%22 height=%22512%22 rx=%22112%22 fill=%22%230b1115%22/%3E %3Crect x=%2224%22 y=%2224%22 width=%22464%22 height=%22464%22 rx=%2292%22 fill=%22none%22 stroke=%22%23203e49%22 stroke-width=%224%22/%3E %3Cpath d=%22M176 112h92c64 0 108 29 108 77 0 30-18 52-47 64 40 10 63 34 63 71 0 52-46 84-118 84h-98%22 fill=%22none%22 stroke=%22%2384c9c0%22 stroke-width=%2232%22 stroke-linecap=%22round%22 stroke-linejoin=%22round%22/%3E %3Cpath d=%22M176 112v296%22 fill=%22none%22 stroke=%22%2381bdcf%22 stroke-width=%2232%22 stroke-linecap=%22round%22/%3E %3Cpath d=%22M104 160h162M104 256h202M104 352h174%22 fill=%22none%22 stroke=%22%2384c9c0%22 stroke-width=%2224%22 stroke-linecap=%22round%22/%3E %3Cpath d=%22M176 141v38M176 333v38%22 stroke=%22%230b1115%22 stroke-width=%2240%22/%3E %3Cpath d=%22M104 160h162M104 352h174%22 fill=%22none%22 stroke=%22%2384c9c0%22 stroke-width=%2224%22 stroke-linecap=%22round%22/%3E %3Cpath d=%22M158 256h36%22 stroke=%22%230b1115%22 stroke-width=%2232%22/%3E %3Cpath d=%22M176 233v46%22 stroke=%22%2381bdcf%22 stroke-width=%2232%22/%3E %3Ccircle cx=%22420%22 cy=%2296%22 r=%2212%22 fill=%22%23dfbe77%22/%3E %3C/svg%3E">
<style>
:root {
  --bg: #080d11; --bg2: #0b1218; --surface: #0f1920; --raised: #142029; --line: #1f2f3a; --line2: #2a3d4a;
  --fg: #d4e1e7; --muted: #7d919b; --accent: #84c9c0; --accent2: #81bdcf; --ink: #071014;
  --ok: #8fdbc3; --warn: #e5c27d; --err: #f08b87; --info: #8fb8f0;
  --glow: rgba(132, 201, 192, .18); --shadow: 0 10px 30px rgba(0, 0, 0, .35);
  --mono: "JetBrains Mono", "Fira Code", "DejaVu Sans Mono", ui-monospace, monospace;
  --sans: "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --ease: cubic-bezier(.2, .8, .2, 1);
  --code: #060a0e;
  --viz-1: #3987e5; --viz-2: #d95926; --viz-3: #199e70; --viz-4: #c98500; --viz-5: #d55181; --viz-6: #008300; --viz-other: #5c6b74;
  color-scheme: dark;
}
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    color-scheme: light; --code: #f3f1ea;
    --bg: #f4f2ec; --bg2: #efece4; --surface: #fbfaf6; --raised: #ffffff; --line: #e1dccf; --line2: #d3ccbb; --fg: #23292f; --muted: #66707a;
    --accent: #17786d; --accent2: #345b91; --ink: #ffffff; --ok: #1f7a4d; --warn: #8a5a00; --err: #b0302c; --info: #2f5f9e;
    --glow: rgba(23, 120, 109, .12); --shadow: 0 10px 30px rgba(60, 50, 20, .10);
    --viz-1: #2a78d6; --viz-2: #eb6834; --viz-3: #1baf7a; --viz-4: #eda100; --viz-5: #e87ba4; --viz-6: #008300; --viz-other: #a3a9ad;
  }
}
:root[data-theme="light"] {
  color-scheme: light; --code: #f3f1ea;
  --bg: #f4f2ec; --bg2: #efece4; --surface: #fbfaf6; --raised: #ffffff; --line: #e1dccf; --line2: #d3ccbb; --fg: #23292f; --muted: #66707a;
  --accent: #17786d; --accent2: #345b91; --ink: #ffffff; --ok: #1f7a4d; --warn: #8a5a00; --err: #b0302c; --info: #2f5f9e;
  --glow: rgba(23, 120, 109, .12); --shadow: 0 10px 30px rgba(60, 50, 20, .10);
  --viz-1: #2a78d6; --viz-2: #eb6834; --viz-3: #1baf7a; --viz-4: #eda100; --viz-5: #e87ba4; --viz-6: #008300; --viz-other: #a3a9ad;
}
/*THEMES*/
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; color: var(--fg); font: 14px/1.5 var(--sans); }
body { background: radial-gradient(1200px 600px at 85% -10%, var(--glow), transparent 60%), radial-gradient(900px 500px at -10% 110%, var(--glow), transparent 60%), var(--bg); background-attachment: fixed; }
button, input, select { font: inherit; color: inherit; }
kbd { font: 11px var(--mono); border: 1px solid var(--line2); border-bottom-width: 2px; border-radius: 5px; padding: 0 5px; color: var(--muted); background: var(--raised); }
.app { display: grid; grid-template-columns: 216px 1fr; grid-template-rows: auto 1fr; height: 100vh; }

/* Header */
header { grid-column: 1 / -1; position: sticky; top: 0; z-index: 55; display: flex; align-items: center; gap: 12px; padding: 10px 18px;
  background: color-mix(in srgb, var(--surface) 82%, transparent); backdrop-filter: blur(14px); border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.brand { display: flex; align-items: center; gap: 10px; font: 700 16px var(--mono); letter-spacing: .02em; }
.brand svg.logo { width: 30px; height: 30px; filter: drop-shadow(0 4px 10px var(--glow)); }
.brand svg.logo path[pathLength] { stroke-dasharray: 1; stroke-dashoffset: 1; animation: weave 1.3s var(--ease) forwards; }
.brand svg.logo path[pathLength]:nth-of-type(2) { animation-delay: .2s; } .brand svg.logo path[pathLength]:nth-of-type(3) { animation-delay: .4s; }
.brand svg.logo circle { animation: blink 3.2s ease-in-out infinite 1.5s; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }
@keyframes weave { to { stroke-dashoffset: 0; } }
.brand .word { background: linear-gradient(90deg, var(--accent), var(--accent2), var(--accent)); background-size: 200% 100%; -webkit-background-clip: text; background-clip: text; color: transparent; animation: sheen 8s linear infinite; }
@keyframes sheen { to { background-position: 200% 0; } }
.context { color: var(--muted); font: 12px var(--mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; flex: 1; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 2px 9px; border-radius: 999px; border: 1px solid var(--line2); font-size: 12px; color: var(--muted); background: var(--raised); white-space: nowrap; }
.chip.lts { color: var(--ok); border-color: color-mix(in srgb, var(--ok) 45%, transparent); }
select, input[type=text], input[type=search] { background: var(--bg2); border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; min-width: 0; transition: border-color .2s, box-shadow .2s; }
input:focus, select:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--glow); }
/* Form controls follow the theme: chevron dropdowns, tinted selection, accent checks, thin scrollbars. */
:root { accent-color: var(--accent); }
select:not([size]) {
  appearance: none; -webkit-appearance: none; padding-right: 30px; cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2384c9c0' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 10px center;
}
select:not([size]):hover { border-color: var(--line2); }
select option { background: var(--surface); color: var(--fg); }
select[size] { padding: 6px; }
select[size] option { padding: 5px 10px; border-radius: 6px; margin: 1px 0; }
select[size] option:hover { background: var(--raised); }
select[size] option:checked { background: var(--glow) linear-gradient(0deg, var(--glow), var(--glow)); color: var(--fg); font-weight: 600; box-shadow: inset 3px 0 0 var(--accent); }
select[size]:focus option:checked { background: linear-gradient(0deg, color-mix(in srgb, var(--accent) 28%, transparent), color-mix(in srgb, var(--accent) 28%, transparent)); }
select optgroup { color: var(--muted); font: 600 11px var(--sans); letter-spacing: .06em; text-transform: uppercase; }
select optgroup option { text-transform: none; letter-spacing: 0; font: 13px var(--sans); color: var(--fg); }
input[type=checkbox]:not(.switch input), input[type=radio] { width: 16px; height: 16px; cursor: pointer; }
* { scrollbar-width: thin; scrollbar-color: var(--line2) transparent; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: var(--line2); border-radius: 999px; border: 3px solid transparent; background-clip: padding-box; }
::-webkit-scrollbar-thumb:hover { background-color: var(--muted); }
::-webkit-scrollbar-track { background: transparent; }
::selection { background: color-mix(in srgb, var(--accent) 35%, transparent); }
button:focus-visible, .row:focus-visible, [tabindex]:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.btn { position: relative; overflow: hidden; background: var(--raised); border: 1px solid var(--line2); border-radius: 8px; padding: 6px 13px; cursor: pointer; white-space: nowrap; transition: transform .15s var(--ease), border-color .2s, background .2s; }
.btn:hover:not(:disabled) { border-color: var(--accent); transform: translateY(-1px); }
.btn:active:not(:disabled) { transform: translateY(0) scale(.98); }
.btn.primary { background: linear-gradient(135deg, var(--accent), var(--accent2)); color: var(--ink); border-color: transparent; font-weight: 650; box-shadow: 0 6px 18px var(--glow); }
.btn.warn { color: var(--warn); } .btn.danger { color: var(--err); }
.btn:disabled { opacity: .4; cursor: default; }
.btn kbd { margin-right: 5px; }
.btn .ripple { position: absolute; border-radius: 50%; transform: scale(0); background: currentColor; opacity: .25; animation: ripple .6s ease-out; pointer-events: none; }
@keyframes ripple { to { transform: scale(4); opacity: 0; } }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; background: var(--muted); }
.dot.ok { background: var(--ok); box-shadow: 0 0 0 0 var(--ok); animation: beacon 2.4s infinite; }
.dot.err { background: var(--err); } .dot.warn { background: var(--warn); }
@keyframes beacon { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--ok) 60%, transparent); } 70% { box-shadow: 0 0 0 7px transparent; } 100% { box-shadow: 0 0 0 0 transparent; } }

/* Navigation */
nav { background: color-mix(in srgb, var(--surface) 70%, transparent); border-right: 1px solid var(--line); padding: 14px 10px; display: flex; flex-direction: column; gap: 2px; }
nav .group { color: var(--muted); font-size: 10.5px; font-weight: 700; letter-spacing: .12em; padding: 12px 10px 4px; }
nav button { all: unset; position: relative; display: flex; gap: 10px; align-items: center; padding: 8px 10px; border-radius: 8px; cursor: pointer; color: var(--muted); transition: background .2s, color .2s; }
nav button:hover { background: var(--raised); color: var(--fg); }
nav button.active { background: linear-gradient(90deg, var(--glow), transparent); color: var(--fg); font-weight: 600; }
nav button.active::before { content: ""; position: absolute; left: -10px; top: 8px; bottom: 8px; width: 3px; border-radius: 3px; background: linear-gradient(var(--accent), var(--accent2)); }
nav button:focus-visible { outline: 2px solid var(--accent); }
nav .num { font: 11px var(--mono); color: var(--muted); width: 12px; }
nav .icon { width: 18px; text-align: center; }
nav .foot { margin-top: auto; padding: 12px 10px; color: var(--muted); font-size: 12px; line-height: 1.6; }
nav .foot .about { display: block; margin-top: 6px; font-size: 11px; opacity: .8; } nav .foot .about a { color: inherit; }
main { overflow: auto; padding: 18px 22px 40px; display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.view { display: flex; flex-direction: column; gap: 16px; animation: enter .35s var(--ease); }
.combo { position: relative; display: flex; align-items: center; }
.combo > input { padding-right: 30px; width: 100%; }
.combo-toggle { position: absolute; right: 4px; top: 50%; transform: translateY(-50%); width: 24px; height: 24px; display: grid; place-items: center; border: 0; border-radius: 6px; background: transparent; color: var(--muted); cursor: pointer; transition: color .15s, background .15s, transform .2s var(--ease); }
.combo-toggle:hover { color: var(--fg); background: var(--raised); }
.combo.open .combo-toggle { color: var(--accent); transform: translateY(-50%) rotate(180deg); }
.combo-list { position: absolute; top: calc(100% + 6px); left: 0; z-index: 40; width: 460px; max-width: calc(100vw - 24px); max-height: min(440px, 70vh); overflow: auto; padding: 6px; border: 1px solid var(--line2); border-radius: 12px; background: var(--surface); box-shadow: var(--shadow); animation: pop .16s var(--ease); }
@keyframes pop { from { opacity: 0; transform: translateY(-4px) scale(.98); } to { opacity: 1; transform: none; } }
.combo-group { padding: 8px 10px 4px; font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.combo-item { display: grid; grid-template-columns: 1fr auto; gap: 2px 10px; padding: 7px 10px; border-radius: 8px; cursor: pointer; scroll-margin: 6px; }
.combo-item .name { font: 13px var(--mono); color: var(--fg); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.combo-item .name mark { background: none; color: var(--accent); font-weight: 700; }
.combo-item .tags { display: flex; gap: 4px; justify-content: flex-end; }
.combo-item .sum { grid-column: 1 / -1; font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.combo-item.active { background: color-mix(in srgb, var(--accent) 14%, transparent); box-shadow: inset 2px 0 0 var(--accent); }
.combo-item[aria-selected="true"] .name::after { content: "  ✓"; color: var(--accent); }
.combo-foot { display: flex; gap: 12px; padding: 8px 10px 4px; margin-top: 4px; border-top: 1px solid var(--line); font-size: 11.5px; color: var(--muted); }
.combo-empty { padding: 14px 10px; color: var(--muted); font-size: 12.5px; }
.tag { font-size: 10.5px; padding: 1px 6px; border-radius: 999px; border: 1px solid var(--line2); color: var(--muted); white-space: nowrap; }
.tag.ok { color: var(--ok); border-color: color-mix(in srgb, var(--ok) 40%, transparent); }
.tag.accent { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 40%, transparent); }
#history .row { animation: none; }
#history .row.arrive { animation: arrive .45s var(--ease); }
@keyframes arrive { from { opacity: 0; transform: translateY(-14px); background: color-mix(in srgb, var(--accent) 18%, transparent); } to { opacity: 1; transform: none; } }
@keyframes enter { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

/* Cards */
.cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.card { position: relative; background: linear-gradient(180deg, var(--raised), var(--surface)); border: 1px solid var(--line); border-radius: 14px; padding: 13px 16px; min-width: 0; box-shadow: var(--shadow); transition: transform .25s var(--ease), border-color .25s; overflow: hidden; }
.card:hover { transform: translateY(-2px); border-color: var(--line2); }
.card h3 { margin: 0 0 6px; font-size: 10.5px; letter-spacing: .12em; color: var(--muted); text-transform: uppercase; font-weight: 700; }
.card .value { font: 700 20px var(--mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card .sub { color: var(--muted); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card .flex { display: flex; align-items: center; gap: 12px; }
.ring { width: 52px; height: 52px; flex: none; }
.ring circle { fill: none; stroke-width: 6; }
.ring .track { stroke: var(--line); }
.ring .bar { stroke: url(#ringGrad); stroke-linecap: round; transform: rotate(-90deg); transform-origin: 50% 50%; transition: stroke-dashoffset .8s var(--ease); }
.ring text { font: 700 13px var(--mono); fill: var(--fg); }
.spark { width: 100%; height: 34px; display: block; margin-top: 4px; }
.spark path.area { fill: url(#sparkGrad); } .spark path.line { fill: none; stroke: var(--accent2); stroke-width: 1.6; }
.meter { height: 6px; background: var(--line); border-radius: 4px; overflow: hidden; margin: 8px 0 4px; }
.meter > i { display: block; height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius: 4px; transition: width .8s var(--ease); }
.meter.hot > i { background: linear-gradient(90deg, var(--warn), var(--err)); }

/* Panels */
.panel { background: linear-gradient(180deg, var(--raised), var(--surface)); border: 1px solid var(--line); border-radius: 14px; min-width: 0; display: flex; flex-direction: column; box-shadow: var(--shadow); overflow: hidden; }
.panel > .head { display: flex; align-items: center; gap: 9px; padding: 11px 16px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.panel > .head h2 { margin: 0; font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); font-weight: 700; }
.split { display: grid; grid-template-columns: minmax(270px, 370px) minmax(0, 1fr); gap: 16px; flex: 1; min-height: 460px; }
.list { overflow: auto; flex: 1; }
.row { display: grid; grid-template-columns: 24px 1fr auto; gap: 8px; padding: 10px 16px; border-bottom: 1px solid var(--line); cursor: pointer; align-items: center; transition: background .2s; animation: enter .3s var(--ease); }
.row:hover { background: color-mix(in srgb, var(--raised) 70%, var(--glow)); }
.row.selected { background: linear-gradient(90deg, var(--glow), transparent 80%); box-shadow: inset 3px 0 var(--accent); }
.row .title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.row .meta, .meta { color: var(--muted); font: 12px var(--mono); }
.glyph { font-family: var(--mono); text-align: center; display: inline-grid; place-items: center; }
.spin { width: 14px; height: 14px; border-radius: 50%; border: 2px solid color-mix(in srgb, var(--accent) 30%, transparent); border-top-color: var(--accent); animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.s-success { color: var(--ok); } .s-failed { color: var(--err); } .s-running { color: var(--accent); }
.s-queued, .s-cancelling, .s-interrupted { color: var(--warn); } .s-cancelled, .s-unknown { color: var(--muted); }
.group-label { color: var(--muted); font-size: 10.5px; font-weight: 700; letter-spacing: .12em; padding: 14px 16px 6px; border-bottom: 1px solid var(--line); }
.detail-title { font-weight: 650; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 14ch; max-width: 60%; flex: 0 0 auto; }
#d-meta { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; flex: 1 1 0; } /* metadata gives way before the title */
#task-rows td:nth-child(2), #task-rows td:nth-child(3) { white-space: nowrap; }
#task-rows td:nth-child(2) { font-size: 12px; }
.panel > .head .btn { flex: none; }
@media (min-width: 901px) { .panel > .head:has(#d-title) { flex-wrap: nowrap; } }

/* Progress */
.prog { padding: 12px 16px 12px; border-bottom: 1px solid var(--line); display: grid; gap: 8px; }
.prog[hidden] { display: none; }
.prog-top { display: flex; align-items: baseline; gap: 10px; min-width: 0; }
.prog-text { color: var(--muted); font-size: 12.5px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.prog-text b { color: var(--fg); font: 600 13px var(--mono); font-variant-numeric: tabular-nums; }
.prog-text .sep { margin: 0 6px; opacity: .5; }
.prog-pct { margin-left: auto; font: 700 17px var(--mono); font-variant-numeric: tabular-nums; color: var(--fg); letter-spacing: -.5px; transition: color .3s; }
.prog.running .prog-pct { color: var(--accent); } .prog.success .prog-pct { color: var(--ok); } .prog.failed .prog-pct { color: var(--err); } .prog.cancelled .prog-pct, .prog.interrupted .prog-pct { color: var(--muted); }
.progress { position: relative; height: 6px; border-radius: 999px; background: color-mix(in srgb, var(--line) 80%, transparent); box-shadow: inset 0 1px 2px rgba(0,0,0,.25); }
.progress > i { position: absolute; inset: 0 auto 0 0; width: 0; border-radius: inherit; background: linear-gradient(90deg, var(--accent2), var(--accent)); transition: width .8s var(--ease), background .4s; overflow: hidden; }
.progress.running > i { box-shadow: 0 0 14px var(--glow), 0 0 4px color-mix(in srgb, var(--accent) 40%, transparent); }
.progress.running > i::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, rgba(255,255,255,.35), transparent); transform: translateX(-100%); animation: shimmer 2.2s var(--ease) infinite; }
/* The head of a running bar: where BitBake is now. */
.progress > b { position: absolute; top: 50%; width: 12px; height: 12px; margin: -6px 0 0 -6px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 25%, transparent), 0 0 14px var(--accent); opacity: 0; transition: left .8s var(--ease), opacity .3s; left: 0; }
.progress.running > b { opacity: 1; animation: head 1.6s ease-in-out infinite; }
.progress.failed > b { opacity: 1; background: var(--err); box-shadow: 0 0 0 3px color-mix(in srgb, var(--err) 25%, transparent); }
.progress.indeterminate { overflow: hidden; }
.progress.indeterminate > i { width: 28% !important; animation: slide 1.6s var(--ease) infinite; }
.progress.indeterminate > b { opacity: 0; }
.progress.success > i { background: linear-gradient(90deg, color-mix(in srgb, var(--ok) 70%, var(--accent2)), var(--ok)); }
.progress.failed > i { background: linear-gradient(90deg, color-mix(in srgb, var(--err) 55%, transparent), var(--err)); }
.progress.cancelled > i, .progress.interrupted > i { background: color-mix(in srgb, var(--muted) 60%, transparent); }
@keyframes shimmer { to { transform: translateX(100%); } }
@keyframes slide { from { left: -28%; } to { left: 100%; } }
@keyframes head { 50% { box-shadow: 0 0 0 6px color-mix(in srgb, var(--accent) 12%, transparent), 0 0 20px var(--accent); } }

/* Tabs */
.tabs { position: relative; display: flex; gap: 2px; padding: 0 10px; border-bottom: 1px solid var(--line); overflow-x: auto; }
.tabs button { all: unset; padding: 10px 13px; cursor: pointer; color: var(--muted); white-space: nowrap; transition: color .2s; }
.tabs button.active { color: var(--fg); }
.tabs button:focus-visible { outline: 2px solid var(--accent); }
.tabs .ink { position: absolute; bottom: -1px; height: 2px; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius: 2px; transition: left .3s var(--ease), width .3s var(--ease); }

/* Logs */
pre.log { position: relative; margin: 0; padding: 12px 16px; font: 12.5px/1.55 var(--mono); white-space: pre-wrap; word-break: break-word; overflow: auto; flex: 1; min-height: 320px; max-height: 64vh; background: var(--code); }
pre.log:empty::before { content: attr(data-empty); position: absolute; inset: 0; display: grid; place-items: center; padding: 24px;
  color: var(--muted); font: 13px/1.6 var(--sans); text-align: center; white-space: normal; }
pre.log span.new { animation: line .5s var(--ease); }
@keyframes line { from { opacity: 0; background: var(--glow); } to { opacity: 1; background: transparent; } }
pre.log .l-err { color: var(--err); } pre.log .l-warn { color: var(--warn); } pre.log .l-cmd { color: var(--accent); font-weight: 650; } pre.log .l-note { color: var(--muted); }
pre.log mark { background: var(--accent); color: var(--ink); border-radius: 3px; padding: 0 2px; }
.jump { position: absolute; right: 18px; bottom: 16px; opacity: 0; transform: translateY(8px); transition: .25s var(--ease); pointer-events: none; }
.jump.show { opacity: 1; transform: none; pointer-events: auto; }
.tools { display: flex; gap: 9px; align-items: center; padding: 9px 16px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.tools input[type=search] { flex: 1; min-width: 150px; }
label.check { display: flex; gap: 6px; align-items: center; color: var(--muted); font-size: 13px; cursor: pointer; user-select: none; }
.switch { position: relative; width: 34px; height: 19px; flex: none; }
.switch input { opacity: 0; width: 0; height: 0; }
.switch span { position: absolute; inset: 0; background: var(--line2); border-radius: 999px; transition: background .2s; cursor: pointer; }
.switch span::after { content: ""; position: absolute; left: 3px; top: 3px; width: 13px; height: 13px; border-radius: 50%; background: var(--fg); transition: transform .25s var(--ease); }
.switch input:checked + span { background: var(--accent); }
.switch input:checked + span::after { transform: translateX(15px); background: var(--ink); }
.switch input:focus-visible + span { outline: 2px solid var(--accent); outline-offset: 2px; }

/* Tables */
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; color: var(--muted); font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase; font-weight: 700; padding: 9px 16px; position: sticky; top: 0; background: var(--raised); border-bottom: 1px solid var(--line); z-index: 1; }
td { padding: 8px 16px; border-bottom: 1px solid var(--line); vertical-align: top; }
td.mono, .mono { font-family: var(--mono); font-size: 12px; word-break: break-all; }
tbody tr { animation: enter .3s var(--ease) both; }
tbody tr.clickable { cursor: pointer; } tbody tr.clickable:hover, tbody tr.selected { background: color-mix(in srgb, var(--raised) 70%, var(--glow)); }
.empty { color: var(--muted); padding: 28px 16px; text-align: center; }
.skeleton { height: 14px; border-radius: 6px; background: linear-gradient(90deg, var(--line) 25%, var(--line2) 50%, var(--line) 75%); background-size: 200% 100%; animation: skeleton 1.2s infinite; margin: 10px 16px; }
@keyframes skeleton { to { background-position: -200% 0; } }
.badge { display: inline-flex; align-items: center; gap: 5px; padding: 1px 8px; border-radius: 999px; font-size: 11.5px; font-weight: 650; border: 1px solid currentColor; }
.badge.ok { color: var(--ok); } .badge.warn { color: var(--warn); } .badge.err { color: var(--err); } .badge.info { color: var(--info); } .badge.muted { color: var(--muted); }

/* Recipes */
.recipes { grid-template-columns: minmax(220px, 290px) minmax(0, 1fr); }
#meta-search { min-width: 220px; }
.layer-item { display: grid; grid-template-columns: 1fr auto; gap: 2px 8px; padding: 9px 16px; border-bottom: 1px solid var(--line); cursor: pointer; transition: background .15s; }
.layer-item:hover { background: color-mix(in srgb, var(--raised) 70%, var(--glow)); }
.layer-item.selected { background: linear-gradient(90deg, var(--glow), transparent 85%); box-shadow: inset 3px 0 var(--accent); }
.layer-item .n { font-weight: 650; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.layer-item .c { font: 12px var(--mono); color: var(--muted); }
.layer-item .d { grid-column: 1 / -1; font-size: 11.5px; color: var(--muted); }
.layer-item.example .n { color: var(--muted); font-weight: 500; }
.layer-label { padding: 12px 16px 6px; font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.seg { display: inline-flex; border: 1px solid var(--line2); border-radius: 9px; overflow: hidden; background: var(--bg2); }
.seg button { all: unset; padding: 5px 10px; font-size: 12.5px; color: var(--muted); cursor: pointer; transition: color .15s, background .15s; white-space: nowrap; }
.seg button + button { border-left: 1px solid var(--line2); }
.seg button:hover { color: var(--fg); }
.seg button[aria-checked="true"] { background: color-mix(in srgb, var(--accent) 18%, transparent); color: var(--fg); }
.seg button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.seg button .k { font: 11px var(--mono); color: var(--muted); margin-left: 5px; }
details.folder { border-bottom: 1px solid var(--line); }
details.folder > summary { list-style: none; display: flex; align-items: center; gap: 10px; padding: 10px 16px; cursor: pointer; position: sticky; top: 0; z-index: 1; background: var(--surface); user-select: none; }
details.folder > summary::-webkit-details-marker { display: none; }
details.folder > summary::before { content: ""; width: 7px; height: 7px; border-right: 2px solid var(--muted); border-bottom: 2px solid var(--muted); transform: rotate(-45deg); transition: transform .2s var(--ease); flex: none; }
details.folder[open] > summary::before { transform: rotate(45deg); }
details.folder > summary:hover { background: var(--raised); }
details.folder > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
details.folder .fname { font: 600 13px var(--mono); }
details.folder .fcount { color: var(--muted); font: 12px var(--mono); }
details.folder .flayer { margin-left: auto; color: var(--muted); font-size: 12px; }
.recipe { display: grid; grid-template-columns: minmax(0, 1.2fr) 110px 74px minmax(0, 1fr) 190px; gap: 10px; align-items: center; padding: 7px 16px 7px 33px; border-top: 1px solid color-mix(in srgb, var(--line) 60%, transparent); font-size: 13px; }
.recipe:hover { background: color-mix(in srgb, var(--raised) 70%, var(--glow)); }
.recipe .rn { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recipe .rn mark { background: none; color: var(--accent); }
.recipe .rv { font: 12px var(--mono); color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recipe .rp { font: 11.5px var(--mono); color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; direction: rtl; text-align: left; }
.recipe .ra { display: flex; gap: 6px; justify-content: flex-end; opacity: 0; transition: opacity .15s; }
.recipe:hover .ra, .recipe:focus-within .ra { opacity: 1; }
.recipe .ra button { all: unset; font-size: 12px; padding: 2px 8px; border-radius: 6px; border: 1px solid var(--line2); color: var(--muted); cursor: pointer; }
.recipe .ra button:hover, .recipe .ra button:focus-visible { color: var(--fg); border-color: var(--accent); }
@media (max-width: 760px) { #meta-search { min-width: 0; } .seg { max-width: 100%; overflow-x: auto; scrollbar-width: none; } .recipe { grid-template-columns: minmax(0, 1fr) auto; padding-left: 26px; } .recipe .rv, .recipe .rp { display: none; } .recipe .ra { opacity: 1; } .recipes .layers .list { max-height: 220px; } }

/* Image explorer */
.img-top .head .who { display: flex; gap: 8px; flex: 1 1 360px; max-width: 520px; }
.img-top .head .who input { flex: 1; }
#img-pick { width: auto; max-width: 360px; }
.img-stats { display: flex; gap: 28px; padding: 14px 16px 4px; flex-wrap: wrap; }
.img-stats div { display: grid; } .img-stats b { font: 700 20px var(--mono); } .img-stats span { color: var(--muted); font-size: 12px; }
.img-charts { display: grid; grid-template-columns: 1.4fr 1fr; gap: 24px; padding: 8px 16px 16px; }
.img-charts h4 { margin: 6px 0 8px; font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.bars { display: grid; gap: 5px; }
.bar-row { all: unset; display: grid; grid-template-columns: minmax(0, 220px) 1fr 74px; gap: 10px; align-items: center; font-size: 12.5px; cursor: pointer; padding: 2px 4px; border-radius: 6px; }
.bar-row:hover, .bar-row:focus-visible { background: var(--raised); }
.bar-row .n { font-family: var(--mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .bar-row .n small { color: var(--muted); margin-left: 6px; }
.bar-row .b { height: 8px; border-radius: 999px; background: linear-gradient(90deg, var(--accent2), var(--accent)); min-width: 2px; transform-origin: left; animation: grow .6s var(--ease); }
.bar-row .s { text-align: right; font: 12px var(--mono); color: var(--muted); }
@keyframes grow { from { transform: scaleX(0); } }
.img-split { grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); height: calc(100vh - 120px); min-height: 460px; }
.img-split > .panel { min-height: 0; } .img-split .list { overflow: auto; }
.img-crumbs { display: flex; gap: 4px; align-items: center; font: 12.5px var(--mono); flex-wrap: wrap; }
.img-crumbs button { all: unset; cursor: pointer; padding: 1px 4px; border-radius: 4px; color: var(--muted); } .img-crumbs button:hover, .img-crumbs button:focus-visible { color: var(--fg); background: var(--raised); }
.img-crumbs button:last-child { color: var(--fg); font-weight: 650; }
.ent { display: grid; grid-template-columns: 20px minmax(0, 1fr) 110px 76px minmax(0, 170px); gap: 10px; align-items: center; padding: 6px 16px; border-bottom: 1px solid color-mix(in srgb, var(--line) 60%, transparent); cursor: pointer; font-size: 13px; }
.ent:hover, .ent:focus-visible { background: color-mix(in srgb, var(--raised) 70%, var(--glow)); outline: none; }
.ent.selected { background: linear-gradient(90deg, var(--glow), transparent 85%); box-shadow: inset 3px 0 var(--accent); }
.ent .i { color: var(--muted); text-align: center; } .ent.dir .i { color: var(--accent); }
.ent .n { font-family: var(--mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .ent.dir .n { font-weight: 650; } .ent .n small { color: var(--muted); }
.ent .w { height: 5px; border-radius: 999px; background: color-mix(in srgb, var(--accent) 55%, transparent); justify-self: start; min-width: 1px; }
.ent .s { text-align: right; font: 12px var(--mono); color: var(--muted); }
.ent .p { font: 12px var(--mono); color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.img-detail { overflow: auto; }
.img-detail .sec { padding: 14px 16px; border-bottom: 1px solid var(--line); display: grid; gap: 8px; }
.img-detail h3 { margin: 0; font: 650 15px var(--mono); word-break: break-all; }
.img-detail dl { display: grid; grid-template-columns: max-content 1fr; gap: 5px 14px; margin: 0; font-size: 13px; } .img-detail dt { color: var(--muted); } .img-detail dd { margin: 0; font-family: var(--mono); font-size: 12.5px; word-break: break-all; }
.img-detail .advice { padding: 10px 12px; border-radius: 10px; background: color-mix(in srgb, var(--accent) 10%, transparent); border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent); font-size: 13px; line-height: 1.5; }
.img-detail .actions { display: flex; gap: 8px; flex-wrap: wrap; }
.img-detail pre { margin: 0; max-height: 360px; overflow: auto; padding: 12px 16px; background: var(--code); font: 12px/1.55 var(--mono); white-space: pre; }
.who-result { display: grid; gap: 6px; padding: 12px 16px; border-bottom: 1px solid var(--line); }
@media (max-width: 1000px) { .img-charts, .img-split { grid-template-columns: 1fr; } .ent { grid-template-columns: 20px minmax(0, 1fr) 76px; } .ent .w, .ent .p { display: none; } }

.caps { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 1px; background: var(--line); }
.cap { display: grid; grid-template-columns: 22px 1fr; gap: 8px; padding: 9px 14px; background: var(--surface); align-items: start; }
.cap .mark { font: 700 13px var(--mono); text-align: center; line-height: 1.5; } .cap.ok .mark { color: var(--ok); } .cap.no .mark { color: var(--muted); } .cap.unknown .mark { color: var(--warn); }
.cap .t { display: grid; gap: 2px; min-width: 0; } .cap b { font-weight: 600; font-size: 13px; } .cap small { color: var(--muted); font-size: 12px; line-height: 1.4; }
.cap.no b { color: var(--muted); }

/* Best practices */
.pr-hero { display: flex; align-items: center; gap: 16px; padding: 14px 18px; flex-wrap: wrap; }
.big-ring { width: 64px; height: 64px; } .big-ring text { font: 600 13px var(--mono); fill: var(--fg); }
.pr-sum .big { font: 650 20px var(--sans); } .pr-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; } #pr-format { width: auto; }
.pr-filter { display: flex; gap: 12px; align-items: center; padding: 0 18px 12px; flex-wrap: wrap; }
.pr-groups { display: grid; gap: 12px; }
.pr-group > .head h2 .n { color: var(--muted); font-weight: 500; margin-left: 6px; letter-spacing: 0; }
details.rule { border-top: 1px solid var(--line); }
details.rule > summary { list-style: none; display: grid; grid-template-columns: 22px minmax(0, 1fr) auto auto auto; gap: 12px; align-items: center; padding: 9px 14px; cursor: pointer; }
details.rule > summary::-webkit-details-marker { display: none; }
details.rule > summary:hover { background: color-mix(in srgb, var(--raised) 70%, var(--glow)); }
details.rule .mark { font: 700 13px var(--mono); text-align: center; }
.rule.pass .mark { color: var(--ok); } .rule.fail.error .mark { color: var(--err); } .rule.fail.warning .mark { color: var(--warn); } .rule.fail.info .mark { color: var(--info); } .rule.na .mark, .rule.off .mark { color: var(--muted); }
.rule.off .t, .rule.na .t { color: var(--muted); }
.rule .t { min-width: 0; } .rule .t small { color: var(--muted); margin-left: 8px; font-size: 12px; }
.rule .count { font: 12px var(--mono); color: var(--muted); white-space: nowrap; }
.rule select.sev { width: auto; padding: 2px 26px 2px 8px; font-size: 12px; }
.rule .body { padding: 2px 14px 14px 48px; display: grid; gap: 8px; font-size: 13px; line-height: 1.5; }
.rule .body .why { color: var(--muted); } .rule .body .fix b { color: var(--accent); font-weight: 600; }
.rule .findings { margin: 0; padding: 8px 12px; list-style: none; background: var(--code); border-radius: 8px; font: 12px/1.6 var(--mono); max-height: 260px; overflow: auto; }
.rule .findings span { color: var(--muted); }
.rule .body .row-actions { display: flex; gap: 8px; }
#pr-dialog { width: min(720px, 94vw); border: 1px solid var(--line2); border-radius: 12px; background: var(--surface); color: var(--fg); padding: 0; box-shadow: var(--shadow); }
#pr-dialog::backdrop { background: rgba(0, 0, 0, .55); }
.pr-form { padding: 18px 20px; display: grid; gap: 10px; } .pr-form h3 { margin: 0; }
.pr-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 14px; } .pr-grid label { display: grid; gap: 4px; font-size: 12.5px; color: var(--muted); } .pr-grid .wide { grid-column: 1 / -1; }
.pr-grid input, .pr-grid select { width: 100%; color: var(--fg); }
.pr-form .err { color: var(--err); font-size: 13px; min-height: 1.2em; }
.pr-form-actions { display: flex; gap: 8px; }
#img-mode { margin-right: 10px; } #img-mode button { padding: 3px 10px; }
/* Image insights: thin marks, values in text ink, one hue for magnitude, categorical only for layers */
.ins { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 14px; align-items: start; }
.ins .panel { margin: 0; } .ins .wide { grid-column: 1 / -1; }
.ins .card-body { padding: 12px 16px 16px; } .ins h3 { margin: 0; font-size: 14px; } .ins .sub { color: var(--muted); font-size: 12.5px; margin: 2px 0 10px; }
.kpis { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 1px; background: var(--line); border-radius: 12px; overflow: hidden; }
.kpi { background: var(--surface); padding: 14px 16px; } .kpi b { display: block; font: 600 22px/1.2 var(--sans); font-variant-numeric: tabular-nums; } .kpi span { color: var(--muted); font-size: 12.5px; }
.kpi.alert b { color: var(--warn); }
.stack { display: flex; gap: 2px; height: 22px; margin: 6px 0 12px; } .stack > span { border-radius: 4px; min-width: 3px; }
.legend { display: grid; gap: 4px; } .legend .li { display: grid; grid-template-columns: 12px minmax(0, 1fr) auto auto; gap: 8px; align-items: center; font-size: 13px; padding: 2px 0; }
.legend .sw { width: 10px; height: 10px; border-radius: 3px; } .legend .v { color: var(--muted); font-variant-numeric: tabular-nums; text-align: right; } .legend .tag { font-size: 11px; color: var(--accent); border: 1px solid var(--accent); border-radius: 999px; padding: 0 6px; }
.hbars { display: grid; gap: 3px; } .hbar { display: grid; grid-template-columns: minmax(0, 190px) minmax(0, 1fr) auto; gap: 10px; align-items: center; font-size: 13px; padding: 3px 4px; border-radius: 6px; border: 0; background: none; color: inherit; text-align: left; cursor: default; }
.hbar.link { cursor: pointer; } .hbar.link:hover, .hbar.link:focus-visible { background: var(--raised); outline: none; }
.hbar .n { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .hbar .n small { color: var(--muted); margin-left: 6px; }
.hbar .t { height: 10px; } .hbar .b { display: block; height: 10px; border-radius: 0 4px 4px 0; background: var(--viz-1); min-width: 2px; }
.hbar .b.other { background: var(--viz-other); } .hbar .v { color: var(--muted); font-variant-numeric: tabular-nums; font-size: 12.5px; white-space: nowrap; }
.ports { width: 100%; border-collapse: collapse; font-size: 13px; } .ports th { text-align: left; color: var(--muted); font-weight: 500; font-size: 12px; padding: 4px 8px; border-bottom: 1px solid var(--line); }
.ports td { padding: 6px 8px; border-bottom: 1px solid var(--line); } .ports .num { font-family: var(--mono); }
.finding { display: grid; grid-template-columns: 18px minmax(0, 1fr); gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
.finding .ic { font-weight: 700; } .finding.error .ic { color: var(--err); } .finding.warning .ic { color: var(--warn); } .finding.info .ic { color: var(--info); } .finding.ok .ic { color: var(--ok); }
.finding small { display: block; color: var(--muted); }
.theme-pick { position: relative; }
.theme-menu { position: absolute; right: 0; top: calc(100% + 6px); z-index: 1000; width: 260px; padding: 6px; background: var(--raised); border: 1px solid var(--line2); border-radius: 12px; box-shadow: var(--shadow); animation: lang-in .12s var(--ease); }
.theme-menu .grp { font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); padding: 8px 8px 4px; }
.theme-menu button { all: unset; box-sizing: border-box; display: grid; grid-template-columns: 34px 1fr auto; gap: 10px; align-items: center; width: 100%; padding: 6px 8px; border-radius: 8px; cursor: pointer; font-size: 13px; }
.theme-menu button:hover, .theme-menu button:focus-visible { background: color-mix(in srgb, var(--fg) 7%, transparent); }
.theme-menu button[aria-checked="true"] { background: color-mix(in srgb, var(--accent) 16%, transparent); } .theme-menu button[aria-checked="true"]::after { content: "✓"; color: var(--accent); }
.theme-menu .sw { display: flex; height: 18px; border-radius: 5px; overflow: hidden; border: 1px solid var(--line2); } .theme-menu .sw span { flex: 1; }
#ins-tip { position: fixed; z-index: 60; pointer-events: none; background: var(--raised); border: 1px solid var(--line2); border-radius: 8px; padding: 6px 10px; font-size: 12.5px; box-shadow: var(--shadow); max-width: 340px; }
@media (max-width: 900px) { .ins { grid-template-columns: 1fr; } .kpis { grid-template-columns: repeat(3, minmax(0, 1fr)); } .hbar { grid-template-columns: minmax(0, 120px) minmax(0, 1fr) auto; } }
/* Migration assistant */
.mg-hero { display: flex; align-items: center; gap: 18px; padding: 16px 18px; flex-wrap: wrap; } .mg-hero .big { font-size: 20px; font-weight: 600; }
.mg-hero select { font-size: 15px; padding: 6px 10px; } .mg-arrow { font-size: 22px; color: var(--muted); }
.mg-path { list-style: none; display: flex; flex-wrap: wrap; gap: 6px; margin: 0; padding: 0 18px 14px; }
.mg-path li a { display: inline-flex; gap: 6px; align-items: center; padding: 3px 10px; border-radius: 999px; border: 1px solid var(--line2); color: var(--fg); font-size: 12.5px; text-decoration: none; }
.mg-path li a:hover { border-color: var(--accent); } .mg-path li:not(:last-child)::after { content: "→"; color: var(--muted); margin-left: 6px; } .mg-path b { font-family: var(--mono); font-weight: 600; }
.mg-kpis { margin: 0 18px 18px; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.mg-flow { display: grid; gap: 14px; margin-top: 14px; }
.mg-step { display: grid; grid-template-columns: 44px minmax(0, 1fr); gap: 4px; padding: 16px 18px 18px 10px; }
.mg-num { width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; font-weight: 700; background: color-mix(in srgb, var(--accent) 16%, transparent); color: var(--accent); margin: 2px auto 0; }
.mg-step.done .mg-num { background: var(--ok); color: var(--ink); } .mg-step.done .mg-num { font-size: 0; } .mg-step.done .mg-num::after { content: "✓"; font-size: 15px; }
.mg-body h3 { margin: 4px 0 2px; font-size: 15px; } .mg-body .sub { color: var(--muted); font-size: 13px; margin: 0 0 12px; }
.mg-group { margin: 10px 0 4px; font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.mg-f { display: grid; grid-template-columns: 22px 20px minmax(0, 1fr); gap: 8px; padding: 8px 6px; border-bottom: 1px solid var(--line); font-size: 13px; align-items: start; }
.mg-f .ic { font-weight: 700; } .mg-f.breaks .ic { color: var(--err); } .mg-f.review .ic { color: var(--warn); } .mg-f.info .ic { color: var(--info); }
.mg-f .w { font-family: var(--mono); font-size: 12px; color: var(--muted); } .mg-f .rel { font: 600 11px var(--mono); padding: 0 6px; border-radius: 999px; border: 1px solid var(--line2); color: var(--muted); margin-right: 6px; }
.mg-f .adv { color: var(--muted); display: block; margin-top: 2px; } .mg-f a { font-size: 12px; } .mg-f .fixtag { color: var(--ok); font-size: 12px; margin-left: 6px; }
.mg-f input[type=checkbox] { margin-top: 3px; }
.mg-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.mg-diff { margin-top: 10px; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; } .mg-diff summary { padding: 6px 10px; cursor: pointer; font: 12.5px var(--mono); background: var(--raised); }
.mg-diff pre { margin: 0; padding: 8px 0; font: 12px/1.5 var(--mono); background: var(--code); overflow: auto; max-height: 360px; } .mg-diff pre span { display: block; padding: 0 12px; white-space: pre; }
.mg-diff .add { background: color-mix(in srgb, var(--ok) 14%, transparent); } .mg-diff .del { background: color-mix(in srgb, var(--err) 14%, transparent); } .mg-diff .hunk { color: var(--info); }
.mg-note { padding: 10px 12px; border-radius: 8px; background: color-mix(in srgb, var(--info) 10%, transparent); border: 1px solid color-mix(in srgb, var(--info) 30%, transparent); font-size: 13px; margin-top: 8px; }
@media (max-width: 900px) { .mg-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.svc.selected { background: color-mix(in srgb, var(--accent) 10%, transparent); }
.dts-bar { display: flex; gap: 10px; align-items: center; } .dts-bar input { flex: 1; }
.dts { font: 12.5px/1.55 var(--mono); padding: 8px 0 14px; max-height: 70vh; overflow: auto; white-space: pre; tab-size: 4; }
.dts > div { padding: 0 14px; } .dts > div.hit { background: color-mix(in srgb, var(--warn) 14%, transparent); } .dts > div.hit-now { background: color-mix(in srgb, var(--accent) 28%, transparent); }
.svc-init { display: flex; gap: 10px; align-items: baseline; padding: 10px 12px; border-bottom: 1px solid var(--line); } .svc-init b { font-size: 15px; }
.svc-group > summary { display: flex; gap: 8px; align-items: baseline; padding: 9px 12px; cursor: pointer; list-style: none; border-bottom: 1px solid var(--line); }
.svc-group > summary::-webkit-details-marker { display: none; } .svc-group > summary::before { content: "▸"; color: var(--muted); transition: transform .15s; } .svc-group[open] > summary::before { transform: rotate(90deg); }
.svc-group .count { font: 11px var(--mono); padding: 0 6px; border-radius: 999px; background: var(--raised); color: var(--muted); } .svc-group summary .meta { margin-left: auto; font-size: 12px; }
.svc { display: grid; grid-template-columns: 14px minmax(0, 1fr) minmax(0, 220px); gap: 10px; align-items: center; padding: 6px 12px 6px 24px; cursor: pointer; border-bottom: 1px solid color-mix(in srgb, var(--line) 60%, transparent); }
.svc:hover, .svc:focus-visible { background: var(--raised); outline: none; }
.svc .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); } .svc.on .dot { background: var(--ok); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ok) 20%, transparent); } .svc.mask .dot { background: var(--err); }
.svc .n { font: 13px var(--mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .svc .n small { display: block; font: 12px var(--sans, inherit); color: var(--muted); overflow: hidden; text-overflow: ellipsis; }
.svc .p { font-size: 12px; color: var(--muted); text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
#img-services .advice { margin: 10px 12px; }
@media (max-width: 700px) { .svc { grid-template-columns: 14px minmax(0, 1fr); } .svc .p { display: none; } }
.prw-head { display: flex; align-items: center; } .prw-head .btn.ghost { border: 0; background: none; color: var(--muted); }
.prw-steps { list-style: none; margin: 0; padding: 0; display: flex; gap: 6px; }
.prw-steps button { border: 1px solid var(--line); background: none; color: var(--muted); border-radius: 999px; padding: 4px 12px 4px 4px; font: inherit; font-size: 12.5px; cursor: pointer; display: flex; align-items: center; gap: 7px; }
.prw-steps b { display: inline-grid; place-items: center; width: 20px; height: 20px; border-radius: 50%; background: var(--line); color: var(--fg); font-size: 11px; }
.prw-steps button[aria-current="step"] { color: var(--fg); border-color: var(--accent); } .prw-steps button[aria-current="step"] b { background: var(--accent); color: var(--ink); }
.prw-steps button.done b { background: color-mix(in srgb, var(--ok) 70%, transparent); }
.prw-plain { margin: 0; padding: 9px 12px; border-left: 3px solid var(--accent); background: color-mix(in srgb, var(--accent) 8%, transparent); border-radius: 0 8px 8px 0; font-size: 13.5px; }
.prw-plain:empty { display: none; } .prw-plain code { font-size: 12.5px; }
.prw-label { font-size: 12.5px; color: var(--muted); margin-top: 2px; }
.prw-templates { display: flex; flex-wrap: wrap; gap: 6px; }
.prw-templates button { border: 1px dashed var(--line2); background: none; color: var(--fg); border-radius: 8px; padding: 6px 10px; font: inherit; font-size: 12.5px; cursor: pointer; }
.prw-templates button:hover, .prw-templates button:focus-visible { border-style: solid; border-color: var(--accent); }
.prw-kinds { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.prw-kind { display: grid; gap: 3px; padding: 10px 12px 10px 34px; border: 1px solid var(--line); border-radius: 10px; cursor: pointer; position: relative; font-size: 12.5px; }
.prw-kind input { position: absolute; left: 11px; top: 12px; margin: 0; } .prw-kind b { font-size: 13.5px; } .prw-kind span { color: var(--muted); }
.prw-kind:has(input:checked) { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 7%, transparent); }
.prw-field { display: grid; gap: 4px; align-content: start; } .prw-field > label { font-size: 12.5px; color: var(--muted); display: flex; align-items: center; gap: 6px; }
.prw-field input, .prw-field select { width: 100%; color: var(--fg); } .prw-field.wide { grid-column: 1 / -1; }
.q { width: 18px; height: 18px; padding: 0; border-radius: 50%; border: 1px solid var(--line2); background: none; color: var(--muted); font: 600 11px/1 inherit; cursor: pointer; }
.q[aria-expanded="true"], .q:hover { color: var(--ink); background: var(--accent); border-color: var(--accent); }
.help { margin: 0; font-size: 12.5px; color: var(--muted); padding: 7px 10px; border-radius: 8px; background: var(--raised); }
.ex { display: flex; flex-wrap: wrap; gap: 5px; } .ex::before { content: "e.g."; font-size: 11.5px; color: var(--muted); align-self: center; }
.ex button { border: 1px solid var(--line); background: none; color: var(--fg); border-radius: 6px; padding: 1px 7px; font: 12px var(--mono, monospace); cursor: pointer; }
.ex button:hover { border-color: var(--accent); }
.prw-try { display: grid; grid-template-columns: auto 1fr; gap: 6px 10px; align-items: center; border-top: 1px solid var(--line); padding-top: 10px; }
.prw-results { grid-column: 1 / -1; list-style: none; margin: 0; padding: 0; max-height: 170px; overflow: auto; font-size: 12.5px; }
.prw-results li { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 3fr); gap: 10px; padding: 3px 0; border-bottom: 1px solid var(--line); }
.prw-results li code { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .prw-results li span { color: var(--muted); overflow-wrap: anywhere; }
.prw-try .pass { color: var(--ok); } .prw-try .fail { color: var(--warn); }
@media (max-width: 700px) { .pr-grid, .prw-kinds { grid-template-columns: 1fr; } .prw-steps button { padding-right: 8px; } details.rule > summary { grid-template-columns: 22px minmax(0, 1fr) auto; } details.rule .sev, details.rule .switch { display: none; } }

/* Compliance */
.hero { display: grid; grid-template-columns: auto 1fr auto; gap: 18px; align-items: center; padding: 18px; }
.hero .big { font: 750 26px var(--sans); }
.gauges { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; padding: 16px; }
.gauge { text-align: center; } .gauge .ring { width: 74px; height: 74px; margin: 0 auto 6px; display: block; }
.gauge .label { color: var(--muted); font-size: 12px; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; padding: 0 16px 16px; }
.checks li { list-style: none; display: grid; grid-template-columns: 26px 210px minmax(0, 1fr); gap: 8px; padding: 9px 16px; border-bottom: 1px solid var(--line); animation: enter .3s var(--ease) both; }
.checks { margin: 0; padding: 0; }
.two { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr); gap: 16px; }
.timeline { position: relative; margin: 0; padding: 14px 16px 14px 36px; list-style: none; }
.timeline::before { content: ""; position: absolute; left: 21px; top: 18px; bottom: 18px; width: 2px; background: var(--line2); }
.timeline li { position: relative; padding: 6px 0 14px; }
.timeline li::before { content: ""; position: absolute; left: -20px; top: 11px; width: 12px; height: 12px; border-radius: 50%; background: var(--surface); border: 2px solid var(--accent); }
.timeline li.past::before { background: var(--accent); box-shadow: 0 0 0 4px var(--glow); }
details.opt { border-bottom: 1px solid var(--line); }
details.opt summary { list-style: none; display: grid; grid-template-columns: 1fr auto auto; gap: 10px; padding: 10px 16px; cursor: pointer; align-items: center; }
details.opt summary::-webkit-details-marker { display: none; }
details.opt[open] summary { background: var(--glow); }
details.opt .body { padding: 6px 16px 14px; color: var(--muted); animation: enter .3s var(--ease); }

/* Studio: a guided way to create Yocto metadata */
body[data-view=studio] .cards { display: none; }
.sg-start { display: grid; gap: 22px; padding: 26px 4px 10px; }
.sg-start header, .sg-done header { all: unset; display: grid; gap: 6px; }
.sg-start h2, .sg-done h2 { margin: 0; font-size: 24px; letter-spacing: -.4px; }
.sg-start p, .sg-done p { margin: 0; color: var(--muted); max-width: 820px; line-height: 1.55; }
.sg-kinds { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.sg-kind { all: unset; cursor: pointer; display: grid; gap: 8px; align-content: start; padding: 18px; border-radius: 14px; border: 1px solid var(--line); background: linear-gradient(160deg, var(--raised), var(--surface)); transition: transform .2s var(--ease), border-color .2s, box-shadow .2s; }
.sg-kind:hover, .sg-kind:focus-visible { transform: translateY(-2px); border-color: var(--accent); box-shadow: 0 0 0 3px var(--glow); outline: none; }
.sg-kind .top { display: flex; align-items: center; gap: 10px; } .sg-kind .ico { font-size: 20px; color: var(--accent); } .sg-kind b { font-size: 16px; }
.sg-kind .key { margin-left: auto; }
.sg-kind p { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.5; }
.sg-kind .gets { font: 12px var(--mono); color: var(--fg); padding: 6px 9px; border-radius: 8px; background: var(--bg2); border: 1px solid var(--line); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sg-kind .when { font-size: 12px; color: var(--muted); } .sg-kind .when b { font-size: 12px; color: var(--accent); font-weight: 600; }
.sg { display: grid; grid-template-columns: 230px minmax(0, 1fr) minmax(0, 1fr); gap: 12px; min-height: calc(100vh - 140px); }
.sg-nav { display: flex; flex-direction: column; }
.sg-nav .kind-title { padding: 14px 16px 4px; display: flex; gap: 8px; align-items: center; font-weight: 700; } .sg-nav .kind-title .ico { color: var(--accent); }
.sg-nav .kind-desc { padding: 0 16px 10px; color: var(--muted); font-size: 12.5px; line-height: 1.45; border-bottom: 1px solid var(--line); }
.sg-steplist { list-style: none; margin: 0; padding: 10px 8px; display: grid; gap: 2px; }
.sg-steplist button { all: unset; display: flex; align-items: center; gap: 10px; width: calc(100% - 20px); padding: 9px 10px; border-radius: 9px; cursor: pointer; color: var(--muted); font-size: 13.5px; }
.sg-steplist button:hover { color: var(--fg); background: var(--raised); }
.sg-steplist button:focus-visible { outline: 2px solid var(--accent); }
.sg-steplist button.current { color: var(--fg); background: color-mix(in srgb, var(--accent) 13%, transparent); font-weight: 650; }
.sg-steplist .dot { width: 22px; height: 22px; flex: none; border-radius: 50%; display: grid; place-items: center; font: 700 11px var(--mono); border: 1px solid var(--line2); background: var(--bg2); }
.sg-steplist .current .dot { border-color: var(--accent); color: var(--accent); }
.sg-steplist .done .dot { background: color-mix(in srgb, var(--ok) 22%, transparent); border-color: transparent; color: var(--ok); }
.sg-steplist .bad .dot { background: color-mix(in srgb, var(--err) 22%, transparent); border-color: transparent; color: var(--err); }
.sg-nav .spacer { flex: 1; }
.sg-nav .restart { margin: 10px; }
.sg-main { display: flex; flex-direction: column; min-width: 0; }
.sg-main .sg-head { padding: 16px 18px 6px; } .sg-main .sg-head h3 { margin: 0; font-size: 18px; } .sg-main .sg-head p { margin: 6px 0 0; color: var(--muted); font-size: 13px; line-height: 1.5; }
.sg-main .form { flex: 1; padding-top: 0; }
.sg-main .st-sec legend { display: none; }
.sg-foot { display: flex; align-items: center; gap: 10px; padding: 12px 16px; border-top: 1px solid var(--line); }
.sg-foot .grow { flex: 1; }
.sg-review { padding: 4px 18px 10px; display: grid; gap: 14px; }
.sg-review h4 { margin: 0 0 6px; font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.sg-summary { display: grid; grid-template-columns: max-content 1fr; gap: 6px 14px; font-size: 13px; }
.sg-summary dt { color: var(--muted); } .sg-summary dd { margin: 0; font-family: var(--mono); font-size: 12.5px; word-break: break-word; }
.sg-review .st-steps { border: 1px solid var(--line); border-radius: 10px; background: var(--bg2); }
.problem { display: flex; gap: 8px; padding: 6px 12px; font-size: 13px; border-radius: 8px; }
.problem.err { color: var(--err); background: color-mix(in srgb, var(--err) 10%, transparent); } .problem.warn { color: var(--warn); background: color-mix(in srgb, var(--warn) 10%, transparent); } .problem.ok { color: var(--muted); }
.sg-preview { display: flex; flex-direction: column; min-width: 0; }
.ide-head { display: flex; align-items: center; gap: 8px; padding: 11px 14px; font-size: 10.5px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); font-weight: 700; border-bottom: 1px solid var(--line); }
.ide-head .meta { text-transform: none; letter-spacing: 0; }
.sg-where { padding: 10px 14px; border-bottom: 1px solid var(--line); font: 12.5px var(--mono); display: grid; gap: 1px; max-height: 210px; overflow: auto; }
.sg-where .row-w { display: flex; gap: 6px; align-items: center; padding: 1px 0 1px calc(var(--d, 0) * 14px); color: var(--muted); white-space: nowrap; }
.sg-where .row-w.layer { color: var(--fg); font-weight: 650; } .sg-where .row-w.new { color: var(--ok); cursor: pointer; } .sg-where .row-w.new:hover { text-decoration: underline; }
.sg-where .row-w .badge-new { font-size: 10px; border: 1px solid color-mix(in srgb, var(--ok) 45%, transparent); border-radius: 999px; padding: 0 6px; }
.sg-where .more { color: var(--muted); font-style: italic; padding-left: calc(var(--d, 0) * 14px); }
.ide-tabs { display: flex; gap: 1px; background: var(--bg2); border-bottom: 1px solid var(--line); overflow-x: auto; scrollbar-width: thin; min-height: 34px; }
.ide-tab { display: flex; align-items: center; gap: 8px; padding: 0 12px; height: 34px; font: 12.5px var(--mono); color: var(--muted); cursor: pointer; white-space: nowrap; border-right: 1px solid var(--line); border-top: 2px solid transparent; }
.ide-tab:hover { color: var(--fg); }
.ide-tab.active { color: var(--fg); background: var(--code); border-top-color: var(--accent); }
.ide-tab.main .nm::after { content: " ●"; color: var(--accent); }
.ide-tab.dirty .nm::after { content: " ✎"; color: var(--warn); }
.ide-path { display: flex; gap: 10px; align-items: center; padding: 6px 14px; font: 11.5px var(--mono); color: var(--muted); background: var(--code); border-bottom: 1px solid var(--line); min-height: 30px; }
.ide-path span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.ide-path label.check { font: 12px var(--sans); }
.ide-editor { position: relative; flex: 1; display: grid; grid-template-columns: 44px 1fr; background: var(--code); min-height: 300px; overflow: hidden; }
.ide-gutter { padding: 10px 8px 10px 0; text-align: right; font: 12.5px/1.65 var(--mono); color: color-mix(in srgb, var(--muted) 60%, transparent); overflow: hidden; user-select: none; }
.ide-gutter div.hl { color: var(--accent); }
.ide-code { position: relative; overflow: hidden; }
.ide-code pre, .ide-code textarea { position: absolute; inset: 0; margin: 0; padding: 10px 14px; border: 0; font: 12.5px/1.65 var(--mono); white-space: pre; tab-size: 4; overflow: auto; letter-spacing: 0; }
.ide-code pre { pointer-events: none; color: var(--fg); }
.ide-code textarea { background: transparent; color: transparent; caret-color: var(--accent); resize: none; outline: none; box-shadow: none; border-radius: 0; }
.ide-code textarea::selection { background: color-mix(in srgb, var(--accent) 30%, transparent); color: transparent; }
.ide-code textarea[readonly] { caret-color: transparent; cursor: default; }
.ide-code pre .ln { display: block; min-height: 1.65em; } .ide-code pre .ln.hl { background: color-mix(in srgb, var(--accent) 15%, transparent); box-shadow: inset 3px 0 var(--accent); margin: 0 -14px; padding: 0 14px; }
.t-com { color: var(--muted); font-style: italic; } .t-var { color: var(--accent2); } .t-op { color: var(--warn); } .t-str { color: var(--ok); } .t-exp { color: var(--warn); } .t-kw { color: var(--accent); font-weight: 600; } .t-fn { color: var(--info); }
.lang-pop { position: absolute; z-index: 20; width: 380px; max-width: calc(100% - 8px); background: color-mix(in srgb, var(--raised) 96%, var(--accent)); border: 1px solid var(--line2);
  border-radius: 10px; box-shadow: 0 14px 34px rgba(0, 0, 0, .38), 0 0 0 1px color-mix(in srgb, var(--accent) 12%, transparent); overflow: hidden; font: 12.5px var(--mono);
  animation: lang-in .12s var(--ease); transform-origin: top left; }
@keyframes lang-in { from { opacity: 0; transform: translateY(-4px) scale(.98); } to { opacity: 1; transform: none; } }
.lang-pop .opts { max-height: 216px; overflow: auto; padding: 4px; scrollbar-width: thin; }
.lang-pop .opt { display: grid; grid-template-columns: 20px minmax(0, 1fr) auto; gap: 9px; align-items: center; height: 27px; padding: 0 8px; border-radius: 6px; cursor: pointer; }
.lang-pop .opt[aria-selected="true"] { background: color-mix(in srgb, var(--accent) 22%, transparent); }
.lang-pop .opt:hover:not([aria-selected="true"]) { background: color-mix(in srgb, var(--fg) 6%, transparent); }
.lang-pop .ico { width: 18px; height: 18px; border-radius: 5px; display: grid; place-items: center; font: 700 10px var(--sans); color: var(--k, var(--muted));
  background: color-mix(in srgb, var(--k, var(--muted)) 16%, transparent); border: 1px solid color-mix(in srgb, var(--k, var(--muted)) 35%, transparent); }
.lang-pop .l { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--fg); } .lang-pop .l mark { background: none; color: var(--accent); font-weight: 700; }
.lang-pop .k { color: var(--muted); font: 11px var(--sans); }
.lang-pop .detail { border-top: 1px solid var(--line); padding: 8px 12px; font: 12.5px/1.45 var(--sans); color: var(--fg); background: color-mix(in srgb, var(--code) 70%, transparent); }
.lang-pop .detail b { font-family: var(--mono); } .lang-pop .detail .muted { color: var(--muted); } .lang-pop .detail:empty { display: none; }
.lang-pop .foot { display: flex; gap: 12px; padding: 5px 12px; border-top: 1px solid var(--line); font: 11px var(--sans); color: var(--muted); }
.lang-pop .foot kbd { font-size: 10px; padding: 0 4px; } .lang-pop .foot .n { margin-left: auto; }
.lang-doc { padding: 6px 14px; font-size: 12.5px; color: var(--muted); background: var(--code); border-top: 1px solid var(--line); min-height: 30px; }
.lang-doc b { color: var(--fg); font-family: var(--mono); font-weight: 600; } .lang-doc:empty { display: none; }
.lang-lint { background: var(--code); border-top: 1px solid var(--line); max-height: 140px; overflow: auto; } .lang-lint:empty { display: none; }
.lang-lint button { all: unset; display: grid; grid-template-columns: 18px 54px minmax(0, 1fr); gap: 6px; padding: 4px 14px; font-size: 12.5px; cursor: pointer; width: 100%; box-sizing: border-box; }
.lang-lint button:hover, .lang-lint button:focus-visible { background: var(--raised); }
.lang-lint .ln { font-family: var(--mono); color: var(--muted); } .lang-lint small { display: block; color: var(--muted); }
.lang-lint .error .i { color: var(--err); } .lang-lint .warning .i { color: var(--warn); } .lang-lint .info .i { color: var(--info); }
.ide-gutter div.lint-error { color: var(--err); font-weight: 700; } .ide-gutter div.lint-warning { color: var(--warn); font-weight: 700; } .ide-gutter div.lint-info { color: var(--info); }
.sg-done { display: grid; gap: 20px; padding: 26px 4px; }
.sg-done .created { font: 12.5px var(--mono); display: grid; gap: 4px; padding: 12px 14px; border-radius: 10px; background: var(--bg2); border: 1px solid var(--line); }
.sg-done .created span::before { content: "+ "; color: var(--ok); }
.sg-next { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.sg-next button { all: unset; cursor: pointer; display: grid; gap: 4px; padding: 14px 16px; border-radius: 12px; border: 1px solid var(--line); background: var(--surface); transition: border-color .2s, transform .2s var(--ease); }
.sg-next button:hover, .sg-next button:focus-visible { border-color: var(--accent); transform: translateY(-2px); outline: none; }
.sg-next button.primary-next { border-color: color-mix(in srgb, var(--accent) 60%, transparent); background: color-mix(in srgb, var(--accent) 10%, var(--surface)); }
.sg-next b { font-size: 14px; } .sg-next small { color: var(--muted); font-size: 12.5px; line-height: 1.4; }
@media (max-width: 1250px) { .sg { grid-template-columns: 200px minmax(0, 1fr) minmax(0, 1fr); } }
@media (max-width: 1050px) { .sg { grid-template-columns: 1fr; } .sg-steplist { grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); } .sg-nav .spacer { display: none; } .sg-kinds { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 600px) { .sg-kinds { grid-template-columns: 1fr; } }
.st-intro { padding: 12px 16px 0; color: var(--muted); font-size: 13.5px; line-height: 1.5; }
.form { padding: 4px 16px 16px; display: flex; flex-direction: column; gap: 4px; overflow: auto; }
.form.swap { animation: enter .3s var(--ease); }
.st-sec { border: 0; margin: 14px 0 0; padding: 0; min-width: 0; }
.st-sec legend { display: flex; align-items: center; gap: 9px; padding: 0; margin-bottom: 2px; font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); font-weight: 700; }
.st-sec legend .n { display: grid; place-items: center; width: 20px; height: 20px; border-radius: 50%; background: color-mix(in srgb, var(--accent) 16%, transparent); color: var(--accent); font: 700 11px var(--mono); letter-spacing: 0; }
.fld { padding: 10px 12px; margin: 6px 0 0; border-radius: 10px; border: 1px solid transparent; transition: border-color .2s, background .2s; }
.fld:focus-within { border-color: var(--line2); background: color-mix(in srgb, var(--raised) 60%, transparent); }
.fld.invalid { border-color: color-mix(in srgb, var(--err) 55%, transparent); }
.fld .top { display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px; }
.fld label.f { font-weight: 650; margin: 0; }
.fld .req { color: var(--accent); }
.var { margin-left: auto; font: 11px var(--mono); color: var(--muted); padding: 1px 6px; border-radius: 5px; background: var(--bg2); border: 1px solid var(--line); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 55%; }
.fld:focus-within .var { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 40%, transparent); }
.form .help { color: var(--muted); font-size: 12px; margin-top: 6px; line-height: 1.45; }
.form .why { color: var(--fg); font-size: 12.5px; margin-top: 6px; min-height: 1.2em; }
.form .why::before { content: "→ "; color: var(--accent); }
.form .err { color: var(--err); font-size: 12.5px; margin-top: 6px; }
.form input[type=text], .form select { width: 100%; }
#nt-format { width: auto; flex: none; }
.toggles { display: flex; flex-wrap: wrap; gap: 6px; }
.toggle { all: unset; cursor: pointer; padding: 3px 10px; border-radius: 999px; border: 1px solid var(--line2); font-size: 12.5px; color: var(--muted); transition: all .2s var(--ease); }
.toggle:hover { color: var(--fg); border-color: var(--accent); }
.toggle.on { background: linear-gradient(135deg, var(--accent), var(--accent2)); color: var(--ink); border-color: transparent; }
.toggle.on::before { content: "✓ "; }
.toggle:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.st-actions { border-top: 1px solid var(--line); border-bottom: 0; }
.st-steps { margin: 0; padding: 12px 16px 12px 40px; border-bottom: 1px solid var(--line); font-size: 13px; line-height: 1.5; counter-reset: step; list-style: none; }
.st-steps li { position: relative; padding: 3px 0; }
.st-steps li::before { counter-increment: step; content: counter(step); position: absolute; left: -26px; top: 4px; width: 18px; height: 18px; border-radius: 50%; display: grid; place-items: center; font: 700 10.5px var(--mono); background: var(--raised); border: 1px solid var(--line2); color: var(--muted); }
.st-steps .cap { margin-left: -24px; font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); font-weight: 700; list-style: none; padding-bottom: 4px; }
.st-steps .cap::before { display: none; }
.st-steps.done li::before { content: "✓"; background: color-mix(in srgb, var(--ok) 20%, transparent); color: var(--ok); border-color: transparent; }
.notice { padding: 10px 16px; color: var(--warn); font-size: 13px; }

/* Toasts */
#toasts { position: fixed; top: 74px; right: 18px; z-index: 50; display: flex; flex-direction: column; gap: 10px; width: min(380px, calc(100vw - 36px)); }
.toast { position: relative; display: grid; grid-template-columns: 28px 1fr auto; gap: 10px; align-items: start; padding: 12px 14px 14px; border-radius: 12px; background: color-mix(in srgb, var(--raised) 92%, transparent); backdrop-filter: blur(12px); border: 1px solid var(--line2); box-shadow: 0 14px 34px rgba(0,0,0,.35); overflow: hidden; animation: toastIn .45s var(--ease); }
.toast.leaving { animation: toastOut .35s var(--ease) forwards; }
.toast .ico { width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; font-weight: 800; color: var(--ink); }
.toast.success .ico { background: var(--ok); } .toast.error .ico { background: var(--err); } .toast.warning .ico { background: var(--warn); } .toast.info .ico { background: var(--info); }
.toast b { display: block; margin-bottom: 2px; } .toast p { margin: 0; color: var(--muted); font-size: 13px; word-break: break-word; }
.toast .x { all: unset; cursor: pointer; color: var(--muted); padding: 0 4px; } .toast .x:hover { color: var(--fg); }
.toast .act { margin-top: 8px; }
.toast .timer { position: absolute; left: 0; bottom: 0; height: 3px; width: 100%; transform-origin: left; }
.toast.success .timer { background: var(--ok); } .toast.error .timer { background: var(--err); } .toast.warning .timer { background: var(--warn); } .toast.info .timer { background: var(--info); }
@keyframes toastIn { from { opacity: 0; transform: translateX(40px) scale(.96); } to { opacity: 1; transform: none; } }
@keyframes toastOut { to { opacity: 0; transform: translateX(40px) scale(.96); height: 0; padding: 0; margin: 0; } }

/* Dialogs */
dialog { background: var(--raised); color: var(--fg); border: 1px solid var(--line2); border-radius: 16px; padding: 0; width: min(700px, 94vw); box-shadow: 0 30px 80px rgba(0,0,0,.5); }
dialog[open] { animation: pop .3s var(--ease); }
@keyframes pop { from { opacity: 0; transform: translateY(10px) scale(.97); } to { opacity: 1; transform: none; } }
dialog::backdrop { background: rgba(4, 8, 10, .6); backdrop-filter: blur(3px); }
dialog .body { padding: 18px 20px; display: flex; flex-direction: column; gap: 11px; }
dialog h2 { margin: 0; font-size: 16px; }
dialog .fields { display: grid; grid-template-columns: 110px 1fr; gap: 8px 10px; align-items: center; }
dialog .preview { font: 12px var(--mono); background: var(--bg2); border: 1px solid var(--line); border-radius: 8px; padding: 9px 11px; white-space: pre-wrap; word-break: normal; overflow-wrap: anywhere; min-height: 2.6em; }
dialog .actions { display: flex; gap: 8px; justify-content: flex-end; }
#palette { width: min(620px, 94vw); }
#palette input { width: 100%; font-size: 16px; padding: 10px 12px; }
#palette ul { list-style: none; margin: 0; padding: 0; max-height: 50vh; overflow: auto; }
#palette li { padding: 8px 12px; border-radius: 8px; cursor: pointer; display: flex; justify-content: space-between; gap: 10px; }
#palette li.active { background: var(--glow); }
#palette li small { color: var(--muted); }
.hint { color: var(--muted); font-size: 12px; }
.keys td:first-child { white-space: nowrap; }
[hidden] { display: none !important; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
@media (max-width: 1100px) { .kinds { grid-template-columns: repeat(3, minmax(0, 1fr)); } .gauges { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 1380px) { header .context { display: none; } }
@media (max-width: 520px) { .card .value { font-size: 16px; } .card .sub { white-space: normal; } #c-ring { display: none; } }
@media (max-width: 900px) {
  .app { grid-template-columns: 1fr; grid-template-rows: auto auto 1fr; }
  nav { flex-direction: row; overflow-x: auto; padding: 4px 8px; border-right: 0; border-bottom: 1px solid var(--line); }
  nav .group, nav .foot { display: none; }
  nav button { white-space: nowrap; } nav button.active::before { left: 10px; right: 10px; top: auto; bottom: 0; width: auto; height: 3px; }
  .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } .split { grid-template-columns: 1fr; } main { padding: 14px; }
  .context { display: none; } .hero { grid-template-columns: 1fr; } .checks li { grid-template-columns: 26px 1fr; } .checks li .meta { grid-column: 2; }
  .kinds { grid-template-columns: repeat(2, minmax(0, 1fr)); } .gauges { grid-template-columns: repeat(2, minmax(0, 1fr)); } .two { grid-template-columns: 1fr; }
  .panel > .head .detail-title { flex-basis: 100%; max-width: none; order: -1; } #d-meta { flex: 1 1 auto; }
  #toasts { top: auto; bottom: 14px; right: 14px; }
  #palette-btn, #keys-btn, header .context { display: none; }
  header { gap: 8px; padding: 8px 12px; } #target-combo { flex: 1 1 160px; min-width: 150px; }
}

/* Refined proportions: lighter weights, tighter spacing, flat surfaces; shadows only on what floats. */
html, body { font-size: 13.5px; }
header { padding: 8px 18px; gap: 10px; }
.brand { font: 650 15px var(--mono); } .brand svg.logo { width: 26px; height: 26px; filter: none; }
select, input[type=text], input[type=search] { padding: 5px 10px; border-radius: 7px; }
.btn { padding: 5px 11px; border-radius: 7px; font-size: 13px; }
.btn:hover:not(:disabled) { transform: none; background: color-mix(in srgb, var(--raised) 80%, var(--glow)); }
.btn.primary { font-weight: 600; box-shadow: 0 1px 8px var(--glow); }
.btn.primary:hover:not(:disabled) { background: linear-gradient(135deg, var(--accent), var(--accent2)); filter: brightness(1.06); }
kbd { font-size: 10.5px; border-bottom-width: 1px; border-radius: 4px; padding: 0 4px; }
.chip { padding: 1px 8px; font-size: 11.5px; }
nav { padding: 12px 8px; }
nav .group { padding: 14px 10px 4px; font-size: 10px; font-weight: 650; letter-spacing: .14em; }
nav button { padding: 6px 10px; font-size: 13.5px; }
nav button.active { font-weight: 550; }
main { padding: 16px 20px 32px; gap: 14px; }
.view { gap: 14px; }
.cards { gap: 12px; }
.card { border-radius: 10px; padding: 11px 14px; box-shadow: none; background: var(--surface); }
.card:hover { transform: none; border-color: var(--line2); }
.card h3 { font-size: 10px; font-weight: 650; margin-bottom: 4px; }
.card .value { font: 600 17px var(--mono); letter-spacing: -.01em; }
.ring { width: 44px; height: 44px; } .ring circle { stroke-width: 5; } .ring text { font-weight: 600; font-size: 12px; }
.spark { height: 28px; }
.panel { border-radius: 10px; box-shadow: none; background: var(--surface); }
.panel > .head { padding: 9px 14px; }
.panel > .head h2 { font-size: 10.5px; font-weight: 650; letter-spacing: .14em; }
.split { gap: 14px; }
.row { padding: 8px 14px; }
.group-label { padding: 12px 14px 5px; font-size: 10px; font-weight: 650; }
.tabs button { padding: 8px 12px; }
.tools { padding: 8px 14px; }
th { padding: 8px 14px; font-size: 10px; font-weight: 650; } td { padding: 7px 14px; }
.badge { font-weight: 600; font-size: 11px; padding: 0 7px; }
.sg-kind, .sg-next button { border-radius: 10px; }
.sg-kind { padding: 16px; } .sg-kind b { font-size: 15px; }
.fld { padding: 8px 10px; }
.fld label.f { font-weight: 600; }
.toggle { padding: 2px 9px; font-size: 12px; }
.prog-pct { font-weight: 650; font-size: 16px; }
.layer-item .n { font-weight: 600; }
details.folder > summary { padding: 8px 14px; }
.recipe { padding: 6px 14px 6px 31px; }
.hero { padding: 14px 18px; gap: 16px; } .hero .big { font: 650 21px var(--sans); letter-spacing: -.01em; }
.gauge .ring { width: 62px; height: 62px; } .gauges { padding: 12px 16px; }
.hero .ring { width: 64px; height: 64px; }
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <defs>
    <linearGradient id="ringGrad" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="var(--accent)"/><stop offset="1" stop-color="var(--accent2)"/></linearGradient>
    <linearGradient id="sparkGrad" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="var(--accent2)" stop-opacity=".45"/><stop offset="1" stop-color="var(--accent2)" stop-opacity="0"/></linearGradient>
  </defs>
</svg>
<div class="app">
  <header>
    <span class="brand"><svg class="logo" viewBox="0 0 512 512" aria-hidden="true"><rect width="512" height="512" rx="112" fill="#0b1115"/><rect x="24" y="24" width="464" height="464" rx="92" fill="none" stroke="#203e49" stroke-width="4"/><path pathLength="1" d="M176 112h92c64 0 108 29 108 77 0 30-18 52-47 64 40 10 63 34 63 71 0 52-46 84-118 84h-98" fill="none" stroke="#84c9c0" stroke-width="32" stroke-linecap="round" stroke-linejoin="round"/><path pathLength="1" d="M176 112v296" fill="none" stroke="#81bdcf" stroke-width="32" stroke-linecap="round"/><path pathLength="1" d="M104 160h162M104 256h202M104 352h174" fill="none" stroke="#84c9c0" stroke-width="24" stroke-linecap="round"/><path d="M176 141v38M176 333v38" stroke="#0b1115" stroke-width="40"/><path d="M104 160h162M104 352h174" fill="none" stroke="#84c9c0" stroke-width="24" stroke-linecap="round"/><path d="M158 256h36" stroke="#0b1115" stroke-width="32"/><path d="M176 233v46" stroke="#81bdcf" stroke-width="32"/><circle cx="420" cy="96" r="12" fill="#dfbe77"/></svg><span class="word">bitloom</span></span>
    <select id="profile" aria-label="Profile"></select>
    <span class="chip" id="release-chip">release …</span>
    <span class="context" id="context"></span>
    <div class="combo" id="target-combo">
      <input type="text" id="target" placeholder="Build target / recipe" aria-label="Build target" size="20" role="combobox" aria-expanded="false" aria-controls="target-list" aria-autocomplete="list" autocomplete="off" spellcheck="false">
      <button type="button" class="combo-toggle" id="target-toggle" tabindex="-1" aria-label="Images in this project" title="Images in this project (Alt+↓)"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></button>
      <div class="combo-list" id="target-list" role="listbox" aria-label="Images in this project" hidden></div>
    </div>
    <button class="btn primary" id="build-btn" title="Build target (b)"><kbd>b</kbd>Build</button>
    <button class="btn" id="queue-btn" title="Queue any operation (q)"><kbd>q</kbd>Operations</button>
    <button class="btn" id="palette-btn" title="Command palette (Ctrl+K)"><kbd>⌘K</kbd>Search</button>
    <span class="chip"><span class="dot" id="service-dot"></span><span id="service-label">connecting…</span></span>
    <button class="btn" id="notify-btn" title="Browser notifications when builds finish" aria-label="Browser notifications when builds finish"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg></button>
    <div class="theme-pick"><button class="btn" id="theme-btn" title="Theme" aria-label="Theme" aria-haspopup="menu" aria-expanded="false"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 0 0 18z" fill="currentColor"/></svg></button>
      <div class="theme-menu" id="theme-menu" role="menu" hidden></div></div>
    <button class="btn" id="keys-btn" title="Keyboard shortcuts (?)">?</button>
  </header>
  <nav aria-label="Sections">
    <div class="group">BUILD</div>
    <button data-view="builds"><span class="num">1</span><span class="icon">◈</span>Builds</button>
    <button data-view="recipes"><span class="num">2</span><span class="icon">◇</span>Recipes</button>
    <button data-view="tasklogs"><span class="num">3</span><span class="icon">≋</span>Task logs</button>
    <div class="group">PRODUCT</div>
    <button data-view="image"><span class="num">4</span><span class="icon">▦</span>Image</button>
    <button data-view="compliance"><span class="num">5</span><span class="icon">⚖</span>SBOM &amp; CRA</button>
    <button data-view="studio"><span class="num">6</span><span class="icon">✦</span>Studio</button>
    <div class="group">WORKSPACE</div>
    <button data-view="practices"><span class="num">7</span><span class="icon">✓</span>Practices</button>
    <button data-view="health"><span class="num">8</span><span class="icon">⚙</span>Configuration</button>
    <button data-view="migrate"><span class="num">9</span><span class="icon">⇪</span>Migrate</button>
    <div class="foot">Same service and history as the TUI.<br><kbd>?</kbd> keys · <kbd>Ctrl</kbd><kbd>K</kbd> search<br><span class="about">Bitloom, originally created by Luca Padovan · <a href="https://github.com/padovanl/bitloom" target="_blank" rel="noopener">AGPL-3.0 · source</a></span></div>
  </nav>
  <main>
    <section class="cards" aria-label="Status">
      <div class="card"><h3>Build</h3><div class="flex"><svg class="ring" viewBox="0 0 60 60" id="c-ring"><circle class="track" cx="30" cy="30" r="24"/><circle class="bar" cx="30" cy="30" r="24" stroke-dasharray="150.8" stroke-dashoffset="150.8"/><text x="30" y="35" text-anchor="middle">—</text></svg><div style="min-width:0"><div class="value" id="c-status">—</div><div class="sub" id="c-title">No jobs yet</div></div></div></div>
      <div class="card"><h3>Tasks</h3><div class="value" id="c-tasks">—</div><div class="sub" id="c-sstate"></div></div>
      <div class="card"><h3>Host</h3><div class="sub" id="c-cpu">CPU sampling…</div><svg class="spark" id="c-spark" viewBox="0 0 120 34" preserveAspectRatio="none"><path class="area" d=""/><path class="line" d=""/></svg><div class="sub" id="c-ram"></div></div>
      <div class="card"><h3>Workspace disk</h3><div class="value" id="c-disk-free">—</div><div class="meter" id="c-disk-meter"><i style="width:0"></i></div><div class="sub" id="c-disk"></div></div>
    </section>

    <section id="view-builds" class="view split">
      <div class="panel">
        <div class="head"><h2>History</h2><span style="flex:1"></span><span class="hint"><kbd>j</kbd><kbd>k</kbd></span></div>
        <div class="list" id="history" role="listbox" aria-label="Build history"><div class="skeleton"></div><div class="skeleton" style="width:70%"></div><div class="skeleton" style="width:80%"></div></div>
      </div>
      <div class="panel">
        <div class="head">
          <span class="glyph" id="d-glyph"></span>
          <span class="detail-title" id="d-title">Select an operation</span>
          <span class="meta" id="d-meta"></span>
          <span style="flex:1"></span>
          <button class="btn warn" id="graceful-btn" title="Graceful stop: one SIGINT to the BitBake client (g)"><kbd>g</kbd>Graceful</button>
          <button class="btn danger" id="stop-btn" title="Force stop (s)"><kbd>s</kbd>Stop</button>
          <button class="btn" id="retry-btn" title="Retry with the original profile (r)"><kbd>r</kbd>Retry</button>
        </div>
        <div class="prog" id="d-prog" hidden><div class="prog-top"><span class="prog-text" id="d-progress-text"></span><span class="prog-pct" id="d-progress-pct"></span></div>
          <div class="progress" id="d-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100"><i></i><b></b></div></div>
        <div class="tabs" role="tablist" id="tabs">
          <button data-tab="output" class="active">Output</button>
          <button data-tab="summary">Summary</button>
          <button data-tab="sstate">Sstate reuse</button>
          <button data-tab="warnings">Warnings</button>
          <button data-tab="timings">Timings</button>
          <button data-tab="compare">Compare</button>
          <span class="ink"></span>
        </div>
        <div class="tools" id="log-tools">
          <input type="search" id="log-search" placeholder="/ search output (±3 lines of context)">
          <label class="check"><span class="switch"><input type="checkbox" id="errors-only"><span></span></span><kbd>e</kbd> errors only</label>
          <label class="check"><span class="switch"><input type="checkbox" id="follow" checked><span></span></span>follow</label>
        </div>
        <div style="position:relative; display:flex; flex:1; min-height:0">
          <pre class="log" id="log" tabindex="0" aria-live="off" style="flex:1" data-empty="Select an operation in History to read its output, or press b to build the target."></pre>
          <button class="btn primary jump" id="jump">↓ Latest</button>
        </div>
      </div>
    </section>

    <section id="view-recipes" class="view split recipes" hidden>
      <nav class="panel layers" aria-label="Layers">
        <div class="head"><h2>Layers</h2><span class="hint" id="layer-count"></span></div>
        <div class="list" id="layer-list" role="listbox" aria-label="Layers"></div>
      </nav>
      <div class="panel">
        <div class="tools">
          <input type="search" id="meta-search" placeholder="/ search recipes, appends, classes, kas files">
          <div class="seg" id="meta-kinds" role="radiogroup" aria-label="Kind"></div>
          <span class="hint" id="meta-count"></span>
          <button class="btn" id="meta-expand" title="Open or close every folder">Expand all</button>
        </div>
        <div class="list" id="meta-groups"></div>
      </div>
    </section>

    <section id="view-tasklogs" class="view split" hidden>
      <div class="panel">
        <div class="tools"><input type="search" id="task-search" placeholder="/ filter by recipe or task"></div>
        <div class="list"><table><thead><tr><th>Recipe</th><th>Task log</th><th>Size</th></tr></thead><tbody id="task-rows"></tbody></table></div>
      </div>
      <div class="panel">
        <div class="head"><h2 id="task-title">Task log</h2></div>
        <div class="tools"><input type="search" id="task-log-search" placeholder="search this task log"><label class="check"><span class="switch"><input type="checkbox" id="task-errors"><span></span></span>errors only</label></div>
        <pre class="log" id="task-log" tabindex="0" data-empty="Select a task log on the left: the log.do_* and run.do_* files BitBake keeps for every recipe task."></pre>
      </div>
    </section>

    <section id="view-image" class="view" hidden>
      <div class="panel img-top">
        <div class="head"><h2>Image</h2><select id="img-pick" aria-label="Built image"></select><span class="meta" id="img-source"></span><span style="flex:1"></span><div class="seg" id="img-mode" role="radiogroup" aria-label="Show"><button role="radio" aria-checked="true" data-mode="files">Files</button><button role="radio" aria-checked="false" data-mode="services" title="What starts on the device: init, systemd units or SysV scripts, udev rules, D-Bus">Services</button><button role="radio" aria-checked="false" data-mode="devicetree" title="The device trees the build deployed, decompiled">Device tree</button><button role="radio" aria-checked="false" data-mode="insights" title="Charts: where the space goes, licences, what listens, security">Insights</button></div>
          <div class="who"><input type="search" id="img-find" placeholder="Which recipe installs… /etc/motd, libc6, busybox" aria-label="Which recipe installs a file or package"><button class="btn" id="img-find-btn">Find</button></div></div>
        <div class="img-stats" id="img-stats"></div>
        <div class="img-charts"><div><h4>Biggest packages</h4><div id="img-packages" class="bars"></div></div><div><h4>Biggest folders</h4><div id="img-folders" class="bars"></div></div></div>
      </div>
      <div id="img-insights" class="ins" hidden></div>
      <div class="split img-split" id="img-split">
        <div class="panel">
          <div class="head">
            <div class="img-crumbs" id="img-crumbs" role="navigation" aria-label="Folder"></div><span style="flex:1"></span><span class="meta" id="img-dir-size"></span></div>
          <div class="list" id="img-list" role="listbox" aria-label="Folder content"></div>
          <div class="list" id="img-services" aria-label="Services" hidden></div>
          <div class="list" id="img-dt" aria-label="Device trees" hidden></div>
        </div>
        <div class="panel img-detail" id="img-detail"><div class="empty">Select a file to see which package and recipe put it in the image, and how to change it.</div></div>
      </div>
    </section>

    <section id="view-migrate" class="view" hidden>
      <div class="panel mg-top">
        <div class="mg-hero">
          <div><div class="hint">This project</div><div class="big" id="mg-from">…</div></div>
          <span class="mg-arrow" aria-hidden="true">→</span>
          <div><div class="hint">Move to</div><select id="mg-to" aria-label="Target release"></select></div>
          <span style="flex:1"></span>
          <button class="btn" id="mg-rescan">↻ Scan again</button><select id="mg-format" aria-label="Report format"><option value="md">Markdown</option><option value="json">JSON</option><option value="text">Text</option></select><button class="btn" id="mg-export">Export</button>
        </div>
        <ol class="mg-path" id="mg-path" aria-label="Releases on the way, each with its migration guide"></ol>
        <div class="kpis mg-kpis" id="mg-kpis"></div>
      </div>
      <div class="mg-flow">
        <section class="panel mg-step" id="mg-step-1"><div class="mg-num">1</div><div class="mg-body"><h3>What changes in your files</h3>
          <p class="sub">From the official migration guides, checked on your layers, the build configuration and the kas files. Upstream layers are replaced by the new release, not migrated.</p>
          <div class="seg" id="mg-show" role="radiogroup" aria-label="Show"></div><div id="mg-findings"></div></div></section>
        <section class="panel mg-step" id="mg-step-2"><div class="mg-num">2</div><div class="mg-body"><h3>Apply the safe fixes</h3>
          <p class="sub">Mechanical changes only (renames, the new syntax, LAYERSERIES_COMPAT). Review the diff first; the originals are kept and one click restores them.</p>
          <div class="mg-actions"><button class="btn" id="mg-preview">Preview the selected fixes</button><button class="btn primary" id="mg-apply" disabled>Apply</button><span class="hint" id="mg-selected"></span><span style="flex:1"></span><select id="mg-backups" aria-label="Earlier changes"></select><button class="btn" id="mg-restore">Undo</button></div>
          <div id="mg-diffs"></div></div></section>
        <section class="panel mg-step" id="mg-step-3"><div class="mg-num">3</div><div class="mg-body"><h3>Move the checkout</h3>
          <p class="sub">A new kas file for the new release, next to the current one, and a profile with its own work directory: the current build keeps working while you try the new one.</p>
          <div id="mg-kas"></div></div></section>
        <section class="panel mg-step" id="mg-step-4"><div class="mg-num">4</div><div class="mg-body"><h3>Build and verify</h3>
          <p class="sub">On the new profile: parse, build the image, then check what is left.</p>
          <div class="mg-actions" id="mg-verify"></div></div></section>
      </div>
    </section>

    <section id="view-practices" class="view" hidden>
      <div class="panel pr-top">
        <div class="pr-hero">
          <svg class="ring big-ring" viewBox="0 0 60 60" aria-hidden="true"><circle class="track" cx="30" cy="30" r="24"/><circle class="bar" id="pr-ring" cx="30" cy="30" r="24" stroke-dasharray="150.8" stroke-dashoffset="150.8"/><text x="30" y="34" text-anchor="middle" id="pr-score">—</text></svg>
          <div class="pr-sum"><div class="hint">Yocto best practices</div><div class="big" id="pr-title">Checking…</div><div class="meta" id="pr-sub"></div></div>
          <span style="flex:1"></span>
          <div class="pr-actions"><button class="btn" id="pr-recheck">↻ Check again</button><select id="pr-format" aria-label="Report format"><option value="md">Markdown</option><option value="json">JSON</option><option value="text">Text</option></select><button class="btn" id="pr-export">Export</button><button class="btn primary" id="pr-add">✦ Add a company rule</button></div>
        </div>
        <div class="pr-filter"><div class="seg" id="pr-show" role="radiogroup" aria-label="Show"></div><span class="hint" id="pr-config"></span></div>
      </div>
      <div id="pr-groups" class="pr-groups"></div>
      <dialog id="pr-dialog" aria-labelledby="pr-dialog-title">
        <form method="dialog" class="pr-form" id="pr-form" novalidate>
          <div class="prw-head"><h3 id="pr-dialog-title">New company rule</h3><span style="flex:1"></span><button class="btn ghost" value="cancel" formnovalidate aria-label="Close">✕</button></div>
          <ol class="prw-steps" id="prw-steps">
            <li><button type="button" data-step="1"><b>1</b> What to check</button></li>
            <li><button type="button" data-step="2"><b>2</b> Details</button></li>
            <li><button type="button" data-step="3"><b>3</b> Name and explain</button></li>
          </ol>
          <p class="prw-plain" id="prw-plain" aria-live="polite"></p>

          <div class="prw-page" data-page="1">
            <div class="prw-label">Start from an example <span class="hint">(you can change everything afterwards)</span></div>
            <div class="prw-templates" id="prw-templates"></div>
            <div class="prw-label">…or choose the kind of check</div>
            <div class="prw-kinds" role="radiogroup" aria-label="Kind of check">
              <label class="prw-kind"><input type="radio" name="prf-type" value="files-must-match"><b>Every file must contain…</b><span>Files in your layers that must all have a line, e.g. every recipe sets <code>MAINTAINER</code>.</span></label>
              <label class="prw-kind"><input type="radio" name="prf-type" value="files-must-not-match"><b>No file may contain…</b><span>Text that must never appear, e.g. internal host names or <code>AUTOREV</code>.</span></label>
              <label class="prw-kind"><input type="radio" name="prf-type" value="layer-file-exists"><b>Every layer has a file</b><span>A file each of your layers must ship, e.g. <code>CODEOWNERS</code>.</span></label>
              <label class="prw-kind"><input type="radio" name="prf-type" value="variable"><b>A variable has a value</b><span>A setting in your configuration, e.g. <code>DISTRO</code> is <code>acme</code>.</span></label>
            </div>
          </div>

          <div class="prw-page" data-page="2" hidden>
            <div class="pr-grid">
              <div class="prw-field wide" data-for="files-must-match files-must-not-match">
                <label for="prf-files">Which files <button type="button" class="q" aria-expanded="false" aria-controls="prh-files" title="What is this?">?</button></label>
                <input type="text" id="prf-files" placeholder="*.bb" autocomplete="off">
                <p class="help" id="prh-files" hidden>A file name pattern: <code>*</code> stands for any text. It is matched against the file name in <b>your</b> layers only (upstream layers are never checked). Several kinds need several rules.</p>
                <div class="ex" data-into="prf-files"><button type="button">*.bb</button><button type="button">*.bbappend</button><button type="button">*.conf</button><button type="button">*.patch</button><button type="button">*.bbclass</button><button type="button">README*</button></div>
              </div>
              <div class="prw-field wide" data-for="files-must-match files-must-not-match">
                <label for="prf-pattern"><span id="prf-pattern-label">Text to look for</span> <button type="button" class="q" aria-expanded="false" aria-controls="prh-pattern" title="What is this?">?</button></label>
                <input type="text" id="prf-pattern" placeholder="^MAINTAINER\s*=" autocomplete="off" spellcheck="false">
                <p class="help" id="prh-pattern" hidden>A regular expression, checked line by line. Plain words work as they are. <code>^</code> means “at the start of the line”, <code>\s*</code> “any spaces”, <code>.*</code> “anything”, <code>\.</code> a literal dot, <code>a|b</code> “a or b”. Use <b>Try it</b> below to see what it finds before saving.</p>
                <div class="ex" data-into="prf-pattern"><button type="button" title="A line that sets MAINTAINER">^MAINTAINER\s*=</button><button type="button" title="A line that sets SUMMARY">^SUMMARY\s*=</button><button type="button" title="AUTOREV anywhere">AUTOREV</button><button type="button" title="An internal host name">\.acme\.internal</button><button type="button" title="A patch header">^Signed-off-by:</button></div>
              </div>
              <div class="prw-field wide" data-for="layer-file-exists">
                <label for="prf-path">File or folder each layer must have <button type="button" class="q" aria-expanded="false" aria-controls="prh-path" title="What is this?">?</button></label>
                <input type="text" id="prf-path" placeholder="CODEOWNERS" autocomplete="off">
                <p class="help" id="prh-path" hidden>A path relative to the top of each of your layers (the folder with <code>conf/layer.conf</code>). A folder counts too: <code>docs</code>, <code>conf/machine</code>.</p>
                <div class="ex" data-into="prf-path"><button type="button">CODEOWNERS</button><button type="button">SECURITY.md</button><button type="button">CHANGELOG.md</button><button type="button">docs</button></div>
              </div>
              <div class="prw-field" data-for="variable">
                <label for="prf-name">Variable <button type="button" class="q" aria-expanded="false" aria-controls="prh-name" title="What is this?">?</button></label>
                <input type="text" id="prf-name" placeholder="DISTRO" autocomplete="off" spellcheck="false">
                <p class="help" id="prh-name" hidden>The name as written in the configuration, in capitals. Bitloom reads <code>local.conf</code>, <code>auto.conf</code>, your distribution files and your image recipes, following <code>=</code>, <code>?=</code>, <code>+=</code>, <code>:append</code>…: what is written there, not what BitBake computes from classes.</p>
                <div class="ex" data-into="prf-name"><button type="button">DISTRO</button><button type="button">DISTRO_FEATURES</button><button type="button">INHERIT</button><button type="button">IMAGE_FEATURES</button><button type="button">MACHINE</button></div>
              </div>
              <div class="prw-field" data-for="variable">
                <label for="prf-op">Must be <button type="button" class="q" aria-expanded="false" aria-controls="prh-op" title="What is this?">?</button></label>
                <select id="prf-op"><option value="set">set (any value)</option><option value="unset">not set at all</option><option value="equals">exactly</option><option value="contains">containing the word</option><option value="not-contains">not containing the word</option></select>
                <p class="help" id="prh-op" hidden><b>exactly</b> compares the whole value. <b>containing the word</b> looks for one word of a list such as <code>DISTRO_FEATURES = "systemd seccomp"</code>.</p>
              </div>
              <div class="prw-field wide" data-for="variable" id="prf-value-field">
                <label for="prf-value">Value</label>
                <input type="text" id="prf-value" placeholder="acme" autocomplete="off">
              </div>
            </div>
            <div class="prw-try">
              <button class="btn" type="button" id="prf-try">▶ Try it on this project</button><span class="hint" id="prf-try-sum">Runs the check now, without saving.</span>
              <ul class="prw-results" id="prf-try-list"></ul>
            </div>
          </div>

          <div class="prw-page" data-page="3" hidden>
            <div class="pr-grid">
              <div class="prw-field wide">
                <label for="prf-title">Title <button type="button" class="q" aria-expanded="false" aria-controls="prh-title" title="What is this?">?</button></label>
                <input type="text" id="prf-title" placeholder="Recipes name a maintainer">
                <p class="help" id="prh-title" hidden>Say what a good project <b>does</b>, as a statement: “Recipes name a maintainer”, not “Missing maintainer”. It is the line everyone sees in the list.</p>
              </div>
              <div class="prw-field">
                <label for="prf-id">Id <button type="button" class="q" aria-expanded="false" aria-controls="prh-id" title="What is this?">?</button></label>
                <input type="text" id="prf-id" placeholder="acme-maintainer" autocomplete="off" spellcheck="false">
                <p class="help" id="prh-id" hidden>Made from the title; change it if you like. Lowercase letters, digits and hyphens. It is how the rule is switched off or re-weighted in <code>bitloom-practices.json</code>, so it does not change once saved.</p>
              </div>
              <div class="prw-field">
                <label for="prf-severity">How serious <button type="button" class="q" aria-expanded="false" aria-controls="prh-severity" title="What is this?">?</button></label>
                <select id="prf-severity"><option value="error">error: must be fixed</option><option value="warning">warning: should be fixed</option><option value="info">suggestion</option></select>
                <p class="help" id="prh-severity" hidden><b>error</b> fails CI (<code>bitloom --practices</code> exits 2). <b>warning</b> fails it only with <code>--fail-on warning</code>. A <b>suggestion</b> never fails anything.</p>
              </div>
              <div class="prw-field">
                <label for="prf-category">Group</label>
                <input type="text" id="prf-category" placeholder="Company" list="prf-categories">
                <datalist id="prf-categories"><option>Company</option><option>Layers</option><option>Recipes</option><option>Appends</option><option>Security</option><option>Configuration</option></datalist>
              </div>
              <div class="prw-field wide">
                <label for="prf-why">Why it matters <button type="button" class="q" aria-expanded="false" aria-controls="prh-why" title="What is this?">?</button></label>
                <input type="text" id="prf-why" placeholder="Our release process needs an owner per component.">
                <p class="help" id="prh-why" hidden>One sentence for whoever breaks the rule. People follow a rule they understand.</p>
              </div>
              <div class="prw-field wide">
                <label for="prf-fix">How to fix it</label>
                <input type="text" id="prf-fix" placeholder='Add MAINTAINER = "Team <team@acme.example>" to the recipe.'>
              </div>
            </div>
            <p class="hint">Saved in <code>bitloom-practices.json</code> at the project root: commit it, and the whole team and CI get the same rules. A rule only reads files: nothing runs.</p>
          </div>

          <div class="err" id="prf-error" role="alert"></div>
          <div class="pr-form-actions"><button class="btn danger" type="button" id="prf-delete" hidden>Delete rule</button><span style="flex:1"></span>
            <button class="btn" type="button" id="prf-back">← Back</button><button class="btn primary" type="button" id="prf-next">Next →</button><button class="btn primary" type="submit" id="prf-save" hidden>Save rule</button></div>
        </form>
      </dialog>
    </section>

    <section id="view-compliance" class="view" hidden>
      <div class="panel"><div class="hero">
        <svg class="ring" viewBox="0 0 60 60" id="support-ring" style="width:84px;height:84px"><circle class="track" cx="30" cy="30" r="24"/><circle class="bar" cx="30" cy="30" r="24" stroke-dasharray="150.8" stroke-dashoffset="150.8"/><text x="30" y="35" text-anchor="middle">—</text></svg>
        <div><div class="hint">Yocto release</div><div class="big" id="cr-release">—</div><div class="hint" id="cr-support"></div></div>
        <div style="text-align:right"><div class="hint">Regulation (EU) 2024/2847 · engineering evidence, not legal advice</div><div id="cr-score" class="big">—</div></div>
      </div></div>
      <div class="panel"><div class="head"><h2>SBOM quality</h2><span class="meta" id="sb-file"></span></div><div class="gauges" id="sb-gauges"></div><div class="chips" id="sb-vex"></div></div>
      <div class="panel">
        <div class="head"><h2>Vulnerabilities</h2><span class="meta" id="vu-summary"></span><span style="flex:1"></span>
          <select id="vu-format" aria-label="Export format" title="Export the findings shown"><option value="md">Markdown report</option><option value="html">HTML report</option><option value="csv">CSV</option><option value="json">JSON</option><option value="sarif">SARIF (GitHub)</option></select><button class="btn" id="vu-csv" title="Export the findings shown, with NVD/OSV links">Export</button><button class="btn primary" id="vu-grype" title="Scan the newest SPDX SBOM with Grype">Scan with Grype</button></div>
        <div class="tools">
          <select id="vu-source"><option value="">Newest report of each tool</option></select>
          <select id="vu-status"><option value="unpatched">Unpatched</option><option value="all">All</option><option value="reviewed">Reviewed</option></select>
          <input type="search" id="vu-min" placeholder="min CVSS" style="max-width:110px;flex:0 0 110px">
          <input type="search" id="vu-q" placeholder="CVE, package or text">
        </div>
        <div class="chips" id="vu-chips" style="padding-top:12px"></div>
        <div class="list" style="max-height:420px"><table><thead><tr><th>Severity</th><th>CVSS</th><th>CVE</th><th>Package</th><th>Status</th><th>Review</th></tr></thead><tbody id="vu-rows"></tbody></table></div>
        <div class="hint" style="padding:10px 16px">Sources: cve-check, sbom-cve-check (Wrynose) and Grype reports. Record reviews in the TUI (Artifacts → v → r); VulnScout and Grype read the same SBOMs.</div>
      </div>
      <div class="two">
        <div class="panel"><div class="head"><h2>CRA readiness checks</h2></div><ul class="checks" id="cr-checks"></ul></div>
        <div class="panel"><div class="head"><h2>Timeline</h2></div><ul class="timeline" id="cr-timeline"></ul>
          <div class="hint" style="padding:0 16px 16px">EN 40000-1-3 (draft, CEN/CENELEC) describes the vulnerability-handling process the reports above provide evidence for.</div></div>
      </div>
      <div class="panel"><div class="head"><h2>SBOM, vulnerability and traceability options</h2><span style="flex:1"></span><span class="hint">Change them in the TUI: Configuration → <kbd>s</kbd> (writes a managed block with a backup)</span></div><div id="sb-options"></div></div>
    </section>

    <section id="view-studio" class="view" hidden>
      <div class="sg-start" id="sg-start">
        <header><h2>What do you want to create?</h2><p>Studio walks you through it one step at a time, explains every choice, shows the files it will write and where they go, and changes nothing until you press Create. Existing files are never overwritten.</p></header>
        <div class="sg-kinds" id="sg-kinds"></div>
      </div>
      <div class="sg" id="sg-flow" hidden>
        <nav class="panel sg-nav" aria-label="Steps">
          <div class="kind-title"><span class="ico" id="sg-kind-ico"></span><span id="st-title"></span></div>
          <div class="kind-desc" id="st-desc"></div>
          <ol class="sg-steplist" id="sg-steplist"></ol>
          <div class="spacer"></div>
          <button class="btn restart" id="sg-restart" title="Choose something else to create (Esc)">← Something else</button>
        </nav>
        <section class="panel sg-main">
          <div class="sg-head"><h3 id="sg-step-title"></h3><p id="sg-step-help"></p></div>
          <div class="form" id="st-form"></div>
          <div class="sg-review" id="sg-review" hidden>
            <div><h4>Your choices</h4><dl class="sg-summary" id="sg-summary"></dl></div>
            <div><h4>Create will</h4><ol class="st-steps" id="st-steps"></ol></div>
            <div id="ide-problems"></div>
            <label class="check" id="st-use-wrap"><span class="switch"><input type="checkbox" id="st-use" checked><span></span></span><span id="st-use-label">use for this profile</span></label>
          </div>
          <div class="sg-foot"><button class="btn" id="sg-back">← Back</button><span class="grow"></span><span class="hint" id="sg-hint"></span><button class="btn primary" id="sg-next">Next →</button><button class="btn primary" id="st-create" hidden title="Create the files (Ctrl+Enter)">✦ Create files</button></div>
        </section>
        <section class="panel sg-preview" aria-label="Preview">
          <div class="ide-head">Where it goes<span class="meta" id="st-layer"></span></div>
          <div class="sg-where" id="sg-where"></div>
          <div class="ide-tabs" id="ide-tabs" role="tablist" aria-label="Files Create will write"></div>
          <div class="ide-path" id="ide-path"><span id="ide-path-text"></span><label class="check" title="Change the generated text yourself before creating it"><span class="switch"><input type="checkbox" id="sg-edit"><span></span></span>edit before creating</label></div>
          <div class="ide-editor" id="ide-editor"><div class="ide-gutter" id="ide-gutter"></div><div class="ide-code"><pre id="ide-hl" aria-hidden="true"></pre><textarea id="ide-text" spellcheck="false" autocomplete="off" aria-label="Generated file" readonly aria-autocomplete="list" aria-controls="lang-pop"></textarea>
            <div class="lang-pop" id="lang-pop" role="listbox" aria-label="Suggestions" hidden></div></div></div>
          <div class="lang-doc" id="lang-doc" aria-live="polite"></div>
          <div class="lang-lint" id="lang-lint"></div>
        </section>
      </div>
      <div class="sg-done" id="sg-done" hidden>
        <header><h2 id="sg-done-title">Created</h2><p id="sg-done-text"></p></header>
        <div class="created" id="sg-created"></div>
        <div><h4 style="margin:0 0 10px; font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted)">What next</h4><div class="sg-next" id="sg-next-actions"></div></div>
      </div>
    </section>

    <section id="view-health" class="view" hidden>
      <div class="panel">
        <div class="head"><h2>Projects</h2><span style="flex:1"></span>
          <button class="btn" id="pj-show-new">✦ New project</button><button class="btn" id="pj-show-clone">⇣ Clone from Git</button></div>
        <div class="list" id="pj-recent" style="max-height:260px"></div>
        <div id="pj-new" hidden>
          <div class="split" style="min-height:0">
            <div class="form">
              <label class="f" for="pj-name">Project name</label><input type="text" id="pj-name" value="my-product">
              <label class="f" for="pj-dir">Folder</label><input type="text" id="pj-dir">
              <label class="f" for="pj-release">Yocto release</label><select id="pj-release"></select>
              <label class="f" for="pj-tool">Set up with</label><select id="pj-tool"><option value="kas">kas: one kas.yml with pinned repositories (recommended)</option><option value="bitbake-setup">bitbake-setup: the Yocto Project's official templates</option></select>
              <div class="help" id="pj-tool-help"></div>
              <div class="help">Both are LTS. Wrynose uses split repositories, SPDX 3 and sbom-cve-check.</div>
              <label class="f" for="pj-machine">MACHINE / DISTRO / image</label>
              <div style="display:flex;gap:8px"><select id="pj-machine"></select><input type="text" id="pj-distro" value="poky"><select id="pj-target"></select></div>
              <label class="f" for="pj-runtime">Runtime</label><select id="pj-runtime"></select>
              <div data-kas><label class="check" style="margin-top:12px"><span class="switch"><input type="checkbox" id="pj-layer" checked><span></span></span>create meta-&lt;name&gt; product layer</label>
              <label class="f" for="pj-owner">Copyright owner</label><input type="text" id="pj-owner" placeholder="Your company"></div>
              <div style="display:flex;justify-content:flex-end;margin-top:12px"><button class="btn primary" id="pj-create">✦ Create project</button></div>
            </div>
            <div class="files list" id="pj-files"></div>
          </div>
        </div>
        <div id="pj-clone" class="form" hidden>
          <label class="f" for="pj-url">Repository URL</label><input type="text" id="pj-url" placeholder="https://github.com/org/product.git or git@github.com:org/product.git">
          <label class="f" for="pj-dest">Destination folder</label><input type="text" id="pj-dest">
          <label class="f" for="pj-branch">Branch or tag (optional)</label><input type="text" id="pj-branch">
          <div class="help">Runs git clone as a job you can follow in Builds; the guided setup opens when it finishes.</div>
          <div style="display:flex;justify-content:flex-end;margin-top:12px"><button class="btn primary" id="pj-clone-go">⇣ Clone</button></div>
        </div>
      </div>
      <div class="panel">
        <div class="head"><h2>Build notifications</h2><span style="flex:1"></span><span class="hint">Sent by the build service: they arrive even with no TUI or browser open.</span></div>
        <div class="form" style="padding-top:10px">
          <div style="display:flex;gap:18px;flex-wrap:wrap;align-items:center">
            <label class="check"><span class="switch"><input type="checkbox" id="nt-success"><span></span></span>success</label>
            <label class="check"><span class="switch"><input type="checkbox" id="nt-failed"><span></span></span>failed</label>
            <label class="check"><span class="switch"><input type="checkbox" id="nt-cancelled"><span></span></span>cancelled</label>
            <label class="check"><span class="switch"><input type="checkbox" id="nt-desktop"><span></span></span>desktop</label>
            <label class="check">longer than <input type="text" id="nt-min" style="width:70px"> s</label>
          </div>
          <label class="f" for="nt-webhook">Webhook</label>
          <div style="display:flex;gap:8px"><input type="text" id="nt-webhook" placeholder="https://ntfy.sh/your-topic or a Slack/Teams/Mattermost webhook" style="flex:1">
            <select id="nt-format"><option value="ntfy">ntfy</option><option value="slack">Slack/Teams text</option><option value="json">JSON</option></select>
            <button class="btn primary" id="nt-save">Save</button></div>
        </div>
      </div>
      <div class="panel">
        <div class="head"><h2>Set up a project</h2><span style="flex:1"></span><span class="hint">Finds kas files, init scripts, build directories and launcher scripts; the new profile becomes active at once.</span></div>
        <div class="tools"><input type="search" id="setup-dir" placeholder="Project directory, e.g. /home/me/src/product (Enter scans)"><button class="btn primary" id="setup-scan">Scan</button></div>
        <div class="split" style="min-height:0">
          <div class="list" id="setup-found" style="max-height:420px"></div>
          <div class="form" id="setup-form">
            <label class="f" for="sp-mode">Runtime</label>
            <select id="sp-mode"><option>kas-container</option><option>kas</option><option>host</option><option>container</option><option>wrapper</option></select>
            <div class="help">kas-container: kas and Yocto in a container (recommended) · kas: kas on the host · host: initialised Poky/OE-Core · container: your image · wrapper: a project script that runs kas.</div>
            <label class="f" for="sp-name">Profile name</label><input type="text" id="sp-name">
            <label class="f" data-mode="kas kas-container" for="sp-kas_file">kas configuration</label><input type="text" id="sp-kas_file" data-mode="kas kas-container">
            <label class="f" data-mode="host container" for="sp-init_script">Init script</label><input type="text" id="sp-init_script" data-mode="host container">
            <label class="f" data-mode="host container" for="sp-build_dir">Build directory</label><input type="text" id="sp-build_dir" data-mode="host container">
            <label class="f" data-mode="wrapper" for="sp-launcher">Launcher script</label><input type="text" id="sp-launcher" data-mode="wrapper">
            <div class="help" data-mode="wrapper">The script must accept kas subcommands (build, dump…) and forward <code>shell -c COMMAND</code>.</div>
            <label class="f" for="sp-environment">Environment (KEY=VALUE per line)</label><textarea id="sp-environment" rows="3" style="background:var(--bg2);border:1px solid var(--line);border-radius:8px;padding:6px 10px;font:12px var(--mono);color:var(--fg)"></textarea>
            <div class="help">kas-container: KAS_WORK_DIR on a Linux filesystem. wrapper: the variable that selects the configuration, e.g. YML=boards/board.yml.</div>
            <label class="f" for="sp-machine">MACHINE / DISTRO / targets</label>
            <div style="display:flex;gap:8px"><input type="text" id="sp-machine" placeholder="MACHINE"><input type="text" id="sp-distro" placeholder="DISTRO"><input type="text" id="sp-targets" placeholder="targets"></div>
            <ul class="checks" id="sp-checks" style="margin-top:12px"></ul>
            <div style="display:flex;justify-content:flex-end;margin-top:8px"><button class="btn primary" id="sp-save">Save and use</button></div>
          </div>
        </div>
      </div>
      <div class="panel">
        <div class="head"><h2>What this release can do</h2><span class="meta" id="cap-release"></span><span style="flex:1"></span><span class="hint">Checked in this project's layers and BitBake; features it lacks are not offered.</span></div>
        <div class="caps" id="cap-rows"></div>
      </div>
      <div class="panel">
      <div class="head"><h2>Health, setup and configuration</h2><span style="flex:1"></span><span class="hint">Literal local.conf values; run bitbake -e for evaluated ones.</span>
        <button class="btn" id="work-btn" title="Disk used per recipe in tmp/work">tmp/work usage</button></div>
      <pre class="log" id="work-usage" hidden style="min-height:0;max-height:360px"></pre>
      <div class="list"><table><thead><tr><th>Status</th><th>Check</th><th>Details</th></tr></thead><tbody id="health-rows"></tbody></table></div>
      </div>
    </section>
  </main>
</div>
<div id="toasts" aria-live="polite"></div>

<dialog id="queue-dialog" aria-label="Queue an operation">
  <form method="dialog" class="body" id="queue-form">
    <h2>Queue an operation</h2>
    <input type="search" id="op-filter" placeholder="Filter: build, devtool, sbom, layers, sdk… (↑ ↓ choose, Enter queues, Esc closes)">
    <select id="op-select" size="8" aria-label="Operation"></select>
    <div class="fields" id="op-fields"></div>
    <div class="preview" id="op-preview"></div>
    <div class="actions"><button class="btn" value="cancel" formnovalidate>Cancel</button><button class="btn primary" id="op-submit" value="default">Queue</button></div>
  </form>
</dialog>

<dialog id="palette" aria-label="Command palette">
  <div class="body"><input type="search" id="pal-input" placeholder="Go to, queue, open a build…"><ul id="pal-list"></ul><div class="hint">↑ ↓ choose · Enter runs · Esc closes</div></div>
</dialog>

<dialog id="keys-dialog" aria-label="Keyboard shortcuts">
  <div class="body">
    <h2>Keyboard shortcuts</h2>
    <table class="keys"><tbody id="keys-rows"></tbody></table>
    <div class="actions"><button class="btn" id="keys-close">Close</button></div>
  </div>
</dialog>

<script>
"use strict";
const $ = (id) => document.getElementById(id);
const token = (new URLSearchParams(location.hash.slice(1))).get("token") || sessionStorage.getItem("bitloom-token") || "";
if (token) { sessionStorage.setItem("bitloom-token", token); history.replaceState(null, "", location.pathname); }
const GLYPH = {success: "✔", failed: "✖", running: "●", queued: "◌", cancelling: "◐", cancelled: "■", interrupted: "⚠", unknown: "·", skipped: "↷"};
const VIEWS = ["builds", "recipes", "tasklogs", "image", "compliance", "studio", "practices", "health", "migrate"];
const KEYS = [["1 – 6", "Switch section"], ["Ctrl+K", "Command palette: sections, operations, profiles, builds"], ["/", "Search in the current section"],
  ["Esc", "Leave a field / close a dialog"], ["j / k", "Next / previous operation"], ["b", "Build the target"], ["q", "Queue any operation"],
  ["t", "Edit the build target"], ["s", "Force stop the selected operation"], ["g", "Graceful stop (BitBake client SIGINT)"],
  ["r", "Retry the selected operation"], ["e", "Toggle errors only"], ["o / u / w / m / d", "Output / Summary / Warnings / Timings / Compare tab"], ["?", "This help"]];
const ICONS = {layer: "▤", distro: "◎", machine: "▣", image: "◉", recipe: "✎", append: "⊕"};
let consoleRows = [], state = null, actions = [], selected = null, view = "builds", tab = "output", logOffset = -1, logFor = null, typingTimer = null;
let lastStatus = {}, studioKind = "distro", studioFields = [], studioValues = {};

async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {"X-Bitloom-Token": token, "Content-Type": "application/json", ...(options.headers || {})}});
  const data = await response.json().catch(() => ({error: response.statusText}));
  if (!response.ok) throw Object.assign(new Error(data.error || response.statusText), {field: data.field});
  return data;
}
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value; else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value); else node.setAttribute(key, value);
  }
  for (const child of children) if (child !== null && child !== undefined) node.append(child);
  return node;
}

/* Toasts: stacked, pausable, with countdown and optional action. */
function toast(title, message = "", type = "info", action = null) {
  const host = $("toasts");
  while (host.children.length >= 5) host.firstElementChild.remove();
  const life = type === "error" ? 9000 : 5000;
  const timer = el("div", {class: "timer"});
  const close = el("button", {class: "x", "aria-label": "Dismiss", text: "✕"});
  const node = el("div", {class: "toast " + type, role: type === "error" ? "alert" : "status"},
    el("div", {class: "ico", text: {success: "✓", error: "!", warning: "!", info: "i"}[type]}),
    el("div", {}, el("b", {text: title}), message ? el("p", {text: message}) : null, action ? el("button", {class: "btn act", text: action.label, onclick: () => { action.run(); dismiss(); }}) : null),
    close, timer);
  const animation = timer.animate([{transform: "scaleX(1)"}, {transform: "scaleX(0)"}], {duration: life, easing: "linear"});
  const dismiss = () => { if (node.classList.contains("leaving")) return; node.classList.add("leaving"); setTimeout(() => node.remove(), 340); };
  animation.onfinish = dismiss;
  node.addEventListener("mouseenter", () => animation.pause());
  node.addEventListener("mouseleave", () => animation.play());
  close.addEventListener("click", dismiss);
  host.append(node);
}
document.addEventListener("click", (event) => {
  const button = event.target.closest(".btn");
  if (!button || button.disabled) return;
  const rect = button.getBoundingClientRect(), size = Math.max(rect.width, rect.height);
  const ripple = el("span", {class: "ripple"});
  ripple.style.cssText = `width:${size}px;height:${size}px;left:${event.clientX - rect.left - size / 2}px;top:${event.clientY - rect.top - size / 2}px`;
  button.append(ripple); setTimeout(() => ripple.remove(), 600);
});

function size(bytes) { const units = ["B", "KiB", "MiB", "GiB", "TiB"]; let i = 0; while (bytes >= 1024 && i < 4) { bytes /= 1024; i++; } return bytes.toFixed(1) + " " + units[i]; }
function elapsed(row) {
  if (row.status === "queued") return "—";
  const end = row.finished ? new Date(row.finished) : new Date();
  let s = Math.max(0, Math.round((end - new Date(row.started)) / 1000));
  const h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60; s %= 60;
  return (h ? h + "h " : "") + (h || m ? m + "m " : "") + s + "s";
}
function glyph(status) { return status === "running" ? el("span", {class: "spin", "aria-label": "running"}) : el("span", {class: "glyph s-" + status, text: GLYPH[status] || "·"}); }
function ring(svg, fraction, label) {
  const bar = svg.querySelector(".bar"), circumference = 150.8;
  bar.style.strokeDashoffset = String(circumference * (1 - Math.max(0, Math.min(1, fraction))));
  svg.querySelector("text").textContent = label;
}
function countTo(node, target, suffix = "") {
  const start = parseFloat(node.dataset.value || "0"), began = performance.now();
  node.dataset.value = String(target);
  const step = (now) => { const t = Math.min(1, (now - began) / 600), eased = 1 - Math.pow(1 - t, 3);
    node.textContent = Math.round(start + (target - start) * eased) + suffix; if (t < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}
function profile() { return state && state.profiles.find((p) => p.name === $("profile").value); }
const prof = () => encodeURIComponent($("profile").value || (state && state.active) || "");

function renderLog(target, text, query, append = false) {
  if (!append) target.textContent = "";
  const fragment = document.createDocumentFragment();
  const needle = (query || "").toLowerCase();
  // Chunks end with a newline: that is the end of the last line, not an empty line after it.
  const lines = text.split("\n");
  if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();
  for (const line of lines) {
    const span = el("span", {class: append ? "new" : ""});
    if (line.startsWith("$ ")) span.classList.add("l-cmd");
    else if (/ERROR:|FAILED|error:/.test(line)) span.classList.add("l-err");
    else if (line.includes("WARNING:")) span.classList.add("l-warn");
    else if (line.includes("NOTE:")) span.classList.add("l-note");
    if (needle) {
      let rest = line, index;
      while ((index = rest.toLowerCase().indexOf(needle)) >= 0) {
        span.append(rest.slice(0, index), el("mark", {text: rest.slice(index, index + needle.length)}));
        rest = rest.slice(index + needle.length);
      }
      span.append(rest);
    } else span.textContent = line;
    fragment.append(span, "\n");
  }
  target.append(fragment);
}

function notifyTransitions(rows) {
  for (const row of rows) {
    const before = lastStatus[row.id];
    if (pendingScan && row.id === pendingScan && before && before !== row.status && row.status === "success") {
      pendingScan = null; toast("Grype scan finished", "Findings updated", "success", {label: "Show", run: () => { setView("compliance"); }});
      if (view === "compliance") loadVulns();
    }
    if (pendingSetup && row.id === pendingSetup.id && before && before !== row.status && ["success", "failed"].includes(row.status)) {
      const done = pendingSetup; pendingSetup = null;
      if (row.status === "success") {
        api("/api/setup/save", {method: "POST", body: JSON.stringify({profile: done.profile})}).then(async (saved) => {
          $("profile").textContent = ""; await refresh(); $("profile").value = saved.active; $("target").dataset.touched = ""; renderState(); loadProjects();
          toast("Project ready", `${done.dest} · profile ${saved.active} is active`, "success", {label: "Build it", run: () => queue("build", {target: $("target").value})});
        }).catch((error) => toast("Save the profile", error.message + " · set it up from Configuration", "error"));
      }
    }
    if (pendingClone && row.id === pendingClone.id && before && before !== row.status && row.status === "success") {
      const destination = pendingClone.dest; pendingClone = null;
      toast("Clone finished", destination, "success", {label: "Set it up", run: () => { setView("health"); $("setup-dir").value = destination; scanSetup(); }});
    }
    if (before && before !== row.status) {
      const open = {label: "Open", run: () => { setView("builds"); select_(row.id); }};
      if (["success", "failed"].includes(row.status) && localStorage.getItem("bitloom-notify") === "1" && "Notification" in window && Notification.permission === "granted" && document.hidden) {
        new Notification(`Bitloom: ${row.title} ${row.status}`, {body: `${row.profile} · ${elapsed(row)}`, tag: row.id});
      }
      if (row.status === "success") toast("Build succeeded", `${row.title} · ${elapsed(row)}`, "success", open);
      else if (row.status === "failed" && row.code === -1) toast("Did not start", `${row.title} · the command could not run · see Output`, "error", {label: "Open output", run: () => { setView("builds"); select_(row.id); setTab("output"); }});
      else if (row.status === "failed") toast("Build failed", `${row.title} · exit ${row.code} · see Summary`, "error", {label: "Open summary", run: () => { setView("builds"); select_(row.id); setTab("summary"); }});
      else if (row.status === "running") toast("Build started", row.title, "info", open);
      else if (row.status === "cancelled") toast("Build cancelled", row.title, "warning");
    }
    lastStatus[row.id] = row.status;
  }
}

function renderState() {
  const select = $("profile"), current = select.value || state.active;
  if (select.options.length !== state.profiles.length) {
    select.textContent = "";
    for (const p of state.profiles) select.append(el("option", {value: p.name, text: p.name + (p.shared ? " (team)" : "")}));
  }
  select.value = state.profiles.some((p) => p.name === current) ? current : state.active;
  const p = profile();
  $("release-chip").textContent = p ? p.release : "release …";
  $("release-chip").className = "chip" + (p && p.release.includes("LTS") ? " lts" : "");
  $("context").textContent = p ? `${p.mode} · MACHINE ${p.machine || "?"} · DISTRO ${p.distro || "?"} · ${p.build}` : "";
  if (!$("target").dataset.touched && p) $("target").value = (p.targets || [])[0] || "";
  const service = state.service;
  $("service-dot").className = "dot " + (service.error ? "err" : service.outdated ? "warn" : "ok");
  $("service-label").textContent = service.error ? "service unavailable" : `service ${service.pid}` + (service.outdated ? " · older, restart when idle" : "");
  notifyTransitions(state.history);
  const rows = state.history.filter((row) => !p || row.profile === p.name);
  const recent = rows[0];
  $("c-status").textContent = recent ? (GLYPH[recent.status] || "·") + " " + recent.status.toUpperCase() : "IDLE";
  $("c-status").className = "value " + (recent ? "s-" + recent.status : "");
  $("c-title").textContent = recent ? recent.title : "No jobs in this profile";
  const progress = recent ? recent.progress : [0, 0], setscene = recent ? recent.setscene : [0, 0];
  const fraction = recent && recent.status === "success" ? 1 : progress[1] ? Math.min(progress[0] / progress[1], 0.99) : 0;
  ring($("c-ring"), fraction, progress[1] || (recent && recent.status === "success") ? Math.round(100 * fraction) + "%" : "—");
  if (progress[1]) { const node = $("c-tasks"); countTo(node, recent.status === "success" ? progress[1] : progress[0], ` / ${progress[1]}`); } else $("c-tasks").textContent = "no task count";
  $("c-sstate").textContent = (setscene && setscene[1] ? `${setscene[0]} / ${setscene[1]} from sstate · ` : "") + state.history.filter((r) => r.status === "queued").length + " queued";
  const host = state.host;
  if (host.cpu !== null && host.cpu !== undefined) $("c-cpu").textContent = `CPU ${host.cpu.toFixed(0)}% · load ${(host.load || []).join(" ")}`;
  const history = host.cpu_history || [];
  if (history.length > 1) {
    const step = 120 / (history.length - 1), points = history.map((v, i) => `${(i * step).toFixed(1)},${(34 - v / 100 * 32).toFixed(1)}`);
    $("c-spark").querySelector(".line").setAttribute("d", "M" + points.join(" L"));
    $("c-spark").querySelector(".area").setAttribute("d", "M0,34 L" + points.join(" L") + " L120,34 Z");
  }
  if (host.ram_total) $("c-ram").textContent = `RAM ${size(host.ram_used)} of ${size(host.ram_total)}`;
  if (host.disk_total) {
    const used = host.disk_used / host.disk_total;
    $("c-disk-free").textContent = size(host.disk_free) + " free";
    $("c-disk-meter").className = "meter" + (used > .85 ? " hot" : "");
    $("c-disk-meter").firstElementChild.style.width = (100 * used).toFixed(0) + "%";
    $("c-disk").textContent = `${(100 * used).toFixed(0)}% used of ${size(host.disk_total)}`;
  }
  renderHistory(p);
  renderDetail();
}

let historyPainted = false;
function historyRow(id, onclick) {
  return el("div", {class: "row", role: "option", tabindex: "-1", "data-id": id, onclick},
    el("span", {class: "glyph"}), el("span", {class: "title"}), el("span", {class: "meta"}));
}
function paintRow(node, status, title, tooltip, tag, meta) {
  // Touch only what changed, so the list stays still while jobs tick.
  const key = status + "\u0000" + title + "\u0000" + tag + "\u0000" + meta;
  if (node.dataset.paint === key) return;
  const old = node.dataset.paint ? node.dataset.paint.split("\u0000") : [];
  if (old[0] !== status) node.firstChild.replaceWith(glyph(status));
  const name = node.children[1];
  if (old[1] !== title || old[2] !== tag) {
    name.textContent = title; name.title = tooltip;
    if (tag) name.append(el("span", {class: "meta", text: "  " + tag}));
  }
  if (old[3] !== meta) node.children[2].textContent = meta;
  node.dataset.paint = key;
}
function renderHistory(p) {
  const list = $("history"), scroll = list.scrollTop;
  const existing = new Map([...list.querySelectorAll(".row")].map((node) => [node.dataset.id, node]));
  const wanted = [];
  for (const row of state.history) {
    let node = existing.get(row.id);
    if (!node) {
      node = historyRow(row.id, () => select_(row.id));
      if (historyPainted) {                                  // a build that just appeared slides in on top
        node.classList.add("arrive");
        node.addEventListener("animationend", () => node.classList.remove("arrive"), {once: true});
      }
    }
    paintRow(node, row.status, row.title, row.title, row.profile !== (p && p.name) ? row.profile : "", elapsed(row));
    wanted.push(node);
  }
  let empty = list.querySelector(".empty");
  if (!state.history.length) {
    empty = empty || el("div", {class: "empty", text: "No operations yet. Press b to build or q for any operation."});
    wanted.unshift(empty);
  }
  if (consoleRows.length) {
    wanted.push(list.querySelector(".group-label") || el("div", {class: "group-label", text: "CONSOLE BUILDS · started outside Bitloom"}));
    for (const row of consoleRows) {
      const id = "console:" + row.path;
      const node = existing.get(id) || historyRow(id, () => select_(id));
      paintRow(node, row.status, new Date(row.modified * 1000).toLocaleString() + "  " + row.machine, row.path, "", size(row.size));
      wanted.push(node);
    }
  }
  // Reconcile in order: reuse nodes, move only those out of place, drop the rest.
  const keep = new Set(wanted);
  for (const node of [...list.children]) if (!keep.has(node)) node.remove();
  wanted.forEach((node, i) => { if (list.children[i] !== node) list.insertBefore(node, list.children[i] || null); });
  for (const node of wanted) if (node.dataset.id) node.classList.toggle("selected", node.dataset.id === selected);
  list.scrollTop = scroll;
  historyPainted = true;
  if (!selected && state.history.length) select_(state.history[0].id);
}

// Target combobox: the image recipes found in the project, filtered as you type; any recipe still works.
let imageRows = null, imagesFor = "", comboActive = -1, comboItems = [];
async function loadImages() {
  const key = prof();
  if (imageRows && imagesFor === key) return;
  imagesFor = key; imageRows = null;
  try { const rows = (await api(`/api/images?profile=${key}`)).rows; if (imagesFor === key) imageRows = rows; } catch (error) { imageRows = []; }
}
function highlight(text, needle) {
  const at = needle ? text.toLowerCase().indexOf(needle) : -1;
  if (at < 0) return [document.createTextNode(text)];
  return [document.createTextNode(text.slice(0, at)), el("mark", {text: text.slice(at, at + needle.length)}), document.createTextNode(text.slice(at + needle.length))];
}
function renderCombo(filter = true) {
  const list = $("target-list"), input = $("target"), value = input.value.trim(), needle = filter ? value.toLowerCase() : "";
  list.textContent = ""; comboItems = []; comboActive = -1;
  if (!imageRows) { list.append(el("div", {class: "combo-empty", text: "Looking for images in the project…"})); return; }
  const rows = imageRows.filter((row) => !needle || (row.name + " " + row.summary + " " + row.layer).toLowerCase().includes(needle));
  const groups = [["In this project", rows.filter((r) => r.configured || r.built)], ["Images in your layers", rows.filter((r) => !r.configured && !r.built && !r.example)], ["Examples and test images", rows.filter((r) => !r.configured && !r.built && r.example)]];
  for (const [label, items] of groups) {
    if (!items.length) continue;
    list.append(el("div", {class: "combo-group", text: label}));
    for (const row of items) {
      const tags = el("span", {class: "tags"});
      if (row.configured) tags.append(el("span", {class: "tag accent", text: "kas target"}));
      if (row.built) tags.append(el("span", {class: "tag ok", text: "built"}));
      if (row.layer) tags.append(el("span", {class: "tag", text: row.layer}));
      const item = el("div", {class: "combo-item", role: "option", id: "target-opt-" + comboItems.length, "aria-selected": String(row.name === value),
        onmousedown: (event) => { event.preventDefault(); pickTarget(row.name); }, onmousemove: () => activate(comboItems.indexOf(item))},
        el("span", {class: "name"}, ...highlight(row.name, needle)), tags, ...(row.summary || !row.path ? [el("span", {class: "sum", text: row.summary || "Target from the kas configuration"})] : []));
      item.title = row.path || row.name;
      list.append(item); comboItems.push(item);
    }
  }
  if (!comboItems.length) list.append(el("div", {class: "combo-empty", text: value ? `No image matches “${value}”. Press Enter to build it anyway: any recipe is a valid target.` : "No image recipes found in this project's layers."}));
  list.append(el("div", {class: "combo-foot"}, el("span", {}, el("kbd", {text: "↑↓"}), " choose"), el("span", {}, el("kbd", {text: "Enter"}), " pick, again to build"), el("span", {}, el("kbd", {text: "Esc"}), " close")));
  if (needle && comboItems.length) activate(0);
}
function activate(i) {
  comboItems.forEach((item, n) => item.classList.toggle("active", n === i));
  comboActive = i;
  $("target").setAttribute("aria-activedescendant", i >= 0 ? "target-opt-" + i : "");
  if (i >= 0) comboItems[i].scrollIntoView({block: "nearest"});
}
async function openCombo(filter = false) {
  const combo = $("target-combo"), list = $("target-list");
  if (!list.hidden) return;
  list.hidden = false; combo.classList.add("open"); $("target").setAttribute("aria-expanded", "true");
  renderCombo(filter);
  const right = list.getBoundingClientRect().right;      // keep it on screen on narrow windows
  list.style.left = right > innerWidth - 12 ? `${Math.min(0, innerWidth - 12 - right)}px` : "0";
  await loadImages();
  if (!list.hidden) renderCombo(filter);
}
function closeCombo() {
  $("target-list").hidden = true; $("target-combo").classList.remove("open");
  $("target").setAttribute("aria-expanded", "false"); $("target").removeAttribute("aria-activedescendant"); comboActive = -1;
}
function pickTarget(name) {
  $("target").value = name; $("target").dataset.touched = "1"; closeCombo(); $("target").focus();
}

async function loadConsole() {
  try { consoleRows = (await api(`/api/console?profile=${prof()}`)).rows; } catch (error) { consoleRows = []; }
}
function consoleRow() { return selected && selected.startsWith("console:") ? consoleRows.find((row) => "console:" + row.path === selected) : null; }
function current() { return state && state.history.find((row) => row.id === selected); }

function setProgress(status, progress, eta) {
  const bar = $("d-progress"), box = $("d-prog"), known = progress && progress[1];
  box.hidden = !status || (!known && !["running", "success", "queued"].includes(status));
  box.className = "prog " + status;
  bar.className = "progress " + status + (status === "running" && !known ? " indeterminate" : "");
  // BitBake's "task N of M" counts tasks that need no rerun too: N reaches M when the last task *starts*.
  const lastRunning = status === "running" && known && progress[0] >= progress[1];
  // Only a successful job is complete: a failed or cancelled one stopped during its last started task.
  const fraction = status === "success" ? 1 : known ? Math.min(progress[0] / progress[1], 0.99) : 0;
  const width = (100 * fraction).toFixed(1) + "%";
  bar.firstElementChild.style.width = width; bar.lastElementChild.style.left = width;
  bar.setAttribute("aria-valuenow", (100 * fraction).toFixed(0));
  const text = $("d-progress-text"); text.textContent = "";
  const sep = () => el("span", {class: "sep", text: "·"});
  // A finished build is done whatever the last "task N of M" line said.
  if (status === "success") text.append(el("b", {text: "done"}), ...(known ? [sep(), `${progress[1].toLocaleString()} tasks`] : []));
  else if (known) text.append(el("b", {text: progress[0].toLocaleString()}), ` / ${progress[1].toLocaleString()} tasks`, ...(lastRunning ? [sep(), "last task running"] : []));
  else if (status !== "success") text.append(status === "running" ? "waiting for BitBake task counts…" : status === "queued" ? "queued" : "");
  if (eta) text.append(sep(), `ETA ~${eta.remaining}`);
  if (eta && eta.basis) text.title = "ETA based on " + eta.basis;
  $("d-progress-pct").textContent = known || status === "success" ? (100 * fraction).toFixed(fraction >= 0.995 || fraction === 0 ? 0 : 1) + "%" : "";
}
function renderDetail() {
  const outside = consoleRow();
  const set = (node, status) => { node.textContent = ""; node.append(glyph(status)); };
  if (outside) {
    for (const id of ["stop-btn", "graceful-btn", "retry-btn"]) $(id).disabled = true;
    set($("d-glyph"), outside.status);
    $("d-title").textContent = "Console build " + outside.name;
    $("d-meta").textContent = `${outside.status} · ${outside.machine} · not started by Bitloom`;
    setProgress(outside.status, null);
    return;
  }
  const row = current();
  const active = row && ["running", "queued", "cancelling"].includes(row.status);
  // Graceful stop signals the BitBake client: only host and managed-container runtimes expose it (as in the TUI).
  const mode = row && ((state.profiles.find((p) => p.name === row.profile) || {}).mode);
  const argv = row ? (Array.isArray(row.argv) ? row.argv : JSON.parse(row.argv || "[]")) : [];
  const drainable = (mode === "host" || mode === "container") && argv[0] === "bitbake";
  $("stop-btn").disabled = !active; $("graceful-btn").disabled = !row || row.status !== "running" || !drainable; $("retry-btn").disabled = !row || active;
  $("graceful-btn").title = row && !drainable ? "Graceful stop needs a host or container BitBake client; kas runtimes stop with s (force), which stops the owned container" : "Graceful stop: one SIGINT to the BitBake client (g)";
  if (!row) return;
  set($("d-glyph"), row.status);
  $("d-title").textContent = row.title;
  $("d-meta").textContent = `${row.status} · ${elapsed(row)}${row.code !== null && row.code !== undefined ? " · exit " + row.code : ""} · ${row.profile}`;
  setProgress(row.status, row.progress, row.eta);
}

function select_(id) {
  if (selected === id) return;
  selected = id; logOffset = -1; logFor = null;
  for (const node of document.querySelectorAll("#history .row")) node.classList.toggle("selected", node.dataset.id === id);
  renderDetail(); loadTab();
}

async function loadTab() {
  const outside = consoleRow(), row = current();
  if (!row && !outside) return;
  $("log-tools").hidden = tab !== "output";
  const log = $("log");
  try {
    if (outside) {
      const base = `profile=${prof()}&path=${encodeURIComponent(outside.path)}`;
      if (tab !== "output") { renderLog(log, (await api(`/api/console/report?${base}`))[tab] || "", ""); return; }
      const query = $("log-search").value;
      const data = await api(`/api/console/log?${base}&q=${encodeURIComponent(query)}&errors=${$("errors-only").checked ? 1 : 0}`);
      renderLog(log, data.text, query); logFor = selected; return;
    }
    if (tab === "compare") { renderLog(log, (await api(`/api/jobs/${row.id}/compare`)).text, ""); return; }
    if (tab !== "output") { renderLog(log, (await api(`/api/jobs/${row.id}/report`))[tab] || "", ""); return; }
    const query = $("log-search").value, errors = $("errors-only").checked;
    if (query || errors) {
      const data = await api(`/api/jobs/${row.id}/log?q=${encodeURIComponent(query)}&errors=${errors ? 1 : 0}`);
      renderLog(log, data.text, query); logFor = null; return;
    }
    const append = logFor === row.id && logOffset >= 0;
    const data = await api(`/api/jobs/${row.id}/log?offset=${append ? logOffset : -1}`);
    if (!append) log.textContent = "";
    if (data.text) renderLog(log, data.text, "", append);
    logOffset = data.offset; logFor = row.id;
    if ($("follow").checked) log.scrollTop = log.scrollHeight;
  } catch (error) { renderLog(log, String(error.message), ""); }
}

let consoleCheck = 0;
async function refresh() {
  if (Date.now() - consoleCheck > 15000 && state) { consoleCheck = Date.now(); await loadConsole(); }
  try { state = await api("/api/state"); renderState(); }
  catch (error) { $("service-dot").className = "dot err"; $("service-label").textContent = error.message; }
  const row = current();
  if (view === "builds" && tab === "output" && row && !consoleRow() && (row.status === "running" || row.status === "cancelling" || logFor !== row.id)) loadTab();
}

function setView(name) {
  view = name; document.body.dataset.view = name;
  for (const section of VIEWS) { const node = $("view-" + section); const show = section === name; if (show && node.hidden) { node.hidden = false; node.style.animation = "none"; void node.offsetWidth; node.style.animation = ""; } else node.hidden = !show; }
  for (const button of document.querySelectorAll("nav button")) button.classList.toggle("active", button.dataset.view === name);
  if (name === "recipes") loadMeta(); if (name === "tasklogs") loadTasks(); if (name === "health") { loadHealth(); loadProjects(); loadNotifications(); if (!setupCandidates.length && !$("setup-dir").value) { const p = profile(); $("setup-dir").value = p ? p.root : ""; scanSetup(); } }
  if (name === "compliance") { loadCompliance(); loadVulns(); } if (name === "studio") loadStudio(); if (name === "image") loadImage(); if (name === "practices") loadPractices(); if (name === "migrate") loadMigrate();
  if (name === "builds") requestAnimationFrame(moveInk);
}
function moveInk() {
  const active = document.querySelector("#tabs button.active"), ink = document.querySelector("#tabs .ink");
  if (active && ink) { ink.style.left = active.offsetLeft + "px"; ink.style.width = active.offsetWidth + "px"; }
}
function setTab(name) {
  tab = name; logFor = null;
  for (const button of document.querySelectorAll("#tabs button")) button.classList.toggle("active", button.dataset.tab === name);
  moveInk(); loadTab();
}
function skeleton(body, columns) {
  body.textContent = "";
  for (let i = 0; i < 4; i++) body.append(el("tr", {}, el("td", {colspan: String(columns)}, el("div", {class: "skeleton", style: `width:${60 + i * 9}%`}))));
}
let metaTimer;
// Recipes: layers on the left, folders (recipes-core, classes…) that open on demand, kind filter.
let metaRows = [], metaLayer = "", metaKind = "all", metaFor = "";
const META_KINDS = [["all", "All"], ["bb", "Recipes"], ["image", "Images"], ["bbappend", "Appends"], ["bbclass", "Classes"], ["yaml", "kas"]];
const EXAMPLE_LAYERS = new Set(["meta-selftest", "meta-skeleton"]);
async function loadMeta(fresh = false) {
  const box = $("meta-groups");
  if (!metaRows.length || metaFor !== prof() || fresh) {
    box.textContent = ""; skeletonIn(box);
    try { metaRows = (await api(`/api/metadata?profile=${prof()}${fresh ? "&fresh=1" : ""}`)).rows; metaFor = prof(); }
    catch (error) { box.textContent = ""; box.append(el("div", {class: "empty", text: "Could not read the workspace: " + error.message})); return; }
  }
  renderLayers(); renderMeta();
}
function skeletonIn(box) { for (let i = 0; i < 6; i++) box.append(el("div", {class: "skeleton", style: `width:${50 + (i * 37) % 45}%`})); }
function metaMatch(row, needle) {
  if (metaKind === "image" ? !row.image : metaKind !== "all" && row.kind !== metaKind) return false;
  return !needle || `${row.name} ${row.kind} ${row.detail} ${row.layer}`.toLowerCase().includes(needle);
}
function renderLayers() {
  const list = $("layer-list"), needle = $("meta-search").value.trim().toLowerCase();
  const counts = new Map(); let total = 0;
  for (const row of metaRows) if (row.kind !== "layer" && metaMatch(row, needle)) { counts.set(row.layer, (counts.get(row.layer) || 0) + 1); total++; }
  const layers = metaRows.filter((row) => row.kind === "layer");
  layers.sort((a, b) => EXAMPLE_LAYERS.has(a.name) - EXAMPLE_LAYERS.has(b.name) || (counts.get(b.name) || 0) - (counts.get(a.name) || 0) || a.name.localeCompare(b.name));
  list.textContent = "";
  const item = (name, label, count, detail, extra = "") => {
    const node = el("div", {class: "layer-item" + (metaLayer === name ? " selected" : "") + extra, role: "option", tabindex: "0", "aria-selected": String(metaLayer === name),
      onclick: () => { metaLayer = name; renderLayers(); renderMeta(); }, onkeydown: (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); node.click(); } }},
      el("span", {class: "n", text: label}), el("span", {class: "c", text: String(count)}), ...(detail ? [el("span", {class: "d", text: detail})] : []));
    list.append(node);
  };
  item("", "All layers", total, "");
  let examples = false;
  for (const layer of layers) {
    if (EXAMPLE_LAYERS.has(layer.name) && !examples) { list.append(el("div", {class: "layer-label", text: "Examples and tests"})); examples = true; }
    item(layer.name, layer.name, counts.get(layer.name) || 0, layer.detail && layer.detail !== "See layer.conf" ? "compatible: " + layer.detail : "", EXAMPLE_LAYERS.has(layer.name) ? " example" : "");
  }
  if (counts.get("")) item("\u0000", "Outside layers", counts.get(""), "kas files and workspace files");
  $("layer-count").textContent = layers.length + " layers";
}
function renderMeta() {
  const box = $("meta-groups"), needle = $("meta-search").value.trim().toLowerCase();
  const kinds = $("meta-kinds");
  if (!kinds.children.length) for (const [kind, label] of META_KINDS) kinds.append(el("button", {role: "radio", "data-kind": kind, "aria-checked": String(kind === metaKind), text: label,
    onclick: () => { metaKind = kind; [...kinds.children].forEach((b) => b.setAttribute("aria-checked", String(b.dataset.kind === kind))); renderLayers(); renderMeta(); }}));
  const layer = metaLayer === "\u0000" ? "" : metaLayer;
  const rows = metaRows.filter((row) => row.kind !== "layer" && (metaLayer === "" || row.layer === layer) && metaMatch(row, needle));
  const groups = new Map();
  for (const row of rows) { const key = (metaLayer === "" ? row.layer + "\u0000" : "") + row.group; if (!groups.has(key)) groups.set(key, []); groups.get(key).push(row); }
  const keys = [...groups.keys()].sort((a, b) => { const [la, ga] = a.includes("\u0000") ? a.split("\u0000") : ["", a], [lb, gb] = b.includes("\u0000") ? b.split("\u0000") : ["", b];
    return EXAMPLE_LAYERS.has(la) - EXAMPLE_LAYERS.has(lb) || (la === lb ? 0 : la.localeCompare(lb)) || (!ga.startsWith("recipes-")) - (!gb.startsWith("recipes-")) || ga.localeCompare(gb); });
  box.textContent = "";
  $("meta-count").textContent = `${rows.length} ${rows.length === 1 ? "file" : "files"} · ${keys.length} ${keys.length === 1 ? "folder" : "folders"}`;
  if (!rows.length) { box.append(el("div", {class: "empty", text: needle ? `Nothing matches “${needle}” here.` : "No metadata in this layer for this filter."})); return; }
  // Open everything when the result is small or searched for; otherwise folders open on click.
  const open = !!needle || rows.length <= 60 || keys.length === 1;
  for (const key of keys) {
    const [layerName, group] = key.includes("\u0000") ? key.split("\u0000") : [layer, key];
    const items = groups.get(key).sort((a, b) => (a.recipe || a.name).localeCompare(b.recipe || b.name));
    const details = el("details", {class: "folder"},
      el("summary", {}, el("span", {class: "fname", text: group}), el("span", {class: "fcount", text: String(items.length)}), ...(metaLayer === "" && layerName ? [el("span", {class: "flayer", text: layerName})] : [])));
    const fill = () => { if (details.dataset.filled) return; details.dataset.filled = "1"; for (const row of items) details.append(recipeRow(row, needle)); };
    details.addEventListener("toggle", () => { if (details.open) fill(); });
    if (open) { details.open = true; fill(); }
    box.append(details);
  }
  $("meta-expand").textContent = open ? "Collapse all" : "Expand all";
}
function recipeRow(row, needle) {
  const name = row.recipe || row.name;
  const kind = {bb: row.image ? "image" : "recipe", bbappend: "append", bbclass: "class", yaml: "kas"}[row.kind] || row.kind;
  const actions = el("span", {class: "ra"});
  if (row.kind === "bb") actions.append(el("button", {text: "Use as target", title: "Put " + name + " in the build target field", onclick: () => { $("target").value = name; $("target").dataset.touched = "1"; toast("Target set", name + " · press b to build it", "success", {label: "Build", run: () => queue("build", {target: name})}); }}));
  actions.append(el("button", {text: "Copy path", title: row.path, onclick: () => navigator.clipboard && navigator.clipboard.writeText(row.path).then(() => toast("Path copied", row.path, "info"))}));
  return el("div", {class: "recipe", title: row.path},
    el("span", {class: "rn"}, ...highlight(name, needle)),
    el("span", {class: "rv", text: row.version === "%" ? "any version" : row.version || ""}),
    el("span", {}, el("span", {class: "badge " + (kind === "image" ? "info" : "muted"), text: kind})),
    el("span", {class: "rp", text: "‎" + (row.detail || row.path)}),
    actions);
}
async function loadTasks() {
  const body = $("task-rows"); if (!body.children.length) skeleton(body, 3);
  const data = await api(`/api/tasklogs?profile=${prof()}&q=${encodeURIComponent($("task-search").value)}`);
  body.textContent = "";
  for (const row of data.rows) {
    const tr = el("tr", {class: "clickable", tabindex: "0"}, el("td", {text: row.recipe}), el("td", {class: "mono", text: row.task}), el("td", {text: row.size}));
    tr.addEventListener("click", () => openTask(row, tr)); tr.addEventListener("keydown", (event) => { if (event.key === "Enter") openTask(row, tr); });
    body.append(tr);
  }
  if (!data.rows.length) body.append(el("tr", {}, el("td", {colspan: "3", class: "empty", text: "No task logs under tmp/work"})));
}
let openTaskRow = null;
async function openTask(row, tr) {
  openTaskRow = row;
  for (const node of document.querySelectorAll("#task-rows tr")) node.classList.toggle("selected", node === tr);
  $("task-title").textContent = row.recipe + " · " + row.task;
  const query = $("task-log-search").value;
  const data = await api(`/api/tasklog?profile=${prof()}&path=${encodeURIComponent(row.path)}&q=${encodeURIComponent(query)}&errors=${$("task-errors").checked ? 1 : 0}`);
  renderLog($("task-log"), data.text, query);
}
const STATUS_BADGE = {OK: "ok", WARN: "warn", INFO: "info"};
async function loadHealth() {
  const body = $("health-rows"); if (!body.children.length) skeleton(body, 3);
  const data = await api(`/api/health?profile=${prof()}`);
  body.textContent = "";
  data.checks.forEach((check, i) => { const tr = el("tr", {}, el("td", {}, el("span", {class: "badge " + (STATUS_BADGE[check.status] || "muted"), text: check.status})), el("td", {text: check.name}), el("td", {class: "mono", text: check.detail})); tr.style.animationDelay = i * 15 + "ms"; body.append(tr); });
  $("cap-release").textContent = data.release;
  const caps = $("cap-rows"); caps.textContent = "";
  for (const cap of data.capabilities || []) {
    const state = cap.available === true ? ["✔", "ok"] : cap.available === false ? ["✖", "no"] : ["?", "unknown"];
    caps.append(el("div", {class: "cap " + state[1], title: cap.reason || cap.note || ""}, el("span", {class: "mark", text: state[0]}),
      el("span", {class: "t"}, el("b", {text: cap.title}), el("small", {text: cap.available === true ? (cap.note || "available") : cap.reason}))));
  }
}

/* Service notifications */
async function loadNotifications() {
  const config = await api("/api/notifications");
  for (const status of ["success", "failed", "cancelled"]) $("nt-" + status).checked = config.on.includes(status);
  $("nt-desktop").checked = config.desktop; $("nt-min").value = config.min_seconds; $("nt-webhook").value = config.webhook; $("nt-format").value = config.format;
}
async function saveNotifications() {
  const body = {on: ["success", "failed", "cancelled"].filter((s) => $("nt-" + s).checked), desktop: $("nt-desktop").checked,
                min_seconds: Number($("nt-min").value || 0), webhook: $("nt-webhook").value.trim(), format: $("nt-format").value};
  try { await api("/api/notifications", {method: "POST", body: JSON.stringify(body)}); toast("Notifications saved", body.webhook ? "Desktop and webhook" : "Desktop only", "success"); }
  catch (error) { toast("Notifications", error.message, "error"); }
}

/* Projects */
let projectInfo = null, pendingClone = null;
async function loadProjects() {
  projectInfo = await api("/api/projects");
  const list = $("pj-recent"); list.textContent = "";
  for (const item of projectInfo.recent) {
    const folder = item.root.split("/").pop() || item.root, names = item.profiles || [], active = names.includes($("profile").value);
    const label = active ? (names.length > 1 ? "active · " + $("profile").value : "active") : names.length > 1 ? "profiles " + names.join(", ") : item.profile ? (item.profile !== folder ? "profile " + item.profile : "switch") : "not set up";
    const row = el("div", {class: "row" + (active ? " current" : ""), tabindex: "0"},
      el("span", {class: "glyph" + (active ? " s-success" : ""), text: active ? "●" : item.profile ? "○" : "+"}),
      el("span", {}, el("b", {text: folder}), el("div", {class: "meta", text: item.root})),
      el("span", {class: active ? "chip lts" : "meta", text: label}));
    const open = () => {
      if (item.profile) { $("profile").value = item.profile; $("profile").dispatchEvent(new Event("change")); toast("Switched project", item.profile, "info"); }
      else { $("setup-dir").value = item.root; scanSetup(); $("setup-dir").scrollIntoView({behavior: "smooth"}); }
    };
    row.addEventListener("click", open); row.addEventListener("keydown", (event) => { if (event.key === "Enter") open(); });
    list.append(row);
  }
  if (!projectInfo.recent.length) list.append(el("div", {class: "empty", text: "No projects yet: create one or clone one."}));
  for (const [id, values] of [["pj-release", Object.entries(projectInfo.releases)], ["pj-machine", projectInfo.machines.map((m) => [m, m])], ["pj-target", projectInfo.images.map((m) => [m, m])]]) {
    const select = $(id); if (select.options.length) continue;
    for (const [value, label] of values) select.append(el("option", {value, text: label}));
  }
  if (!$("pj-dir").value) $("pj-dir").value = projectInfo.home + "/yocto/my-product";
  syncProjectTool();
}
function syncProjectTool() {
  // bitbake-setup exists only from BitBake 2.16 (Yocto 5.3): offered where the release has it, with its template's choices.
  const template = (projectInfo.bbsetup || {})[$("pj-release").value];
  const bbOption = $("pj-tool").querySelector('option[value="bitbake-setup"]');
  bbOption.disabled = !template; bbOption.textContent = template ? "bitbake-setup: the Yocto Project's official templates" : "bitbake-setup: not available for this release (BitBake 2.16+)";
  if (!template && $("pj-tool").value === "bitbake-setup") $("pj-tool").value = "kas";
  const bb = $("pj-tool").value === "bitbake-setup";
  const fill = (select, values, keep) => { const old = select.value; select.textContent = ""; for (const [v, l] of values) select.append(el("option", {value: v, text: l})); if (keep && values.some(([v]) => v === old)) select.value = old; };
  fill($("pj-machine"), (bb ? template.machines : projectInfo.machines).map((m) => [m, m]), true);
  fill($("pj-runtime"), bb ? [["container", "container: the kas build image, nothing to install (recommended)"], ["host", "host: needs the Yocto host packages"]]
                           : [["kas-container", "kas-container (recommended)"], ["kas", "kas on the host"]], true);
  for (const node of document.querySelectorAll("#pj-new [data-kas]")) node.hidden = bb;
  $("pj-tool-help").textContent = bb ? `Runs bitbake-setup init with the ${template.config} template as a job: the layers are fetched, MACHINE and DISTRO become configuration fragments. DISTRO: ${template.distros.join(", ")}.`
    : "A kas.yml pinned to the release's tags, with your own layer if you want one. Works for every release.";
  previewProject();
}
function projectBody() {
  return {name: $("pj-name").value.trim(), dir: $("pj-dir").value.trim(), release: $("pj-release").value, machine: $("pj-machine").value, distro: $("pj-distro").value.trim(),
          target: $("pj-target").value, runtime: $("pj-runtime").value, layer: $("pj-layer").checked, owner: $("pj-owner").value.trim(), tool: $("pj-tool").value};
}
let projectTimer;
function previewProject() {
  clearTimeout(projectTimer);
  projectTimer = setTimeout(async () => {
    const files = $("pj-files"); files.textContent = "";
    try {
      const plan = await api("/api/projects/preview", {method: "POST", body: JSON.stringify(projectBody())});
      $("pj-create").disabled = false;
      if (plan.tool === "bitbake-setup") {
        files.append(el("details", {open: ""}, el("summary", {text: "Runs as a job"}), el("pre", {text: plan.display})),
          el("div", {class: "help", style: "padding:8px 12px", text: `Creates ${plan.setup}: layers/ (bitbake, openembedded-core, meta-yocto), build/ with init-build-env, and the fragments for MACHINE and DISTRO. Bitloom saves the profile when the job succeeds. Add your own layer afterwards with Studio → Layer.`}));
        return;
      }
      Object.entries(plan.files).forEach(([name, text]) => files.append(el("details", name === "kas.yml" ? {open: ""} : {}, el("summary", {text: "+ " + name}), el("pre", {text}))));
    } catch (error) { $("pj-create").disabled = true; files.append(el("div", {class: "notice", text: "✖ " + error.message})); }
  }, 150);
}
let pendingSetup = null;
async function createProject() {
  try {
    const result = await api("/api/projects/create", {method: "POST", body: JSON.stringify(projectBody())});
    if (result.profile) {
      // bitbake-setup runs as a job: follow it in Builds; its profile is saved when it succeeds.
      pendingSetup = result; toast("bitbake-setup started", result.dest, "info"); selected = null; await refresh(); select_(result.id); setView("builds"); $("pj-new").hidden = true;
      return;
    }
    $("profile").textContent = ""; await refresh(); $("profile").value = result.active; $("target").dataset.touched = ""; renderState();
    toast("Project created", `${result.root} · profile ${result.active} is active`, "success", {label: "Build it", run: () => queue("build", {target: $("target").value})});
    $("pj-new").hidden = true; loadProjects();
  } catch (error) { toast("New project", error.message, "error"); }
}
async function cloneProject() {
  try {
    pendingClone = await api("/api/projects/clone", {method: "POST", body: JSON.stringify({url: $("pj-url").value, dest: $("pj-dest").value, branch: $("pj-branch").value})});
    toast("Cloning", pendingClone.dest, "info"); selected = null; await refresh(); select_(pendingClone.id); setView("builds");
  } catch (error) { toast("Clone", error.message, "error"); }
}

/* Guided project setup */
let setupCandidates = [], setupRoot = "";
async function scanSetup() {
  const list = $("setup-found"); list.textContent = ""; list.append(el("div", {class: "skeleton"}), el("div", {class: "skeleton", style: "width:70%"}));
  try {
    const data = await api(`/api/setup/scan?dir=${encodeURIComponent($("setup-dir").value)}`);
    setupRoot = data.dir; $("setup-dir").value = data.dir; setupCandidates = data.candidates; list.textContent = "";
    if (!setupCandidates.length) { list.append(el("div", {class: "empty", text: "Nothing recognised: fill the form by hand."})); fillSetup({name: "project", mode: "kas-container"}); return; }
    const products = setupCandidates.filter((candidate) => candidate.mode === "wrapper");
    if (products.length > 1) {
      // One launcher, several products (YML=a.yml / YML=b.yml): one profile each, P or the profile menu switches.
      list.append(el("div", {class: "tools"}, el("span", {class: "hint", text: `${products.length} products use the same launcher`}), el("span", {style: "flex:1"}),
        el("button", {class: "btn primary", text: `Save all ${products.length} products`, onclick: () => saveAllProducts(products)})));
    }
    setupCandidates.forEach((candidate, i) => {
      const row = el("div", {class: "row" + (i === 0 ? " selected" : ""), tabindex: "0"}, el("span", {class: "glyph", text: {wrapper: "⇄", host: "⌂", kas: "◇", "kas-container": "▣"}[candidate.mode] || "·"}),
        el("span", {}, el("b", {text: candidate.title}), el("div", {class: "meta", text: candidate.evidence.join(" · ")}), ...candidate.hints.map((h) => el("div", {class: "hint", text: h}))), el("span"));
      row.addEventListener("click", () => { for (const node of list.children) node.classList.toggle("selected", node === row); fillSetup(candidate.profile); });
      list.append(row);
    });
    fillSetup(setupCandidates[0].profile);
  } catch (error) { list.textContent = ""; list.append(el("div", {class: "empty", text: error.message})); }
}
async function saveAllProducts(products) {
  let saved = [], skipped = [];
  try { saved = (await api("/api/setup/save", {method: "POST", body: JSON.stringify({profiles: products.map((c) => c.profile)})})).saved; }
  catch (error) { skipped.push(error.message); }
  $("profile").textContent = ""; await refresh(); if (saved.length) $("profile").value = saved[0]; $("target").dataset.touched = ""; await loadConsole(); renderState(); loadProjects();
  if (saved.length) toast(`Saved ${saved.length} profiles`, saved.join(", ") + " · switch with the profile menu or P", "success", {label: "Go to Builds", run: () => setView("builds")});
  if (skipped.length) toast("Not saved", skipped.join("; "), "warning");
}
function fillSetup(profile) {
  $("sp-mode").value = profile.mode || "kas-container";
  for (const key of ["name", "kas_file", "init_script", "build_dir", "machine", "distro"]) $("sp-" + key).value = profile[key] || "";
  $("sp-launcher").value = (profile.launcher || []).join(" ");
  $("sp-targets").value = (profile.targets || []).join(" ");
  $("sp-environment").value = Object.entries(profile.environment || {}).map(([k, v]) => `${k}=${v}`).join("\n");
  checkSetup();
}
function setupProfile() {
  const environment = {};
  for (const line of $("sp-environment").value.split("\n")) { const at = line.indexOf("="); if (at > 0) environment[line.slice(0, at).trim()] = line.slice(at + 1).trim(); }
  const mode = $("sp-mode").value, profile = {name: $("sp-name").value.trim(), root: setupRoot || $("setup-dir").value, mode, environment,
    kas_file: $("sp-kas_file").value.trim() || "kas.yml", init_script: $("sp-init_script").value.trim(), build_dir: $("sp-build_dir").value.trim() || "build",
    machine: $("sp-machine").value.trim(), distro: $("sp-distro").value.trim(), targets: $("sp-targets").value.split(/\s+/).filter(Boolean)};
  if (mode === "wrapper") profile.launcher = $("sp-launcher").value.split(/\s+/).filter(Boolean);
  for (const node of document.querySelectorAll("#setup-form [data-mode]")) node.hidden = !node.dataset.mode.split(" ").includes(mode);
  return profile;
}
let setupTimer;
function checkSetup() {
  clearTimeout(setupTimer);
  setupTimer = setTimeout(async () => {
    const data = await api("/api/setup/check", {method: "POST", body: JSON.stringify({profile: setupProfile()})});
    const list = $("sp-checks"); list.textContent = "";
    for (const row of data.checks) list.append(el("li", {style: "grid-template-columns:26px 1fr"}, el("span", {class: {OK: "s-success", WARN: "s-queued", ERR: "s-failed"}[row.status], text: {OK: "✔", WARN: "▲", ERR: "✖"}[row.status]}), el("span", {text: row.message})));
    $("sp-save").disabled = data.checks.some((row) => row.status === "ERR");
  }, 150);
}
async function saveSetup() {
  try {
    const result = await api("/api/setup/save", {method: "POST", body: JSON.stringify({profile: setupProfile()})});
    $("profile").textContent = ""; await refresh(); $("profile").value = result.active; $("target").dataset.touched = ""; await loadConsole(); renderState();
    toast("Project set up", `Profile ${result.active} is active and ready to build.`, "success", {label: "Go to Builds", run: () => setView("builds")});
    loadHealth();
  } catch (error) { toast("Setup", error.message, "error"); }
}

/* Compliance */
function gauge(label, fraction) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 60 60"); svg.setAttribute("class", "ring");
  for (const [cls, extra] of [["track", {}], ["bar", {"stroke-dasharray": "150.8", "stroke-dashoffset": "150.8"}]]) {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    for (const [k, v] of Object.entries({class: cls, cx: "30", cy: "30", r: "24", ...extra})) circle.setAttribute(k, v);
    svg.append(circle);
  }
  const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
  for (const [k, v] of Object.entries({x: "30", y: "35", "text-anchor": "middle"})) text.setAttribute(k, v);
  svg.append(text);
  requestAnimationFrame(() => ring(svg, fraction, Math.round(100 * fraction) + "%"));
  return el("div", {class: "gauge"}, svg, el("div", {class: "label", text: label}));
}
async function loadCompliance() {
  const data = await api(`/api/compliance?profile=${prof()}`);
  $("cr-release").textContent = data.release;
  if (data.support_until) {
    const end = new Date(data.support_until), days = Math.round((end - new Date()) / 86400000), span = data.lts ? 4 * 365 : 7 * 30;
    ring($("support-ring"), Math.max(0, days) / span, days > 0 ? Math.round(days / 30) + "m" : "EOL");
    $("cr-support").textContent = (data.lts ? "LTS · " : "") + "community support until " + data.support_until + (days > 0 ? ` (${days} days)` : " (ended)");
  } else { ring($("support-ring"), 0, "?"); $("cr-support").textContent = "release not detected"; }
  const passed = data.checks.filter((c) => c.status === "OK").length;
  $("cr-score").textContent = `${passed} / ${data.checks.length} checks OK`;
  const gauges = $("sb-gauges"), vex = $("sb-vex"); gauges.textContent = ""; vex.textContent = "";
  const sbom = data.sboms.find((s) => !s.error);
  if (sbom) {
    $("sb-file").textContent = `${sbom.format} · ${sbom.packages} ${Object.keys(sbom.other_elements || {}).length ? "installed " : ""}packages · ${sbom.file.split("/").pop()}`;
    for (const [label, key] of [["Version", "with_version"], ["PURL", "with_purl"], ["CPE", "with_cpe"], ["Licence", "with_license"], ["Supplier", "with_supplier"]]) gauges.append(gauge(label, sbom[key]));
    const colors = {affected: "err", "under investigation": "warn", fixed: "ok", "not affected": "info"};
    for (const [status, count] of Object.entries(sbom.vex)) vex.append(el("span", {class: "badge " + (colors[status] || "muted"), text: `${count} ${status}`}));
    for (const cve of (sbom.vex_examples.affected || [])) vex.append(el("span", {class: "badge err", text: cve}));
    if (!Object.keys(sbom.vex).length) vex.append(el("span", {class: "hint", text: "No VEX statements in this SBOM."}));
  } else { $("sb-file").textContent = ""; gauges.append(el("div", {class: "empty", text: "No *.spdx.json SBOM yet: enable create-spdx and build an image."})); }
  const checks = $("cr-checks"); checks.textContent = "";
  data.checks.forEach((check, i) => { const li = el("li", {}, el("span", {class: "s-" + ({OK: "success", WARN: "queued", INFO: "running"}[check.status] || "unknown"), text: {OK: "✔", WARN: "▲", INFO: "ℹ"}[check.status] || "·"}), el("b", {text: check.item}), el("span", {class: "meta", text: check.detail})); li.style.animationDelay = i * 40 + "ms"; checks.append(li); });
  const timeline = $("cr-timeline"); timeline.textContent = "";
  for (const item of data.timeline) {
    const days = Math.round((new Date(item.date) - new Date()) / 86400000);
    timeline.append(el("li", {class: days <= 0 ? "past" : ""}, el("b", {text: item.date + (days <= 0 ? " · in force" : ` · in ${days} days`)}), el("div", {class: "hint", text: item.text})));
  }
  const options = $("sb-options"); options.textContent = "";
  for (const option of data.options) {
    const badge = option.available === false ? el("span", {class: "badge err", text: "n/a in this release"}) : option.value ? el("span", {class: "badge ok", text: option.value === "1" ? "on" : option.value}) : el("span", {class: "badge muted", text: "off"});
    const span = el("span", {class: "meta", text: option.requires + (option.verified ? "" : " · verify")});
    options.append(el("details", {class: "opt"}, el("summary", {}, el("span", {}, el("b", {text: option.title}), el("span", {class: "meta", text: "  " + option.name})), span, badge),
      el("div", {class: "body"}, el("p", {text: option.info}), option.cra ? el("p", {}, el("b", {text: "CRA: "}), option.cra) : null, option.reason ? el("p", {class: "s-queued", text: option.reason}) : null)));
  }
}

/* Vulnerabilities */
let vulnRows = [], vulnTimer, pendingScan = null;
async function loadVulns() {
  const query = `profile=${prof()}&source=${encodeURIComponent($("vu-source").value)}&status=${$("vu-status").value}&min=${encodeURIComponent($("vu-min").value)}&q=${encodeURIComponent($("vu-q").value)}`;
  const data = await api(`/api/vulnerabilities?${query}`);
  const select = $("vu-source");
  if (select.options.length !== data.sources.length + 1) {
    const keep = select.value; select.textContent = ""; select.append(el("option", {value: "", text: "Newest report of each tool"}));
    for (const label of data.sources) select.append(el("option", {value: label, text: label}));
    select.value = keep;
  }
  $("vu-grype").disabled = !data.scanners.grype;
  $("vu-grype").title = data.scanners.grype ? "Scan the newest SPDX SBOM with Grype" : "Install grype to scan SBOMs";
  const c = data.counts;
  $("vu-summary").textContent = data.sources.length ? `${c.total} assessed · showing ${data.shown}` : "no CVE report yet";
  const chips = $("vu-chips"); chips.textContent = "";
  for (const [key, cls, label] of [["unpatched_critical", "err", "critical"], ["unpatched_high", "err", "high"], ["unpatched_medium", "warn", "medium"], ["unpatched_low", "info", "low"], ["patched", "ok", "patched"], ["ignored", "muted", "ignored"], ["reviewed", "ok", "reviewed"]]) {
    if (c[key]) chips.append(el("span", {class: "badge " + cls, text: `${c[key]} ${label}` + (key.startsWith("unpatched_") ? " unpatched" : "")}));
  }
  if (!data.sources.length) chips.append(el("span", {class: "hint", text: "Wrynose: enable sbom-cve-check (TUI Configuration → s) and build; older releases: INHERIT += \"cve-check\"; or scan an SPDX SBOM with Grype."}));
  for (const error of data.errors) chips.append(el("span", {class: "badge warn", text: error}));
  vulnRows = data.findings;
  const body = $("vu-rows"); body.textContent = "";
  const colour = {critical: "err", high: "err", medium: "warn", low: "info"};
  vulnRows.forEach((f, i) => {
    const tr = el("tr", {class: "clickable", tabindex: "0", title: f.summary},
      el("td", {}, el("span", {class: "badge " + (colour[f.severity] || "muted"), text: f.severity})), el("td", {class: "mono", text: f.score ? f.score.toFixed(1) : "—"}),
      el("td", {class: "mono"}, f.link ? el("a", {href: f.link, target: "_blank", rel: "noopener noreferrer", text: f.id}) : f.id),
      el("td", {text: `${f.package} ${f.version}`}), el("td", {text: f.status + (f.detail ? " · " + f.detail : "")}), el("td", {class: "s-success", text: f.review}));
    tr.style.animationDelay = Math.min(i, 20) * 12 + "ms";
    tr.addEventListener("click", () => toast(f.id, `${f.package} ${f.version} · ${f.status} · ${f.source} · ${f.summary}`, f.status === "Unpatched" ? "warning" : "info"));
    body.append(tr);
  });
  if (!vulnRows.length && data.sources.length) body.append(el("tr", {}, el("td", {colspan: "6", class: "empty", text: "No finding matches the filters."})));
}
async function exportVulns() {
  // Same filters as the table; the server builds the report with links and remediation guidance.
  const query = `profile=${prof()}&source=${encodeURIComponent($("vu-source").value)}&status=${$("vu-status").value}&min=${encodeURIComponent($("vu-min").value)}&q=${encodeURIComponent($("vu-q").value)}&format=${$("vu-format").value}`;
  try {
    const response = await fetch(`/api/vulnerabilities/export?${query}`, {headers: {"X-Bitloom-Token": token}});
    if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.error || response.statusText); }
    const name = (/filename="([^"]+)"/.exec(response.headers.get("Content-Disposition") || "") || [])[1] || "vulnerabilities";
    const link = el("a", {href: URL.createObjectURL(await response.blob()), download: name});
    document.body.append(link); link.click(); link.remove();
    toast("Exported", name, "success");
  } catch (error) { toast("Export failed", error.message, "error"); }
}
async function exportPractices() {
  try {
    const response = await fetch(`/api/practices/export?profile=${prof()}&format=${$("pr-format").value}`, {headers: {"X-Bitloom-Token": token}});
    if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.error || response.statusText); }
    const name = (/filename="([^"]+)"/.exec(response.headers.get("Content-Disposition") || "") || [])[1] || "practices";
    const link = el("a", {href: URL.createObjectURL(await response.blob()), download: name});
    document.body.append(link); link.click(); link.remove();
    toast("Exported", name, "success");
  } catch (error) { toast("Export failed", error.message, "error"); }
}
async function scanGrype() {
  try { const job = await api("/api/vulnerabilities/scan", {method: "POST", body: JSON.stringify({profile: $("profile").value})}); toast("Grype scan queued", "Follow it in Builds; results appear here when it finishes.", "info"); pendingScan = job.id; }
  catch (error) { toast("Grype", error.message, "error"); }
}

/* Best practices: built-in rules plus the company's, tuned in bitloom-practices.json */
let practices = null, prShow = "attention", prEditing = null;
async function loadPractices(data = null) {
  const groups = $("pr-groups");
  if (!data) { if (!practices) { groups.textContent = ""; skeletonIn(groups); } try { data = await api(`/api/practices?profile=${prof()}`); } catch (error) { groups.textContent = ""; groups.append(el("div", {class: "panel empty", text: error.message})); return; } }
  practices = data;
  ring($("pr-ring").closest("svg"), (data.score ?? 0) / 100, data.score === null ? "—" : data.score + "%");
  $("pr-title").textContent = data.score === null ? "Nothing to check yet" : `${data.score}% followed`;
  const n = (count, one, many) => `${count} ${count === 1 ? one : many}`;
  $("pr-sub").textContent = `${n(data.errors, "error", "errors")} · ${n(data.warnings, "warning", "warnings")} · ${n(data.infos, "suggestion", "suggestions")} · your layers: ${data.layers.join(", ") || "none yet"}`;
  $("pr-config").textContent = (data.config_exists ? "Company rules and settings: " : "No company rules yet; they will be saved in ") + data.config.split("/").slice(-2).join("/");
  const seg = $("pr-show");
  if (!seg.children.length) for (const [id, label] of [["attention", "Needs attention"], ["all", "All rules"], ["off", "Switched off"]])
    seg.append(el("button", {role: "radio", "aria-checked": String(id === prShow), "data-id": id, text: label, onclick: () => { prShow = id; [...seg.children].forEach((b) => b.setAttribute("aria-checked", String(b.dataset.id === id))); renderPractices(); }}));
  renderPractices();
}
function renderPractices() {
  const groups = $("pr-groups"); groups.textContent = "";
  const order = {fail: 0, pass: 1, "n/a": 2, off: 3}, sev = {error: 0, warning: 1, info: 2};
  const visible = practices.rules.filter((r) => prShow === "all" || (prShow === "off" ? r.status === "off" : r.status === "fail"));
  if (!visible.length) { groups.append(el("div", {class: "panel empty", text: prShow === "attention" ? "Every rule that applies is followed. ✔" : "Nothing here."})); return; }
  const byCategory = new Map();
  for (const rule of visible.sort((a, b) => order[a.status] - order[b.status] || sev[a.severity] - sev[b.severity])) { if (!byCategory.has(rule.category)) byCategory.set(rule.category, []); byCategory.get(rule.category).push(rule); }
  for (const [category, rules] of byCategory) {
    const panel = el("div", {class: "panel pr-group"}, el("div", {class: "head"}, el("h2", {}, category, el("span", {class: "n", text: String(rules.length)}))));
    for (const rule of rules) panel.append(ruleRow(rule));
    groups.append(panel);
  }
}
function ruleRow(rule) {
  const status = rule.status === "n/a" ? "na" : rule.status;
  const mark = {pass: "✔", fail: "✖", na: "–", off: "○"}[status];
  const severity = el("select", {class: "sev", title: "Severity", "aria-label": "Severity of " + rule.title, onclick: (e) => e.stopPropagation(), onchange: (e) => savePractices({severity: {...currentConfig().severity, [rule.id]: e.target.value}})});
  for (const level of ["error", "warning", "info"]) severity.append(el("option", {value: level, text: level}));
  severity.value = rule.severity;
  const toggle = el("input", {type: "checkbox", "aria-label": (rule.enabled ? "Switch off " : "Switch on ") + rule.title});
  toggle.checked = rule.enabled;
  toggle.addEventListener("click", (e) => e.stopPropagation());
  toggle.addEventListener("change", () => { const off = new Set(currentConfig().disabled); toggle.checked ? off.delete(rule.id) : off.add(rule.id); savePractices({disabled: [...off]}); });
  const count = rule.status === "fail" ? `${rule.findings.length} ${rule.findings.length === 1 ? "place" : "places"}` : rule.status === "n/a" ? "does not apply" : rule.status === "off" ? "off" : "followed";
  const body = el("div", {class: "body"}, el("div", {class: "why", text: rule.why}), el("div", {class: "fix"}, el("b", {text: "Fix: "}), rule.fix));
  if (rule.findings.length) { const list = el("ul", {class: "findings"}); for (const f of rule.findings) list.append(el("li", {}, f.where, f.detail ? el("span", {text: " · " + f.detail}) : "")); body.append(list); }
  const actions = el("div", {class: "row-actions"});
  if (rule.source) actions.append(el("a", {class: "btn", href: rule.source, target: "_blank", rel: "noopener", text: "Yocto documentation ↗"}));
  if (rule.custom) actions.append(el("button", {class: "btn", text: "Edit rule", onclick: () => openRuleDialog(rule)}));
  if (actions.children.length) body.append(actions);
  return el("details", {class: `rule ${status} ${rule.severity}`, ...(rule.status === "fail" && prShow === "attention" && practices.rules.filter((r) => r.status === "fail").length <= 3 ? {open: ""} : {})},
    el("summary", {}, el("span", {class: "mark", text: mark}), el("span", {class: "t"}, rule.title, rule.custom ? el("small", {text: "company"}) : ""), el("span", {class: "count", text: count}), severity,
      el("label", {class: "switch", title: rule.enabled ? "On: click to switch off for this project" : "Off: click to switch on"}, toggle, el("span"))), body);
}
function currentConfig() {
  return {disabled: practices.rules.filter((r) => !r.enabled).map((r) => r.id),
          severity: Object.fromEntries(practices.rules.filter((r) => !r.custom).map((r) => [r.id, r.severity])),
          rules: practices.rules.filter((r) => r.custom).map((r) => ({id: r.id, title: r.title, category: r.category, severity: r.severity, why: r.why, fix: r.fix, source: r.source, check: r.check}))};
}
async function savePractices(changes) {
  try { loadPractices(await api("/api/practices", {method: "POST", body: JSON.stringify({profile: prof(), ...changes})})); toast("Practices saved", "bitloom-practices.json updated", "success"); }
  catch (error) { toast("Not saved", error.message, "error"); loadPractices(); }
}
const RULE_TEMPLATES = [
  {label: "Every recipe names a maintainer", title: "Recipes name a maintainer", id: "maintainer", severity: "warning",
   why: "Each component needs an owner for reviews and security fixes.", fix: 'Add MAINTAINER = "Team <team@company.example>" to the recipe.',
   check: {type: "files-must-match", files: "*.bb", pattern: "^MAINTAINER\\s*="}},
  {label: "Every recipe has a SUMMARY", title: "Recipes describe themselves", id: "recipe-summary", severity: "info",
   why: "The summary appears in package lists, SBOMs and the image explorer.", fix: 'Add SUMMARY = "…" to the recipe.',
   check: {type: "files-must-match", files: "*.bb", pattern: "^SUMMARY\\s*="}},
  {label: "No internal host names", title: "No internal host names in the metadata", id: "no-internal-hosts", severity: "error",
   why: "Layers are shared with customers and suppliers.", fix: "Use a variable set in site.conf or a mirror instead.",
   check: {type: "files-must-not-match", files: "*.bb", pattern: "\\.internal\\b"}},
  {label: "Each layer has CODEOWNERS", title: "Layers name their owners", id: "codeowners", severity: "info",
   why: "Reviews go to the right people.", fix: "Add a CODEOWNERS file at the top of the layer.",
   check: {type: "layer-file-exists", path: "CODEOWNERS"}},
  {label: "Products build our distribution", title: "Products build the company distribution", id: "company-distro", severity: "error",
   why: "Our distribution carries the security and licence policies.", fix: 'Set DISTRO = "acme" in the kas file or auto.conf.',
   check: {type: "variable", name: "DISTRO", op: "equals", value: "acme"}},
  {label: "A distro feature is required", title: "seccomp is enabled", id: "seccomp", severity: "warning",
   why: "Our security baseline requires it.", fix: 'Add DISTRO_FEATURES:append = " seccomp" to the distribution.',
   check: {type: "variable", name: "DISTRO_FEATURES", op: "contains", value: "seccomp"}},
];
let prStep = 1, prIdTouched = false;
const ruleType = () => (document.querySelector('#pr-form input[name="prf-type"]:checked') || {}).value || "";
const slug = (text) => text.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").slice(0, 40).replace(/^-+|-+$/g, "");
let prTemplate = null;
function ruleFromForm() {
  const type = ruleType(), check = {type};
  for (const key of {"files-must-match": ["files", "pattern"], "files-must-not-match": ["files", "pattern"], "layer-file-exists": ["path"], variable: ["name", "op", "value"]}[type] || []) check[key] = $("prf-" + key).value.trim();
  return {id: $("prf-id").value.trim(), title: $("prf-title").value.trim(), category: $("prf-category").value.trim() || "Company", severity: $("prf-severity").value,
          why: $("prf-why").value.trim(), fix: $("prf-fix").value.trim(), check};
}
function plainRule() {
  const r = ruleFromForm(), c = r.check, out = $("prw-plain"); out.textContent = "";
  if (!c.type) return;
  const sev = {error: "An error", warning: "A warning", info: "A suggestion"}[r.severity];
  const code = (text, fallback) => text ? el("code", {text}) : el("em", {text: fallback});
  const parts = c.type === "files-must-match" ? [sev, " for every ", code(c.files, "file"), " file in your layers without a line matching ", code(c.pattern, "…"), "."]
    : c.type === "files-must-not-match" ? [sev, " for every line matching ", code(c.pattern, "…"), " in ", code(c.files, "files"), " of your layers."]
    : c.type === "layer-file-exists" ? [sev, " for each of your layers without ", code(c.path, "the file"), "."]
    : [sev, " unless ", code(c.name, "the variable"), {set: " is set", unset: " is not set at all", equals: " is exactly ", contains: " contains the word ", "not-contains": " does not contain the word "}[c.op],
       ...(["set", "unset"].includes(c.op) ? [] : [code(c.value, "…")]), " in your configuration."];
  out.append(...parts);
}
function syncRuleForm() {
  const type = ruleType();
  for (const node of document.querySelectorAll("#pr-form [data-for]")) node.hidden = !node.dataset.for.split(" ").includes(type);
  $("prf-value-field").hidden = type !== "variable" || ["set", "unset"].includes($("prf-op").value);
  $("prf-pattern-label").textContent = type === "files-must-not-match" ? "Text that must not appear" : "Text each file must contain";
  plainRule();
}
function ruleStep(step) {
  prStep = step;
  for (const page of document.querySelectorAll("#pr-form .prw-page")) page.hidden = Number(page.dataset.page) !== step;
  for (const button of document.querySelectorAll("#prw-steps button")) {
    const n = Number(button.dataset.step);
    if (n === step) button.setAttribute("aria-current", "step"); else button.removeAttribute("aria-current");
    button.classList.toggle("done", n < step);
  }
  $("prf-back").hidden = step === 1; $("prf-next").hidden = step === 3; $("prf-save").hidden = step !== 3; $("prf-error").textContent = "";
  syncRuleForm();
  const first = document.querySelector(`#pr-form .prw-page[data-page="${step}"] :is(input:not([type=radio]):not([hidden]), select)`);
  if (step === 1) (document.querySelector('#pr-form input[name="prf-type"]:checked') || document.querySelector("#prw-templates button")).focus();
  else if (first && !first.closest("[hidden]")) first.focus();
}
function ruleStepError(step) {
  const r = ruleFromForm(), c = r.check;
  if (step >= 1 && !c.type) return "Choose an example or a kind of check.";
  if (step >= 2) {
    if (c.type.startsWith("files") && !c.files) return "Say which files to look at (for example *.bb).";
    if (c.type.startsWith("files") && !c.pattern) return "Say what text to look for.";
    if (c.type === "layer-file-exists" && !c.path) return "Name the file each layer must have.";
    if (c.type === "variable" && !c.name) return "Name the variable.";
    if (c.type === "variable" && !["set", "unset"].includes(c.op) && !c.value) return "Give the value to compare with.";
  }
  if (step >= 3 && !r.title) return "Give the rule a title.";
  if (step >= 3 && !/^[a-z0-9][a-z0-9-]{1,40}$/.test(r.id)) return "The id uses lowercase letters, digits and hyphens (at least two characters).";
  return "";
}
function ruleGo(step) {
  const error = step > prStep ? ruleStepError(Math.min(step - 1, 2)) : "";
  if (error) { $("prf-error").textContent = "✖ " + error; return; }
  ruleStep(step);
}
function fillRule(rule) {
  const check = rule.check || {};
  for (const radio of document.querySelectorAll('#pr-form input[name="prf-type"]')) radio.checked = radio.value === check.type;
  for (const key of ["files", "pattern", "path", "name", "value"]) $("prf-" + key).value = check[key] || "";
  $("prf-op").value = check.op || "set";
  $("prf-title").value = rule.title || ""; $("prf-id").value = rule.id || ""; $("prf-category").value = rule.category || "Company";
  $("prf-severity").value = rule.severity || "warning"; $("prf-why").value = rule.why || ""; $("prf-fix").value = rule.fix || "";
  $("prf-try-list").textContent = ""; $("prf-try-sum").textContent = "Runs the check now, without saving.";
}
function openRuleDialog(rule = null) {
  prEditing = rule; prIdTouched = !!rule;
  fillRule(rule || {category: "Company", severity: "warning"});
  $("pr-dialog-title").textContent = rule ? "Edit company rule" : "New company rule";
  $("prf-id").readOnly = !!rule; $("prf-delete").hidden = !rule;
  const host = $("prw-templates"); host.textContent = "";
  for (const t of RULE_TEMPLATES) host.append(el("button", {type: "button", text: t.label, onclick: () => { fillRule({...t, category: "Company"}); prTemplate = t; prIdTouched = false; ruleStep(2); }}));
  prTemplate = null;
  $("pr-dialog").showModal(); ruleStep(rule ? 2 : 1);
}
async function tryRule() {
  const error = ruleStepError(2), list = $("prf-try-list"), sum = $("prf-try-sum");
  if (error) { $("prf-error").textContent = "✖ " + error; return; }
  const rule = ruleFromForm();
  sum.className = "hint"; sum.textContent = "Checking…"; list.textContent = ""; $("prf-error").textContent = "";
  try {
    const result = await api("/api/practices/try", {method: "POST", body: JSON.stringify({profile: prof(), rule: {...rule, id: rule.id || "draft-rule", title: rule.title || "Draft"}})});
    const layers = result.layers.join(", ") || "none";
    if (result.status === "pass") { sum.className = "pass"; sum.textContent = `✔ Your project follows it (checked in ${layers}).`; }
    else if (result.status === "n/a") { sum.className = "hint"; sum.textContent = `– Nothing to check: no matching files in your layers (${layers}). Check the file pattern.`; }
    else {
      sum.className = "fail"; sum.textContent = `▲ ${result.total} ${result.total === 1 ? "place does" : "places do"} not follow it${result.total > result.findings.length ? ` (first ${result.findings.length})` : ""}:`;
      for (const f of result.findings) list.append(el("li", {}, el("code", {text: f.where, title: f.where}), el("span", {text: f.detail})));
    }
  } catch (err) { sum.className = "fail"; sum.textContent = "✖ " + err.message; }
}
async function saveRule(event) {
  event.preventDefault();
  if (event.submitter && event.submitter.value === "cancel") { $("pr-dialog").close(); return; }
  const error = ruleStepError(3);
  if (error) { $("prf-error").textContent = "✖ " + error; return; }
  const rule = ruleFromForm();
  const config = currentConfig();
  config.rules = [...config.rules.filter((r) => r.id !== (prEditing ? prEditing.id : rule.id)), rule];
  try { loadPractices(await api("/api/practices", {method: "POST", body: JSON.stringify({profile: prof(), rules: config.rules})})); $("pr-dialog").close(); toast("Rule saved", rule.title, "success"); }
  catch (err) { $("prf-error").textContent = "✖ " + err.message; }
}
async function deleteRule() {
  if (!prEditing || !confirm(`Delete the rule “${prEditing.title}”?`)) return;
  const config = currentConfig(); config.rules = config.rules.filter((r) => r.id !== prEditing.id);
  await savePractices({rules: config.rules}); $("pr-dialog").close();
}

/* Image explorer: the built root filesystem, file by file, with the package and recipe behind each */
let imgList = [], imgCurrent = null, imgDir = "/", imgSelected = null, imgLast = null, imgMode = "files";
function human(bytes) { return bytes >= 1048576 ? (bytes / 1048576).toFixed(1) + " MiB" : bytes >= 1024 ? (bytes / 1024).toFixed(1) + " KiB" : bytes + " B"; }
const imgQuery = () => `profile=${prof()}&image=${encodeURIComponent(imgCurrent.image)}&machine=${encodeURIComponent(imgCurrent.machine)}`;
async function loadImage() {
  const pick = $("img-pick");
  try { imgList = (await api(`/api/image/list?profile=${prof()}`)).images; } catch (error) { imgList = []; }
  pick.textContent = "";
  for (const [i, img] of imgList.entries()) pick.append(el("option", {value: String(i), text: `${img.image} · ${img.machine}`}));
  if (!imgList.length) {
    pick.hidden = true; $("img-stats").textContent = ""; $("img-packages").textContent = ""; $("img-folders").textContent = ""; $("img-list").textContent = ""; $("img-crumbs").textContent = "";
    $("img-stats").append(el("div", {class: "empty", style: "padding:6px 0", text: "No built image to explore yet. Build an image (b with an image recipe as target); its root filesystem archive (IMAGE_FSTYPES with tar.bz2, tar.gz, tar.xz or tar.zst) appears here."}));
    return;
  }
  pick.hidden = false;
  const keep = imgCurrent ? imgList.findIndex((i) => i.image === imgCurrent.image && i.machine === imgCurrent.machine) : -1;
  pick.value = String(keep >= 0 ? keep : 0);
  await chooseImage(imgList[Number(pick.value)], keep >= 0 ? imgDir : "/");
}
async function chooseImage(img, dir = "/") {
  imgCurrent = img;
  $("img-source").textContent = (img.kind === "archive" ? img.source.split("/").pop() : "rootfs folder") + " · built " + new Date(img.mtime * 1000).toLocaleString();
  const stats = $("img-stats"); stats.textContent = ""; skeletonIn(stats);
  try {
    const sum = await api(`/api/image/summary?${imgQuery()}`);
    stats.textContent = "";
    for (const [value, label] of [[human(sum.total), "on the device"], [sum.files.toLocaleString(), "files"], [String(sum.package_count), "packages"]]) stats.append(el("div", {}, el("b", {text: value}), el("span", {text: label})));
    const bars = (box, rows, label, run) => { box.textContent = ""; const top = rows[0] ? rows[0].size : 1;
      for (const row of rows.slice(0, 10)) box.append(el("button", {class: "bar-row", title: label(row), onclick: () => run(row)},
        el("span", {class: "n"}, ...label(row).split("\u0000").map((t, i) => i ? el("small", {text: t}) : t)), el("span", {class: "b", style: `width:${Math.max(1, 100 * row.size / top)}%`}), el("span", {class: "s", text: human(row.size)}))); };
    bars($("img-packages"), sum.packages, (r) => r.package + (r.recipe && r.recipe !== r.package ? "\u0000" + r.recipe : ""), (r) => whoInstalls(r.package));
    bars($("img-folders"), sum.folders, (r) => r.path, (r) => openDir(r.path));
  } catch (error) { stats.textContent = ""; stats.append(el("div", {class: "empty", text: error.message})); }
  await openDir(dir);
  if (imgMode === "services") loadServices();
  if (imgMode === "insights") loadInsights();
}
function setImgMode(mode) {
  imgMode = mode;
  for (const b of document.querySelectorAll("#img-mode button")) b.setAttribute("aria-checked", String(b.dataset.mode === mode));
  $("img-list").hidden = mode !== "files"; $("img-crumbs").hidden = mode !== "files"; $("img-services").hidden = mode !== "services"; $("img-dt").hidden = mode !== "devicetree";
  $("img-split").hidden = mode === "insights"; $("img-insights").hidden = mode !== "insights";
  if (mode === "insights") loadInsights();
  $("img-dir-size").textContent = mode === "files" && imgLast ? human(imgLast.size) : "";
  if (mode === "services") loadServices();
  if (mode === "devicetree") loadDeviceTrees();
}
let dtFiles = [], dtCurrent = null;
function tipOn(node, text) {
  // Hover (and keyboard focus) shows the exact values; the label stays readable without it.
  const show = (x, y) => { let tip = $("ins-tip"); if (!tip) { tip = el("div", {id: "ins-tip", role: "tooltip"}); document.body.append(tip); }
    tip.textContent = text; tip.hidden = false; tip.style.left = Math.min(x + 14, innerWidth - tip.offsetWidth - 8) + "px"; tip.style.top = (y + 14) + "px"; };
  node.addEventListener("mousemove", (e) => show(e.clientX, e.clientY));
  node.addEventListener("focus", () => { const r = node.getBoundingClientRect(); show(r.left, r.bottom); });
  for (const ev of ["mouseleave", "blur"]) node.addEventListener(ev, () => { const tip = $("ins-tip"); if (tip) tip.hidden = true; });
  node.setAttribute("aria-label", text);
  return node;
}
function card(title, sub, wide = false) {
  const body = el("div", {class: "card-body"}, el("h3", {text: title}), el("div", {class: "sub", text: sub}));
  return [el("div", {class: "panel" + (wide ? " wide" : "")}, body), body];
}
function hbars(rows, {value, label, note = () => "", tip, run = null, max = null}) {
  const top = max || Math.max(1, ...rows.map(value));
  const box = el("div", {class: "hbars"});
  for (const row of rows) {
    const bar = el(run ? "button" : "div", {class: "hbar" + (run ? " link" : ""), tabindex: run ? "0" : "-1", ...(run ? {type: "button", onclick: () => run(row)} : {})},
      el("span", {class: "n"}, label(row), ...(note(row) ? [el("small", {text: note(row)})] : [])),
      el("span", {class: "t"}, el("span", {class: "b" + (row.other ? " other" : ""), style: `width:${Math.max(0.5, 100 * value(row) / top)}%`})),
      el("span", {class: "v", text: tip(row).split(" · ")[0]}));
    box.append(tipOn(bar, label(row) + " · " + tip(row)));
  }
  return box;
}
let insightsTicket = 0;
async function loadInsights() {
  const box = $("img-insights"), ticket = ++insightsTicket;
  box.textContent = "";
  if (!imgCurrent) { box.append(el("div", {class: "panel wide"}, el("div", {class: "empty", text: "No built image to analyse yet."}))); return; }
  const wait = el("div", {class: "panel wide"}, el("div", {class: "card-body"})); skeletonIn(wait.firstChild); box.append(wait);
  let d;
  try { d = await api(`/api/image/insights?${imgQuery()}`); } catch (error) { box.textContent = ""; box.append(el("div", {class: "panel wide"}, el("div", {class: "empty", text: error.message}))); return; }
  if (ticket !== insightsTicket) return;
  box.textContent = "";
  const pct = (n) => (100 * n / Math.max(1, d.total)).toFixed(n / d.total < 0.01 ? 1 : 0) + "%";
  // Headline numbers: tiles, not charts.
  const kpis = el("div", {class: "kpis wide"});
  for (const [value, label, alert] of [[human(d.total), "on the device"], [d.files.toLocaleString(), "files"], [String(d.packages), "packages"],
      [String(d.boot), `started at boot · ${d.init}`], [String(d.ports.length), d.ports.length === 1 ? "port listening" : "ports listening", d.ports.length > 0],
      [String(d.setuid.length), "setuid / setgid files", d.setuid.length > 6]])
    kpis.append(el("div", {class: "kpi" + (alert ? " alert" : "")}, el("b", {text: value}), el("span", {text: label})));
  box.append(kpis);
  // Part-to-whole by layer: the only categorical chart (≤6 layers + Other, colours by slot, legend with values).
  const [layers, lb] = card("Where the space goes · by layer", "Your layers are marked; upstream ones are where an append changes things.", true);
  const stack = el("div", {class: "stack", role: "img", "aria-label": "Size by layer"}), legend = el("div", {class: "legend"});
  d.layers.forEach((row, i) => {
    const colour = row.other || row.name === "not from a package" ? "var(--viz-other)" : `var(--viz-${i + 1})`;
    stack.append(tipOn(el("span", {style: `flex:${Math.max(row.size, d.total / 400)};background:${colour}`, tabindex: "0"}), `${row.name}: ${human(row.size)} · ${pct(row.size)} · ${row.files} files`));
    legend.append(el("div", {class: "li"}, el("span", {class: "sw", style: `background:${colour}`}), el("span", {}, row.name + (row.other ? ` (${row.count} layers)` : ""), ...(row.mine ? [" ", el("span", {class: "tag", text: "yours"})] : [])),
      el("span", {class: "v", text: human(row.size)}), el("span", {class: "v", text: pct(row.size)})));
  });
  lb.append(stack, legend); box.append(layers);
  const [kinds, kb] = card("By kind of file", "Debug symbols, development files and documentation are rarely needed on a device.");
  kb.append(hbars(d.kinds, {value: (r) => r.size, label: (r) => r.name, tip: (r) => `${human(r.size)} · ${pct(r.size)} · ${r.files} files`}));
  box.append(kinds);
  const [recipes, rb] = card("Biggest recipes", "Select one for its packages, layer and how to change it.");
  rb.append(hbars(d.recipes, {value: (r) => r.size, label: (r) => r.name, tip: (r) => `${human(r.size)} · ${pct(r.size)} · ${r.files} files`,
    run: (r) => { if (!r.other && r.name !== "not from a package") { setImgMode("files"); whoInstalls(r.name); } }}));
  box.append(recipes);
  const [lic, lcb] = card("Licences", "Packages in the image per licence expression, with the space they take.");
  lcb.append(hbars(d.licences, {value: (r) => r.packages, label: (r) => r.name, note: (r) => r.other ? `${r.count} more` : "",
    tip: (r) => `${r.packages} ${r.packages === 1 ? "package" : "packages"} · ${human(r.size)}` + (r.names ? " · " + r.names.join(", ") : "")}));
  box.append(lic);
  const [hubs, hb] = card("What everything depends on", "Installed packages that most others need (RDEPENDS): changing them touches the whole image.");
  if (d.hubs.length) hb.append(hbars(d.hubs, {value: (r) => r.dependants, label: (r) => r.package, tip: (r) => `${r.dependants} ${r.dependants === 1 ? "package needs" : "packages need"} it · ${r.examples.join(", ")}`, run: (r) => { setImgMode("files"); whoInstalls(r.package); }}));
  else hb.append(el("div", {class: "meta", text: "No dependencies between installed packages found (pkgdata missing?)."}));
  box.append(hubs);
  const [net, nb] = card("What listens on the network", "From systemd sockets, inetd and the server programs in the image, with their configured port.");
  if (d.ports.length) {
    const table = el("table", {class: "ports"}, el("tr", {}, ...["Port", "Service", "Found in", "At boot", "Package"].map((h) => el("th", {text: h}))));
    for (const p of d.ports) table.append(el("tr", {}, el("td", {class: "num", text: `${p.port}/${p.proto}`}), el("td", {text: p.what}), el("td", {class: "meta", text: p.how}),
      el("td", {text: p.boot ? "● yes" : "○ on demand"}), el("td", {class: "meta", text: p.package || "—"})));
    nb.append(table);
  } else nb.append(el("div", {class: "finding ok"}, el("span", {class: "ic", text: "✔"}), el("span", {text: "Nothing listens on the network.", }, el("small", {text: "No SSH, web, DNS, MQTT or other server program, socket unit or inetd service in this image."}))));
  box.append(net);
  const [sec, sb] = card("Security at a glance", "Accounts, special permissions and what should not ship.");
  const finding = (level, text, fix) => el("div", {class: "finding " + level}, el("span", {class: "ic", text: {error: "✖", warning: "▲", info: "●", ok: "✔"}[level]}), el("span", {text}, ...(fix ? [el("small", {text: fix})] : [])));
  if (d.root.password) sb.append(finding(d.root.empty ? "error" : "ok", `root password: ${d.root.password}`));
  for (const f of d.findings) sb.append(finding(f.level, f.text.replace(/(\d+) bytes/, (_, n) => human(Number(n))), f.fix));
  sb.append(finding(d.setuid.length ? "info" : "ok", `${d.setuid.length} setuid/setgid ${d.setuid.length === 1 ? "file" : "files"}`, d.setuid.map((f) => `${f.path} (${f.mode}${f.recipe ? ", " + f.recipe : ""})`).join(" · ")));
  sb.append(finding(d.writable.length ? "warning" : "ok", d.writable.length ? `${d.writable.length} world-writable paths without the sticky bit` : "No world-writable path without the sticky bit", d.writable.slice(0, 8).join(" · ")));
  box.append(sec);
}
async function loadDeviceTrees() {
  const box = $("img-dt"); box.textContent = ""; skeletonIn(box);
  try { dtFiles = (await api(`/api/devicetree?profile=${prof()}`)).files; } catch (error) { box.textContent = ""; box.append(el("div", {class: "empty", text: error.message})); return; }
  box.textContent = "";
  if (!dtFiles.length) {
    box.append(el("div", {class: "empty", text: "No device tree deployed. ARM, RISC-V and most board machines deploy .dtb files with the kernel (KERNEL_DEVICETREE); x86 and most QEMU machines have none."}));
    return;
  }
  const machine = imgCurrent ? imgCurrent.machine : "";
  const ordered = [...dtFiles].sort((a, b) => (b.machine === machine) - (a.machine === machine));
  const files = el("div", {class: "svc-rows"});
  box.append(el("details", {class: "svc-group", open: ""}, el("summary", {}, el("b", {text: "Deployed device trees"}), el("span", {class: "count", text: String(dtFiles.length)}), el("span", {class: "meta", text: "tmp/deploy/images"})), files));
  for (const f of ordered) files.append(el("div", {class: "svc " + (f.overlay ? "off" : "on") + (dtCurrent && dtCurrent.name === f.name && dtCurrent.machine === f.machine ? " selected" : ""), tabindex: "0", role: "button", title: f.path,
    onclick: () => openDeviceTree(f), onkeydown: (e) => { if (e.key === "Enter") openDeviceTree(f); }},
    el("span", {class: "dot", "aria-hidden": "true"}), el("span", {class: "n"}, f.name, el("small", {text: f.overlay ? "overlay" : "base device tree"})), el("span", {class: "p", text: `${f.machine} · ${human(f.size)}`})));
  box.append(el("div", {id: "dt-devices"}));
  if (!dtCurrent) openDeviceTree(ordered[0]);
}
async function openDeviceTree(file) {
  const detail = $("img-detail"); detail.textContent = ""; skeletonIn(detail);
  let data;
  try { data = await api(`/api/devicetree?profile=${prof()}&name=${encodeURIComponent(file.name)}&machine=${encodeURIComponent(file.machine)}`); }
  catch (error) { detail.textContent = ""; detail.append(el("div", {class: "empty", text: error.message})); return; }
  dtCurrent = data;
  for (const row of document.querySelectorAll("#img-dt .svc")) row.classList.toggle("selected", row.title === file.path);
  detail.textContent = "";
  const facts = [["Model", data.model], ["Compatible", data.compatible.join(", ")], ["Boot arguments", data.bootargs], ["Console", data.stdout], ["Memory", data.memory.join(", ")],
                 ["Devices", `${data.enabled.length} enabled · ${data.disabled.length} disabled`]].filter(([, v]) => v);
  detail.append(el("div", {class: "sec"}, el("h3", {text: data.name}), el("dl", {}, ...facts.flatMap(([k, v]) => [el("dt", {text: k}), el("dd", {text: v})])),
    el("div", {class: "advice", text: data.overlay ? "An overlay: the bootloader applies it on top of a base device tree." :
      "To change it, add a .dts or .dtsi to your BSP layer and list it in KERNEL_DEVICETREE, or ship an overlay; never edit the kernel's own tree."})));
  const find = el("input", {type: "search", placeholder: "Search the device tree… (node, compatible, property)", "aria-label": "Search the device tree"});
  const lines = el("div", {class: "dts", role: "document"});
  const rows = data.dts.split("\n");
  rows.forEach((line, i) => lines.append(el("div", {"data-line": String(i), text: line || "\u00a0"})));
  const status = el("span", {class: "meta"});
  let hits = [], at = -1;
  const jump = (index) => { const target = lines.children[index]; if (!target) return; for (const n of lines.querySelectorAll(".hit-now")) n.classList.remove("hit-now"); target.classList.add("hit-now"); target.scrollIntoView({block: "center"}); };
  find.addEventListener("input", () => {
    const q = find.value.trim().toLowerCase(); hits = []; at = -1;
    for (const [i, node] of [...lines.children].entries()) { const hit = q && rows[i].toLowerCase().includes(q); node.classList.toggle("hit", !!hit); if (hit) hits.push(i); }
    status.textContent = q ? `${hits.length} lines` : "";
  });
  find.addEventListener("keydown", (e) => { if (e.key === "Enter" && hits.length) { at = (at + (e.shiftKey ? -1 + hits.length : 1)) % hits.length; jump(hits[at]); status.textContent = `${at + 1} of ${hits.length}`; } });
  detail.append(el("div", {class: "sec dts-bar"}, find, status), lines);
  const nodeLine = (path) => { const name = path.split("/").pop(); return rows.findIndex((l) => new RegExp("^\\s*(\\w+: )?" + name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{$").test(l)); };
  const devices = $("dt-devices"); if (!devices) return; devices.textContent = "";
  for (const [title, hint, list, state] of [["Enabled devices", "status okay", data.enabled, "on"], ["Disabled devices", "status disabled: present, not used", data.disabled, "off"]]) {
    if (!list.length) continue;
    const body = el("div", {class: "svc-rows"});
    devices.append(el("details", {class: "svc-group", open: ""}, el("summary", {}, el("b", {text: title}), el("span", {class: "count", text: String(list.length)}), el("span", {class: "meta", text: hint})), body));
    for (const d of list.slice(0, 400)) body.append(el("div", {class: "svc " + state, tabindex: "0", role: "button", title: d.path,
      onclick: () => jump(nodeLine(d.path)), onkeydown: (e) => { if (e.key === "Enter") jump(nodeLine(d.path)); }},
      el("span", {class: "dot", "aria-hidden": "true"}), el("span", {class: "n"}, d.path.split("/").pop(), el("small", {text: d.path})), el("span", {class: "p", text: d.compatible[0]})));
  }
}
async function revealPath(path) {
  // Open the folder of a file and show it, as if it had been clicked in Files.
  await openDir(path.split("/").slice(0, -1).join("/") || "/");
  const child = imgLast && imgLast.children.find((c) => c.path === path);
  if (child) showFile(child);
}
async function loadServices() {
  const box = $("img-services"); box.textContent = ""; skeletonIn(box);
  if (!imgCurrent) { box.textContent = ""; return; }
  let data;
  try { data = await api(`/api/image/services?${imgQuery()}`); }
  catch (error) { box.textContent = ""; box.append(el("div", {class: "empty", text: error.message})); return; }
  box.textContent = "";
  box.append(el("div", {class: "svc-init"}, el("b", {text: data.init}), el("span", {class: "meta", text: data.init === "unknown" ? "init system not recognised" :
    `init system${data.default_target ? " · boots to " + data.default_target : ""} · ${data.starts.length} started at boot`})));
  const owner = (row) => row.package ? row.package + (row.recipe && row.recipe !== row.package ? " · " + row.recipe : "") : "not from a package";
  const group = (title, hint, rows, render) => {
    if (!rows.length) return;
    const body = el("div", {class: "svc-rows"});
    box.append(el("details", {class: "svc-group", open: ""}, el("summary", {}, el("b", {text: title}), el("span", {class: "count", text: String(rows.length)}), el("span", {class: "meta", text: hint})), body));
    for (const row of rows) body.append(render(row));
  };
  const item = (state, name, sub, side, path, title = "") => el("div", {class: "svc " + state, tabindex: "0", role: "button", title: title || path,
    onclick: () => revealPath(path), onkeydown: (e) => { if (e.key === "Enter") revealPath(path); }},
    el("span", {class: "dot", "aria-hidden": "true"}), el("span", {class: "n"}, name, ...(sub ? [el("small", {text: sub})] : [])), el("span", {class: "p", text: side}));
  const units = data.units.filter((u) => u.kind !== "target");
  group("Starts at boot", "enabled systemd units", units.filter((u) => u.enabled.length && !u.masked), (u) =>
    item("on", u.name, u.description || u.exec, `${u.enabled.join(", ")} · ${owner(u)}`, u.path, u.exec));
  group("Installed, not enabled", "started on demand (sockets, D-Bus, other units) or not at all", units.filter((u) => !u.enabled.length && !u.masked), (u) =>
    item("off", u.name, u.description || u.exec, owner(u), u.path, u.exec));
  group("Masked", "linked to /dev/null: never starts", data.units.filter((u) => u.masked), (u) => item("mask", u.name, "", owner(u), u.path));
  const sysv = (s) => item(s.runlevels.length ? "on" : "off", s.name, s.runlevels.length ? `runlevel ${s.runlevels.join("")} · S${s.order}` : "not linked in any runlevel", owner(s), s.path);
  group("Init scripts at boot", "SysV, in start order: rcS.d first, then the runlevel (S links in /etc/rc?.d)", data.sysv.filter((s) => s.boot), sysv);
  group("At shutdown and reboot", "runlevels 0 and 6", data.sysv.filter((s) => !s.boot && s.runlevels.length), sysv);
  group("Init scripts not linked", "helpers and scripts started by others", data.sysv.filter((s) => !s.runlevels.length), sysv);
  group("udev rules", "applied in name order; a file in /etc replaces the one in /lib", data.udev, (r) =>
    item(r.masked ? "mask" : r.overridden ? "off" : "on", r.name, r.masked ? "disabled by a /dev/null link in /etc" : r.overridden ? "replaced by the file in /etc" : `${r.rules} rules${r.comment ? " · " + r.comment : ""}`, owner(r), r.path));
  group("D-Bus", "services started on request and bus policies", data.dbus, (d) =>
    item(d.kind === "activation" ? "on" : "off", d.name, d.kind === "activation" ? `${d.bus} bus · ${d.unit || d.exec}` : `${d.bus} bus policy`, owner(d), d.path));
  box.append(el("div", {class: "advice", text: "To change what starts: an append to the recipe (SYSTEMD_AUTO_ENABLE, SYSTEMD_SERVICE, INITSCRIPT_PARAMS), or remove its package from the image. Select an entry for its recipe and Change it with an append."}));
}
async function openDir(dir) {
  const list = $("img-list"); list.textContent = ""; skeletonIn(list);
  let data;
  try { data = await api(`/api/image/dir?${imgQuery()}&dir=${encodeURIComponent(dir)}`); }
  catch (error) { list.textContent = ""; list.append(el("div", {class: "empty", text: error.message})); return; }
  imgDir = data.dir; imgLast = data; list.textContent = "";
  const crumbs = $("img-crumbs"); crumbs.textContent = "";
  const parts = imgDir.split("/").filter(Boolean);
  crumbs.append(el("button", {text: "/", onclick: () => openDir("/")}));
  parts.forEach((part, i) => { crumbs.append(el("span", {class: "meta", text: "›"}), el("button", {text: part, onclick: () => openDir("/" + parts.slice(0, i + 1).join("/"))})); });
  $("img-dir-size").textContent = imgMode === "files" ? human(data.size) : "";
  const biggest = Math.max(1, ...data.children.map((c) => c.size));
  if (imgDir !== "/") list.append(entRow({name: "..", type: "up", size: 0}, biggest, () => openDir(imgDir.split("/").slice(0, -1).join("/") || "/")));
  for (const child of data.children) list.append(entRow(child, biggest, () => child.type === "dir" ? openDir(child.path) : showFile(child)));
  if (!data.children.length) list.append(el("div", {class: "empty", text: "Empty folder"}));
}
function entRow(child, biggest, open) {
  const icon = {dir: "▸", file: "·", link: "↪", up: "↰"}[child.type];
  const row = el("div", {class: "ent " + child.type + (imgSelected === child.path ? " selected" : ""), tabindex: "0", role: "option", title: child.path || "", onclick: open,
    onkeydown: (event) => { if (event.key === "Enter") open(); else if (event.key === "Backspace" && imgDir !== "/") openDir(imgDir.split("/").slice(0, -1).join("/") || "/"); }},
    el("span", {class: "i", text: icon}), el("span", {class: "n"}, child.name, ...(child.type === "link" ? [el("small", {text: " → " + child.target})] : [])),
    el("span", {class: "w", style: `width:${child.type === "up" ? 0 : Math.max(child.size ? 2 : 0, 100 * child.size / biggest)}%`}),
    el("span", {class: "s", text: child.type === "up" || child.type === "link" ? "" : human(child.size)}),
    el("span", {class: "p", text: child.package ? child.package + (child.recipe && child.recipe !== child.package ? " · " + child.recipe : "") : ""}));
  return row;
}
async function showFile(child) {
  imgSelected = child.path;
  for (const row of document.querySelectorAll("#img-list .ent")) row.classList.toggle("selected", row.title === child.path);
  const box = $("img-detail"); box.textContent = "";
  box.append(el("div", {class: "sec"}, el("h3", {text: child.path}), el("dl", {},
    el("dt", {text: "Size"}), el("dd", {text: human(child.size)}), el("dt", {text: "Mode"}), el("dd", {text: (child.mode & 0o7777).toString(8).padStart(4, "0")}),
    ...(child.owner ? [el("dt", {text: "Owner"}), el("dd", {text: child.owner.replace(":", " · group ")})] : []),
    ...(child.target ? [el("dt", {text: "Link to"}), el("dd", {text: child.target})] : []))));
  const who = el("div", {class: "sec"}, el("div", {class: "skeleton"})); box.append(who);
  const content = el("div"); box.append(content);
  whoInto(who, child.path);
  if (child.type === "file" && child.size <= 262144) {
    try {
      const file = await api(`/api/image/file?${imgQuery()}&path=${encodeURIComponent(child.path)}`);
      content.append(file.binary ? el("div", {class: "sec meta", text: "Binary file: not shown."}) : el("pre", {text: file.text || "(empty)"}));
    } catch (error) { content.append(el("div", {class: "sec meta", text: error.message})); }
  }
}
async function whoInto(box, query) {
  let data;
  try { data = await api(`/api/whois?profile=${prof()}&q=${encodeURIComponent(query)}`); }
  catch (error) { box.textContent = ""; box.append(el("div", {class: "meta", text: error.message})); return; }
  box.textContent = "";
  if (!data.results.length) { box.append(el("div", {class: "advice", text: data.note || "No package installs it."})); return; }
  for (const row of data.results.slice(0, 3)) {
    const mine = row.appends.filter((a) => a.mine);
    box.append(el("dl", {},
      el("dt", {text: "Package"}), el("dd", {text: row.installed_as + (row.installed_as !== row.package ? ` (${row.package})` : "")}),
      el("dt", {text: "Recipe"}), el("dd", {text: `${row.recipe} ${row.version}`}),
      el("dt", {text: "Layer"}), el("dd", {text: row.layer ? row.layer + (row.mine ? " · yours" : " · upstream") : "unknown"}),
      ...(row.images.length ? [el("dt", {text: "In"}), el("dd", {text: row.images.map((i) => i.image + (i.pulled_in_by.length ? " (pulled in by " + i.pulled_in_by.slice(0, 3).join(", ") + ")" : "")).join("; ")})] : []),
      ...(row.appends.length ? [el("dt", {text: "Appends"}), el("dd", {text: row.appends.map((a) => a.path.split("/").slice(-4).join("/") + (a.mine ? " (yours)" : "")).join("\n")})] : [])));
    const advice = mine.length ? `Your layer already appends ${row.recipe}: change ${mine[0].path.split("/").pop()}.` : row.mine ? `${row.recipe} is in your layer: edit ${row.recipe_file.split("/").pop()}.` :
      `${row.recipe} comes from ${row.layer || "an upstream layer"}: never edit it there. Add a ${row.recipe}_%.bbappend to your layer; Studio creates it for you.`;
    box.append(el("div", {class: "advice", text: advice}));
    const actions = el("div", {class: "actions"});
    if (!mine.length && !row.mine) {
      const file = query.startsWith("/etc/") && query.split("/").length === 3 ? query.split("/").pop() : "";
      actions.append(el("button", {class: "btn primary", text: "✦ Change it with an append", title: file ? `Studio: a ${row.recipe} append that installs your own /etc/${file}, starting from today's content` : `Studio: a ${row.recipe} append`,
        onclick: async () => {
          let content = "";
          if (file && imgCurrent) { try { const data = await api(`/api/image/file?${imgQuery()}&path=${encodeURIComponent(query)}`); content = data.binary ? "" : data.text; } catch (error) { content = ""; } }
          setView("studio"); await startForm("append", {recipe: row.recipe, category: row.group && row.group.startsWith("recipes-") ? row.group : "recipes-core", file, file_content: content});
          if (content) toast("Starting from the device's file", `${row.recipe}_%.bbappend will install your /etc/${file}; edit it in the preview with "edit before creating"`, "info");
        }}));
    }
    actions.append(el("button", {class: "btn", text: "Show the recipe", onclick: () => { setView("recipes"); $("meta-search").value = row.recipe; setTimeout(() => { renderLayers(); renderMeta(); }, 50); }}));
    box.append(actions);
  }
  if (data.more) box.append(el("div", {class: "meta", text: `${data.more} more packages match`}));
}
async function whoInstalls(query) {
  query = (query || $("img-find").value).trim(); if (!query) return;
  $("img-find").value = query;
  const box = $("img-detail"); box.textContent = "";
  box.append(el("div", {class: "sec"}, el("h3", {text: "Which recipe installs " + query}), el("div", {class: "meta", text: "From the package data of your last builds; no BitBake run."})));
  const who = el("div", {class: "sec"}); box.append(who);
  await whoInto(who, query);
  // A file path: open its folder and select it.
  if (query.startsWith("/") && imgCurrent) { const dir = query.split("/").slice(0, -1).join("/") || "/"; imgSelected = query; await openDir(dir); }
}

/* Studio: a guided way to create Yocto metadata, one step at a time */
let lastPlan = null, studioVar = "", studioSections = {}, studioMode = "", studioKinds = [], studioActive = false;
let sgSteps = [], sgStep = 0, sgVisited = new Set(), planEdits = {}, ideCurrent = null, layerFiles = {};
let studioPreviewTimer = null;
function previewStudioSoon() { clearTimeout(studioPreviewTimer); studioPreviewTimer = setTimeout(previewStudio, 300); }
const GUIDE = {
  layer: {gets: "meta-acme/conf/layer.conf, README, licence", when: "Start here: what you create next goes into it."},
  distro: {gets: "conf/distro/acme.conf", when: "Your product's name and version on the device, its init system, security and SBOM policy."},
  machine: {gets: "conf/machine/acme-board.conf", when: "Your board, starting from a reference machine you already build for."},
  image: {gets: "recipes-core/images/acme-image.bb", when: "What ends up on the device. Build it with bitbake acme-image."},
  recipe: {gets: "recipes-example/acme-hello/ with source and licence", when: "Your application, built and packaged, ready to add to an image."},
  append: {gets: "recipes-…/<recipe>/<recipe>_%.bbappend", when: "Change an existing recipe without copying it: add a file, set options."},
};
const STEP_HELP = {
  where: "Everything you create lives in a layer of your own; upstream layers such as Poky and OE-Core are never modified.",
  identity: "The names BitBake uses and, for distributions, what the device shows.",
  contents: "What it starts from and what goes in. Each option says what it does.",
  policy: "Security hardening, licences and the SBOM policy.",
  review: "Check your choices and exactly what Create will do. Nothing has been written yet.",
};

let studioRequest = 0;
async function loadStudio() {
  const ticket = ++studioRequest, kind = studioKind;
  const data = await api(`/api/studio/fields?profile=${prof()}&kind=${kind}`);
  studioSections = data.sections || {}; studioMode = data.mode; studioKinds = data.kinds;
  const box = $("sg-kinds"); box.textContent = "";
  studioKinds.forEach((kind, i) => box.append(el("button", {class: "sg-kind", onclick: () => startForm(kind.id)},
    el("div", {class: "top"}, el("span", {class: "ico", text: ICONS[kind.id] || "✦"}), el("b", {text: kind.title})),
    el("p", {text: kind.description}),
    el("div", {class: "gets", title: "You get", text: (GUIDE[kind.id] || {}).gets || ""}),
    el("div", {class: "when"}, el("b", {text: "Use it for "}), (GUIDE[kind.id] || {}).when || ""))));
  // A form opened meanwhile (Change it, What next) wins over this load.
  if (ticket !== studioRequest || kind !== studioKind) return;
  showScreen(studioActive ? "flow" : "start");
  if (studioActive) await openForm(studioKind, data);
}
function showScreen(name) { $("sg-start").hidden = name !== "start"; $("sg-flow").hidden = name !== "flow"; $("sg-done").hidden = name !== "done"; }

async function startForm(kind, preset = {}) {
  studioRequest++;
  studioKind = kind; studioValues = {layer: studioValues.layer, new_layer: studioValues.new_layer, ...preset};
  planEdits = {}; studioVar = ""; studioActive = true; sgStep = 0; sgVisited = new Set(); $("sg-edit").checked = false;
  showScreen("flow");
  await openForm(kind);
}
async function openForm(kind, data = null) {
  data = data && data.fields ? data : await api(`/api/studio/fields?profile=${prof()}&kind=${kind}`);
  if (kind !== studioKind) return;
  const info = studioKinds.find((k) => k.id === kind) || {title: kind, description: ""};
  $("st-title").textContent = info.title; $("st-desc").textContent = info.description; $("sg-kind-ico").textContent = ICONS[kind] || "✦";
  studioFields = data.fields;
  const choosable = ["distro", "machine"].includes(kind) && ["host", "container"].includes(data.mode);
  $("st-use-wrap").hidden = !choosable;
  $("st-use-label").textContent = `use this ${kind === "distro" ? "DISTRO" : "MACHINE"} in profile ${prof()}`;
  const form = $("st-form"); form.textContent = "";
  let section = null;
  for (const field of studioFields) {
    if (field.choices.length && !field.choices.includes(studioValues[field.id] ?? "") && field.kind === "choice") delete studioValues[field.id];
    const value = studioValues[field.id] ?? field.default;
    studioValues[field.id] = value;
    if (field.section !== section) { section = field.section; form.append(el("fieldset", {class: "st-sec", "data-section": section}, el("legend", {text: studioSections[section] || section}))); }
    form.lastChild.append(studioField(field, value));
  }
  sgSteps = [...new Set(studioFields.map((f) => f.section)), "review"];
  syncNewLayer();
  await previewStudio();
  showStep(sgStep);
}
function stepOf(fieldId) { const field = studioFields.find((f) => f.id === fieldId); return field ? sgSteps.indexOf(field.section) : -1; }
function showStep(index) {
  sgStep = Math.max(0, Math.min(index, sgSteps.length - 1)); sgVisited.add(sgStep);
  const name = sgSteps[sgStep], review = name === "review";
  for (const set of document.querySelectorAll("#st-form fieldset")) set.hidden = set.dataset.section !== name;
  $("st-form").hidden = review; $("sg-review").hidden = !review;
  $("sg-step-title").textContent = review ? "Review and create" : (studioSections[name] || name);
  $("sg-step-help").textContent = STEP_HELP[name] || "";
  $("sg-back").disabled = sgStep === 0;
  $("sg-next").hidden = review; $("st-create").hidden = !review;
  $("sg-next").textContent = sgSteps[sgStep + 1] === "review" ? "Review →" : "Next →";
  $("sg-hint").textContent = review ? "Ctrl+Enter creates" : "Enter: next step";
  if (review) renderReview();
  renderStepList();
  const first = review ? $("st-create") : $("st-form").querySelector(`fieldset[data-section="${name}"] input[type=text], fieldset[data-section="${name}"] select, fieldset[data-section="${name}"] button`);
  if (first && !first.disabled) first.focus({preventScroll: true});
}
function renderStepList() {
  const list = $("sg-steplist"); list.textContent = "";
  const bad = new Set([...document.querySelectorAll("#st-form .fld.invalid")].map((n) => stepOf(n.dataset.field)));
  if (!lastPlan) bad.add(sgSteps.length - 1);
  sgSteps.forEach((name, i) => {
    const state = i === sgStep ? "current" : bad.has(i) ? "bad" : sgVisited.has(i) ? "done" : "";
    list.append(el("li", {}, el("button", {class: state, onclick: () => showStep(i), "aria-current": String(i === sgStep)},
      el("span", {class: "dot", text: state === "done" ? "✓" : state === "bad" ? "!" : String(i + 1)}), name === "review" ? "Review and create" : (studioSections[name] || name))));
  });
}
function renderReview() {
  const summary = $("sg-summary"); summary.textContent = "";
  for (const field of studioFields) {
    if (field.id === "new_layer" && !(studioValues.layer || "").startsWith("new layer")) continue;
    let value = studioValues[field.id] ?? "";
    if (field.kind === "bool") value = value === "1" ? "yes" : "no";
    if (field.id === "layer" && value.startsWith("/")) value = value.split("/").pop();
    summary.append(el("dt", {text: field.label}), el("dd", {text: value || "—"}));
  }
}
function closeForm() {
  if (Object.keys(planEdits).length && !confirm("Leave this and drop your edits to the generated files?")) return;
  studioActive = false; lastPlan = null; planEdits = {}; studioVar = "";
  showScreen("start");
}

function hintFor(field, choice) { const pair = (field.hints || []).find(([c]) => c === choice); return pair ? pair[1] : ""; }
function studioField(field, value) {
  const box = el("div", {class: "fld", "data-field": field.id});
  const id = "sf-" + field.id;
  box.append(el("div", {class: "top"}, el("label", {class: "f", for: id, text: field.label}), ...(field.required ? [el("span", {class: "req", title: "required", text: "*"})] : []),
    ...(field.var ? [el("code", {class: "var", title: "BitBake variable this sets", text: field.var})] : [])));
  const why = el("div", {class: "why"});
  const focus = () => { studioVar = field.var || ""; renderCode(true); };
  if (field.kind === "choice") {
    const select = el("select", {id});
    // Layers by folder name; the full path is the tooltip and the preview header.
    for (const choice of field.choices) select.append(el("option", {value: choice, text: field.id === "layer" && choice.startsWith("/") ? choice.split("/").pop() : choice, title: choice}));
    select.value = value;
    const explain = () => { const text = hintFor(field, select.value); why.textContent = text; why.hidden = !text; };
    select.addEventListener("change", () => { studioValues[field.id] = select.value; explain(); if (field.id === "layer") syncNewLayer(); previewStudio(); });
    select.addEventListener("focus", focus);
    box.append(select, why); explain();
  } else if (field.kind === "multi") {
    const chosen = new Set(value.split(" ").filter(Boolean)), chips = el("div", {class: "toggles", role: "group", "aria-label": field.label});
    const summary = () => { why.textContent = chosen.size ? [...chosen].map((c) => hintFor(field, c) ? `${c}: ${hintFor(field, c)}` : c).join(" · ") : "none selected"; };
    for (const choice of field.choices) {
      const chip = el("button", {class: "toggle" + (chosen.has(choice) ? " on" : ""), type: "button", text: choice, title: hintFor(field, choice), "aria-pressed": String(chosen.has(choice))});
      chip.addEventListener("click", () => { chosen.has(choice) ? chosen.delete(choice) : chosen.add(choice); chip.classList.toggle("on"); chip.setAttribute("aria-pressed", String(chosen.has(choice))); studioValues[field.id] = [...chosen].join(" "); summary(); previewStudio(); });
      chip.addEventListener("mouseenter", () => { why.textContent = `${choice}: ${hintFor(field, choice) || "no description"}`; });
      chip.addEventListener("focus", () => { focus(); why.textContent = `${choice}: ${hintFor(field, choice) || "no description"}`; });
      chip.addEventListener("mouseleave", summary); chip.addEventListener("blur", summary);
      chips.append(chip);
    }
    box.append(chips, why); summary();
  } else if (field.kind === "bool") {
    const input = el("input", {type: "checkbox", id}); input.checked = value === "1";
    const label = el("span", {text: input.checked ? "on" : "off"});
    input.addEventListener("change", () => { studioValues[field.id] = input.checked ? "1" : ""; label.textContent = input.checked ? "on" : "off"; previewStudio(); });
    input.addEventListener("focus", focus);
    box.append(el("label", {class: "check"}, el("span", {class: "switch"}, input, el("span")), label));
  } else {
    const input = el("input", {type: "text", id, placeholder: field.placeholder || "", spellcheck: "false", autocomplete: "off"}); input.value = value;
    input.addEventListener("input", () => {
      studioValues[field.id] = input.value; clearTimeout(typingTimer); typingTimer = setTimeout(previewStudio, 180);
      // Help that quotes the default ("bitbake acme-image") follows what is typed.
      if (help && field.default && field.info.includes(field.default)) help.textContent = field.info.split(field.default).join(input.value.trim() || field.default);
    });
    input.addEventListener("focus", focus);
    box.append(input);
  }
  const help = field.info ? el("div", {class: "help", text: field.kind === "text" && field.default && value ? field.info.split(field.default).join(value) : field.info}) : null;
  if (help) box.append(help);
  return box;
}
function syncNewLayer() {
  const node = document.querySelector('#st-form [data-field="new_layer"]');
  if (node) node.hidden = !(studioValues.layer || "").startsWith("new layer");
}
function strings(text) {
  // Tokens of a value: "strings" (with their ${expansions}) and bare ${expansions}.
  const out = [], re = /"(?:[^"\\]|\\.)*"|\$\{[^}"]*\}/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(["", text.slice(last, m.index)]);
    if (m[0][0] === '"') {
      let at = 0, e; const inner = /\$\{[^}]*\}/g;
      while ((e = inner.exec(m[0]))) { if (e.index > at) out.push(["t-str", m[0].slice(at, e.index)]); out.push(["t-exp", e[0]]); at = e.index + e[0].length; }
      if (at < m[0].length) out.push(["t-str", m[0].slice(at)]);
    } else out.push(["t-exp", m[0]]);
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(["", text.slice(last)]);
  return out;
}
function highlightLine(line) {
  // A small BitBake highlighter returning [class, text] tokens: comments, assignments, keywords, strings, ${expansions}.
  if (/^\s*#/.test(line)) return [["t-com", line]];
  let m = line.match(/^(\s*)(export\s+)?([A-Za-z_][\w${}:/.+-]*?)(\s*)(\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)(.*)$/);
  if (m) return [["", m[1]], ["t-kw", m[2] || ""], ["t-var", m[3]], ["", m[4]], ["t-op", m[5]], ...strings(m[6])];
  m = line.match(/^(\s*)(inherit|require|include|addtask|deltask|EXPORT_FUNCTIONS|addhandler|python|fakeroot)\b(.*)$/);
  if (m) return [["", m[1]], ["t-kw", m[2]], ...strings(m[3])];
  m = line.match(/^(\s*)([\w:-]+)(\s*\(\s*\)\s*\{.*)$/);
  if (m) return [["", m[1]], ["t-fn", m[2]], ...strings(m[3])];
  return strings(line);
}
/* Preview: where the files go, and their content */
async function renderWhere() {
  const box = $("sg-where"); box.textContent = "";
  if (!lastPlan) { box.append(el("div", {class: "more", text: "Fix the highlighted field to see where the files go."})); return; }
  const layerName = lastPlan.layer.split("/").pop();
  $("st-layer").textContent = lastPlan.new_layer ? " · new layer" : "";
  let existing = [];
  if (!lastPlan.new_layer) {
    if (!(lastPlan.layer in layerFiles)) { try { layerFiles[lastPlan.layer] = (await api(`/api/studio/files?profile=${prof()}&layer=${encodeURIComponent(lastPlan.layer)}`)).files; } catch (error) { layerFiles[lastPlan.layer] = []; } }
    existing = layerFiles[lastPlan.layer];
  }
  box.textContent = "";
  box.append(el("div", {class: "row-w layer", title: lastPlan.layer}, "▤ " + layerName, ...(lastPlan.new_layer ? [el("span", {class: "badge-new", text: "new layer"})] : [])));
  const planned = Object.keys(lastPlan.files), folders = [...new Set(planned.map((n) => n.includes("/") ? n.slice(0, n.lastIndexOf("/")) : ""))].sort();
  for (const folder of folders) {
    const depth = folder ? 1 : 0;
    if (folder) box.append(el("div", {class: "row-w", style: "--d:1"}, "▾ " + folder + "/"));
    const here = (n) => (n.includes("/") ? n.slice(0, n.lastIndexOf("/")) : "") === folder;
    const mine = planned.filter(here), others = existing.filter((n) => here(n) && !mine.includes(n)).sort();
    for (const name of mine) box.append(el("div", {class: "row-w new", style: `--d:${depth + 1}`, title: "Will be created", onclick: () => openPlanTab(name)},
      "+ " + name.split("/").pop(), el("span", {class: "badge-new", text: "new"})));
    for (const name of others.slice(0, 6)) box.append(el("div", {class: "row-w", style: `--d:${depth + 1}`}, "  " + name.split("/").pop()));
    if (others.length > 6) box.append(el("div", {class: "more", style: `--d:${depth + 1}`, text: `… ${others.length - 6} more already there`}));
  }
}
function planNames() { return lastPlan ? [lastPlan.main, ...Object.keys(lastPlan.files).filter((n) => n !== lastPlan.main)].filter((n) => n in lastPlan.files) : []; }
function tabText(name) { return planEdits[name] ?? lastPlan.files[name]; }
function openPlanTab(name) { ideCurrent = name; renderTabs(); renderEditor(); }
function renderTabs() {
  const box = $("ide-tabs"); box.textContent = "";
  for (const name of planNames()) box.append(el("div", {class: "ide-tab" + (name === ideCurrent ? " active" : "") + (name === lastPlan.main ? " main" : "") + (name in planEdits ? " dirty" : ""),
    role: "tab", title: name + (name === lastPlan.main ? " · the main file" : ""), "aria-selected": String(name === ideCurrent), onclick: () => openPlanTab(name)}, el("span", {class: "nm", text: name.split("/").pop()})));
}
function renderEditor() {
  const text = $("ide-text");
  if (!lastPlan || !(ideCurrent in lastPlan.files)) { text.value = ""; $("ide-path-text").textContent = ""; paintCode(); return; }
  if (text.value !== tabText(ideCurrent)) text.value = tabText(ideCurrent);
  text.readOnly = !$("sg-edit").checked;
  $("ide-path-text").textContent = ideCurrent + (ideCurrent in planEdits ? " · edited by you" : "");
  paintCode();
}
function paintCode() {
  const lines = $("ide-text").value.split("\n");
  // Whole words only: DISTRO must not light up DISTRO_NAME or ${DISTRO}.
  const word = studioVar ? new RegExp("(^|[^\\w@{-])" + studioVar.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&") + "(?![\\w-])") : null;
  let first = -1;
  const code = document.createDocumentFragment(), gutter = document.createDocumentFragment();
  lines.forEach((line, i) => {
    const hit = !!word && word.test(line); if (hit && first < 0) first = i;
    const row = el("span", {class: "ln" + (hit ? " hl" : "")});
    for (const [cls, text] of highlightLine(line)) if (text) row.append(cls ? el("span", {class: cls, text}) : document.createTextNode(text));
    if (!line) row.append(" ");
    code.append(row); gutter.append(el("div", {class: hit ? "hl" : "", text: String(i + 1)}));
  });
  $("ide-hl").replaceChildren(code); $("ide-gutter").replaceChildren(gutter);
  clearTimeout(lintTimer); lintTimer = setTimeout(langLint, 350);
  syncScroll();
  if (first >= 0) { const area = $("ide-text"), top = first * parseFloat(getComputedStyle(area).lineHeight); if (top < area.scrollTop || top > area.scrollTop + area.clientHeight - 40) { area.scrollTop = Math.max(0, top - 60); syncScroll(); } }
}
/* Themes: System follows the operating system; the others are chosen here and remembered in this browser. */
const THEME_LIST = [["system", "System", ["#080d11", "#84c9c0", "#f4f2ec"]], ["dark", "Bitloom dark", ["#0f1920", "#84c9c0", "#d4e1e7"]], ["light", "Bitloom light", ["#fbfaf6", "#17786d", "#23292f"]],
  ...Object.entries(window.BITLOOM_THEMES || {}).map(([id, t]) => [id, t.label, [t.surface, t.accent, t.fg]])];
function themeNow() { try { return localStorage.getItem("bitloom-theme") || "system"; } catch (error) { return "system"; } }
function applyTheme(id) {
  if (id === "system") document.documentElement.removeAttribute("data-theme"); else document.documentElement.setAttribute("data-theme", id);
  try { if (id === "system") localStorage.removeItem("bitloom-theme"); else localStorage.setItem("bitloom-theme", id); } catch (error) { /* private window: this session only */ }
  for (const b of document.querySelectorAll("#theme-menu button")) b.setAttribute("aria-checked", String(b.dataset.theme === id));
}
function openThemes() {
  const menu = $("theme-menu"), open = menu.hidden;
  menu.hidden = !open; $("theme-btn").setAttribute("aria-expanded", String(open));
  if (!open) return;
  menu.textContent = "";
  const current = themeNow();
  for (const [title, items] of [["Bitloom", THEME_LIST.slice(0, 3)], ["Palettes", THEME_LIST.slice(3)]]) {
    menu.append(el("div", {class: "grp", text: title}));
    for (const [id, label, colours] of items) menu.append(el("button", {role: "menuitemradio", "data-theme": id, "aria-checked": String(id === current), onclick: () => applyTheme(id)},
      el("span", {class: "sw", "aria-hidden": "true"}, ...colours.map((c) => el("span", {style: `background:${c}`}))), el("span", {text: label})));
  }
  menu.querySelector('[aria-checked="true"]')?.focus();
}

/* Migration assistant: from the official migration guides to a build on the new release, one step after the other. */
let mgData = null, mgShow = "all", mgSelected = new Set(), mgKas = null;
async function loadMigrate(target = null) {
  const box = $("mg-findings"); box.textContent = ""; skeletonIn(box);
  let data;
  try { data = await api(`/api/migrate?profile=${prof()}${target || $("mg-to").value ? "&to=" + encodeURIComponent(target || $("mg-to").value) : ""}`); }
  catch (error) { box.textContent = ""; box.append(el("div", {class: "empty", text: error.message})); return; }
  mgData = data; box.textContent = "";
  $("mg-from").textContent = data.source_label || "release unknown";
  const pick = $("mg-to"); pick.textContent = "";
  for (const t of data.targets || []) pick.append(el("option", {value: t.series, text: t.label}));
  if (data.target) pick.value = data.target;
  pick.disabled = !(data.targets || []).length;
  if (!(data.targets || []).length) { box.append(el("div", {class: "empty", text: data.reason || "Nothing to migrate."})); $("mg-path").textContent = ""; $("mg-kpis").textContent = ""; return; }
  const path = $("mg-path"); path.textContent = "";
  path.append(el("li", {}, el("a", {href: "#", onclick: (e) => e.preventDefault()}, el("b", {text: data.source}), " now")));
  for (const step of data.steps) path.append(el("li", {}, el("a", {href: step.guide, target: "_blank", rel: "noopener", title: "Migration guide " + step.version}, el("b", {text: step.version}), step.series)));
  const kpis = $("mg-kpis"); kpis.textContent = "";
  for (const [value, label, alert] of [[data.counts.breaks, "break the build", data.counts.breaks > 0], [data.counts.review, "to review"], [data.counts.info, "good to know"], [data.fixable, "with a safe fix"]])
    kpis.append(el("div", {class: "kpi" + (alert ? " alert" : "")}, el("b", {text: String(value)}), el("span", {text: label})));
  mgSelected = new Set(data.findings.map((f, i) => f.fixes.length ? i : -1).filter((i) => i >= 0));
  renderMigrateFindings(); loadBackups(); loadMigrateKas();
  $("mg-step-1").classList.toggle("done", data.counts.breaks === 0);
  $("mg-step-2").classList.toggle("done", data.fixable === 0);
}
function renderMigrateFindings() {
  const box = $("mg-findings"); box.textContent = "";
  const seg = $("mg-show"); seg.textContent = "";
  for (const [id, label] of [["all", `All ${mgData.findings.length}`], ["breaks", "Breaks the build"], ["review", "To review"], ["info", "Good to know"], ["fixable", "Safe fixes"]])
    seg.append(el("button", {role: "radio", "aria-checked": String(mgShow === id), text: label, onclick: () => { mgShow = id; renderMigrateFindings(); }}));
  if (!mgData.findings.length) { box.append(el("div", {class: "finding ok"}, el("span", {class: "ic", text: "✔"}), el("span", {text: "Nothing in your files needs changing for this migration. Move the checkout (step 3)."}))); return; }
  const titles = {breaks: "Breaks the build", review: "Changes behaviour: review", info: "Good to know"};
  let group = null;
  mgData.findings.forEach((f, i) => {
    if (mgShow === "fixable" ? !f.fixes.length : mgShow !== "all" && f.severity !== mgShow) return;
    if (f.severity !== group) { group = f.severity; box.append(el("div", {class: "mg-group", text: titles[group]})); }
    const check = f.fixes.length ? el("input", {type: "checkbox", "aria-label": "Apply this fix", onchange: (e) => { if (e.target.checked) mgSelected.add(i); else mgSelected.delete(i); updateMigrateSelection(); }}) : el("span");
    if (f.fixes.length && mgSelected.has(i)) check.checked = true;
    const version = (mgData.steps.find((s) => s.series === f.step) || {}).version || f.step;
    box.append(el("div", {class: "mg-f " + f.severity}, el("span", {class: "ic", text: {breaks: "✖", review: "▲", info: "●"}[f.severity]}), check,
      el("div", {}, el("span", {class: "rel", text: version}), el("b", {text: f.title}), ...(f.fixes.length ? [el("span", {class: "fixtag", text: "✓ safe fix"})] : []),
        el("div", {class: "w", text: f.where}), el("span", {text: f.detail}), ...(f.advice ? [el("span", {class: "adv", text: f.advice})] : []),
        el("a", {href: f.guide, target: "_blank", rel: "noopener", text: "Migration guide " + version + " ↗"}))));
  });
  updateMigrateSelection();
}
function selectedFixes() { return [...mgSelected].flatMap((i) => mgData.findings[i].fixes); }
function updateMigrateSelection() { $("mg-selected").textContent = `${mgSelected.size} of ${mgData.fixable} selected`; $("mg-apply").disabled = true; $("mg-diffs").textContent = ""; }
function diffBlock(file) {
  const pre = el("pre");
  for (const line of file.diff.split("\n")) pre.append(el("span", {class: line.startsWith("@@") ? "hunk" : line.startsWith("+") && !line.startsWith("+++") ? "add" : line.startsWith("-") && !line.startsWith("---") ? "del" : "", text: line || " "}));
  return el("details", {class: "mg-diff", open: ""}, el("summary", {text: `${file.shown || file.path} · ${file.changes} ${file.changes === 1 ? "change" : "changes"}`}), pre);
}
async function previewMigrate() {
  const box = $("mg-diffs"); box.textContent = "";
  if (!mgSelected.size) { box.append(el("div", {class: "hint", text: "Select at least one fix."})); return; }
  try {
    const data = await api("/api/migrate/preview", {method: "POST", body: JSON.stringify({profile: prof(), fixes: selectedFixes()})});
    for (const file of data.files) box.append(diffBlock(file));
    $("mg-apply").disabled = false; $("mg-apply").textContent = `Apply to ${data.files.length} ${data.files.length === 1 ? "file" : "files"}`;
  } catch (error) { box.append(el("div", {class: "notice", text: "✖ " + error.message})); }
}
async function applyMigrate() {
  try {
    const result = await api("/api/migrate/apply", {method: "POST", body: JSON.stringify({profile: prof(), fixes: selectedFixes()})});
    toast("Fixes applied", `${result.written.length} files changed · the originals are kept: Undo restores them`, "success");
    await loadMigrate($("mg-to").value);
  } catch (error) { toast("Not applied", error.message, "error"); }
}
async function loadBackups() {
  const pick = $("mg-backups"); pick.textContent = "";
  try {
    const rows = (await api(`/api/migrate/backups?profile=${prof()}`)).backups;
    for (const row of rows) pick.append(el("option", {value: row.id, text: `${row.id.replace(/(\d{4})(\d\d)(\d\d)-(\d\d)(\d\d)\d\d/, "$1-$2-$3 $4:$5")} · ${row.files.length} files`}));
    pick.hidden = $("mg-restore").hidden = !rows.length;
  } catch (error) { pick.hidden = $("mg-restore").hidden = true; }
}
async function restoreMigrate() {
  const id = $("mg-backups").value; if (!id || !confirm("Restore the files as they were before these fixes?")) return;
  try { const r = await api("/api/migrate/restore", {method: "POST", body: JSON.stringify({profile: prof(), id})}); toast("Restored", `${r.restored.length} files`, "success"); await loadMigrate($("mg-to").value); }
  catch (error) { toast("Not restored", error.message, "error"); }
}
async function loadMigrateKas() {
  const box = $("mg-kas"); box.textContent = "";
  let data;
  try { data = await api(`/api/migrate/kas?profile=${prof()}&to=${encodeURIComponent($("mg-to").value)}`); } catch (error) { box.append(el("div", {class: "notice", text: error.message})); return; }
  mgKas = data;
  if (!data.available) { box.append(el("div", {class: "mg-note", text: data.text})); renderMigrateVerify(null); return; }
  box.append(el("ul", {}, ...data.notes.map((n) => el("li", {text: n}))),
    diffBlock({path: data.name, diff: data.diff, changes: data.notes.length}),
    el("div", {class: "mg-note", text: `Creates ${data.name} (the current file is not touched) and the profile ${data.profile.name}` +
      (data.profile.environment.KAS_WORK_DIR ? ` with its own work directory ${data.profile.environment.KAS_WORK_DIR}` : "") + ". Downloads and sstate are shared only if you set DL_DIR and SSTATE_DIR outside the build."}),
    el("div", {class: "mg-actions", style: "margin-top:10px"}, el("button", {class: "btn primary", text: `✦ Write ${data.name} and the profile`, onclick: writeMigrateKas})));
  renderMigrateVerify(null);
}
async function writeMigrateKas() {
  try {
    const data = await api("/api/migrate/kas", {method: "POST", body: JSON.stringify({profile: prof(), to: $("mg-to").value, write: true})});
    toast("Ready to try", `${data.name} and the profile ${data.profile.name}`, "success");
    $("mg-step-3").classList.add("done");
    $("mg-kas").textContent = ""; $("mg-kas").append(el("div", {class: "finding ok"}, el("span", {class: "ic", text: "✔"}), el("span", {text: `Wrote ${data.name}; profile ${data.profile.name} is ready.`})));
    await refresh(); renderMigrateVerify(data.profile.name);
  } catch (error) { toast("Not written", error.message, "error"); }
}
function renderMigrateVerify(name) {
  const box = $("mg-verify"); box.textContent = "";
  if (!name) { box.append(el("span", {class: "hint", text: "After step 3: switch to the new profile, parse, build, and scan again."})); return; }
  const use = () => { $("profile").value = name; $("profile").dispatchEvent(new Event("change")); };
  box.append(el("button", {class: "btn primary", text: `Switch to ${name}`, onclick: use}),
    el("button", {class: "btn", text: "Parse metadata (bitbake -p)", onclick: () => { use(); setTimeout(() => queue("parse", {}), 400); }}),
    el("button", {class: "btn", text: "Build the image", onclick: () => { use(); setTimeout(() => queue("build", {target: $("target").value}), 400); }}),
    el("button", {class: "btn", text: "Best practices", onclick: () => { use(); setView("practices"); }}));
}
async function exportMigrate() {
  const fmt = $("mg-format").value;
  const response = await fetch(`/api/migrate/export?profile=${prof()}&to=${encodeURIComponent($("mg-to").value)}&format=${fmt}`, {headers: {"X-Bitloom-Token": token}});
  if (!response.ok) { toast("Export", (await response.json().catch(() => ({}))).error || response.statusText, "error"); return; }
  const link = el("a", {href: URL.createObjectURL(await response.blob()), download: `migration-${$("mg-to").value}.${fmt === "text" ? "txt" : fmt}`}); link.click();
}

/* BitBake language assistant in the editor: completion (Ctrl+Space or as you type), the meaning of the word
   under the caret, and the problems a parse would report, from the project's own layers. */
let langItems = [], langIndex = 0, langFrom = 0, langTimer = null, lintTimer = null, docTimer = null, langProblems = [], langQuiet = false;
const caretLine = () => { const area = $("ide-text"), upto = area.value.slice(0, area.selectionStart); const row = upto.split("\n").length - 1; return {row, before: upto.slice(upto.lastIndexOf("\n") + 1)}; };
function langClose() { $("lang-pop").hidden = true; langItems = []; }
async function langSuggest(force = false) {
  const area = $("ide-text");
  if (area.readOnly || area.selectionStart !== area.selectionEnd) return langClose();
  const {row, before} = caretLine();
  const trigger = force || /(\$\{\w*|:\w*|\[\w*|^\s*(inherit|inherit_defer|require|include)\s+\S*|"[^"]*\w{2,}|^\s*[A-Za-z_]\w{1,})$/.test(before);
  if (!trigger) return langClose();
  let data;
  try { data = await api(`/api/lang/complete?profile=${prof()}&before=${encodeURIComponent(before)}`); } catch (error) { return langClose(); }
  if (caretLine().before !== before) return;                        // typed meanwhile: a newer request follows
  langItems = data.items.filter((i) => force || i.label !== data.word); langIndex = 0; langFrom = before.length - (before.length - data.from);
  if (!langItems.length) return langClose();
  const pop = $("lang-pop"); pop.textContent = "";
  const opts = el("div", {class: "opts"}), detail = el("div", {class: "detail"});
  langItems.forEach((item, i) => {
    // The typed letters in bold: the rest of the name is what the suggestion adds.
    const at = data.word ? item.label.toLowerCase().indexOf(data.word.toLowerCase()) : -1;
    const label = el("span", {class: "l"});
    if (at >= 0) label.append(item.label.slice(0, at), el("mark", {text: item.label.slice(at, at + data.word.length)}), item.label.slice(at + data.word.length));
    else label.textContent = item.label;
    const [glyph, colour] = LANG_KINDS[item.kind] || ["·", "var(--muted)"];
    opts.append(el("div", {class: "opt", role: "option", id: "lang-opt-" + i, "aria-selected": String(i === 0), title: item.doc || item.label,
      onmousedown: (e) => { e.preventDefault(); langIndex = i; langAccept(); }, onmousemove: () => { if (langIndex !== i) langMove(i - langIndex); }},
      el("span", {class: "ico", style: `--k:${colour}`, text: glyph, "aria-hidden": "true"}), label, el("span", {class: "k", text: item.kind})));
  });
  pop.append(opts, detail, el("div", {class: "foot"}, el("span", {}, el("kbd", {text: "↑↓"}), " choose"), el("span", {}, el("kbd", {text: "Enter"}), " insert"),
    el("span", {}, el("kbd", {text: "Esc"}), " close"), el("span", {class: "n", text: `${langItems.length} ${langItems.length === 1 ? "match" : "matches"}`})));
  langDetail();
  // Under the caret: monospace, so columns × character width.
  const style = getComputedStyle(area), probe = el("span", {text: "M".repeat(10), style: `font:${style.font};position:absolute;visibility:hidden`}); document.body.append(probe);
  const cw = probe.getBoundingClientRect().width / 10; probe.remove();
  const lh = parseFloat(style.lineHeight);
  pop.style.left = Math.max(4, Math.min(14 + data.from * cw - area.scrollLeft - 30, area.clientWidth - 384)) + "px";
  pop.hidden = false; area.setAttribute("aria-activedescendant", "lang-opt-0");
  // Below the line when it fits, otherwise above it.
  const below = 10 + (row + 1) * lh - area.scrollTop + 2, above = 10 + row * lh - area.scrollTop - pop.offsetHeight - 2;
  pop.style.top = (below + pop.offsetHeight > area.clientHeight && above > 0 ? above : below) + "px";
}
const LANG_KINDS = {variable: ["V", "var(--viz-1)"], keyword: ["K", "var(--viz-5)"], class: ["C", "var(--viz-3)"], file: ["F", "var(--viz-4)"],
  task: ["T", "var(--viz-2)"], recipe: ["R", "var(--accent)"], feature: ["★", "var(--viz-4)"], machine: ["M", "var(--viz-6)"], distro: ["D", "var(--viz-6)"],
  licence: ["§", "var(--muted)"], flag: ["[ ]", "var(--viz-2)"], override: [":", "var(--viz-5)"], operation: ["+", "var(--viz-5)"]};
function langDetail() {
  const item = langItems[langIndex], box = document.querySelector("#lang-pop .detail"); if (!box || !item) return;
  box.textContent = "";
  if (item.doc) box.append(el("b", {text: item.label}), el("span", {class: "muted", text: " · " + item.kind}), el("div", {text: item.doc}));
}
function langMove(step) {
  langIndex = (langIndex + step + langItems.length) % langItems.length;
  const rows = document.querySelectorAll("#lang-pop .opt");
  rows.forEach((n, i) => n.setAttribute("aria-selected", String(i === langIndex)));
  rows[langIndex].scrollIntoView({block: "nearest"}); $("ide-text").setAttribute("aria-activedescendant", "lang-opt-" + langIndex);
  langDetail();
}
function langAccept() {
  const item = langItems[langIndex], area = $("ide-text"); if (!item) return;
  const caret = area.selectionStart, lineStart = area.value.lastIndexOf("\n", caret - 1) + 1;
  const start = lineStart + langFrom;
  area.setRangeText(item.insert, start, caret, "end");
  langClose(); langQuiet = true; area.dispatchEvent(new Event("input"));
}
async function langExplain() {
  const area = $("ide-text"), text = area.value, at = area.selectionStart;
  const left = text.slice(0, at).match(/[A-Za-z0-9_\-]*$/)[0], right = text.slice(at).match(/^[A-Za-z0-9_\-]*/)[0], word = left + right;
  const box = $("lang-doc");
  if (word.length < 2) { box.textContent = ""; return; }
  try {
    const data = await api(`/api/lang/explain?profile=${prof()}&word=${encodeURIComponent(word)}`);
    box.textContent = "";
    if (data.doc) box.append(el("b", {text: data.word}), ` · ${data.kind} · ${data.doc}`);
    else if (data.suggest && data.suggest.length) box.append(el("b", {text: data.word}), ` · not known here: ${data.suggest.join(", ")}?`);
  } catch (error) { box.textContent = ""; }
}
async function langLint() {
  if (!lastPlan || !(ideCurrent in lastPlan.files) || !/\.(bb|bbappend|bbclass|inc|conf)$/.test(ideCurrent)) { langProblems = []; renderLint(); return; }
  try { langProblems = (await api("/api/lang/lint", {method: "POST", body: JSON.stringify({profile: prof(), text: $("ide-text").value, filename: ideCurrent})})).problems; }
  catch (error) { langProblems = []; }
  renderLint();
}
function renderLint() {
  const box = $("lang-lint"); box.textContent = "";
  const gutter = $("ide-gutter").children;
  for (const node of gutter) node.classList.remove("lint-error", "lint-warning", "lint-info");
  for (const p of langProblems) {
    const mark = gutter[p.line - 1]; if (mark) { mark.classList.add("lint-" + p.level); mark.title = p.message; }
    box.append(el("button", {class: p.level, type: "button", onclick: () => goLine(p.line)}, el("span", {class: "i", text: {error: "✖", warning: "▲", info: "●"}[p.level]}),
      el("span", {class: "ln", text: "line " + p.line}), el("span", {text: p.message}, ...(p.fix ? [el("small", {text: p.fix})] : []))));
  }
}
function goLine(line) {
  const area = $("ide-text"), lines = area.value.split("\n"), at = lines.slice(0, line - 1).join("\n").length + (line > 1 ? 1 : 0);
  area.focus(); area.setSelectionRange(at, at + lines[line - 1].length);
  area.scrollTop = Math.max(0, (line - 4) * parseFloat(getComputedStyle(area).lineHeight)); syncScroll();
}
function syncScroll() { const area = $("ide-text"); $("ide-hl").scrollTop = area.scrollTop; $("ide-hl").scrollLeft = area.scrollLeft; $("ide-gutter").scrollTop = area.scrollTop; }
// The form calls this when a field gets the focus: show the file it writes, with its lines highlighted.
function renderCode(follow) {
  if (follow && studioVar && lastPlan) {
    const word = new RegExp("(^|[^\\w@{-])" + studioVar.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&") + "(?![\\w-])");
    if (!(ideCurrent in lastPlan.files && tabText(ideCurrent).split("\n").some((l) => word.test(l)))) {
      const other = planNames().find((n) => tabText(n).split("\n").some((l) => word.test(l)));
      if (other) { ideCurrent = other; renderTabs(); renderEditor(); return; }
    }
  }
  paintCode();
}

async function previewStudio() {
  if (!studioActive) return;
  const steps = $("st-steps"), problems = $("ide-problems");
  for (const node of document.querySelectorAll("#st-form .fld.invalid")) { node.classList.remove("invalid"); node.querySelector(".err")?.remove(); }
  const issues = [];
  try {
    const plan = await api("/api/studio/preview", {method: "POST", body: JSON.stringify({profile: $("profile").value, kind: studioKind, values: studioValues, use: $("st-use").checked})});
    for (const name of Object.keys(planEdits)) if (!(name in plan.files)) delete planEdits[name];
    lastPlan = plan;
    const count = Object.keys(plan.files).length;
    $("st-create").disabled = false; $("st-create").textContent = `✦ Create ${count} ${count === 1 ? "file" : "files"}`;
    steps.className = "st-steps"; steps.textContent = "";
    steps.append(...plan.steps.map((text) => el("li", {text})));
    for (const note of plan.notes) issues.push(["warn", note]);
    if (Object.keys(planEdits).length) issues.push(["ok", `You edited ${Object.keys(planEdits).join(", ")} by hand: the form no longer changes ${Object.keys(planEdits).length === 1 ? "it" : "them"}.`]);
    if (!(ideCurrent in plan.files)) ideCurrent = plan.main;
  } catch (error) {
    lastPlan = null; $("st-create").disabled = true; $("st-create").textContent = "✦ Create files";
    const field = error.field && document.querySelector(`#st-form [data-field="${error.field}"]`) || document.querySelector('#st-form [data-field="name"]');
    if (field) { field.classList.add("invalid"); field.append(el("div", {class: "err", text: "✖ " + error.message})); }
    steps.className = "st-steps"; steps.textContent = ""; steps.append(el("li", {class: "cap", text: "Fix the problem first"}));
    issues.push(["err", error.message + (field ? ` (step ${stepOf(field.dataset.field) + 1})` : "")]);
  }
  problems.textContent = "";
  for (const [level, text] of issues) problems.append(el("div", {class: "problem " + level, text: (level === "err" ? "✖ " : level === "warn" ? "⚠ " : "ℹ ") + text}));
  renderTabs(); renderEditor(); renderWhere(); renderStepList();
  if (sgSteps[sgStep] === "review") renderReview();
}
async function createStudio() {
  if (!lastPlan || sgSteps[sgStep] !== "review") return;
  const plan = lastPlan, kind = studioKind;
  try {
    const result = await api("/api/studio/create", {method: "POST", body: JSON.stringify({profile: $("profile").value, kind, values: studioValues, use: $("st-use").checked, edits: planEdits})});
    metaRows = []; imageRows = null; layerFiles = {};   // Recipes, the image list and the layer view pick the new files up
    studioActive = false; lastPlan = null; planEdits = {};
    showDone(kind, plan, result);
  } catch (error) { toast("Studio", error.message, "error"); }
}
function showDone(kind, plan, result) {
  showScreen("done");
  const info = studioKinds.find((k) => k.id === kind) || {title: kind};
  $("sg-done-title").textContent = `${info.title} created`;
  $("sg-done-text").textContent = result.messages.join(" · ");
  const created = $("sg-created"); created.textContent = "";
  for (const path of result.written) created.append(el("span", {text: path}));
  const next = $("sg-next-actions"); next.textContent = "";
  const action = (title, text, run, primary = false) => next.append(el("button", {class: primary ? "primary-next" : "", onclick: run}, el("b", {text: title}), el("small", {text})));
  const name = plan.main.split("/").pop().replace(/(_[^_]*)?\.(bb|bbappend|conf)$/, "");
  if (result.target) {
    action(`Build ${result.target}`, "Queue the build now and follow it in Builds.", () => { $("target").value = result.target; $("target").dataset.touched = "1"; queue("build", {target: result.target}); }, true);
    action("Make it the build target", "Put it in the target field; b builds it later.", () => { $("target").value = result.target; $("target").dataset.touched = "1"; toast("Target set", result.target, "success"); });
  } else if (kind === "distro" || kind === "machine") {
    action(`Build ${$("target").value || "the target"}`, `The next build uses the new ${kind === "distro" ? "DISTRO" : "MACHINE"} (see the steps above).`, () => queue("build", {target: $("target").value}), true);
  } else if (kind === "append") {
    action(`Rebuild ${name}`, "Build the recipe again so the change applies.", () => queue("build", {target: name}), true);
  }
  if (kind === "layer" || plan.new_layer) {
    const layer = plan.layer;
    action("Add a distribution to it", "Your product's name, version and policies.", () => startForm("distro", {layer}), kind === "layer");
    action("Add an image to it", "What ends up on the device.", () => startForm("image", {layer}));
  }
  action("See it in Recipes", "Find the new files in the layer view.", () => { setView("recipes"); $("meta-search").value = name; renderLayers(); renderMeta(); });
  action("Create something else", "Back to the list of what Studio creates.", () => showScreen("start"));
  next.querySelector("button")?.focus();
}

/* Operations */
function fillOperations() {
  const filter = $("op-filter").value.toLowerCase(), select = $("op-select"), previous = select.value;
  select.textContent = "";
  const groups = {};
  for (const action of actions) {
    if (action.interactive || !`${action.group} ${action.title} ${action.id}`.toLowerCase().includes(filter)) continue;
    (groups[action.group] ||= el("optgroup", {label: action.group})).append(el("option", {value: action.id, text: action.title}));
  }
  for (const group of Object.values(groups)) select.append(group);
  if ([...select.options].some((o) => o.value === previous)) select.value = previous; else if (select.options.length) select.selectedIndex = 0;
  fillFields();
}
function fillFields() {
  const action = actions.find((a) => a.id === $("op-select").value), fields = $("op-fields");
  fields.textContent = "";
  for (const name of action ? action.inputs : []) {
    const input = el("input", {type: "text", id: "op-" + name, "data-field": name, placeholder: name});
    if (name === "target") input.value = $("target").value;
    input.addEventListener("input", preview);
    fields.append(el("label", {for: "op-" + name, text: name}), input);
  }
  preview();
}
function values() { const result = {}; for (const input of document.querySelectorAll("#op-fields input")) result[input.dataset.field] = input.value; return result; }
let previewTimer;
function preview() {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(async () => {
    const action = $("op-select").value;
    if (!action) { $("op-preview").textContent = "No matching operation"; return; }
    try { const data = await api("/api/preview", {method: "POST", body: JSON.stringify({profile: $("profile").value, action, values: values()})}); $("op-preview").textContent = data.command + (data.help ? "\n" + data.help : ""); $("op-submit").disabled = false; }
    catch (error) { $("op-preview").textContent = error.message; $("op-submit").disabled = true; }
  }, 120);
}
async function queue(action, vals) {
  try {
    const job = await api("/api/jobs", {method: "POST", body: JSON.stringify({profile: $("profile").value, action, values: vals})});
    // Known as queued now, so an end before the next poll (an instant failure) still raises its toast.
    lastStatus[job.id] = "queued";
    const subject = Object.values(vals || {}).map((v) => String(v).trim()).filter(Boolean).join(" · ");
    toast("Queued", (actions.find((a) => a.id === action) || {title: action}).title + (subject ? " · " + subject : ""), "info"); selected = null; await refresh(); select_(job.id); setView("builds");
  } catch (error) { toast("Cannot queue", error.message, "error"); }
}
function openQueue(filter = "") { $("op-filter").value = filter; fillOperations(); $("queue-dialog").showModal(); $("op-filter").focus(); }
async function control(kind) {
  const row = current(); if (!row) return;
  if (kind === "stop" && !confirm("Force stop " + row.title + "? Interrupted work directories may need cleaning.")) return;
  try {
    if (kind === "retry") { const job = await api(`/api/jobs/${row.id}/retry`, {method: "POST", body: "{}"}); lastStatus[job.id] = "queued"; toast("Retry queued", row.title, "info"); selected = null; await refresh(); select_(job.id); }
    else { await api(`/api/jobs/${row.id}/stop`, {method: "POST", body: JSON.stringify({mode: kind === "graceful" ? "graceful" : "force"})}); toast(kind === "graceful" ? "Graceful stop sent" : "Stop requested", row.title, "warning"); refresh(); }
  } catch (error) { toast("Stop/retry failed", error.message, "error"); }
}

/* Command palette */
let paletteItems = [], paletteIndex = 0;
function paletteEntries() {
  const entries = VIEWS.map((name, i) => ({label: "Go to " + document.querySelector(`nav button[data-view=${name}]`).lastChild.textContent.trim(), hint: String(i + 1), run: () => setView(name)}));
  entries.push({label: "Build target", hint: "b", run: () => queue("build", {target: $("target").value})});
  entries.push({label: "Which recipe installs… (a file on the device or a package)", hint: "4", run: () => { setView("image"); setTimeout(() => $("img-find").focus(), 100); }});
  entries.push({label: "Explore the built image", hint: "4", run: () => setView("image")});
  entries.push({label: "Best practices", hint: "7", run: () => setView("practices")});
  entries.push({label: "Migrate to a newer Yocto release", hint: "9", run: () => setView("migrate")});
  for (const [id, label] of THEME_LIST) entries.push({label: "Theme: " + label, hint: "theme", run: () => applyTheme(id)});
  entries.push({label: "Add a company rule (best practices)", hint: "7", run: () => { setView("practices"); openRuleDialog(); }});
  for (const profile of (state ? state.profiles : [])) {
    if (profile.name === $("profile").value) continue;
    entries.push({label: `Switch profile: ${profile.name}`, hint: profile.release || profile.mode || "", run: () => {
      $("profile").value = profile.name; $("profile").dispatchEvent(new Event("change")); toast("Switched profile", profile.name, "info"); }});
  }
  for (const action of actions.filter((a) => !a.interactive)) entries.push({label: `Queue: ${action.group} / ${action.title}`, hint: action.id, run: () => openQueue(action.title)});
  for (const row of (state ? state.history.slice(0, 30) : [])) entries.push({label: `Open build: ${row.title}`, hint: row.status, run: () => { setView("builds"); select_(row.id); }});
  return entries;
}
function renderPalette() {
  const needle = $("pal-input").value.toLowerCase().split(/\s+/).filter(Boolean);
  paletteItems = paletteEntries().filter((e) => needle.every((n) => e.label.toLowerCase().includes(n))).slice(0, 40);
  paletteIndex = Math.min(paletteIndex, Math.max(0, paletteItems.length - 1));
  const list = $("pal-list"); list.textContent = "";
  paletteItems.forEach((entry, i) => list.append(el("li", {class: i === paletteIndex ? "active" : "", onclick: () => runPalette(i)}, el("span", {text: entry.label}), el("small", {text: entry.hint}))));
}
function runPalette(i) { const entry = paletteItems[i]; $("palette").close(); if (entry) entry.run(); }
function openPalette() { $("pal-input").value = ""; paletteIndex = 0; renderPalette(); $("palette").showModal(); $("pal-input").focus(); }

function wire() {
  for (const button of document.querySelectorAll("nav button")) button.addEventListener("click", () => setView(button.dataset.view));
  for (const button of document.querySelectorAll("#tabs button")) button.addEventListener("click", () => setTab(button.dataset.tab));
  window.addEventListener("resize", moveInk);
  $("profile").addEventListener("change", async () => { $("target").dataset.touched = ""; await loadConsole(); renderState(); setView(view); });
  $("target").addEventListener("input", () => { $("target").dataset.touched = "1"; });
  $("target").addEventListener("keydown", (event) => {
    const open = !$("target-list").hidden;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) { openCombo(false); return; }
      if (comboItems.length) activate((comboActive + (event.key === "ArrowDown" ? 1 : -1) + comboItems.length) % comboItems.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      const choice = open && comboActive >= 0 ? comboItems[comboActive].querySelector(".name").textContent : "";
      if (choice && choice !== $("target").value.trim()) pickTarget(choice);
      else { closeCombo(); queue("build", {target: $("target").value}); }
    } else if (event.key === "Escape" && open) { event.stopPropagation(); closeCombo(); }
    else if (event.key === "Tab") closeCombo();
  });
  $("target").addEventListener("input", () => { if ($("target-list").hidden) openCombo(true); else renderCombo(true); });
  $("target").addEventListener("click", () => openCombo(false));
  $("target").addEventListener("blur", () => setTimeout(() => { if (document.activeElement !== $("target")) closeCombo(); }, 120));
  $("target-toggle").addEventListener("mousedown", (event) => { event.preventDefault(); if ($("target-list").hidden) { $("target").focus(); openCombo(false); } else closeCombo(); });
  $("build-btn").addEventListener("click", () => queue("build", {target: $("target").value}));
  $("queue-btn").addEventListener("click", () => openQueue());
  $("palette-btn").addEventListener("click", openPalette);
  $("keys-btn").addEventListener("click", () => $("keys-dialog").showModal());
  const bell = () => { $("notify-btn").style.opacity = localStorage.getItem("bitloom-notify") === "1" ? "1" : ".45"; };
  bell();
  $("notify-btn").addEventListener("click", async () => {
    if (!("Notification" in window)) { toast("Notifications", "This browser has no notification support.", "warning"); return; }
    if (localStorage.getItem("bitloom-notify") === "1") { localStorage.setItem("bitloom-notify", "0"); bell(); toast("Browser notifications off", "", "info"); return; }
    const permission = await Notification.requestPermission();
    localStorage.setItem("bitloom-notify", permission === "granted" ? "1" : "0"); bell();
    toast(permission === "granted" ? "Browser notifications on" : "Notifications blocked by the browser", "Shown when a build ends while this tab is in the background.", permission === "granted" ? "success" : "warning");
  });
  $("keys-close").addEventListener("click", () => $("keys-dialog").close());
  $("stop-btn").addEventListener("click", () => control("stop"));
  $("graceful-btn").addEventListener("click", () => control("graceful"));
  $("retry-btn").addEventListener("click", () => control("retry"));
  $("pr-recheck").addEventListener("click", () => loadPractices());
  $("pr-export").addEventListener("click", exportPractices);
  for (const b of document.querySelectorAll("#img-mode button")) b.addEventListener("click", () => setImgMode(b.dataset.mode));
  $("mg-to").addEventListener("change", () => loadMigrate($("mg-to").value)); $("mg-rescan").addEventListener("click", () => loadMigrate($("mg-to").value));
  $("mg-preview").addEventListener("click", previewMigrate); $("mg-apply").addEventListener("click", applyMigrate); $("mg-restore").addEventListener("click", restoreMigrate);
  $("mg-export").addEventListener("click", exportMigrate);
  $("theme-btn").addEventListener("click", (e) => { e.stopPropagation(); openThemes(); });
  document.addEventListener("click", (e) => { if (!$("theme-menu").hidden && !e.target.closest(".theme-pick")) { $("theme-menu").hidden = true; $("theme-btn").setAttribute("aria-expanded", "false"); } });
  $("theme-menu").addEventListener("keydown", (e) => {
    const items = [...$("theme-menu").querySelectorAll("button")], at = items.indexOf(document.activeElement);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); items[(at + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length].focus(); }
    if (e.key === "Escape") { e.stopPropagation(); $("theme-menu").hidden = true; $("theme-btn").focus(); }
  });
  $("pr-add").addEventListener("click", () => openRuleDialog());
  $("pr-form").addEventListener("submit", saveRule);
  $("pr-form").addEventListener("input", syncRuleForm); $("pr-form").addEventListener("change", syncRuleForm);
  for (const radio of document.querySelectorAll('#pr-form input[name="prf-type"]')) radio.addEventListener("change", () => {
    // A different kind of check: the example's texts no longer describe it.
    if (prTemplate && radio.value !== prTemplate.check.type) {
      for (const [key, field] of [["title", "prf-title"], ["why", "prf-why"], ["fix", "prf-fix"], ["id", "prf-id"]]) if ($(field).value === prTemplate[key]) $(field).value = "";
      for (const key of ["files", "pattern", "path", "name", "value"]) if ($("prf-" + key).value === (prTemplate.check[key] || "")) $("prf-" + key).value = "";
      prTemplate = null; prIdTouched = false;
    }
  });
  $("prf-title").addEventListener("input", () => { if (!prIdTouched && !prEditing) $("prf-id").value = slug($("prf-title").value); });
  $("prf-id").addEventListener("input", () => { prIdTouched = true; });
  $("prf-next").addEventListener("click", () => ruleGo(prStep + 1)); $("prf-back").addEventListener("click", () => ruleStep(prStep - 1));
  for (const button of document.querySelectorAll("#prw-steps button")) button.addEventListener("click", () => ruleGo(Number(button.dataset.step)));
  $("prf-try").addEventListener("click", tryRule);
  for (const q of document.querySelectorAll("#pr-form .q")) q.addEventListener("click", () => { const help = $(q.getAttribute("aria-controls")); help.hidden = !help.hidden; q.setAttribute("aria-expanded", String(!help.hidden)); });
  for (const box of document.querySelectorAll("#pr-form .ex")) for (const b of box.querySelectorAll("button")) b.addEventListener("click", () => { const input = $(box.dataset.into); input.value = b.textContent; input.focus(); syncRuleForm(); });
  $("pr-form").addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target.tagName === "INPUT" && e.target.type !== "radio") { e.preventDefault(); if (prStep < 3) ruleGo(prStep + 1); else $("pr-form").requestSubmit(); } });
  $("prf-delete").addEventListener("click", deleteRule);
  $("prf-title").addEventListener("input", () => { if (!prEditing) $("prf-id").value = $("prf-title").value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40); });
  $("img-pick").addEventListener("change", () => { imgSelected = null; chooseImage(imgList[Number($("img-pick").value)]); });
  $("img-find-btn").addEventListener("click", () => whoInstalls());
  $("img-find").addEventListener("keydown", (event) => { if (event.key === "Enter") whoInstalls(); });
  $("st-create").addEventListener("click", createStudio);
  $("st-use").addEventListener("change", previewStudio);
  $("sg-next").addEventListener("click", () => showStep(sgStep + 1));
  $("sg-back").addEventListener("click", () => showStep(sgStep - 1));
  $("sg-restart").addEventListener("click", closeForm);
  $("sg-edit").addEventListener("change", () => { renderEditor(); if ($("sg-edit").checked) $("ide-text").focus(); });
  $("ide-text").addEventListener("scroll", syncScroll);
  $("ide-text").addEventListener("keydown", (e) => {
    if (e.key === " " && e.ctrlKey) { e.preventDefault(); langSuggest(true); return; }
    if ($("lang-pop").hidden) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); langMove(e.key === "ArrowDown" ? 1 : -1); }
    else if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); langAccept(); }
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); langClose(); }
  });
  // After a suggestion is taken the menu stays closed until the next character typed.
  $("ide-text").addEventListener("input", () => { clearTimeout(langTimer); if (langQuiet) { langQuiet = false; return; } langTimer = setTimeout(() => langSuggest(false), 120); });
  for (const ev of ["click", "keyup"]) $("ide-text").addEventListener(ev, () => { clearTimeout(docTimer); docTimer = setTimeout(langExplain, 200); });
  $("ide-text").addEventListener("blur", () => setTimeout(langClose, 150));
  $("ide-text").addEventListener("input", () => { if (!lastPlan || !(ideCurrent in lastPlan.files)) return; planEdits[ideCurrent] = $("ide-text").value; paintCode(); renderTabs(); previewStudioSoon(); });
  $("ide-text").addEventListener("keydown", (event) => { if (event.key === "Tab" && !event.shiftKey && !$("ide-text").readOnly) { event.preventDefault(); document.execCommand("insertText", false, "    "); } });
  $("st-form").addEventListener("keydown", (event) => {
    // Enter moves on, as in any wizard; chips and selects keep their own Enter.
    if (event.key === "Enter" && event.target.tagName === "INPUT" && event.target.type === "text") { event.preventDefault(); showStep(sgStep + 1); }
  });
  document.addEventListener("keydown", (event) => {
    if (view !== "studio") return;
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); if (sgSteps[sgStep] === "review") createStudio(); else showStep(sgSteps.length - 1); }
    else if (event.key === "Escape" && !$("sg-flow").hidden && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName) && !document.querySelector("dialog[open]")) closeForm();
    else if (event.key === "Escape" && !$("sg-done").hidden) showScreen("start");
  });
  for (const id of ["vu-source", "vu-status"]) $(id).addEventListener("change", loadVulns);
  for (const id of ["vu-min", "vu-q"]) $(id).addEventListener("input", () => { clearTimeout(vulnTimer); vulnTimer = setTimeout(loadVulns, 200); });
  $("vu-csv").addEventListener("click", exportVulns);
  $("vu-grype").addEventListener("click", scanGrype);
  $("setup-scan").addEventListener("click", scanSetup);
  $("pj-tool").addEventListener("change", syncProjectTool); $("pj-release").addEventListener("change", syncProjectTool);
  $("pj-show-new").addEventListener("click", () => { $("pj-new").hidden = !$("pj-new").hidden; $("pj-clone").hidden = true; previewProject(); });
  $("pj-show-clone").addEventListener("click", () => { $("pj-clone").hidden = !$("pj-clone").hidden; $("pj-new").hidden = true; });
  for (const id of ["pj-name", "pj-dir", "pj-release", "pj-machine", "pj-distro", "pj-target", "pj-runtime", "pj-layer", "pj-owner"]) $(id).addEventListener("input", previewProject);
  $("pj-name").addEventListener("input", () => { const dir = $("pj-dir").value; $("pj-dir").value = dir.slice(0, dir.lastIndexOf("/") + 1) + $("pj-name").value; });
  $("pj-url").addEventListener("input", () => { const name = $("pj-url").value.replace(/\/$/, "").split(/[\/:]/).pop().replace(/\.git$/, ""); if (projectInfo && name) $("pj-dest").value = projectInfo.home + "/yocto/" + name; });
  $("pj-create").addEventListener("click", createProject);
  $("nt-save").addEventListener("click", saveNotifications);
  $("work-btn").addEventListener("click", async () => {
    const box = $("work-usage"); box.hidden = false; box.textContent = "Measuring tmp/work (up to 30 s)…";
    try { box.textContent = (await api(`/api/workusage?profile=${prof()}`)).text; } catch (error) { box.textContent = error.message; }
  });
  $("pj-clone-go").addEventListener("click", cloneProject);
  $("setup-dir").addEventListener("keydown", (event) => { if (event.key === "Enter") scanSetup(); });
  for (const id of ["sp-mode", "sp-name", "sp-kas_file", "sp-init_script", "sp-build_dir", "sp-launcher", "sp-environment", "sp-machine", "sp-distro", "sp-targets"]) $(id).addEventListener("input", checkSetup);
  $("sp-save").addEventListener("click", saveSetup);
  $("log-search").addEventListener("input", () => { clearTimeout(typingTimer); typingTimer = setTimeout(loadTab, 200); });
  $("errors-only").addEventListener("change", loadTab);
  $("log").addEventListener("scroll", () => { const log = $("log"); $("jump").classList.toggle("show", log.scrollHeight - log.scrollTop - log.clientHeight > 80); });
  $("jump").addEventListener("click", () => { const log = $("log"); log.scrollTo({top: log.scrollHeight, behavior: "smooth"}); $("follow").checked = true; });
  $("meta-search").addEventListener("input", () => { clearTimeout(metaTimer); metaTimer = setTimeout(() => { renderLayers(); renderMeta(); }, 150); });
  $("meta-expand").addEventListener("click", () => { const all = [...document.querySelectorAll("#meta-groups details.folder")], open = !all.every((d) => d.open); all.forEach((d) => { d.open = open; }); $("meta-expand").textContent = open ? "Collapse all" : "Expand all"; });
  $("task-search").addEventListener("input", () => { clearTimeout(metaTimer); metaTimer = setTimeout(loadTasks, 200); });
  for (const id of ["task-log-search", "task-errors"]) $(id).addEventListener(id === "task-errors" ? "change" : "input", () => openTaskRow && openTask(openTaskRow, document.querySelector("#task-rows tr.selected")));
  $("op-filter").addEventListener("input", fillOperations);
  $("op-filter").addEventListener("keydown", (event) => {
    const select = $("op-select");
    if (event.key === "Escape") { event.preventDefault(); $("queue-dialog").close(); return; }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      select.selectedIndex = Math.max(0, Math.min(select.options.length - 1, select.selectedIndex + (event.key === "ArrowDown" ? 1 : -1)));
      fillFields();
    }
  });
  $("op-select").addEventListener("change", fillFields);
  $("queue-form").addEventListener("submit", (event) => {
    if (event.submitter && event.submitter.value === "cancel") return;
    event.preventDefault();
    if ($("op-submit").disabled || !$("op-select").value) return;
    $("queue-dialog").close(); queue($("op-select").value, values());
  });
  $("pal-input").addEventListener("input", () => { paletteIndex = 0; renderPalette(); });
  $("pal-input").addEventListener("keydown", (event) => {
    if (event.key === "Escape") { event.preventDefault(); $("palette").close(); }
    else if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); paletteIndex = Math.max(0, Math.min(paletteItems.length - 1, paletteIndex + (event.key === "ArrowDown" ? 1 : -1))); renderPalette(); }
    else if (event.key === "Enter") { event.preventDefault(); runPalette(paletteIndex); }
  });
  const body = $("keys-rows");
  for (const [key, text] of KEYS) body.append(el("tr", {}, el("td", {}, el("kbd", {text: key})), el("td", {text})));
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); openPalette(); return; }
    const typing = /INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName);
    if (event.key === "Escape" && typing && !document.querySelector("dialog[open]")) { document.activeElement.blur(); return; }
    if (typing || document.querySelector("dialog[open]") || event.ctrlKey || event.metaKey || event.altKey) return;
    const tabs = {o: "output", u: "summary", w: "warnings", m: "timings", d: "compare"};
    const handled = () => event.preventDefault();
    if (/^[1-9]$/.test(event.key)) { setView(VIEWS[Number(event.key) - 1]); handled(); }
    else if (event.key === "/") { const input = document.querySelector(`#view-${view} input[type=search]`); if (input) { input.focus(); handled(); } }
    else if (event.key === "?") { $("keys-dialog").showModal(); handled(); }
    else if (event.key === "b") { queue("build", {target: $("target").value}); handled(); }
    else if (event.key === "q") { openQueue(); handled(); }
    else if (event.key === "t") { $("target").focus(); $("target").select(); openCombo(false); handled(); }
    else if (view === "builds") {
      const rows = state ? [...state.history.map((row) => row.id), ...consoleRows.map((row) => "console:" + row.path)] : [], index = rows.indexOf(selected);
      if ((event.key === "j" || event.key === "ArrowDown") && index < rows.length - 1) { select_(rows[index + 1]); handled(); }
      else if ((event.key === "k" || event.key === "ArrowUp") && index > 0) { select_(rows[index - 1]); handled(); }
      else if (event.key === "s") { control("stop"); handled(); }
      else if (event.key === "g") { control("graceful"); handled(); }
      else if (event.key === "r") { control("retry"); handled(); }
      else if (event.key === "e") { $("errors-only").checked = !$("errors-only").checked; loadTab(); handled(); }
      else if (tabs[event.key]) { setTab(tabs[event.key]); handled(); }
      const node = document.querySelector("#history .row.selected"); if (node) node.scrollIntoView({block: "nearest", behavior: "smooth"});
    }
  });
}

(async () => {
  wire(); setView("builds");
  if (!token) { toast("Session token missing", "Open the URL printed by bitloom --web: it carries the session token.", "error"); return; }
  try { actions = await api("/api/actions"); } catch (error) { toast("Cannot reach Bitloom", error.message, "error"); }
  await refresh(); await loadConsole(); renderState();
  if (state && state.first_run) {
    // First start in a project: propose profiles for this folder, as the TUI does.
    $("setup-dir").value = state.cwd; setView("health"); await scanSetup();
    $("setup-dir").scrollIntoView({behavior: "smooth", block: "center"});
    toast("Welcome to Bitloom", "Pick how this project builds: the proposals come from " + state.cwd + ". Save makes it your first profile.", "info");
    return void setInterval(refresh, 1500);
  }
  toast("Connected", state ? `${state.profiles.length} profiles · ${state.history.length} operations in history` : "", "success");
  setInterval(refresh, 1500);
})();
</script>
</body>
</html>
"""


# Named palettes for the dashboard, as the TUI has them (F7). Chart colours (--viz-*) are the validated dark or light
# set for the theme's surface; status colours keep their meaning in every theme.
WEB_THEMES = {
    # id: (label, dark, bg, bg2, surface, raised, line, line2, fg, muted, accent, accent2, ok, warn, err, info, code)
    "ubuntu": ("Ubuntu", True, "#300a24", "#2a0820", "#3a1230", "#45183a", "#552247", "#6a2d5a", "#eeeeec", "#c4a9bd", "#e95420", "#f08a5d", "#8ae234", "#fce94f", "#ff6b6b", "#729fcf", "#26071d"),
    "monokai": ("Monokai", True, "#272822", "#23241f", "#2f3029", "#3a3b33", "#44453d", "#57584e", "#f8f8f2", "#a6a28c", "#a6e22e", "#66d9ef", "#a6e22e", "#e6db74", "#f92672", "#66d9ef", "#1e1f1a"),
    "darcula": ("Darcula", True, "#2b2b2b", "#262626", "#313335", "#3c3f41", "#45494a", "#555a5c", "#bbc5cf", "#8c959e", "#cc7832", "#6897bb", "#8fb573", "#d6cf5a", "#ff6b68", "#6897bb", "#232323"),
    "nord": ("Nord", True, "#2e3440", "#2b303b", "#3b4252", "#434c5e", "#4c566a", "#5a657b", "#eceff4", "#a8b1c2", "#88c0d0", "#81a1c1", "#a3be8c", "#ebcb8b", "#e48b93", "#81a1c1", "#2a2f3a"),
    "dracula": ("Dracula", True, "#21222c", "#232530", "#282a36", "#343746", "#3a3d4d", "#4a4e62", "#f8f8f2", "#a4a9c7", "#bd93f9", "#8be9fd", "#50fa7b", "#f1fa8c", "#ff6e6e", "#8be9fd", "#1e1f29"),
    "tokyo-night": ("Tokyo Night", True, "#16161e", "#1a1b26", "#1f2335", "#24283b", "#2f3549", "#3b4261", "#c0caf5", "#8a93bd", "#7aa2f7", "#bb9af7", "#9ece6a", "#e0af68", "#f7768e", "#7dcfff", "#13131a"),
    "catppuccin-mocha": ("Catppuccin Mocha", True, "#11111b", "#181825", "#1e1e2e", "#313244", "#313244", "#45475a", "#cdd6f4", "#a6adc8", "#cba6f7", "#89b4fa", "#a6e3a1", "#f9e2af", "#f38ba8", "#89b4fa", "#11111b"),
    "gruvbox": ("Gruvbox", True, "#1d2021", "#232526", "#282828", "#32302f", "#3c3836", "#504945", "#ebdbb2", "#a89984", "#8ec07c", "#83a598", "#b8bb26", "#fabd2f", "#fb4934", "#83a598", "#1d2021"),
    "solarized-dark": ("Solarized Dark", True, "#002029", "#00252f", "#002b36", "#073642", "#0b3a46", "#1f4b57", "#a7b4b4", "#7a9095", "#2aa198", "#268bd2", "#859900", "#b58900", "#e2504d", "#4aa0e0", "#001f27"),
    "high-contrast": ("High contrast", True, "#000000", "#000000", "#0a0a0a", "#161616", "#5a5a5a", "#8a8a8a", "#ffffff", "#d0d0d0", "#00ffff", "#ffff00", "#00ff7f", "#ffd700", "#ff6b6b", "#80c8ff", "#000000"),
    "catppuccin-latte": ("Catppuccin Latte", False, "#eff1f5", "#e6e9ef", "#f7f8fb", "#ffffff", "#ccd0da", "#bcc0cc", "#4c4f69", "#5c5f77", "#8839ef", "#1e66f5", "#2f7d1f", "#a35a00", "#c4113a", "#1e5fd6", "#e6e9ef"),
    "solarized-light": ("Solarized Light", False, "#eee8d5", "#e9e2cb", "#fdf6e3", "#fffbf0", "#ddd6c1", "#cfc8b2", "#3a4f57", "#586e75", "#1f7f78", "#1d6fae", "#5f7a00", "#8a6500", "#c3281f", "#1d6fae", "#f5eedb"),
}
_VIZ = {True: "--viz-1: #3987e5; --viz-2: #d95926; --viz-3: #199e70; --viz-4: #c98500; --viz-5: #d55181; --viz-6: #008300; --viz-other: #5c6b74;",
        False: "--viz-1: #2a78d6; --viz-2: #eb6834; --viz-3: #1baf7a; --viz-4: #eda100; --viz-5: #e87ba4; --viz-6: #008300; --viz-other: #a3a9ad;"}


def _theme_css() -> str:
    blocks = [":root[data-theme=\"dark\"] { color-scheme: dark; }"]
    for ident, (label, dark, bg, bg2, surface, raised, line, line2, fg, muted, accent, accent2, ok, warn, err, info, code) in WEB_THEMES.items():
        r, g, b = (int(accent[i:i + 2], 16) for i in (1, 3, 5))
        blocks.append(f":root[data-theme=\"{ident}\"] {{ color-scheme: {'dark' if dark else 'light'}; --bg: {bg}; --bg2: {bg2}; --surface: {surface}; --raised: {raised}; "
                      f"--line: {line}; --line2: {line2}; --fg: {fg}; --muted: {muted}; --accent: {accent}; --accent2: {accent2}; --ink: {'#0b0d12' if dark else '#ffffff'}; "
                      f"--ok: {ok}; --warn: {warn}; --err: {err}; --info: {info}; --code: {code}; --glow: rgba({r}, {g}, {b}, {'.16' if dark else '.10'}); "
                      f"--shadow: {'0 10px 30px rgba(0, 0, 0, .40)' if dark else '0 10px 30px rgba(60, 50, 20, .10)'}; {_VIZ[dark]} }}")
    return "\n".join(blocks)


def _theme_js() -> str:
    import json
    data = {k: {"label": v[0], "surface": v[4], "accent": v[10], "fg": v[8]} for k, v in WEB_THEMES.items()}
    # Applied before the first paint, so a chosen theme never flashes the default one.
    return ("<script>window.BITLOOM_THEMES = " + json.dumps(data) + ";try{const t=localStorage.getItem(\"bitloom-theme\");"
            "if(t)document.documentElement.setAttribute(\"data-theme\",t);}catch(e){}</script>")


PAGE = PAGE.replace("/*THEMES*/", _theme_css(), 1).replace("</head>", _theme_js() + "\n</head>", 1)
