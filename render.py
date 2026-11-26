"""Builds the single-page site from the saved items."""

import json
from html import escape

PALETTE = ["--c1", "--c2", "--c3", "--c4", "--c5", "--c6"]


def build_page(items, categories, watch, errors, updated_iso, interests=(), local=None):
    cats = [{"key": k, "title": v.get("title", k), "color": f"var({PALETTE[i % len(PALETTE)]})"}
            for i, (k, v) in enumerate(categories.items())]
    data = {"items": items, "categories": cats, "watch": watch, "errors": errors, "updated": updated_iso,
            "interests": list(interests), "local": local}
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

.controls { background: var(--bg); padding: 16px 0 12px; margin-top: 20px;
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
.chips.when { margin-top: 8px; }
.chips.when .chip { font-weight: 500; font-size: 13px; padding: 4px 11px; }
.hidden-n { font-size: 13px; color: var(--muted); }
.tagbox { flex: 1 1 220px; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 5px 8px;
  border-radius: 8px; border: 1px dashed var(--line); cursor: text; min-height: 38px; }
.tagbox:focus-within { border-style: solid; border-color: var(--muted); }
.tag-label { font-size: 13px; font-weight: 600; color: var(--muted); margin-right: 2px; }
.tags { display: contents; }
.tag { display: inline-flex; align-items: center; gap: 2px; font-size: 13px; padding: 2px 4px 2px 10px; border-radius: 999px;
  background: var(--surface); border: 1px solid var(--line); }
.tag button { font: inherit; font-size: 15px; line-height: 1; border: 0; background: none; color: var(--muted); cursor: pointer;
  padding: 1px 5px; border-radius: 50%; }
.tag button:hover { color: var(--ink); background: var(--line); }
.tagbox input { flex: 1 1 120px; min-width: 100px; font: inherit; font-size: 14px; border: 0; outline: 0; padding: 3px 2px;
  background: transparent; color: var(--ink); }
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

.tabs { display: flex; gap: 26px; margin: -4px 0 14px; border-bottom: 1px solid var(--line); }
.tabs button { font: inherit; font-stretch: 75%; font-size: 24px; font-weight: 700; background: none; border: 0;
  padding: 4px 0 8px; margin-bottom: -1px; color: var(--muted); cursor: pointer; border-bottom: 3px solid transparent; }
.tabs button[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--new); }
.daterange { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 10px; font-size: 14px; }
.daterange[hidden] { display: none; }
.daterange label { display: inline-flex; align-items: center; gap: 6px; }
.daterange input { font: inherit; font-size: 14px; padding: 5px 8px; border-radius: 8px; border: 1px solid var(--line);
  background: var(--surface); color: var(--ink); }
.item { position: relative; }
.item .t { padding-right: 34px; }
.like { position: absolute; top: 8px; right: 8px; width: 32px; height: 32px; border-radius: 50%; border: 0;
  background: none; color: var(--muted); font-size: 19px; line-height: 1; cursor: pointer; }
