// Sources & API keys page.
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.detail || r.statusText);
  return body;
}

function extraField(s, f) {
  const v = s.extra[f.name] ?? f.default;
  const id = `x-${s.id}-${f.name}`;
  if (f.type === "lines") return `<label class="field full" for="${id}">${esc(f.label)}<textarea id="${id}" data-extra="${f.name}" data-type="lines">${esc((v || []).join("\n"))}</textarea></label>`;
  if (f.type === "bool") return `<label class="check full"><input type="checkbox" data-extra="${f.name}" data-type="bool" ${v ? "checked" : ""}> ${esc(f.label)}</label>`;
  return `<label class="field full" for="${id}">${esc(f.label)}<input id="${id}" data-extra="${f.name}" value="${esc(v)}"></label>`;
}

function card(s) {
  const keyless = !s.needs_key;
  return `<form class="src ${s.enabled ? "" : "off"}" data-id="${s.id}">
    <div class="src-head">
      <span class="dot ${esc(s.state)}"></span>
      <h3>${esc(s.name)}</h3>
      <span class="muted" style="font-size:12px">${esc(s.kind)}</span>
      <span class="grow"></span>
      <span class="muted" style="font-size:12px">${esc(s.state)}${s.detail ? " · " + esc(s.detail) : ""}</span>
      <label class="check"><input type="checkbox" name="enabled" ${s.enabled ? "checked" : ""}> Enabled</label>
    </div>
    <div class="fields">
      <label class="field">Plan<select name="plan">${["Free", "Paid"].map((p) => `<option ${p === s.plan ? "selected" : ""}>${p}</option>`).join("")}</select></label>
      ${keyless ? `<div class="field wide">API key<input disabled placeholder="No key required"></div>` :
        `<label class="field wide">API key${s.needs_secret ? " ID" : ""}<input type="password" name="api_key" autocomplete="off" placeholder="${esc(s.key_masked || "Paste API key")}"></label>`}
      ${s.group === "platform" && s.id === "anthropic" ? "" :
        `<label class="field">Poll every (s)<input type="number" name="poll_seconds" min="${s.min_poll}" value="${s.poll_seconds}"></label>`}
      ${s.needs_secret ? `<label class="field wide">Secret key<input type="password" name="api_secret" autocomplete="off" placeholder="${esc(s.secret_masked || "Paste secret key")}"></label>` : ""}
      ${(s.extra_fields || []).map((f) => extraField(s, f)).join("")}
    </div>
    <div class="src-foot">
      <span>${esc(s.limit_hint)}</span>
      ${s.signup_url ? `<a href="${esc(s.signup_url)}" target="_blank" rel="noopener">get a key</a>` : ""}
      <span>Today: <span class="mono">${s.today}</span> · first to report: <span class="mono">${s.firsts}</span></span>
      <span class="grow"></span>
      <span class="result" data-r></span>
      ${s.key_masked ? `<button class="btn small" type="button" data-clear>Remove key</button>` : ""}
      <button class="btn small" type="button" data-test>Test connection</button>
      <button class="btn small primary" type="submit">Save</button>
    </div>
  </form>`;
}

function collect(form) {
  const body = { enabled: form.enabled.checked, plan: form.plan.value };
  if (form.api_key && form.api_key.value) body.api_key = form.api_key.value;
  if (form.api_secret && form.api_secret.value) body.api_secret = form.api_secret.value;
  if (form.poll_seconds) body.poll_seconds = Number(form.poll_seconds.value);
  const extras = form.querySelectorAll("[data-extra]");
  if (extras.length) {
    body.extra = {};
    extras.forEach((el) => {
      body.extra[el.dataset.extra] = el.dataset.type === "lines" ? el.value.split("\n").map((x) => x.trim()).filter(Boolean)
        : el.dataset.type === "bool" ? el.checked : el.value;
    });
  }
  return body;
}

async function render() {
  const { sources, settings } = await api("/api/sources");
  $("#platform").innerHTML = sources.filter((s) => s.group === "platform").map(card).join("");
  $("#platform").style.cssText = "display:flex;flex-direction:column;gap:12px";
  $("#news").innerHTML = sources.filter((s) => s.group !== "platform").map(card).join("");
  const f = $("#settings");
  for (const [k, v] of Object.entries(settings)) {
    if (!f[k]) continue;
    f[k].value = Array.isArray(v) ? v.join(", ") : v;
  }
  $("#simv").textContent = f.similarity.value;
}

document.addEventListener("submit", async (e) => {
  const form = e.target.closest("form.src");
  if (!form) return;
  e.preventDefault();
  const res = form.querySelector("[data-r]");
  try {
    await api(`/api/sources/${form.dataset.id}`, { method: "PUT", body: JSON.stringify(collect(form)) });
    await render();
    const r = document.querySelector(`form.src[data-id="${form.dataset.id}"] [data-r]`);
    if (r) { r.className = "result ok"; r.textContent = "Saved"; }
  } catch (err) { res.className = "result bad"; res.textContent = err.message; }
});

document.addEventListener("click", async (e) => {
  const form = e.target.closest("form.src");
  if (!form) return;
  const res = form.querySelector("[data-r]");
  if (e.target.closest("[data-test]")) {
    // Save first so the test uses what's on screen.
    res.className = "result"; res.textContent = "Testing…";
    try {
      await api(`/api/sources/${form.dataset.id}`, { method: "PUT", body: JSON.stringify(collect(form)) });
      const r = await api(`/api/sources/${form.dataset.id}/test`, { method: "POST" });
      res.className = `result ${r.ok ? "ok" : "bad"}`; res.textContent = r.message;
    } catch (err) { res.className = "result bad"; res.textContent = err.message; }
  } else if (e.target.closest("[data-clear]")) {
    if (!confirm("Remove the stored key for this source?")) return;
    await api(`/api/sources/${form.dataset.id}`, { method: "PUT", body: JSON.stringify({ clear_key: true, enabled: false }) });
    render();
  }
});

$("#settings").addEventListener("input", (e) => { if (e.target.name === "similarity") $("#simv").textContent = e.target.value; });
$("#settings").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const body = {
    watchlist: f.watchlist.value.split(/[\s,]+/).filter(Boolean),
    new_window_min: Number(f.new_window_min.value), dedupe_hours: Number(f.dedupe_hours.value),
    similarity: Number(f.similarity.value), classifier: f.classifier.value, ai_model: f.ai_model.value.trim(),
    topic_refresh_min: Number(f.topic_refresh_min.value), alpaca_feed: f.alpaca_feed.value,
    sec_user_agent: f.sec_user_agent.value.trim(),
  };
  try { await api("/api/settings", { method: "PUT", body: JSON.stringify(body) }); $("#sres").className = "result ok"; $("#sres").textContent = "Saved"; render(); }
  catch (err) { $("#sres").className = "result bad"; $("#sres").textContent = err.message; }
});

render();
// Refresh status counters, but never while the user has unsaved edits.
let dirty = false;
document.addEventListener("input", (e) => { if (e.target.closest("form.src")) dirty = true; });
document.addEventListener("submit", () => { dirty = false; }, true);
setInterval(() => { if (!dirty) render(); }, 15000);
