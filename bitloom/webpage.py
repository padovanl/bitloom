"""Single-page web dashboard. Data is always inserted with textContent, never as HTML."""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bitloom dashboard</title>
<style>
:root {
  --bg: #0b1115; --surface: #111b22; --raised: #16232c; --line: #22343f; --fg: #bdcbd2; --muted: #7b8e98;
  --accent: #84c9c0; --accent-ink: #0b1115; --secondary: #81bdcf; --ok: #8fdbc3; --warn: #dfbe77; --err: #f08b87;
  --mono: "JetBrains Mono", "Fira Code", "DejaVu Sans Mono", ui-monospace, monospace;
  --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    --bg: #f5f3ed; --surface: #ebe7dd; --raised: #fffdf8; --line: #d6d0c2; --fg: #292f35; --muted: #66707a;
    --accent: #176f65; --accent-ink: #ffffff; --secondary: #345b91; --ok: #246441; --warn: #815300; --err: #a32121;
  }
}
:root[data-theme="light"] {
  --bg: #f5f3ed; --surface: #ebe7dd; --raised: #fffdf8; --line: #d6d0c2; --fg: #292f35; --muted: #66707a;
  --accent: #176f65; --accent-ink: #ffffff; --secondary: #345b91; --ok: #246441; --warn: #815300; --err: #a32121;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: var(--bg); color: var(--fg); font: 14px/1.45 var(--sans); }
button, input, select { font: inherit; color: inherit; }
kbd { font: 11px var(--mono); border: 1px solid var(--line); border-bottom-width: 2px; border-radius: 4px; padding: 0 4px; color: var(--muted); background: var(--surface); }
.app { display: grid; grid-template-columns: 200px 1fr; grid-template-rows: auto 1fr; height: 100vh; }
header { grid-column: 1 / -1; display: flex; align-items: center; gap: 10px; padding: 8px 16px; background: var(--surface); border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.brand { font: 600 15px var(--mono); background: var(--accent); color: var(--accent-ink); padding: 2px 10px; border-radius: 4px; letter-spacing: .02em; }
.context { color: var(--muted); font-family: var(--mono); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.grow { flex: 1; }
select, input[type=text], input[type=search] { background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 5px 8px; min-width: 0; }
input:focus, select:focus, button:focus-visible, .row:focus-visible, [tabindex]:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.btn { background: var(--raised); border: 1px solid var(--line); border-radius: 6px; padding: 5px 12px; cursor: pointer; white-space: nowrap; }
.btn:hover { border-color: var(--accent); }
.btn.primary { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); font-weight: 600; }
.btn.warn { color: var(--warn); }
.btn.danger { color: var(--err); }
.btn:disabled { opacity: .45; cursor: default; }
.btn kbd { margin-right: 4px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; background: var(--muted); margin-right: 6px; }
.dot.ok { background: var(--ok); } .dot.err { background: var(--err); }
nav { background: var(--surface); border-right: 1px solid var(--line); padding: 14px 0; display: flex; flex-direction: column; gap: 2px; }
nav .group { color: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: .08em; padding: 10px 18px 4px; }
nav button { all: unset; display: flex; gap: 10px; align-items: center; padding: 6px 16px; border-left: 3px solid transparent; cursor: pointer; color: var(--muted); }
nav button:hover { background: var(--raised); color: var(--fg); }
nav button.active { border-left-color: var(--accent); background: var(--raised); color: var(--fg); font-weight: 600; }
nav button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
nav .num { font: 12px var(--mono); color: var(--muted); width: 10px; }
nav .foot { margin-top: auto; padding: 12px 18px; color: var(--muted); font-size: 12px; }
main { overflow: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 10px 14px; min-width: 0; }
.card h3 { margin: 0 0 4px; font-size: 11px; letter-spacing: .08em; color: var(--muted); text-transform: uppercase; }
.card .value { font: 600 16px var(--mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card .sub { color: var(--muted); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.meter { height: 5px; background: var(--raised); border-radius: 3px; overflow: hidden; margin: 6px 0 2px; }
.meter > i { display: block; height: 100%; background: var(--secondary); }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; min-width: 0; display: flex; flex-direction: column; }
.panel > .head { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.panel > .head h2 { margin: 0; font-size: 13px; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.split { display: grid; grid-template-columns: minmax(260px, 360px) minmax(0, 1fr); gap: 14px; flex: 1; min-height: 420px; }
.list { overflow: auto; flex: 1; }
.row { display: grid; grid-template-columns: 22px 1fr auto; gap: 6px; padding: 8px 14px; border-bottom: 1px solid var(--line); cursor: pointer; align-items: center; }
.row:hover { background: var(--raised); }
.row.selected { background: var(--raised); box-shadow: inset 3px 0 var(--accent); }
.row .title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.row .meta { color: var(--muted); font: 12px var(--mono); }
.group-label { color: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: .08em; padding: 12px 14px 6px; border-bottom: 1px solid var(--line); }
.glyph { font-family: var(--mono); text-align: center; }
.s-success { color: var(--ok); } .s-failed { color: var(--err); } .s-running { color: var(--accent); }
.s-queued, .s-cancelling, .s-interrupted { color: var(--warn); } .s-cancelled { color: var(--muted); }
.detail-title { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.progress { height: 6px; background: var(--raised); }
.progress > i { display: block; height: 100%; background: var(--accent); transition: width .4s; }
.progress.failed > i { background: var(--err); } .progress.success > i { background: var(--ok); }
.tabs { display: flex; gap: 2px; padding: 0 10px; border-bottom: 1px solid var(--line); overflow-x: auto; }
.tabs button { all: unset; padding: 8px 12px; cursor: pointer; color: var(--muted); border-bottom: 2px solid transparent; white-space: nowrap; }
.tabs button.active { color: var(--fg); border-bottom-color: var(--accent); }
.tabs button:focus-visible { outline: 2px solid var(--accent); }
pre.log { margin: 0; padding: 10px 14px; font: 12.5px/1.5 var(--mono); white-space: pre-wrap; word-break: break-word; overflow: auto; flex: 1; min-height: 300px; max-height: 64vh; background: var(--bg); border-radius: 0 0 10px 10px; }
pre.log .l-err { color: var(--err); } pre.log .l-warn { color: var(--warn); } pre.log .l-cmd { color: var(--accent); font-weight: 600; } pre.log .l-note { color: var(--muted); }
pre.log mark { background: var(--accent); color: var(--accent-ink); border-radius: 2px; }
.tools { display: flex; gap: 8px; align-items: center; padding: 8px 14px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.tools input[type=search] { flex: 1; min-width: 140px; }
label.check { display: flex; gap: 6px; align-items: center; color: var(--muted); font-size: 13px; cursor: pointer; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; color: var(--accent); font-weight: 600; padding: 7px 14px; position: sticky; top: 0; background: var(--surface); border-bottom: 1px solid var(--line); }
td { padding: 6px 14px; border-bottom: 1px solid var(--line); vertical-align: top; }
td.mono, .mono { font-family: var(--mono); font-size: 12px; word-break: break-all; }
tbody tr { cursor: default; } tbody tr.clickable { cursor: pointer; } tbody tr.clickable:hover, tbody tr.selected { background: var(--raised); }
.empty { color: var(--muted); padding: 24px 14px; text-align: center; }
dialog { background: var(--surface); color: var(--fg); border: 1px solid var(--line); border-radius: 12px; padding: 0; width: min(680px, 94vw); }
dialog::backdrop { background: rgba(0,0,0,.55); }
dialog .body { padding: 16px 18px; display: flex; flex-direction: column; gap: 10px; }
dialog h2 { margin: 0; font-size: 15px; }
dialog .fields { display: grid; grid-template-columns: 110px 1fr; gap: 8px 10px; align-items: center; }
dialog .preview { font: 12px var(--mono); background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; white-space: pre-wrap; word-break: break-all; min-height: 2.6em; }
dialog .actions { display: flex; gap: 8px; justify-content: flex-end; }
.hint { color: var(--muted); font-size: 12px; }
.toast { position: fixed; right: 18px; bottom: 18px; background: var(--raised); border: 1px solid var(--line); border-left: 4px solid var(--accent); padding: 10px 14px; border-radius: 8px; max-width: 420px; box-shadow: 0 6px 24px rgba(0,0,0,.35); }
.toast.error { border-left-color: var(--err); }
.keys td:first-child { white-space: nowrap; }
[hidden] { display: none !important; }
@media (max-width: 900px) {
  .app { grid-template-columns: 1fr; grid-template-rows: auto auto 1fr; }
  nav { flex-direction: row; overflow-x: auto; padding: 0; border-right: 0; border-bottom: 1px solid var(--line); }
  nav .group, nav .foot { display: none; }
  nav button { border-left: 0; border-bottom: 3px solid transparent; padding: 10px 12px; white-space: nowrap; }
  .panel > .head .detail-title { flex-basis: 100%; order: -1; }
  nav button.active { border-bottom-color: var(--accent); }
  .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .split { grid-template-columns: 1fr; }
  main { padding: 12px 16px; }
  .context { display: none; }
}
</style>
</head>
<body>
<div class="app">
  <header>
    <span class="brand">◆ bitloom</span>
    <select id="profile" aria-label="Profile"></select>
    <span class="context" id="context"></span>
    <span class="grow"></span>
    <input type="text" id="target" placeholder="Build target / recipe" aria-label="Build target" size="22">
    <button class="btn primary" id="build-btn" title="Build target (b)"><kbd>b</kbd>Build</button>
    <button class="btn" id="queue-btn" title="Queue any operation (q)"><kbd>q</kbd>Operations</button>
    <span class="hint"><span class="dot" id="service-dot"></span><span id="service-label">connecting…</span></span>
    <button class="btn" id="keys-btn" title="Keyboard shortcuts (?)">?</button>
  </header>
  <nav aria-label="Sections">
    <div class="group">BUILD</div>
    <button data-view="builds"><span class="num">1</span>◈ Builds</button>
    <button data-view="recipes"><span class="num">2</span>◇ Recipes</button>
    <button data-view="tasklogs"><span class="num">3</span>≋ Task logs</button>
    <div class="group">WORKSPACE</div>
    <button data-view="health"><span class="num">4</span>⚙ Configuration</button>
    <div class="foot">Same service and history as the TUI. Press <kbd>?</kbd> for keys.</div>
  </nav>
  <main>
    <section class="cards" aria-label="Status">
      <div class="card"><h3>Build</h3><div class="value" id="c-status">—</div><div class="sub" id="c-title">No jobs yet</div></div>
      <div class="card"><h3>Tasks</h3><div class="value" id="c-tasks">—</div><div class="sub" id="c-sstate"></div></div>
      <div class="card"><h3>Host memory</h3><div class="meter"><i id="c-ram-bar" style="width:0"></i></div><div class="sub" id="c-ram"></div></div>
      <div class="card"><h3>Workspace disk</h3><div class="meter"><i id="c-disk-bar" style="width:0"></i></div><div class="sub" id="c-disk"></div></div>
    </section>

    <section id="view-builds" class="split">
      <div class="panel">
        <div class="head"><h2>History</h2><span class="grow"></span><span class="hint"><kbd>j</kbd><kbd>k</kbd></span></div>
        <div class="list" id="history" role="listbox" aria-label="Build history"></div>
      </div>
      <div class="panel">
        <div class="head">
          <span class="glyph" id="d-glyph"></span>
          <span class="detail-title" id="d-title">Select an operation</span>
          <span class="meta mono" id="d-meta"></span>
          <span class="grow"></span>
          <button class="btn warn" id="graceful-btn" title="Graceful stop: one SIGINT to the BitBake client (g)"><kbd>g</kbd>Graceful</button>
          <button class="btn danger" id="stop-btn" title="Force stop (s)"><kbd>s</kbd>Stop</button>
          <button class="btn" id="retry-btn" title="Retry with the original profile (r)"><kbd>r</kbd>Retry</button>
        </div>
        <div class="progress" id="d-progress"><i style="width:0"></i></div>
        <div class="tabs" role="tablist">
          <button data-tab="output" class="active">Output</button>
          <button data-tab="summary">Summary</button>
          <button data-tab="sstate">Sstate reuse</button>
          <button data-tab="warnings">Warnings</button>
          <button data-tab="timings">Timings</button>
        </div>
        <div class="tools" id="log-tools">
          <input type="search" id="log-search" placeholder="/ search output (±3 lines of context)">
          <label class="check"><input type="checkbox" id="errors-only"> <kbd>e</kbd> errors only</label>
          <label class="check"><input type="checkbox" id="follow" checked> follow</label>
        </div>
        <pre class="log" id="log" tabindex="0" aria-live="off"></pre>
      </div>
    </section>

    <section id="view-recipes" class="panel" hidden>
      <div class="tools"><input type="search" id="meta-search" placeholder="/ search recipes, layers, appends, classes, kas files"><span class="hint" id="meta-count"></span></div>
      <div class="list"><table><thead><tr><th>Name</th><th>Type</th><th>Location</th></tr></thead><tbody id="meta-rows"></tbody></table></div>
    </section>

    <section id="view-tasklogs" class="split" hidden>
      <div class="panel">
        <div class="tools"><input type="search" id="task-search" placeholder="/ filter by recipe or task"></div>
        <div class="list"><table><thead><tr><th>Recipe</th><th>Task log</th><th>Size</th></tr></thead><tbody id="task-rows"></tbody></table></div>
      </div>
      <div class="panel">
        <div class="head"><h2 id="task-title">Task log</h2></div>
        <div class="tools"><input type="search" id="task-log-search" placeholder="search this task log"><label class="check"><input type="checkbox" id="task-errors"> errors only</label></div>
        <pre class="log" id="task-log" tabindex="0"></pre>
      </div>
    </section>

    <section id="view-health" class="panel" hidden>
      <div class="head"><h2>Health and configuration</h2><span class="grow"></span><span class="hint">Literal local.conf values; run bitbake -e for evaluated ones.</span></div>
      <div class="list"><table><thead><tr><th>Status</th><th>Check</th><th>Details</th></tr></thead><tbody id="health-rows"></tbody></table></div>
    </section>
  </main>
</div>

<dialog id="queue-dialog" aria-label="Queue an operation">
  <form method="dialog" class="body" id="queue-form">
    <h2>Queue an operation</h2>
    <input type="search" id="op-filter" placeholder="Filter: build, devtool, layers, sdk… (↑ ↓ choose, Enter queues)">
    <select id="op-select" size="8" aria-label="Operation"></select>
    <div class="fields" id="op-fields"></div>
    <div class="preview" id="op-preview"></div>
    <div class="actions"><button class="btn" value="cancel" formnovalidate>Cancel</button><button class="btn primary" id="op-submit" value="default">Queue</button></div>
  </form>
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
const GLYPH = {success: "✔", failed: "✖", running: "●", queued: "◌", cancelling: "◐", cancelled: "■", interrupted: "⚠"};
const KEYS = [["1 – 4", "Switch section"], ["/", "Search in the current section"], ["Esc", "Leave a field / close a dialog"],
  ["j / k", "Next / previous operation"], ["b", "Build the target"], ["q", "Queue any operation"], ["t", "Edit the build target"],
  ["s", "Force stop the selected operation"], ["g", "Graceful stop (BitBake client SIGINT)"], ["r", "Retry the selected operation"],
  ["e", "Toggle errors only"], ["o / u / w / m", "Output / Summary / Warnings / Timings tab"], ["?", "This help"]];
let consoleRows = [], state = null, actions = [], selected = null, view = "builds", tab = "output", logOffset = -1, logFor = null, followTimer = null;

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
  for (const child of children) node.append(child);
  return node;
}
function toast(message, error = false) {
  const node = el("div", {class: "toast" + (error ? " error" : ""), role: "status", text: message});
  document.body.append(node); setTimeout(() => node.remove(), error ? 7000 : 3500);
}
function size(bytes) { const units = ["B", "KiB", "MiB", "GiB", "TiB"]; let i = 0; while (bytes >= 1024 && i < 4) { bytes /= 1024; i++; } return bytes.toFixed(1) + " " + units[i]; }
function elapsed(row) {
  if (row.status === "queued") return "—";
  const end = row.finished ? new Date(row.finished) : new Date();
  let s = Math.max(0, Math.round((end - new Date(row.started)) / 1000));
  const h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60; s %= 60;
  return (h ? h + "h " : "") + (h || m ? m + "m " : "") + s + "s";
}
function profile() { return state && state.profiles.find((p) => p.name === $("profile").value); }

function renderLog(target, text, query, append = false) {
  if (!append) target.textContent = "";
  const fragment = document.createDocumentFragment();
  const needle = (query || "").toLowerCase();
  for (const line of text.split("\n")) {
    if (!line && append) continue;
    const span = el("span");
    if (line.startsWith("$ ")) span.className = "l-cmd";
    else if (/ERROR:|FAILED|error:/.test(line)) span.className = "l-err";
    else if (line.includes("WARNING:")) span.className = "l-warn";
    else if (line.includes("NOTE:")) span.className = "l-note";
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

function renderState() {
  const select = $("profile"), current = select.value || state.active;
  if (select.options.length !== state.profiles.length) {
    select.textContent = "";
    for (const p of state.profiles) select.append(el("option", {value: p.name, text: p.name}));
  }
  select.value = state.profiles.some((p) => p.name === current) ? current : state.active;
  const p = profile();
  $("context").textContent = p ? `${p.mode} · MACHINE ${p.machine || "?"} · DISTRO ${p.distro || "?"} · ${p.release}${p.shared ? " · team profile" : ""} · ${p.build}` : "";
  if (!$("target").dataset.touched && p) $("target").value = (p.targets || [])[0] || "";
  const service = state.service;
  $("service-dot").className = "dot " + (service.error ? "err" : "ok");
  $("service-label").textContent = service.error ? "service unavailable" : "service pid " + service.pid;
  const rows = state.history.filter((row) => !p || row.profile === p.name);
  const recent = rows[0];
  $("c-status").textContent = recent ? (GLYPH[recent.status] || "·") + " " + recent.status.toUpperCase() : "IDLE";
  $("c-status").className = "value " + (recent ? "s-" + recent.status : "");
  $("c-title").textContent = recent ? recent.title : "No jobs in this profile";
  const progress = recent ? recent.progress : [0, 0], setscene = recent ? recent.setscene : [0, 0];
  $("c-tasks").textContent = progress[1] ? `${progress[0]} / ${progress[1]}` : "no task count";
  $("c-sstate").textContent = (setscene && setscene[1] ? `${setscene[0]} / ${setscene[1]} from sstate · ` : "") + state.history.filter((r) => r.status === "queued").length + " queued";
  const host = state.host;
  if (host.ram_total) { $("c-ram-bar").style.width = (100 * host.ram_used / host.ram_total).toFixed(0) + "%"; $("c-ram").textContent = `${size(host.ram_used)} of ${size(host.ram_total)} · load ${(host.load || []).join(" ")}`; }
  if (host.disk_total) { $("c-disk-bar").style.width = (100 * host.disk_used / host.disk_total).toFixed(0) + "%"; $("c-disk").textContent = `${size(host.disk_free)} free of ${size(host.disk_total)}`; }
  const list = $("history"); list.textContent = "";
  if (!state.history.length) list.append(el("div", {class: "empty", text: "No operations yet. Press b to build or q for any operation."}));
  for (const row of state.history) {
    const item = el("div", {class: "row" + (row.id === selected ? " selected" : ""), role: "option", tabindex: "-1", "data-id": row.id, onclick: () => select_(row.id)},
      el("span", {class: "glyph s-" + row.status, text: GLYPH[row.status] || "·"}),
      el("span", {class: "title", title: row.title, text: row.title}),
      el("span", {class: "meta", text: elapsed(row)}));
    if (row.profile !== (p && p.name)) item.querySelector(".title").append(el("span", {class: "meta", text: "  " + row.profile}));
    list.append(item);
  }
  if (consoleRows.length) {
    list.append(el("div", {class: "group-label", text: "CONSOLE BUILDS · started outside Bitloom"}));
    for (const row of consoleRows) {
      const id = "console:" + row.path;
      const when = new Date(row.modified * 1000).toLocaleString();
      list.append(el("div", {class: "row" + (id === selected ? " selected" : ""), role: "option", tabindex: "-1", "data-id": id, onclick: () => select_(id)},
        el("span", {class: "glyph s-" + row.status, text: GLYPH[row.status] || "·"}),
        el("span", {class: "title", title: row.path, text: when + "  " + row.machine}),
        el("span", {class: "meta", text: size(row.size)})));
    }
  }
  if (!selected && state.history.length) select_(state.history[0].id);
  renderDetail();
}
async function loadConsole() {
  try { consoleRows = (await api(`/api/console?profile=${encodeURIComponent($("profile").value || state.active)}`)).rows; } catch (error) { consoleRows = []; }
}

function consoleRow() { return selected && selected.startsWith("console:") ? consoleRows.find((row) => "console:" + row.path === selected) : null; }
function current() { return state && state.history.find((row) => row.id === selected); }
function renderDetail() {
  const outside = consoleRow();
  if (outside) {
    for (const id of ["stop-btn", "graceful-btn", "retry-btn"]) $(id).disabled = true;
    $("d-glyph").textContent = GLYPH[outside.status] || "·"; $("d-glyph").className = "glyph s-" + outside.status;
    $("d-title").textContent = "Console build " + outside.name;
    $("d-meta").textContent = `${outside.status} · ${outside.machine} · not started by Bitloom`;
    $("d-progress").className = "progress " + outside.status;
    $("d-progress").firstElementChild.style.width = outside.status === "success" ? "100%" : "0";
    return;
  }
  const row = current();
  const active = row && ["running", "queued", "cancelling"].includes(row.status);
  $("stop-btn").disabled = !active; $("graceful-btn").disabled = !row || row.status !== "running"; $("retry-btn").disabled = !row || active;
  if (!row) return;
  $("d-glyph").textContent = GLYPH[row.status] || "·"; $("d-glyph").className = "glyph s-" + row.status;
  $("d-title").textContent = row.title;
  $("d-meta").textContent = `${row.status} · ${elapsed(row)}${row.code !== null && row.code !== undefined ? " · exit " + row.code : ""} · ${row.profile}`;
  const bar = $("d-progress");
  bar.className = "progress " + row.status;
  bar.firstElementChild.style.width = row.status === "success" ? "100%" : row.progress[1] ? (100 * row.progress[0] / row.progress[1]).toFixed(1) + "%" : "0";
}

function select_(id) {
  if (selected === id) return;
  selected = id; logOffset = -1; logFor = null;
  for (const node of document.querySelectorAll("#history .row")) node.classList.toggle("selected", node.dataset.id === id);
  renderDetail(); loadTab();
}

async function loadTab() {
  const outside = consoleRow();
  const row = current(); if (!row && !outside) return;
  $("log-tools").hidden = tab !== "output";
  const log = $("log");
  try {
    if (outside) {
      const base = `profile=${prof()}&path=${encodeURIComponent(outside.path)}`;
      if (tab !== "output") { const report = await api(`/api/console/report?${base}`); renderLog(log, report[tab] || "", ""); return; }
      const query = $("log-search").value;
      const data = await api(`/api/console/log?${base}&q=${encodeURIComponent(query)}&errors=${$("errors-only").checked ? 1 : 0}`);
      renderLog(log, data.text, query); logFor = selected; return;
    }
    if (tab !== "output") {
      const report = await api(`/api/jobs/${row.id}/report`);
      renderLog(log, report[tab] || "", ""); return;
    }
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
  for (const section of ["builds", "recipes", "tasklogs", "health"]) $("view-" + section).hidden = section !== name;
  for (const button of document.querySelectorAll("nav button")) button.classList.toggle("active", button.dataset.view === name);
  if (name === "recipes") loadMeta(); if (name === "tasklogs") loadTasks(); if (name === "health") loadHealth();
}
function setTab(name) {
  tab = name; logFor = null;
  for (const button of document.querySelectorAll(".tabs button")) button.classList.toggle("active", button.dataset.tab === name);
  loadTab();
}
const prof = () => encodeURIComponent($("profile").value);
let metaTimer;
async function loadMeta() {
  const data = await api(`/api/metadata?profile=${prof()}&q=${encodeURIComponent($("meta-search").value)}`);
  const body = $("meta-rows"); body.textContent = "";
  $("meta-count").textContent = `${data.total} entries` + (data.total > data.rows.length ? ` · first ${data.rows.length}` : "");
  for (const row of data.rows) body.append(el("tr", {}, el("td", {text: row.name}), el("td", {text: row.kind}), el("td", {class: "mono", text: row.detail || row.path})));
  if (!data.rows.length) body.append(el("tr", {}, el("td", {colspan: "3", class: "empty", text: "No matching metadata"})));
}
async function loadTasks() {
  const data = await api(`/api/tasklogs?profile=${prof()}&q=${encodeURIComponent($("task-search").value)}`);
  const body = $("task-rows"); body.textContent = "";
  for (const row of data.rows) {
    const tr = el("tr", {class: "clickable", tabindex: "0", onclick: () => openTask(row, tr), onkeydown: (event) => { if (event.key === "Enter") openTask(row, tr); }},
      el("td", {text: row.recipe}), el("td", {class: "mono", text: row.task}), el("td", {text: row.size}));
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
async function loadHealth() {
  const data = await api(`/api/health?profile=${prof()}`);
  const body = $("health-rows"); body.textContent = "";
  for (const check of data.checks) body.append(el("tr", {}, el("td", {class: {OK: "s-success", WARN: "s-queued", INFO: "s-running"}[check.status] || "", text: check.status}), el("td", {text: check.name}), el("td", {class: "mono", text: check.detail})));
}

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
    toast("Queued " + action); selected = null; await refresh(); select_(job.id); setView("builds");
  } catch (error) { toast(error.message, true); }
}
function openQueue() {
  $("op-filter").value = ""; fillOperations(); $("queue-dialog").showModal(); $("op-filter").focus();
}
async function control(kind) {
  const row = current(); if (!row) return;
  if (kind === "stop" && !confirm("Force stop " + row.title + "? Interrupted work directories may need cleaning.")) return;
  try {
    if (kind === "retry") { const job = await api(`/api/jobs/${row.id}/retry`, {method: "POST", body: "{}"}); selected = null; await refresh(); select_(job.id); }
    else { await api(`/api/jobs/${row.id}/stop`, {method: "POST", body: JSON.stringify({mode: kind === "graceful" ? "graceful" : "force"})}); toast("Stop requested"); refresh(); }
  } catch (error) { toast(error.message, true); }
}

function wire() {
  for (const button of document.querySelectorAll("nav button")) button.addEventListener("click", () => setView(button.dataset.view));
  for (const button of document.querySelectorAll(".tabs button")) button.addEventListener("click", () => setTab(button.dataset.tab));
  $("profile").addEventListener("change", async () => { $("target").dataset.touched = ""; await loadConsole(); renderState(); setView(view); });
  $("target").addEventListener("input", () => { $("target").dataset.touched = "1"; });
  $("target").addEventListener("keydown", (event) => { if (event.key === "Enter") queue("build", {target: $("target").value}); });
  $("build-btn").addEventListener("click", () => queue("build", {target: $("target").value}));
  $("queue-btn").addEventListener("click", openQueue);
  $("keys-btn").addEventListener("click", () => $("keys-dialog").showModal());
  $("keys-close").addEventListener("click", () => $("keys-dialog").close());
  $("stop-btn").addEventListener("click", () => control("stop"));
  $("graceful-btn").addEventListener("click", () => control("graceful"));
  $("retry-btn").addEventListener("click", () => control("retry"));
  for (const id of ["log-search"]) $(id).addEventListener("input", () => { clearTimeout(followTimer); followTimer = setTimeout(loadTab, 200); });
  $("errors-only").addEventListener("change", loadTab);
  $("meta-search").addEventListener("input", () => { clearTimeout(metaTimer); metaTimer = setTimeout(loadMeta, 200); });
  $("task-search").addEventListener("input", () => { clearTimeout(metaTimer); metaTimer = setTimeout(loadTasks, 200); });
  for (const id of ["task-log-search", "task-errors"]) $(id).addEventListener(id === "task-errors" ? "change" : "input", () => openTaskRow && openTask(openTaskRow, document.querySelector("#task-rows tr.selected")));
  $("op-filter").addEventListener("input", fillOperations);
  $("op-filter").addEventListener("keydown", (event) => {
    const select = $("op-select");
    // A search field spends the first Esc on clearing itself; close the dialog instead.
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
  const body = $("keys-rows");
  for (const [key, text] of KEYS) body.append(el("tr", {}, el("td", {}, el("kbd", {text: key})), el("td", {text})));
  document.addEventListener("keydown", (event) => {
    const typing = /INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName);
    if (event.key === "Escape" && typing && !document.querySelector("dialog[open]")) { document.activeElement.blur(); return; }
    if (typing || document.querySelector("dialog[open]") || event.ctrlKey || event.metaKey || event.altKey) return;
    const views = {"1": "builds", "2": "recipes", "3": "tasklogs", "4": "health"}, tabs = {o: "output", u: "summary", w: "warnings", m: "timings"};
    const handled = () => event.preventDefault();
    if (views[event.key]) { setView(views[event.key]); handled(); }
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
      const node = document.querySelector("#history .row.selected"); if (node) node.scrollIntoView({block: "nearest"});
    }
  });
}

(async () => {
  wire(); setView("builds");
  if (!token) { toast("Open the URL printed by bitloom --web (it carries the session token).", true); return; }
  try { actions = await api("/api/actions"); } catch (error) { toast(error.message, true); }
  await refresh(); await loadConsole(); renderState();
  setInterval(refresh, 1500);
})();
</script>
</body>
</html>
"""
