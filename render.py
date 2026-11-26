"""Builds the single-page site from the saved items."""

import json
from html import escape

PALETTE = ["--c1", "--c2", "--c3", "--c4", "--c5", "--c6"]


def build_page(items, categories, watch, errors, updated_iso):
    cats = [{"key": k, "title": v.get("title", k), "color": f"var({PALETTE[i % len(PALETTE)]})"}
            for i, (k, v) in enumerate(categories.items())]
    data = {"items": items, "categories": cats, "watch": watch, "errors": errors, "updated": updated_iso}
    blob = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return TEMPLATE.replace("__DATA__", blob)


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>What’s on, Glasgow</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #E8EBEE; --surface: #FFFFFF; --ink: #16212C; --muted: #56626E; --line: #D2D8DE;
  --new: #FF6200; --new-ink: #FFFFFF; --star: #C98A00;
  --c1: #E05A00; --c2: #6A4CE0; --c3: #14855A; --c4: #C2255C; --c5: #1F6FB2; --c6: #8A6D1F;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #131A21; --surface: #1B242E; --ink: #E6EBF0; --muted: #94A1AE; --line: #2B3744;
    --new: #FF7A26; --new-ink: #131A21; --star: #F2B630;
    --c1: #FF8040; --c2: #A08BFF; --c3: #3CC48A; --c4: #F0628F; --c5: #5AA9F0; --c6: #D4B254;
    color-scheme: dark;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font-family: Archivo, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; line-height: 1.45; }
.wrap { max-width: 760px; margin: 0 auto; padding: 40px 20px 72px; }

header h1 { margin: 0; font-weight: 800; font-stretch: 62%; font-size: clamp(64px, 17vw, 136px);
  line-height: .82; letter-spacing: -.005em; }
header h1 span { display: block; font-stretch: 125%; font-weight: 400; font-size: max(22px, .3em); line-height: 1.2;
  letter-spacing: .01em; color: var(--muted); }
.status { margin: 18px 0 0; font-size: 15px; color: var(--muted); }
.status strong { color: var(--ink); }

.controls { position: sticky; top: 0; z-index: 2; background: var(--bg); padding: 16px 0 12px; margin-top: 20px;
  border-bottom: 1px solid var(--line); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font: inherit; font-size: 14px; font-weight: 600; display: inline-flex; align-items: center; gap: 7px;
  padding: 6px 12px; border-radius: 999px; border: 1px solid var(--line); background: var(--surface);
  color: var(--ink); cursor: pointer; }
.chip .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--chip, var(--muted)); }
.chip .n { color: var(--muted); font-weight: 400; }
.chip[aria-pressed="true"] { background: var(--ink); color: var(--bg); border-color: var(--ink); }
.chip[aria-pressed="true"] .n { color: inherit; opacity: .75; }
.row2 { display: flex; gap: 12px; align-items: center; margin-top: 12px; flex-wrap: wrap; }
.row2 input[type=search] { flex: 1 1 220px; font: inherit; font-size: 15px; padding: 8px 12px; border-radius: 8px;
  border: 1px solid var(--line); background: var(--surface); color: var(--ink); }
