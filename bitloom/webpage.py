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
  color-scheme: dark;
}
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    color-scheme: light; --code: #f3f1ea;
    --bg: #f4f2ec; --bg2: #efece4; --surface: #fbfaf6; --raised: #ffffff; --line: #e1dccf; --line2: #d3ccbb; --fg: #23292f; --muted: #66707a;
    --accent: #17786d; --accent2: #345b91; --ink: #ffffff; --ok: #1f7a4d; --warn: #8a5a00; --err: #b0302c; --info: #2f5f9e;
    --glow: rgba(23, 120, 109, .12); --shadow: 0 10px 30px rgba(60, 50, 20, .10);
  }
}
:root[data-theme="light"] {
  color-scheme: light; --code: #f3f1ea;
  --bg: #f4f2ec; --bg2: #efece4; --surface: #fbfaf6; --raised: #ffffff; --line: #e1dccf; --line2: #d3ccbb; --fg: #23292f; --muted: #66707a;
  --accent: #17786d; --accent2: #345b91; --ink: #ffffff; --ok: #1f7a4d; --warn: #8a5a00; --err: #b0302c; --info: #2f5f9e;
  --glow: rgba(23, 120, 109, .12); --shadow: 0 10px 30px rgba(60, 50, 20, .10);
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; color: var(--fg); font: 14px/1.5 var(--sans); }
body { background: radial-gradient(1200px 600px at 85% -10%, var(--glow), transparent 60%), radial-gradient(900px 500px at -10% 110%, var(--glow), transparent 60%), var(--bg); background-attachment: fixed; }
button, input, select { font: inherit; color: inherit; }
kbd { font: 11px var(--mono); border: 1px solid var(--line2); border-bottom-width: 2px; border-radius: 5px; padding: 0 5px; color: var(--muted); background: var(--raised); }
.app { display: grid; grid-template-columns: 216px 1fr; grid-template-rows: auto 1fr; height: 100vh; }

