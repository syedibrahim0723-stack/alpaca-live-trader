// News Radar desk: live feed on the left, technicals for the selected ticker on the right.
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (x, d = 2) => (x === null || x === undefined || Number.isNaN(x) ? "—" : Number(x).toFixed(d));
const pct = (x) => (x === null || x === undefined ? "—" : `${x > 0 ? "+" : ""}${Number(x).toFixed(2)}%`);
const big = (v) => (v == null ? "—" : v >= 1e9 ? (v / 1e9).toFixed(2) + "B" : v >= 1e6 ? (v / 1e6).toFixed(2) + "M" : v >= 1e3 ? (v / 1e3).toFixed(1) + "K" : String(Math.round(v)));
const etTime = (ts) => new Date(ts * 1000).toLocaleTimeString("en-US", { timeZone: "America/New_York", hour12: false });
const etDate = (ts) => new Date(ts * 1000).toLocaleDateString("en-US", { timeZone: "America/New_York", month: "short", day: "numeric" });

const state = {
  items: new Map(), // id -> item
  category: "All", topic: null, newOnly: false, wlOnly: false,
  categories: [], topics: [], watchlist: [],
  selected: null, sym: null, tf: "5m", newsTs: null, timer: null, chart: null,
};

const SOURCE_LABEL = {
  alpaca: "Benzinga via Alpaca", sec: "SEC EDGAR", halts: "Nasdaq halts", rss: "RSS", tickertick: "TickerTick",
  finnhub: "Finnhub", massive: "Massive", marketaux: "Marketaux", tiingo: "Tiingo", alphavantage: "Alpha Vantage", newsapi: "NewsAPI",
};

// ── data ────────────────────────────────────────────────────────────────────
async function api(path, opts) {
  const r = await fetch(path, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || body.detail || r.statusText);
  return body;
}

async function load() {
  const [news, topics, src] = await Promise.all([api("/api/news?limit=400"), api("/api/topics"), api("/api/sources")]);
  state.categories = news.categories;
  news.items.forEach((it) => state.items.set(it.id, it));
  state.topics = topics.topics;
  state.watchlist = src.settings.watchlist || [];
  renderFeeds(src.sources);
  renderAll();
}

function visible() {
  let arr = [...state.items.values()].sort((a, b) => b.published_at - a.published_at);
  if (state.category !== "All") arr = arr.filter((i) => i.category === state.category);
  if (state.topic !== null) arr = arr.filter((i) => i.topic_id === state.topic);
  if (state.newOnly) arr = arr.filter((i) => i.is_new);
  if (state.wlOnly) arr = arr.filter((i) => i.tickers.some((t) => state.watchlist.includes(t)));
  return arr.slice(0, 300);
}

// ── rendering: filters ──────────────────────────────────────────────────────
function renderCats() {
  const counts = {};
  for (const it of state.items.values()) counts[it.category] = (counts[it.category] || 0) + 1;
  const cats = ["All", ...state.categories.filter((c) => counts[c])];
  $("#cats").innerHTML = cats
    .map((c) => `<button type="button" class="pill ${state.category === c ? "on" : ""}" data-cat="${esc(c)}">${esc(c)}<span class="n">${c === "All" ? state.items.size : counts[c]}</span></button>`)
    .join("");
}

function renderTopics() {
  $("#topics").innerHTML = state.topics.length
    ? state.topics.slice(0, 12).map((t) => `<button type="button" class="pill topic ${state.topic === t.id ? "on" : ""}" data-topic="${t.id}" title="${esc(t.terms)}">${esc(t.label)}<span class="n">${t.size}</span></button>`).join("")
    : `<span class="muted" style="font-size:12px">Topics appear once ~12 stories have arrived.</span>`;
}

function renderFeeds(sources) {
  $("#feeds").innerHTML = sources
    .filter((s) => s.enabled || s.state === "no key")
    .map((s) => `<span class="chip" title="${esc(s.detail || "")}"><span class="dot ${esc(s.state)}"></span>${esc(s.name.split(" (")[0])}<span class="muted">${esc(s.state === "ok" || s.state === "live" ? (s.today ? s.today + " today" : s.state) : s.state)}</span></span>`)
    .join("");
}

