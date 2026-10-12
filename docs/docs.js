// Documentation pages: theme, mobile navigation, table-of-contents highlighting,
// code copy buttons and a client-side search over search.json.
(function () {
  const root = document.documentElement;
  const store = {
    get(key) { try { return localStorage.getItem(key); } catch (e) { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } },
  };

  // Theme: follows the system until the visitor chooses.
  const saved = store.get("bitloom-docs-theme");
  if (saved === "light" || saved === "dark") root.dataset.theme = saved;
  const themeButton = document.getElementById("theme-toggle");
  function currentTheme() {
    return root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  }
  function paintThemeButton() {
    if (!themeButton) return;
    const dark = currentTheme() === "dark";
    themeButton.textContent = dark ? "☀" : "☾";
    themeButton.setAttribute("aria-label", dark ? "Use light theme" : "Use dark theme");
    themeButton.title = themeButton.getAttribute("aria-label");
  }
  if (themeButton) {
    themeButton.addEventListener("click", () => {
      root.dataset.theme = currentTheme() === "dark" ? "light" : "dark";
      store.set("bitloom-docs-theme", root.dataset.theme);
      paintThemeButton();
    });
    paintThemeButton();
  }

  // Mobile navigation.
  const menu = document.getElementById("menu-toggle");
  if (menu) {
    menu.addEventListener("click", () => {
      const open = document.body.classList.toggle("nav-open");
      menu.setAttribute("aria-expanded", String(open));
    });
    document.querySelectorAll(".sidebar a").forEach((a) => a.addEventListener("click", () => document.body.classList.remove("nav-open")));
  }

  // Copy buttons on code blocks.
  document.querySelectorAll(".doc pre").forEach((pre) => {
    const button = document.createElement("button");
    button.className = "copy"; button.type = "button"; button.textContent = "Copy";
    button.addEventListener("click", async () => {
      const text = pre.querySelector("code") ? pre.querySelector("code").innerText : pre.innerText;
      try { await navigator.clipboard.writeText(text); button.textContent = "Copied"; }
      catch (e) { button.textContent = "Select and copy"; }
      setTimeout(() => { button.textContent = "Copy"; }, 1500);
    });
    pre.appendChild(button);
  });

  // Highlight the section being read in "On this page".
  const tocLinks = Array.from(document.querySelectorAll(".toc a"));
  if (tocLinks.length && "IntersectionObserver" in window) {
    const byId = new Map(tocLinks.map((a) => [decodeURIComponent(a.hash.slice(1)), a]));
    const visible = new Set();
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((e) => (e.isIntersecting ? visible.add(e.target.id) : visible.delete(e.target.id)));
      const headings = Array.from(byId.keys()).map((id) => document.getElementById(id)).filter(Boolean);
      const first = headings.find((h) => visible.has(h.id));
      if (!first) return;
      tocLinks.forEach((a) => a.classList.toggle("active", a === byId.get(first.id)));
    }, { rootMargin: "-70px 0px -65% 0px" });
    byId.forEach((_, id) => { const h = document.getElementById(id); if (h) observer.observe(h); });
  }

  // Search.
  const input = document.getElementById("search-input");
  const results = document.getElementById("search-results");
  if (!input || !results) return;
  let index = null, selected = -1;
  async function load() {
    if (index) return index;
    try { index = await (await fetch("search.json")).json(); } catch (e) { index = []; }
    return index;
  }
  function words(query) { return query.toLowerCase().split(/\s+/).filter((w) => w.length > 1); }
  function snippet(text, terms) {
    const lower = text.toLowerCase();
    let at = Math.max(0, ...terms.map((t) => lower.indexOf(t)).filter((i) => i >= 0).slice(0, 1));
    const start = Math.max(0, at - 50);
    return (start ? "…" : "") + text.slice(start, start + 160) + (start + 160 < text.length ? "…" : "");
  }
  function highlight(element, text, terms) {
    // Builds text nodes and <mark> elements: no HTML from the index is interpreted.
    const pattern = new RegExp("(" + terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")", "gi");
    text.split(pattern).forEach((part, i) => {
      if (i % 2) { const m = document.createElement("mark"); m.textContent = part; element.appendChild(m); }
      else if (part) element.appendChild(document.createTextNode(part));
    });
  }
  function render(query) {
    const terms = words(query);
    results.replaceChildren(); selected = -1;
    if (!terms.length) { results.hidden = true; return; }
    const scored = [];
    (index || []).forEach((entry) => {
      const title = entry.title.toLowerCase(), text = entry.text.toLowerCase();
      if (!terms.every((t) => title.includes(t) || text.includes(t) || entry.page.toLowerCase().includes(t))) return;
      const score = terms.reduce((s, t) => s + (title.includes(t) ? 10 : 0) + (text.split(t).length - 1), 0);
      scored.push([score, entry]);
    });
    scored.sort((a, b) => b[0] - a[0]);
    if (!scored.length) {
      const empty = document.createElement("div"); empty.className = "empty"; empty.textContent = "No results for “" + query + "”";
      results.appendChild(empty);
    }
    scored.slice(0, 12).forEach(([, entry]) => {
      const a = document.createElement("a");
      a.href = entry.url; a.setAttribute("role", "option");
      const where = document.createElement("span"); where.className = "where"; where.textContent = entry.page;
      const title = document.createElement("strong"); highlight(title, entry.title, terms);
      const snip = document.createElement("span"); snip.className = "snippet"; highlight(snip, snippet(entry.text, terms), terms);
      a.append(where, title, snip);
      results.appendChild(a);
    });
    results.hidden = false;
  }
  function move(step) {
    const items = Array.from(results.querySelectorAll("a"));
    if (!items.length) return;
    selected = (selected + step + items.length) % items.length;
    items.forEach((a, i) => a.setAttribute("aria-selected", String(i === selected)));
    items[selected].scrollIntoView({ block: "nearest" });
  }
  input.addEventListener("focus", load);
  input.addEventListener("input", async () => { await load(); render(input.value.trim()); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
    else if (e.key === "Enter") {
      const items = results.querySelectorAll("a");
      const target = items[selected >= 0 ? selected : 0];
      if (target) location.href = target.href;
    } else if (e.key === "Escape") { results.hidden = true; input.blur(); }
  });
  document.addEventListener("keydown", (e) => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    if (!typing && (e.key === "/" || (e.key === "k" && (e.ctrlKey || e.metaKey)))) { e.preventDefault(); input.focus(); input.select(); }
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".search")) results.hidden = true; });
})();