/* Header */
header { grid-column: 1 / -1; position: sticky; top: 0; z-index: 20; display: flex; align-items: center; gap: 12px; padding: 10px 18px;
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
main { overflow: auto; padding: 18px 22px 40px; display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.view { display: flex; flex-direction: column; gap: 16px; animation: enter .35s var(--ease); }
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
.progress { position: relative; height: 8px; background: var(--line); overflow: hidden; }
.progress > i { position: absolute; inset: 0 auto 0 0; width: 0; background: linear-gradient(90deg, var(--accent), var(--accent2)); transition: width .7s var(--ease); }
.progress.running > i { background-image: linear-gradient(45deg, rgba(255,255,255,.18) 25%, transparent 25%, transparent 50%, rgba(255,255,255,.18) 50%, rgba(255,255,255,.18) 75%, transparent 75%), linear-gradient(90deg, var(--accent), var(--accent2)); background-size: 22px 22px, 100% 100%; animation: stripes .8s linear infinite; }
.progress.running > i::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, rgba(255,255,255,.45), transparent); transform: translateX(-100%); animation: shimmer 1.8s infinite; }
.progress.indeterminate > i { width: 35% !important; animation: slide 1.4s var(--ease) infinite; }
.progress.success > i { background: linear-gradient(90deg, var(--ok), var(--accent)); }
.progress.failed > i { background: linear-gradient(90deg, var(--err), #f6b073); }
@keyframes stripes { to { background-position: 22px 0, 0 0; } }
@keyframes shimmer { to { transform: translateX(100%); } }
@keyframes slide { from { left: -35%; } to { left: 100%; } }
.progress-label { display: flex; justify-content: space-between; padding: 6px 16px 0; color: var(--muted); font: 12px var(--mono); }

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

/* Studio */
.kinds { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
.kind { all: unset; cursor: pointer; padding: 14px; border-radius: 12px; border: 1px solid var(--line); background: linear-gradient(180deg, var(--raised), var(--surface)); transition: transform .2s var(--ease), border-color .2s, box-shadow .2s; }
.kind:hover { transform: translateY(-2px); border-color: var(--line2); }
.kind.active { border-color: var(--accent); box-shadow: 0 0 0 3px var(--glow); }
.kind:focus-visible { outline: 2px solid var(--accent); }
.kind .ico { font-size: 20px; } .kind b { display: block; margin-top: 4px; } .kind small { color: var(--muted); display: block; margin-top: 4px; line-height: 1.35; }
.form { padding: 6px 16px 16px; display: flex; flex-direction: column; gap: 4px; overflow: auto; }
.form label.f { font-weight: 650; margin-top: 12px; }
.form .help { color: var(--muted); font-size: 12px; }
.form input[type=text], .form select { width: 100%; }
#nt-format { width: auto; flex: none; }
#meta-rows td:first-child { white-space: nowrap; }
.toggles { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.toggle { all: unset; cursor: pointer; padding: 3px 10px; border-radius: 999px; border: 1px solid var(--line2); font-size: 12.5px; color: var(--muted); transition: all .2s var(--ease); }
.toggle.on { background: linear-gradient(135deg, var(--accent), var(--accent2)); color: var(--ink); border-color: transparent; }
.toggle:focus-visible { outline: 2px solid var(--accent); }
.files details { border-bottom: 1px solid var(--line); }
.files summary { cursor: pointer; padding: 9px 16px; font: 12.5px var(--mono); color: var(--ok); }
.files pre { margin: 0; padding: 10px 16px; background: color-mix(in srgb, var(--bg) 85%, black); font: 12px/1.5 var(--mono); white-space: pre-wrap; }
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
  header { gap: 8px; padding: 8px 12px; } #target { flex: 1 1 160px; min-width: 150px; }
}
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
    <input type="text" id="target" placeholder="Build target / recipe" aria-label="Build target" size="20">
    <button class="btn primary" id="build-btn" title="Build target (b)"><kbd>b</kbd>Build</button>
    <button class="btn" id="queue-btn" title="Queue any operation (q)"><kbd>q</kbd>Operations</button>
    <button class="btn" id="palette-btn" title="Command palette (Ctrl+K)"><kbd>⌘K</kbd>Search</button>
    <span class="chip"><span class="dot" id="service-dot"></span><span id="service-label">connecting…</span></span>
    <button class="btn" id="notify-btn" title="Browser notifications when builds finish" aria-label="Browser notifications when builds finish"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg></button>
    <button class="btn" id="keys-btn" title="Keyboard shortcuts (?)">?</button>
  </header>
  <nav aria-label="Sections">
    <div class="group">BUILD</div>
    <button data-view="builds"><span class="num">1</span><span class="icon">◈</span>Builds</button>
    <button data-view="recipes"><span class="num">2</span><span class="icon">◇</span>Recipes</button>
    <button data-view="tasklogs"><span class="num">3</span><span class="icon">≋</span>Task logs</button>
    <div class="group">PRODUCT</div>
    <button data-view="compliance"><span class="num">4</span><span class="icon">⚖</span>SBOM &amp; CRA</button>
    <button data-view="studio"><span class="num">5</span><span class="icon">✦</span>Studio</button>
    <div class="group">WORKSPACE</div>
    <button data-view="health"><span class="num">6</span><span class="icon">⚙</span>Configuration</button>
    <div class="foot">Same service and history as the TUI.<br><kbd>?</kbd> keys · <kbd>Ctrl</kbd><kbd>K</kbd> search</div>
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
        <div class="progress" id="d-progress"><i></i></div>
        <div class="progress-label"><span id="d-progress-text"></span><span id="d-progress-pct"></span></div>
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

    <section id="view-recipes" class="view panel" hidden>
      <div class="tools"><input type="search" id="meta-search" placeholder="/ search recipes, layers, appends, classes, kas files"><span class="hint" id="meta-count"></span></div>
      <div class="list"><table><thead><tr><th>Name</th><th>Type</th><th>Location</th></tr></thead><tbody id="meta-rows"></tbody></table></div>
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
      <div class="kinds" id="kinds"></div>
      <div class="split">
        <div class="panel"><div class="head"><h2 id="st-title">Distribution</h2></div><div class="hint" style="padding:10px 16px 0" id="st-desc"></div><div class="form" id="st-form"></div>
          <div class="tools" style="border-top:1px solid var(--line); border-bottom:0"><label class="check" id="st-use-wrap"><span class="switch"><input type="checkbox" id="st-use" checked><span></span></span>use for this profile</label><span style="flex:1"></span><button class="btn primary" id="st-create">✦ Create files</button></div></div>
        <div class="panel"><div class="head"><h2>Files to create</h2><span class="meta" id="st-layer"></span></div><div class="notice" id="st-notes" hidden></div><div class="files list" id="st-files"></div></div>
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
              <div class="help">Both are LTS. Wrynose uses split repositories, SPDX 3 and sbom-cve-check.</div>
              <label class="f" for="pj-machine">MACHINE / DISTRO / image</label>
              <div style="display:flex;gap:8px"><select id="pj-machine"></select><input type="text" id="pj-distro" value="poky"><select id="pj-target"></select></div>
              <label class="f" for="pj-runtime">Runtime</label><select id="pj-runtime"><option value="kas-container">kas-container (recommended)</option><option value="kas">kas on the host</option></select>
              <label class="check" style="margin-top:12px"><span class="switch"><input type="checkbox" id="pj-layer" checked><span></span></span>create meta-&lt;name&gt; product layer</label>
              <label class="f" for="pj-owner">Copyright owner</label><input type="text" id="pj-owner" placeholder="Your company">
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
const VIEWS = ["builds", "recipes", "tasklogs", "compliance", "studio", "health"];
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
  if (!response.ok) throw new Error(data.error || response.statusText);
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
  for (const line of text.split("\n")) {
    if (!line && append) continue;
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

async function loadConsole() {
  try { consoleRows = (await api(`/api/console?profile=${prof()}`)).rows; } catch (error) { consoleRows = []; }
}
function consoleRow() { return selected && selected.startsWith("console:") ? consoleRows.find((row) => "console:" + row.path === selected) : null; }
function current() { return state && state.history.find((row) => row.id === selected); }

function setProgress(status, progress) {
  const bar = $("d-progress"), known = progress && progress[1];
  bar.className = "progress " + status + (status === "running" && !known ? " indeterminate" : "");
  // BitBake's "task N of M" counts tasks that need no rerun too: N reaches M when the last task *starts*.
  const lastRunning = status === "running" && known && progress[0] >= progress[1];
  // Only a successful job is complete: a failed or cancelled one stopped during its last started task.
  const fraction = status === "success" ? 1 : known ? Math.min(progress[0] / progress[1], 0.99) : 0;
  bar.firstElementChild.style.width = (100 * fraction).toFixed(1) + "%";
  $("d-progress-text").textContent = known ? (lastRunning ? `last task running · ${progress[0]} of ${progress[1]}` : `task ${progress[0]} of ${progress[1]}`)
    : status === "running" ? "waiting for BitBake task counts…" : "";
  $("d-progress-pct").textContent = known || status === "success" ? (100 * fraction).toFixed(1) + "%" : "";
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
  setProgress(row.status, row.progress);
  if (row.eta) $("d-progress-text").textContent += ` · ETA ~${row.eta.remaining} (${row.eta.basis})`;
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
  view = name;
  for (const section of VIEWS) { const node = $("view-" + section); const show = section === name; if (show && node.hidden) { node.hidden = false; node.style.animation = "none"; void node.offsetWidth; node.style.animation = ""; } else node.hidden = !show; }
  for (const button of document.querySelectorAll("nav button")) button.classList.toggle("active", button.dataset.view === name);
  if (name === "recipes") loadMeta(); if (name === "tasklogs") loadTasks(); if (name === "health") { loadHealth(); loadProjects(); loadNotifications(); if (!setupCandidates.length && !$("setup-dir").value) { const p = profile(); $("setup-dir").value = p ? p.root : ""; scanSetup(); } }
  if (name === "compliance") { loadCompliance(); loadVulns(); } if (name === "studio") loadStudio();
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
async function loadMeta() {
  const body = $("meta-rows"); if (!body.children.length) skeleton(body, 3);
  const data = await api(`/api/metadata?profile=${prof()}&q=${encodeURIComponent($("meta-search").value)}`);
  body.textContent = "";
  $("meta-count").textContent = `${data.total} entries` + (data.total > data.rows.length ? ` · first ${data.rows.length}` : "");
  data.rows.forEach((row, i) => { const tr = el("tr", {}, el("td", {text: row.name}), el("td", {}, el("span", {class: "badge muted", text: row.kind})), el("td", {class: "mono", text: row.detail || row.path})); tr.style.animationDelay = Math.min(i, 20) * 12 + "ms"; body.append(tr); });
  if (!data.rows.length) body.append(el("tr", {}, el("td", {colspan: "3", class: "empty", text: "No matching metadata"})));
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
    const folder = item.root.split("/").pop() || item.root, active = item.profile && item.profile === $("profile").value;
    const label = active ? "active" : item.profile ? (item.profile !== folder ? "profile " + item.profile : "switch") : "not set up";
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
}
function projectBody() {
  return {name: $("pj-name").value.trim(), dir: $("pj-dir").value.trim(), release: $("pj-release").value, machine: $("pj-machine").value, distro: $("pj-distro").value.trim(),
          target: $("pj-target").value, runtime: $("pj-runtime").value, layer: $("pj-layer").checked, owner: $("pj-owner").value.trim()};
}
let projectTimer;
function previewProject() {
  clearTimeout(projectTimer);
  projectTimer = setTimeout(async () => {
    const files = $("pj-files"); files.textContent = "";
    try {
      const plan = await api("/api/projects/preview", {method: "POST", body: JSON.stringify(projectBody())});
      $("pj-create").disabled = false;
      Object.entries(plan.files).forEach(([name, text]) => files.append(el("details", name === "kas.yml" ? {open: ""} : {}, el("summary", {text: "+ " + name}), el("pre", {text}))));
    } catch (error) { $("pj-create").disabled = true; files.append(el("div", {class: "notice", text: "✖ " + error.message})); }
  }, 150);
}
async function createProject() {
  try {
    const result = await api("/api/projects/create", {method: "POST", body: JSON.stringify(projectBody())});
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
    setupCandidates.forEach((candidate, i) => {
      const row = el("div", {class: "row" + (i === 0 ? " selected" : ""), tabindex: "0"}, el("span", {class: "glyph", text: {wrapper: "⇄", host: "⌂", kas: "◇", "kas-container": "▣"}[candidate.mode] || "·"}),
        el("span", {}, el("b", {text: candidate.title}), el("div", {class: "meta", text: candidate.evidence.join(" · ")}), ...candidate.hints.map((h) => el("div", {class: "hint", text: h}))), el("span"));
      row.addEventListener("click", () => { for (const node of list.children) node.classList.toggle("selected", node === row); fillSetup(candidate.profile); });
      list.append(row);
    });
    fillSetup(setupCandidates[0].profile);
  } catch (error) { list.textContent = ""; list.append(el("div", {class: "empty", text: error.message})); }
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
    const span = el("span", {class: "meta", text: (option.since || "any") + (option.until ? "…" + option.until : "+") + (option.verified ? "" : " · verify")});
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
async function scanGrype() {
  try { const job = await api("/api/vulnerabilities/scan", {method: "POST", body: JSON.stringify({profile: $("profile").value})}); toast("Grype scan queued", "Follow it in Builds; results appear here when it finishes.", "info"); pendingScan = job.id; }
  catch (error) { toast("Grype", error.message, "error"); }
}

/* Studio */
async function loadStudio() {
  const data = await api(`/api/studio/fields?profile=${prof()}&kind=${studioKind}`);
  const kinds = $("kinds"); kinds.textContent = "";
  for (const kind of data.kinds) {
    const card = el("button", {class: "kind" + (kind.id === studioKind ? " active" : "")}, el("span", {class: "ico", text: ICONS[kind.id] || "✦"}), el("b", {text: kind.title}), el("small", {text: kind.description}));
    card.addEventListener("click", () => { studioKind = kind.id; studioValues = {}; loadStudio(); });
    kinds.append(card);
    if (kind.id === studioKind) { $("st-title").textContent = kind.title; $("st-desc").textContent = kind.description; }
  }
  studioFields = data.fields;
  $("st-use-wrap").hidden = !(["distro", "machine"].includes(studioKind) && ["host", "container"].includes(data.mode));
  const form = $("st-form"); form.textContent = "";
  const sync = () => { for (const node of form.querySelectorAll("[data-for=new_layer]")) node.hidden = !(studioValues.layer || "").startsWith("new layer"); };
  for (const field of studioFields) {
    const value = studioValues[field.id] ?? field.default;
    studioValues[field.id] = value;
    const start = form.childElementCount;
    form.append(el("label", {class: "f", for: "sf-" + field.id, text: field.label + (field.required ? " *" : "")}));
    if (field.kind === "choice") {
      const select = el("select", {id: "sf-" + field.id});
      for (const choice of field.choices) select.append(el("option", {value: choice, text: choice}));
      select.value = value; select.addEventListener("change", () => { studioValues[field.id] = select.value; previewStudio(); });
      form.append(select);
    } else if (field.kind === "multi") {
      const chosen = new Set(value.split(" ").filter(Boolean)), box = el("div", {class: "toggles"});
      for (const choice of field.choices) {
        const chip = el("button", {class: "toggle" + (chosen.has(choice) ? " on" : ""), type: "button", text: choice});
        chip.addEventListener("click", () => { chosen.has(choice) ? chosen.delete(choice) : chosen.add(choice); chip.classList.toggle("on"); studioValues[field.id] = [...chosen].join(" "); previewStudio(); });
        box.append(chip);
      }
      form.append(box);
    } else if (field.kind === "bool") {
      const input = el("input", {type: "checkbox", id: "sf-" + field.id}); input.checked = value === "1";
      input.addEventListener("change", () => { studioValues[field.id] = input.checked ? "1" : ""; previewStudio(); });
      form.append(el("label", {class: "check"}, el("span", {class: "switch"}, input, el("span")), "enabled"));
    } else {
      const input = el("input", {type: "text", id: "sf-" + field.id}); input.value = value;
      input.addEventListener("input", () => { studioValues[field.id] = input.value; clearTimeout(typingTimer); typingTimer = setTimeout(previewStudio, 180); });
      form.append(input);
    }
    if (field.info) form.append(el("div", {class: "help", text: field.info}));
    if (field.id === "new_layer") [...form.children].slice(start).forEach((node) => { node.dataset.for = "new_layer"; });
  }
  form.addEventListener("change", sync); sync();
  previewStudio();
}
let lastPlan = null;
async function previewStudio() {
  const files = $("st-files"), notes = $("st-notes");
  try {
    const plan = await api("/api/studio/preview", {method: "POST", body: JSON.stringify({profile: $("profile").value, kind: studioKind, values: studioValues})});
    lastPlan = plan; $("st-create").disabled = false;
    $("st-layer").textContent = (plan.new_layer ? "new layer " : "into ") + plan.layer;
    files.textContent = "";
    Object.entries(plan.files).forEach(([name, text], i) => files.append(el("details", i === 0 || name.includes("/distro/") || name.includes("/machine/") || name.endsWith(".bb") ? {open: ""} : {}, el("summary", {text: "+ " + name}), el("pre", {text}))));
    notes.hidden = !plan.notes.length; notes.textContent = plan.notes.map((n) => "⚠ " + n).join("  ");
  } catch (error) {
    lastPlan = null; $("st-create").disabled = true; files.textContent = ""; notes.hidden = false; notes.textContent = "✖ " + error.message;
  }
}
async function createStudio() {
  if (!lastPlan) return;
  try {
    const result = await api("/api/studio/create", {method: "POST", body: JSON.stringify({profile: $("profile").value, kind: studioKind, values: studioValues, use: $("st-use").checked})});
    toast("Created " + result.written.length + " files", result.messages.join(" · "), "success", result.target ? {label: "Build " + result.target, run: () => { $("target").value = result.target; $("target").dataset.touched = "1"; queue("build", {target: result.target}); }} : null);
    previewStudio();
  } catch (error) { toast("Studio", error.message, "error"); }
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
  $("target").addEventListener("keydown", (event) => { if (event.key === "Enter") queue("build", {target: $("target").value}); });
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
  $("st-create").addEventListener("click", createStudio);
  for (const id of ["vu-source", "vu-status"]) $(id).addEventListener("change", loadVulns);
  for (const id of ["vu-min", "vu-q"]) $(id).addEventListener("input", () => { clearTimeout(vulnTimer); vulnTimer = setTimeout(loadVulns, 200); });
  $("vu-csv").addEventListener("click", exportVulns);
  $("vu-grype").addEventListener("click", scanGrype);
  $("setup-scan").addEventListener("click", scanSetup);
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
  $("meta-search").addEventListener("input", () => { clearTimeout(metaTimer); metaTimer = setTimeout(loadMeta, 200); });
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
    if (/^[1-6]$/.test(event.key)) { setView(VIEWS[Number(event.key) - 1]); handled(); }
    else if (event.key === "/") { const input = document.querySelector(`#view-${view} input[type=search]`); if (input) { input.focus(); handled(); } }
    else if (event.key === "?") { $("keys-dialog").showModal(); handled(); }
    else if (event.key === "b") { queue("build", {target: $("target").value}); handled(); }
    else if (event.key === "q") { openQueue(); handled(); }
    else if (event.key === "t") { $("target").focus(); $("target").select(); handled(); }
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
  toast("Connected", state ? `${state.profiles.length} profiles · ${state.history.length} operations in history` : "", "success");
  setInterval(refresh, 1500);
})();
</script>
</body>
</html>
"""