// ── rendering: feed ─────────────────────────────────────────────────────────
function cardHtml(it) {
  const srcs = it.sources.filter((s) => s !== it.source).map((s) => SOURCE_LABEL[s] || s);
  const age = Date.now() / 1000 - it.published_at;
  const seen = it.is_new ? "" : age < 3600 ? `${Math.max(1, Math.round(age / 60))}m ago` : age < 86400 ? `${Math.round(age / 3600)}h ago` : etDate(it.published_at);
  return `<article class="card ${it.is_new ? "new" : ""} ${state.selected === it.id ? "sel" : ""}" tabindex="0" data-id="${it.id}">
    <div class="meta">
      ${it.is_new ? '<span class="badge">NEW</span>' : ""}
      <span class="mono">${etTime(it.published_at)}</span><span>·</span>
      <span style="color:var(--text2)">${esc(SOURCE_LABEL[it.source] || it.source)}</span>
      <span class="grow"></span>
      ${it.impact >= 4 ? `<span class="impact" title="AI impact score">▲${it.impact}</span>` : ""}
      <span class="sent ${esc(it.sentiment)}">${esc(it.sentiment)}</span>
    </div>
    <h3>${esc(it.headline)}</h3>
    ${it.ai_summary && it.ai_summary.toLowerCase() !== it.headline.toLowerCase() ? `<div class="ai-sum">${esc(it.ai_summary)}</div>` : ""}
    <div class="meta">
      ${it.tickers.slice(0, 6).map((t) => `<span class="tk">$${esc(t)}</span>`).join("")}
      <span class="cat">${esc(it.category)}${it.classified_by === "ai" ? "" : " ·kw"}</span>
      ${srcs.length ? `<span>also on ${esc(srcs.join(", "))} (merged)</span>` : ""}
      ${seen ? `<span>${esc(seen)}</span>` : ""}
      ${it.url ? `<a href="${esc(it.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">open</a>` : ""}
    </div>
  </article>`;
}

function renderList() {
  const arr = visible();
  $("#list").innerHTML = arr.length ? arr.map(cardHtml).join("") : `<div class="empty">No stories match these filters yet.</div>`;
  const n = [...state.items.values()].filter((i) => i.is_new).length;
  $("#newCount").hidden = !n;
  $("#newCount").textContent = `${n} NEW`;
}

function renderAll() { renderCats(); renderTopics(); renderList(); }

// ── live updates ────────────────────────────────────────────────────────────
let beepCtx;
function beep() {
  if (!$("#sound").checked) return;
  try {
    beepCtx = beepCtx || new AudioContext();
    const o = beepCtx.createOscillator(), g = beepCtx.createGain();
    o.frequency.value = 880; g.gain.value = 0.05;
    o.connect(g).connect(beepCtx.destination);
    o.start(); o.stop(beepCtx.currentTime + 0.12);
  } catch (e) { /* audio blocked until the user interacts */ }
}

let renderPending = false;
function scheduleRender() {
  if (renderPending) return;
  renderPending = true;
  requestAnimationFrame(() => { renderPending = false; renderAll(); });
}

function connect() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "news") {
      state.items.set(msg.item.id, msg.item);
      scheduleRender();
      if (msg.item.is_new && msg.item.tickers.some((t) => state.watchlist.includes(t))) {
        beep();
        requestAnimationFrame(() => document.querySelector(`[data-id="${msg.item.id}"]`)?.classList.add("flash"));
      }
      if (msg.item.tickers.includes(state.sym)) loadTicker(true);
    } else if (msg.type === "update") {
      if (state.items.has(msg.item.id)) { state.items.set(msg.item.id, msg.item); scheduleRender(); }
    } else if (msg.type === "topics") {
      state.topics = msg.topics; renderTopics();
    } else if (msg.type === "status") {
      renderFeeds(msg.sources);
    }
  };
  const ping = setInterval(() => ws.readyState === 1 && ws.send("ping"), 20000);
  ws.onclose = () => { clearInterval(ping); setTimeout(connect, 2000); };
}