.like:hover { background: var(--bg); color: var(--c4); }
.like[aria-pressed="true"] { color: var(--c4); }
.item .meta .why { color: var(--ink); font-weight: 600; }
.intro { background: var(--surface); border-radius: 8px; padding: 14px 16px; margin: 24px 0 4px; font-size: 15px; }
.intro p { margin: 0 0 6px; } .intro p:last-child { margin: 0; color: var(--muted); font-size: 14px; }
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
    <div class="tabs" role="tablist">
      <button type="button" role="tab" id="tabFor" data-tab="for">For you</button>
      <button type="button" role="tab" id="tabAll" data-tab="all">Everything</button>
    </div>
    <div class="chips" id="chips" role="group" aria-label="Category"></div>
    <div class="chips when" id="when" role="group" aria-label="When"></div>
    <div class="daterange" id="dateRange" hidden>
      <label>From <input type="date" id="dFrom"></label>
      <label>To <input type="date" id="dTo"></label>
    </div>
    <div class="row2">
      <input type="search" id="q" placeholder="Search titles, venues, sources" aria-label="Search">
      <label><input type="checkbox" id="newOnly"> New since last visit</label>
    </div>
    <div class="row2">
      <div class="tagbox" id="hideWrap">
        <span class="tag-label">Hide</span>
        <span class="tags" id="hideTags"></span>
        <input type="text" id="hide" placeholder="type a word, press Enter" aria-label="Hide anything mentioning this word">
      </div>
      <span class="hidden-n" id="hiddenN"></span>
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

  const DAY = 864e5;
  const midnight = t => { const d = new Date(t); d.setHours(0, 0, 0, 0); return d.getTime(); };
  const today0 = midnight(now);
  // "This weekend": Friday to Sunday night; if it's already the weekend, from today.
  const dow = new Date(now).getDay();
  const wkStart = (dow === 0 || dow === 6 || dow === 5) ? today0 : today0 + ((5 - dow + 7) % 7) * DAY;
  const wkEnd = wkStart + ((8 - new Date(wkStart).getDay()) % 7 || 7) * DAY + 3 * 3600e3;  // Monday 3am, for late Sunday nights

  D.items.forEach(it => {
    const text = (it.title + " " + (it.summary || "") + " " + (it.venue || "")).toLowerCase();
    it._new = Date.parse(it.first_seen) > since;
    it._star = watch.some(w => text.includes(w));
    it._text = (text + " " + it.source).toLowerCase();
    it._start = it.starts ? Date.parse(it.starts) : null;
    it._end = it.ends ? Date.parse(it.ends) + DAY - 1 : it._start;   // exhibitions run to the end of their last day
    it._ongoing = !!it.ends && it._start < today0;
  });

  // An event matches a time window if it overlaps it (so a running exhibition counts as "today").
  const during = (from, to) => it => it._start != null && it._start < to && it._end >= from;
  const WHEN = [
    ["any", "Any time", () => true],
    ["today", "Today", during(today0, today0 + DAY)],
    ["weekend", "This weekend", during(wkStart, wkEnd)],
    ["week", "Next 7 days", during(today0, today0 + 7 * DAY)],
    ["news", "News", it => it._start == null],
    ["dates", "Pick dates…", it => during(range.from, range.to)(it)],
  ];
  // Picked date range (local midnights; "to" includes the whole of that day plus late-night events).
  const range = { from: today0, to: today0 + 7 * DAY };
  const isoDay = t => { const d = new Date(t); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); };
  const fromIso = s => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d).getTime(); };

  const load = (key, fallback) => { try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; } };
  const store = (key, v) => { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {} };

  const state = { tab: load("tab", "for"), cat: "all", when: "any", q: "", newOnly: false, hide: load("hideWords", []) };
  // What the For you tab learns from: hearts (strong) and links opened (weak). Snapshots, so they outlive the items.
  let likes = load("likes", []), opened = load("opened", []);
  const snap = it => ({ uid: it.uid, title: it.title, venue: it.venue || "", category: it.category });
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

  const whenBox = $("when");
  WHEN.forEach(([key, label]) => {
    const b = el("button", "chip", label); b.type = "button"; b.dataset.key = key;
    b.addEventListener("click", () => { state.when = key; render(); if (key === "dates") $("dFrom").focus(); });
    whenBox.append(b);
  });
  const dFrom = $("dFrom"), dTo = $("dTo");
  dFrom.value = isoDay(range.from); dTo.value = isoDay(range.to - DAY);
  dFrom.min = dTo.min = isoDay(today0);
  function readRange() {
    if (dFrom.value) range.from = fromIso(dFrom.value);
    if (dTo.value) range.to = fromIso(dTo.value) + DAY + 3 * 3600e3;
    if (range.to <= range.from) { range.to = range.from + DAY + 3 * 3600e3; dTo.value = dFrom.value; }
    dTo.min = dFrom.value || isoDay(today0);
    render();
  }
  dFrom.addEventListener("change", readRange);
  dTo.addEventListener("change", readRange);

  document.querySelectorAll(".tabs button").forEach(b => b.addEventListener("click", () => {
    state.tab = b.dataset.tab; store("tab", state.tab); render();
  }));

  // ── For you: score each item against what you've liked, opened, watch-listed and listed as interests ──
  const STOP = new Set(("glasgow with from your this that night nights live presents present christmas festive xmas event events "
    + "party tickets ticket edition special show shows tour 2026 2027 2028 saturday sunday friday monday tuesday wednesday "
    + "thursday january february march april june july august september october november december plus guests session "
    + "sessions club").split(" "));
  const words = s => [...new Set((s.toLowerCase().match(/[a-z0-9][a-z0-9']{3,}/g) || []).filter(w => !STOP.has(w)))];
  const interests = (D.interests || []).map(w => w.toLowerCase());

  function buildProfile() {
    const P = { n: 0, venue: {}, cat: {}, word: {}, liked: new Set(likes.map(l => l.uid)) };
    const add = (x, w) => {
      P.n += w;
      if (x.venue) P.venue[x.venue.toLowerCase()] = (P.venue[x.venue.toLowerCase()] || 0) + w;
      P.cat[x.category] = (P.cat[x.category] || 0) + w;
      words(x.title).forEach(t => { P.word[t] = (P.word[t] || 0) + w; });
    };
    likes.forEach(x => add(x, 1));
    opened.forEach(x => add(x, 0.35));
    return P;
  }

  function scoreItem(it, P) {
    let s = 0; const why = [];
    if (it._star) { s += 3; why.push("On your watch list"); }
    const hit = interests.filter(w => it._text.includes(w));
    if (hit.length) { s += 2 * Math.min(2, hit.length); why.push("Matches “" + hit[0] + "”"); }
    if (P.n) {
      const v = it.venue ? (P.venue[it.venue.toLowerCase()] || 0) : 0;
      if (v) { s += 2 * Math.min(v, 2); why.push("You like things at " + it.venue); }
      s += 2.5 * (P.cat[it.category] || 0) / P.n;
      const w = words(it.title).reduce((a, t) => a + (P.word[t] || 0), 0);
      if (w) { s += Math.min(w, 3); if (!v) why.push("Similar to things you liked"); }
    }
    if (s > 0 && it._start != null && it._start < today0 + 14 * DAY) s += 0.5;   // nudge soon things up
    if (it._start == null) s -= 1;                                              // news matters less than events
    return { s, why: why[0] || "" };
  }

  function toggleLike(it) {
    likes = likes.some(l => l.uid === it.uid) ? likes.filter(l => l.uid !== it.uid) : [...likes, snap(it)];
    store("likes", likes); render();
  }
  function noteOpened(it) {
    opened = [...opened.filter(o => o.uid !== it.uid), snap(it)].slice(-150);
    store("opened", opened);
  }

  $("q").addEventListener("input", e => { state.q = e.target.value.trim().toLowerCase(); render(); });
  $("newOnly").addEventListener("change", e => { state.newOnly = e.target.checked; render(); });
  // Hide words as tags: type a word, press Enter (or comma) to add it; × or Backspace removes.
  const hideBox = $("hide"), tagsEl = $("hideTags");
  function saveHide() {
    try { localStorage.setItem("hideWords", JSON.stringify(state.hide)); } catch (err) {}
    drawTags(); render();
  }
  function drawTags() {
    tagsEl.replaceChildren(...state.hide.map(w => {
      const t = el("span", "tag", w);
      const x = el("button", null, "×"); x.type = "button"; x.setAttribute("aria-label", "Stop hiding " + w);
      x.addEventListener("click", () => { state.hide = state.hide.filter(h => h !== w); saveHide(); hideBox.focus(); });
      t.append(x); return t;
    }));
  }
  function addHide() {
    const w = hideBox.value.replace(/,/g, "").trim().toLowerCase();
    hideBox.value = "";
    if (w && !state.hide.includes(w)) { state.hide.push(w); saveHide(); }
  }
  hideBox.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addHide(); }
    else if (e.key === "Backspace" && !hideBox.value && state.hide.length) { state.hide.pop(); saveHide(); }
  });
  hideBox.addEventListener("blur", addHide);
  $("hideWrap").addEventListener("click", e => { if (e.target.id === "hideWrap") hideBox.focus(); });
  drawTags();

  // Events are grouped by the day they happen; news by when it was found.
  function eventGroup(t) {
    const d0 = midnight(t), days = Math.round((d0 - today0) / DAY);
    if (days <= 0) return "Today";
    if (days === 1) return "Tomorrow";
    const d = new Date(t);
    if (days < 14 || state.when === "dates") return d.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
    return d.toLocaleDateString("en-GB", { month: "long", year: "numeric" });
  }
  function newsGroup(iso) {
    const days = (now - Date.parse(iso)) / DAY;
    return days < 7 ? "News this week" : days < 14 ? "News last week" : "Earlier news";
  }

  function card(it, why) {
    const c = catBy[it.category] || { title: it.category, color: "var(--muted)" };
    const a = el("article", "item"); a.style.setProperty("--cat", c.color);
    const t = el("div", "t");
    if (it._new) t.append(el("span", "badge", "New"));
    if (it._star) { const s = el("span", "star", "★"); s.title = "On your watch list"; t.append(s); }
    if (/^https?:\/\//.test(it.link)) {
      const l = el("a", null, it.title); l.href = it.link; l.target = "_blank"; l.rel = "noopener";
      l.addEventListener("click", () => noteOpened(it)); t.append(l);
    } else t.append(it.title);
    const liked = likes.some(l => l.uid === it.uid);
    const h = el("button", "like", liked ? "♥" : "♡"); h.type = "button";
    h.setAttribute("aria-pressed", String(liked));
    h.setAttribute("aria-label", (liked ? "Unlike " : "Like ") + it.title);
    h.title = liked ? "Liked: more like this will show in For you" : "Like: shows you more like this in For you";
    h.addEventListener("click", () => toggleLike(it));
    a.append(h);
    const m = el("div", "meta");
    if (why) m.append(el("span", "why", why));
    if (state.cat === "all") m.append(el("span", "cat", c.title));
    if (it._ongoing) m.append(el("span", null, "Until " + new Date(it.ends).toLocaleDateString("en-GB", { day: "numeric", month: "long", timeZone: "UTC" })));
    else if (it.when) m.append(el("span", null, it.when));
    if (it.venue && it.venue !== it.source) m.append(el("span", null, it.venue));
    m.append(el("span", null, it.source));
    a.append(t, m);
    if (it.summary) a.append(el("div", "s", it.summary));
    return a;
  }

  function renderForYou(list, shown) {
    const P = buildProfile();
    const scored = shown.filter(it => !P.liked.has(it.uid)).map(it => ({ it, ...scoreItem(it, P) }))
      .filter(x => x.s > 0.6)
      .sort((a, b) => (b.s - a.s) || ((a.it._start ?? 9e15) - (b.it._start ?? 9e15)));
    // Keep it varied: one card per series (same thing, different dates/times), at most 4 per venue.
    const series = it => (it.venue || "").toLowerCase() + "|" + words(it.title.replace(/\d[\d:.]*\s*(am|pm)?/gi, " ")).slice(0, 4).join(" ");
    const picks = [], bySeries = {}, perVenue = {};
    for (const x of scored) {
      const k = series(x.it), v = (x.it.venue || x.it.source).toLowerCase();
      if (bySeries[k]) { bySeries[k].more++; continue; }
      if ((perVenue[v] || 0) >= 4) continue;
      x.more = 0; bySeries[k] = x; perVenue[v] = (perVenue[v] || 0) + 1;
      picks.push(x);
      if (picks.length >= 40) break;
    }

    if (likes.length < 3) {
      const box = el("div", "intro");
      box.append(el("p", null, likes.length
        ? "Good start. Like a few more things and this gets sharper."
        : "This tab learns what you’re into. Tap ♡ on anything that appeals, here or under Everything."));
      box.append(el("p", null, "It looks at the venues, kinds of thing and words in what you like and what you open, plus your watch list"
        + (interests.length ? " and interests (" + interests.slice(0, 4).join(", ") + (interests.length > 4 ? "…" : "") + ")" : "")
        + ". Likes are saved in this browser only."));
      list.append(box);
    }
    if (picks.length) {
      list.append(el("h2", null, "Top picks"));
      picks.forEach(x => list.append(card(x.it,
        [x.why, x.more ? "+" + x.more + " more date" + (x.more > 1 ? "s" : "") : ""].filter(Boolean).join(" · "))));
    }
    const likedNow = shown.filter(it => P.liked.has(it.uid)).sort((a, b) => (a._start ?? 9e15) - (b._start ?? 9e15));
    const renderLiked = () => {
      if (!likedNow.length) return;
      list.append(el("h2", null, "Your likes"));
      likedNow.forEach(it => list.append(card(it)));
    };
    // Not much to go on yet: show a spread of what's coming up, one per category in turn, to like from.
    if (picks.length < 12) {
      const taken = new Set(picks.map(x => x.it.uid));
      const byCat = D.categories.map(c => shown.filter(it => it.category === c.key && !taken.has(it.uid) && !P.liked.has(it.uid)
        && it._start != null && !it._ongoing).sort((a, b) => a._start - b._start));
      const spread = [];
      for (let i = 0; spread.length < 18 && byCat.some(l => l.length > i); i++)
        byCat.forEach(l => { if (l[i] && spread.length < 18) spread.push(l[i]); });
      if (spread.length) {
        list.append(el("h2", null, "A mix of what’s coming up"));
        spread.sort((a, b) => a._start - b._start).forEach(it => list.append(card(it)));
      }
    }
    renderLiked();
  }

  function render() {
    chips.querySelectorAll(".chip").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.key === state.cat)));
    whenBox.querySelectorAll(".chip").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.key === state.when)));
    document.querySelectorAll(".tabs button").forEach(b => b.setAttribute("aria-selected", String(b.dataset.tab === state.tab)));
    $("dateRange").hidden = state.when !== "dates";
    const list = $("list"); list.replaceChildren();
    const whenTest = WHEN.find(w => w[0] === state.when)[2];
    const muted = it => state.hide.some(w => it._text.includes(w));
    const base = D.items.filter(it => (state.cat === "all" || it.category === state.cat)
      && whenTest(it) && (!state.newOnly || it._new) && (!state.q || it._text.includes(state.q)));
    const shown = base.filter(it => !muted(it));
    const nHidden = base.length - shown.length;
    $("hiddenN").textContent = nHidden ? nHidden + " hidden" : "";

    if (!shown.length) {
      const e = el("div", "empty", D.items.length ? "Nothing matches these filters." : "Nothing found yet. Check the sources in config.yaml.");
      if (D.items.length) { const btn = el("button", null, "Show everything"); btn.type = "button";
        btn.addEventListener("click", () => { state.cat = "all"; state.when = "any"; state.q = ""; state.newOnly = false;
          $("q").value = ""; $("newOnly").checked = false; render(); }); e.append(el("br"), btn); }
      list.append(e); return;
    }

    if (state.tab === "for") { renderForYou(list, shown); return; }

    const groups = new Map();
    const add = (name, it) => { if (!groups.has(name)) groups.set(name, []); groups.get(name).push(it); };
    shown.filter(it => it._start != null && !it._ongoing).sort((a, b) => a._start - b._start)
      .forEach(it => add(eventGroup(it._start), it));
    shown.filter(it => it._ongoing).sort((a, b) => a._end - b._end)
      .forEach(it => add("On now", it));
    shown.filter(it => it._start == null).sort((a, b) => b.first_seen.localeCompare(a.first_seen))
      .forEach(it => add(newsGroup(it.first_seen), it));
    groups.forEach((group, name) => {
      list.append(el("h2", null, name));
      group.sort((a, b) => b._star - a._star).forEach(it => list.append(card(it)));
    });
  }

  const foot = $("foot");
  foot.append("Events stay listed until they've happened; news for a few weeks. Starred items match your watch list. Hidden words are remembered in this browser only.");
  // Sites that refuse GitHub are topped up by running update_local.py; say how fresh that is.
  if (D.local && D.local.sources.length) {
    const names = [...new Set(D.local.sources.map(s => s.split(" – ")[0]))].join(" and ");
    const p = el("p");
    if (D.local.last) {
      const days = Math.floor((now - Date.parse(D.local.last)) / DAY);
      p.append(names + " listings were last updated from your computer "
        + (days < 1 ? "today" : days === 1 ? "yesterday" : days + " days ago") + ".");
      if (days >= 7) { p.append(" "); p.append(el("strong", null, "Time to run update_local.py.")); }
    } else p.append(names + " listings come from running update_local.py on your computer. Not run yet.");
    foot.append(p);
  }
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