.row2 label { font-size: 14px; display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
:focus-visible { outline: 2px solid var(--new); outline-offset: 2px; }

h2 { font-stretch: 62%; font-weight: 700; font-size: 30px; margin: 32px 0 10px; }
.item { background: var(--surface); border-left: 4px solid var(--cat); padding: 12px 14px; margin: 0 0 6px;
  border-radius: 2px 8px 8px 2px; }
.item .t { font-size: 17px; font-weight: 650; line-height: 1.3; }
.item .t a { color: inherit; text-decoration: none; }
.item .t a:hover { text-decoration: underline; }
.item .badge { display: inline-block; vertical-align: 2px; margin-right: 8px; font-size: 11px; font-weight: 700;
  padding: 2px 7px; border-radius: 4px; background: var(--new); color: var(--new-ink); }
.item .star { color: var(--star); margin-right: 4px; }
.item .meta { display: flex; flex-wrap: wrap; gap: 4px 14px; margin-top: 4px; font-size: 13px; color: var(--muted); }
.item .meta .cat { color: var(--cat); font-weight: 600; }
.item .s { margin-top: 6px; font-size: 14px; color: var(--muted); max-width: 65ch; }

.empty { padding: 32px 0; color: var(--muted); }
.empty button { font: inherit; margin-top: 8px; padding: 6px 12px; border-radius: 8px; border: 1px solid var(--line);
  background: var(--surface); color: var(--ink); cursor: pointer; }
footer { margin-top: 40px; font-size: 13px; color: var(--muted); }
footer details { margin-top: 8px; }
footer summary { cursor: pointer; }
@media (prefers-reduced-motion: no-preference) { .chip { transition: background .12s, color .12s; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>What’s on<span>Glasgow</span></h1>
    <p class="status" id="status"></p>
  </header>
  <div class="controls">
    <div class="chips" id="chips" role="group" aria-label="Category"></div>
    <div class="row2">
      <input type="search" id="q" placeholder="Search titles, venues, sources" aria-label="Search">
      <label><input type="checkbox" id="newOnly"> New since last visit</label>
    </div>
  </div>
  <main id="list"></main>
  <footer id="foot"></footer>
</div>
<script type="application/json" id="data">__DATA__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById("data").textContent);
  const catBy = Object.fromEntries(D.categories.map(c => [c.key, c]));
  const watch = D.watch.map(w => w.toLowerCase());
  let last = null;
  try { last = localStorage.getItem("lastVisit"); } catch (e) {}
  const since = last ? Date.parse(last) : Date.now() - 7 * 864e5;
  const now = Date.now();

  D.items.forEach(it => {
    const text = (it.title + " " + (it.summary || "")).toLowerCase();
    it._new = Date.parse(it.first_seen) > since;
    it._star = watch.some(w => text.includes(w));
    it._text = (text + " " + it.source).toLowerCase();
  });

  const state = { cat: "all", q: "", newOnly: false };
  const $ = id => document.getElementById(id);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls;
    if (text != null) e.textContent = text; return e; };

  const updated = new Date(D.updated);
  const newCount = D.items.filter(i => i._new).length;
  const st = $("status");
  st.append("Updated " + updated.toLocaleString("en-GB", { weekday: "long", day: "numeric", month: "long",
    hour: "2-digit", minute: "2-digit" }) + ". ");
  if (newCount) { const b = el("strong", null, String(newCount)); st.append(b, newCount === 1 ? " new thing" : " new things", last ? " since you last looked." : " this week."); }
  else st.append("Nothing new since you last looked.");

  function chip(key, label, color, n) {
    const b = el("button", "chip"); b.type = "button"; b.dataset.key = key;
    if (color) { b.style.setProperty("--chip", color); b.append(el("span", "dot")); }
    b.append(label, " ", el("span", "n", String(n)));
    b.addEventListener("click", () => { state.cat = key; render(); });
    return b;
  }
  const chips = $("chips");
  chips.append(chip("all", "All", null, D.items.length));
  D.categories.forEach(c => chips.append(chip(c.key, c.title, c.color, D.items.filter(i => i.category === c.key).length)));

  $("q").addEventListener("input", e => { state.q = e.target.value.trim().toLowerCase(); render(); });
  $("newOnly").addEventListener("change", e => { state.newOnly = e.target.checked; render(); });

  function bucket(iso) {
    const days = (now - Date.parse(iso)) / 864e5;
    return days < 7 ? "This week" : days < 14 ? "Last week" : "Earlier";
  }

  function card(it) {
    const c = catBy[it.category] || { title: it.category, color: "var(--muted)" };
    const a = el("article", "item"); a.style.setProperty("--cat", c.color);
    const t = el("div", "t");
    if (it._new) t.append(el("span", "badge", "New"));
    if (it._star) { const s = el("span", "star", "★"); s.title = "On your watch list"; t.append(s); }
    if (/^https?:\/\//.test(it.link)) { const l = el("a", null, it.title); l.href = it.link; l.target = "_blank"; l.rel = "noopener"; t.append(l); }
    else t.append(it.title);
    const m = el("div", "meta");
    if (state.cat === "all") m.append(el("span", "cat", c.title));
    if (it.when) m.append(el("span", null, it.when));
    m.append(el("span", null, it.source));
    a.append(t, m);
    if (it.summary) a.append(el("div", "s", it.summary));
    return a;
  }

  function render() {
    chips.querySelectorAll(".chip").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.key === state.cat)));
    const list = $("list"); list.replaceChildren();
    const shown = D.items.filter(it => (state.cat === "all" || it.category === state.cat)
      && (!state.newOnly || it._new) && (!state.q || it._text.includes(state.q)))
      .sort((a, b) => (b._star - a._star) || b.first_seen.localeCompare(a.first_seen));
    if (!shown.length) {
      const e = el("div", "empty", D.items.length ? "Nothing matches these filters." : "Nothing found yet. Check the sources in config.yaml.");
      if (D.items.length) { const btn = el("button", null, "Show everything"); btn.type = "button";
        btn.addEventListener("click", () => { state.cat = "all"; state.q = ""; state.newOnly = false;
          $("q").value = ""; $("newOnly").checked = false; render(); }); e.append(el("br"), btn); }
      list.append(e); return;
    }
    ["This week", "Last week", "Earlier"].forEach(name => {
      const group = shown.filter(it => bucket(it.first_seen) === name);
      if (!group.length) return;
      list.append(el("h2", null, name));
      group.forEach(it => list.append(card(it)));
    });
  }

  const foot = $("foot");
  foot.append("Showing finds from the last few weeks. Starred items match your watch list.");
  if (D.errors.length) {
    const d = el("details"); d.append(el("summary", null, D.errors.length + " source" + (D.errors.length > 1 ? "s" : "") + " couldn’t be read on the last update"));
    const ul = el("ul"); D.errors.forEach(e => { const li = el("li"); li.append(el("strong", null, e.source), ": " + e.message); ul.append(li); });
    d.append(ul); foot.append(d);
  }

  render();
  const remember = () => { try { localStorage.setItem("lastVisit", D.updated); } catch (e) {} };
  addEventListener("pagehide", remember);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") remember(); });
})();
</script>
</body>
</html>
"""