// NEW badges expire on a timer; re-evaluate locally every 30s.
setInterval(() => {
  api("/api/news?limit=400").then((r) => { r.items.forEach((it) => state.items.set(it.id, it)); renderList(); }).catch(() => {});
}, 60000);

// ── ticker panel ────────────────────────────────────────────────────────────
function selectStory(id) {
  const it = state.items.get(id);
  if (!it) return;
  state.selected = id;
  if (it.is_new) api(`/api/news/${id}/seen`, { method: "POST" }).catch(() => {});
  if (it.tickers.length) {
    state.sym = it.tickers[0];
    state.newsTs = it.published_at;
    loadTicker();
  }
  renderList();
}

async function loadTicker(quiet) {
  if (!state.sym) return;
  clearTimeout(state.timer);
  const side = $("#side");
  if (!quiet && !side.querySelector("#chart")) side.innerHTML = `<div class="placeholder">Loading ${esc(state.sym)}…</div>`;
  try {
    const q = new URLSearchParams({ tf: state.tf });
    if (state.newsTs) q.set("news_ts", state.newsTs);
    const rep = await api(`/api/ticker/${encodeURIComponent(state.sym)}?${q}`);
    renderSide(rep);
  } catch (e) {
    side.innerHTML = `<div class="placeholder err">${esc(e.message)}</div>`;
    state.chart = null;
  }
  state.timer = setTimeout(() => loadTicker(true), 15000);
}

function row(k, v, tag, good) {
  const cls = good === true ? "good" : good === false ? "bad" : "";
  return `<div class="row"><span class="k">${esc(k)}</span><span class="v">${v}${tag ? `<span class="tag ${cls}">${esc(tag)}</span>` : ""}</span></div>`;
}

function renderSide(r) {
  const side = $("#side");
  if (!side.querySelector("#chart") || side.dataset.sym !== r.symbol) {
    side.innerHTML = $("#sideTpl").innerHTML;
    side.dataset.sym = r.symbol;
    state.chart = null;
  }
  const f = (n) => side.querySelector(`[data-f="${n}"]`);
  const up = (r.change ?? 0) >= 0;
  f("sym").textContent = r.symbol;
  f("feed").textContent = `Alpaca · ${r.feed.toUpperCase()} feed`;
  f("price").textContent = fmt(r.price);
  f("chg").textContent = r.change == null ? "" : `${up ? "+" : ""}${fmt(r.change)}  (${pct(r.change_pct)})`;
  f("chg").className = `chg ${up ? "up" : "down"}`;
  f("stats").innerHTML = [["Open", fmt(r.open)], ["High", fmt(r.high)], ["Low", fmt(r.low)], ["Prev close", fmt(r.prev_close)], ["Volume", big(r.volume)], ["Bid × Ask", `${fmt(r.bid)} × ${fmt(r.ask)}`]]
    .map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("");
  f("tfs").innerHTML = ["1m", "5m", "15m", "1H", "1D"].map((t) => `<button type="button" class="tf ${t === state.tf ? "on" : ""}" data-tf="${t}">${t}</button>`).join("");

  const t = r.technicals, p = r.price_action;
  const rsiZone = t.rsi14 == null ? "" : t.rsi14 >= 70 ? "overbought" : t.rsi14 <= 30 ? "oversold" : "neutral";
  f("tech").innerHTML = `<h3>Technicals <span class="muted" style="font-weight:400">· 5m intraday, daily for EMA 50/200 + ATR</span></h3>
    <div style="display:flex;justify-content:space-between;font-size:12px"><span class="muted">RSI (14)</span><span class="mono">${fmt(t.rsi14, 1)} ${rsiZone}</span></div>
    <div class="rsi-bar"><span class="mid"></span>${t.rsi14 == null ? "" : `<span class="mark" style="left:calc(${t.rsi14}% - 2px)"></span>`}</div>
    ${row("MACD (12,26,9)", `${fmt(t.macd, 3)} / ${fmt(t.macd_signal, 3)}`, t.macd_hist == null ? "" : t.macd_hist >= 0 ? "Bullish" : "Bearish", t.macd_hist == null ? null : t.macd_hist >= 0)}
    ${row("EMA 9 / 20", `${fmt(t.ema9)} / ${fmt(t.ema20)}`, r.price && t.ema20 ? (r.price >= t.ema20 ? "Above" : "Below") : "", r.price && t.ema20 ? r.price >= t.ema20 : null)}
    ${row("EMA 50 / 200 (1D)", `${fmt(t.ema50_d)} / ${fmt(t.ema200_d)}`, t.trend || "", t.trend === "Uptrend" ? true : t.trend === "Downtrend" ? false : null)}
    ${row("VWAP", `${fmt(t.vwap)} (${pct(t.vwap_dist_pct)})`, t.vwap_dist_pct == null ? "" : t.vwap_dist_pct >= 0 ? "Above" : "Below", t.vwap_dist_pct == null ? null : t.vwap_dist_pct >= 0)}
    ${row("ATR (14, daily)", fmt(t.atr14_d))}
    ${row("Relative volume", t.rel_volume == null ? "—" : `${t.rel_volume}×`, t.rel_volume >= 2 ? "Elevated" : "", t.rel_volume >= 2 ? true : null)}`;

  f("pa").innerHTML = `<h3>Reaction &amp; levels</h3>
    <div class="tiles">
      <div class="tile"><div class="k">Since headline</div><div class="v ${p.since_news_pct >= 0 ? "up" : "down"}">${pct(p.since_news_pct)}</div></div>
      <div class="tile"><div class="k">Vol vs 20d avg</div><div class="v">${t.rel_volume == null ? "—" : t.rel_volume + "×"}</div></div>
      <div class="tile"><div class="k">Gap at open</div><div class="v ${p.gap_pct >= 0 ? "up" : "down"}">${pct(p.gap_pct)}</div></div>
    </div>
    ${row("Price at headline", fmt(p.price_at_news))}
    ${row("Premarket high / low", `${fmt(p.premarket_high)} / ${fmt(p.premarket_low)}`)}
    ${row("Opening range (30m) high / low", `${fmt(p.opening_range_high)} / ${fmt(p.opening_range_low)}`)}
    ${row("Prior-day high / low", `${fmt(p.prior_day_high)} / ${fmt(p.prior_day_low)}`)}
    <p class="note">${esc(p.summary)}</p>`;

  f("tnews").innerHTML = `<h3>${esc(r.symbol)} news</h3>` + (r.news.length
    ? r.news.slice(0, 10).map((n) => `<div class="row"><span class="k mono">${etDate(n.published_at)} ${etTime(n.published_at).slice(0, 5)}</span><span style="flex:1;color:var(--text2)">${esc(n.headline)}</span><span class="sent ${esc(n.sentiment)}">${esc(n.sentiment)}</span></div>`).join("")
    : `<div class="muted">No stories for ${esc(r.symbol)} yet.</div>`);

  drawChart(r);
}

// Lightweight Charts expects UTC seconds; shift bars so the axis reads US/Eastern.
function etOffset(ts) {
  const d = new Date(ts * 1000);
  const et = new Date(d.toLocaleString("en-US", { timeZone: "America/New_York" }));
  const utc = new Date(d.toLocaleString("en-US", { timeZone: "UTC" }));
  return (et - utc) / 1000;
}

function drawChart(r) {
  const el = $("#chart");
  if (!el || !window.LightweightCharts) return;
  if (!state.chart) {
    const chart = LightweightCharts.createChart(el, {
      autoSize: true,
      layout: { background: { color: "#151B23" }, textColor: "#9BA6B4", fontFamily: "Inter, system-ui" },
      grid: { vertLines: { color: "#1E252F" }, horzLines: { color: "#1E252F" } },
      timeScale: { timeVisible: r.timeframe !== "1D", secondsVisible: false, borderColor: "#2A3240" },
      rightPriceScale: { borderColor: "#2A3240" },
      crosshair: { mode: 0 },
    });
    state.chart = {
      chart,
      candles: chart.addCandlestickSeries({ upColor: "#3FB950", downColor: "#F85149", wickUpColor: "#3FB950", wickDownColor: "#F85149", borderVisible: false }),
      vol: chart.addHistogramSeries({ priceScaleId: "", priceFormat: { type: "volume" } }),
      vwap: chart.addLineSeries({ color: "#F0B429", lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false }),
      ema: chart.addLineSeries({ color: "#B392F0", lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false }),
    };
    state.chart.vol.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
  }
  const c = state.chart;
  c.chart.applyOptions({ timeScale: { timeVisible: r.timeframe !== "1D" } });
  const off = r.bars.length ? etOffset(r.bars[r.bars.length - 1].t) : 0;
  const bars = r.bars.map((b) => ({ ...b, time: Math.round(b.t + off) }));
  c.candles.setData(bars.map((b) => ({ time: b.time, open: b.o, high: b.h, low: b.l, close: b.c })));
  c.vol.setData(bars.map((b) => ({ time: b.time, value: b.v, color: b.c >= b.o ? "rgba(63,185,80,.45)" : "rgba(248,81,73,.45)" })));
  // EMA 9 and session VWAP (reset each ET day; skipped on daily bars).
  let e = null, pv = 0, vv = 0, day = null;
  const emaPts = [], vwPts = [];
  for (const b of bars) {
    e = e === null ? b.c : b.c * 0.2 + e * 0.8;
    emaPts.push({ time: b.time, value: e });
    if (r.timeframe !== "1D") {
      const d = Math.floor(b.time / 86400);
      if (d !== day) { day = d; pv = 0; vv = 0; }
      pv += ((b.h + b.l + b.c) / 3) * b.v; vv += b.v;
      if (vv) vwPts.push({ time: b.time, value: pv / vv });
    }
  }
  c.ema.setData(emaPts);
  c.vwap.setData(vwPts);
  // Marker on the bar that contains the headline.
  const markers = [];
  if (state.newsTs && bars.length) {
    const nt = state.newsTs + off;
    let hit = null;
    for (const b of bars) if (b.time <= nt) hit = b;
    if (hit) markers.push({ time: hit.time, position: "aboveBar", color: "#58A6FF", shape: "arrowDown", text: "News" });
  }
  c.candles.setMarkers(markers);
}

// ── events ──────────────────────────────────────────────────────────────────
document.addEventListener("click", (e) => {
  const cat = e.target.closest("[data-cat]");
  if (cat) { state.category = cat.dataset.cat; renderAll(); return; }
  const tp = e.target.closest("[data-topic]");
  if (tp) { const id = Number(tp.dataset.topic); state.topic = state.topic === id ? null : id; renderAll(); return; }
  const tf = e.target.closest("[data-tf]");
  if (tf) { state.tf = tf.dataset.tf; state.chart?.chart.remove(); state.chart = null; $("#side").dataset.sym = ""; loadTicker(); return; }
  const card = e.target.closest(".card[data-id]");
  if (card) selectStory(card.dataset.id);
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.target.matches(".card[data-id]")) selectStory(e.target.dataset.id);
});
$("#newOnly").onchange = (e) => { state.newOnly = e.target.checked; renderList(); };
$("#wlOnly").onchange = (e) => { state.wlOnly = e.target.checked; renderList(); };
$("#search").onsubmit = (e) => {
  e.preventDefault();
  const s = $("#q").value.trim().toUpperCase().replace(/^\$/, "");
  if (!s) return;
  state.sym = s; state.newsTs = null; state.selected = null;
  state.category = "All"; renderAll(); loadTicker();
};
$("#seenAll").onclick = async () => {
  await api("/api/news/seen_all", { method: "POST" });
  for (const it of state.items.values()) it.is_new = false;
  renderList();
};
$("#rebuild").onclick = async () => {
  $("#rebuild").textContent = "Refreshing…";
  try { state.topics = (await api("/api/topics/rebuild", { method: "POST" })).topics; renderTopics(); }
  finally { $("#rebuild").textContent = "Refresh topics"; }
};
setInterval(() => { $("#clock").textContent = new Date().toLocaleTimeString("en-US", { timeZone: "America/New_York", hour12: false }) + " ET"; }, 1000);

load().catch((e) => { $("#list").innerHTML = `<div class="empty err">${esc(e.message)}</div>`; });
connect();
