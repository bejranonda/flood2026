"use strict";
// BKK FloodWatch frontend. Talks only to our API (D-001). Every external string goes through esc().

const STATUS = {
  critical: { th: "ล้นตลิ่ง", long: "วิกฤต (ล้นตลิ่ง)", color: "#c62828" },
  warning: { th: "ใกล้ตลิ่ง", long: "เตือนภัย (ใกล้ตลิ่ง)", color: "#e46c0a" },
  watch: { th: "เฝ้าระวัง", long: "เฝ้าระวัง", color: "#b58900" },
  normal: { th: "ปกติ", long: "ปกติ", color: "#2e9d5b" },
  unknown: { th: "ไม่ทราบ", long: "ไม่ทราบ (ไม่มีระดับตลิ่ง)", color: "#8a94a3" },
};
const RANK = { critical: 0, warning: 1, watch: 2, normal: 3, unknown: 4 };
const TREND = { rising: "📈 มีแนวโน้มเพิ่มขึ้น", falling: "📉 มีแนวโน้มลดลง", steady: "➖ ทรงตัว", unknown: "ยังไม่มีข้อมูลพอสำหรับคาดการณ์" };
const CHANCE = { "<5%": "ต่ำมาก (น้อยกว่า 5%)", "5-25%": "มีโอกาส (5–25%)", "25-50%": "ค่อนข้างสูง (25–50%)", ">50%": "สูง (มากกว่า 50%)" };
const VERDICT = { matches: "✅ ตรง", higher: "⬆️ น้ำจริงสูงกว่า", lower: "⬇️ น้ำจริงต่ำกว่า", unsure: "🤷 ไม่แน่ใจ" };
const DEPTH = { none: "ไม่มีน้ำท่วม", ankle: "ท่วมถึงข้อเท้า (ไม่เกิน 20 ซม.)", knee: "ท่วมถึงเข่า (ราว 50 ซม.)", waist: "ท่วมถึงเอว (ราว 1 ม.)", above: "สูงกว่าเอว" };

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const TZ = { timeZone: "Asia/Bangkok" };
const fmtTime = (iso) => iso ? new Date(iso).toLocaleString("th-TH", { ...TZ, day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "-";
const fmtHour = (ms) => new Date(ms).toLocaleTimeString("th-TH", { ...TZ, hour: "2-digit", minute: "2-digit" });
const fmtAge = (m) => m == null ? "-" : m < 60 ? `${Math.round(m)} นาทีที่แล้ว` : m < 1440 ? `${Math.round(m / 60)} ชม.ที่แล้ว` : `${Math.round(m / 1440)} วันที่แล้ว`;
const cm = (m) => m == null ? "-" : `${m > 0 ? "+" : ""}${Math.round(m * 100)} ซม.`;
// Round first: -0.4 cm used to render as "ต่ำกว่าตลิ่ง 0 ซม." next to an "overflowing" badge (BKK009, 2026-09-26).
const freeboardText = (fb) => {
  if (fb == null) return "";
  const c = Math.round(fb * 100);
  return c === 0 ? "ระดับเท่าตลิ่ง" : c < 0 ? `สูงกว่าตลิ่ง ${-c} ซม.` : `ต่ำกว่าตลิ่ง ${c} ซม.`;
};
// Region filter for the list: only 10 of ~111 gauges are in Bangkok, so severity sorting put Ayutthaya first.
const REGIONS = {
  all: { th: "ทั้งหมด", test: () => true },
  bkk: { th: "กทม.", test: (p) => p === "กรุงเทพมหานคร" },
  metro: { th: "ปริมณฑล", test: (p) => ["นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "สมุทรสาคร", "นครปฐม"].includes(p) },
  up: { th: "เหนือ กทม.", test: (p) => !["กรุงเทพมหานคร", "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "สมุทรสาคร", "นครปฐม"].includes(p) },
};
// Default "bkk" (owner, 2026-09-26: "Bangkok as default this week"; revisit 2026-10-03). A tapped choice is remembered.
const DEFAULT_REGION = "bkk";
let region = (() => { try { return REGIONS[localStorage.getItem("region")] ? localStorage.getItem("region") : DEFAULT_REGION; } catch { return DEFAULT_REGION; } })();
const NOTE = {
  datum_suspect: "ค่าระดับน้ำของสถานีนี้ไม่ได้อยู่ในหน่วย ม.รทก. (ตรวจพบค่าผิดปกติ) จึงไม่แสดงค่า",
  no_recent_data: "ไม่มีข้อมูลใหม่เกิน 24 ชม. สถานะจึงเป็น “ไม่ทราบ”",
  stale: "ข้อมูลเก่ากว่า 3 ชม.",
  no_bank: "ไม่มีข้อมูลระดับตลิ่ง จึงประเมินสถานะไม่ได้",
  approx_location: "ตำแหน่งบนแผนที่โดยประมาณ (จากชื่อสถานี)",
  no_location: "ไม่มีพิกัด จึงไม่แสดงบนแผนที่",
  suspect_values_hidden: "ค่าล่าสุดผิดปกติ (เช่น สูงเกินตลิ่งมากเกินจริง) จึงซ่อนไว้ และแสดงค่าที่เชื่อถือได้ล่าสุดแทน",
};
const notesText = (s) => (s.notes || []).filter((n) => n !== "stale").map((n) => NOTE[n] + (n === "approx_location" && s.coord_precision_km ? ` ±${s.coord_precision_km} กม.` : "")).join(" · ");
const norm = (s) => String(s ?? "").toLowerCase().replace(/\s+/g, "");

let stations = [];
let statusFilter = null;
let map, layer, legend;
let lastPos = null;

async function getJSON(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

/* ---------- summary strip ---------- */
function renderSummary(st) {
  const f = st.focus, n = st.network;
  const chips = ["critical", "warning", "watch", "normal", "unknown"].map((k) =>
    `<button class="chip" data-status="${k}" aria-pressed="${statusFilter === k}" title="แสดงเฉพาะ${esc(STATUS[k].long)}">
      <span class="dot" style="background:${STATUS[k].color}"></span>${esc(STATUS[k].th)} <b>${f.status[k]}</b></button>`).join("");
  const bar = (x) => `<span class="fresh" aria-hidden="true">
    <span style="width:${(100 * x.h1) / x.total}%;background:#2e9d5b"></span>
    <span style="width:${(100 * (x.h3 - x.h1)) / x.total}%;background:#9ccc65"></span>
    <span style="width:${(100 * (x.h24 - x.h3)) / x.total}%;background:#f4d35e"></span></span>`;
  const pct = (a, b) => Math.round((100 * a) / (b || 1));
  const rain = st.rain_bkk_next24_mm_max;
  document.getElementById("summary").innerHTML = `<div class="chips">${chips}</div>
    <p class="sumline">${esc(TREND.rising)} <b>${f.trend12.rising}</b> · ${esc(TREND.falling)} <b>${f.trend12.falling}</b> สถานี (12 ชม.)
      ${rain != null ? ` · 🌧️ ฝน กทม. 24 ชม. ข้างหน้า สูงสุด ~${Math.round(rain)} มม.` : ""}</p>
    <div class="sumline">📡 ส่งข้อมูลภายใน 1 ชม. <b>${f.h1}</b> · 3 ชม. <b>${f.h3}</b> · 24 ชม. <b>${f.h24}</b> จาก ${f.total} สถานี${bar(f)}
      <details><summary>ทั้งประเทศ</summary> เครือข่าย สสน. ${n.total} สถานี: ภายใน 1 ชม. ${n.h1} (${pct(n.h1, n.total)}%) ·
        3 ชม. ${n.h3} (${pct(n.h3, n.total)}%) · 24 ชม. ${n.h24} (${pct(n.h24, n.total)}%) · เกิน 24 ชม./ไม่มีข้อมูล ${n.older + n.never}
        · ในพื้นที่ติดตาม ${f.no_coords} สถานีไม่มีพิกัด, ${f.no_bank} สถานีไม่มีระดับตลิ่ง</details></div>`;
  document.querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => {
    statusFilter = statusFilter === b.dataset.status ? null : b.dataset.status;
    document.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c.dataset.status === statusFilter)));
    setTab("list");
    renderList();
  }));
}

/* ---------- list ---------- */
function itemHTML(s, extra = "") {
  const st = STATUS[s.status] || STATUS.unknown;
  return `<li class="item s-${esc(s.status)} ${s.stale ? "stale" : ""}" data-code="${esc(s.code)}" tabindex="0">
    <div class="row"><span class="name">${esc(s.name_th)} <span class="muted">${esc(s.code)}</span></span>
      <span class="badge b-${esc(s.status)}">${esc(st.th)}</span></div>
    <div class="row"><span class="meta">${esc(s.amphoe || s.river || "")} ${esc(s.province || "")}${s.agency === "BMA" ? " · ข้อมูล กทม." : ""}</span><span class="fb">${esc(freeboardText(s.freeboard_m))}</span></div>
    <div class="meta">${esc(TREND[s.trend12] || TREND.unknown)}${s.delta12_median != null && s.trend12 !== "steady" ? " " + esc(cm(s.delta12_median)) + " ใน 12 ชม." : ""}
      · ${esc(fmtAge(s.age_min))}${s.stale ? " ⚠️ ข้อมูลเก่า" : ""}</div>${notesText(s) ? `<div class="meta note">ℹ️ ${esc(notesText(s))}</div>` : ""}${extra}</li>`;
}

function bindItems(root) {
  root.querySelectorAll(".item").forEach((li) => {
    li.addEventListener("click", () => showDetail(li.dataset.code));
    li.addEventListener("keydown", (e) => { if (e.key === "Enter") showDetail(li.dataset.code); });
  });
}

function renderRegions() {
  const el = document.getElementById("regions");
  if (!el) return;
  el.innerHTML = Object.entries(REGIONS).map(([k, r]) => {
    const n = stations.filter((s) => r.test(s.province || "")).length;
    return `<button type="button" class="rchip" data-region="${k}" aria-pressed="${k === region}">${esc(r.th)} <b>${n}</b></button>`;
  }).join("");
  el.querySelectorAll(".rchip").forEach((b) => b.addEventListener("click", () => {
    region = b.dataset.region;
    try { localStorage.setItem("region", region); } catch { /* private mode */ }
    renderList();
  }));
}

function renderList() {
  const q = norm(document.getElementById("q").value);
  renderRegions();
  const rows = stations
    .filter((s) => q || REGIONS[region].test(s.province || ""))  // a search looks in every region
    .filter((s) => !statusFilter || s.status === statusFilter)
    .filter((s) => !q || norm([s.name_th, s.code, s.amphoe, s.province, s.river].join(" ")).includes(q))
    .sort((a, b) => (RANK[a.status] - RANK[b.status]) || ((a.freeboard_m ?? 99) - (b.freeboard_m ?? 99)));
  const ul = document.getElementById("list");
  const raw = document.getElementById("q").value.trim();
  const place = raw.length >= 2 ? `<li class="placeq"><button type="button" class="btn placebtn">🔎 ค้นหาสถานที่ “${esc(raw)}” (ซอย ถนน ย่าน)</button><div class="placeres"></div></li>` : "";
  ul.innerHTML = place + (rows.map((s) => itemHTML(s)).join("") || "<li class='muted'>ไม่พบสถานีชื่อนี้ ลองค้นหาเป็นสถานที่ด้านบน</li>");
  ul.querySelector(".placebtn")?.addEventListener("click", () => placeSearch(raw));
  bindItems(ul);
}

// Place search (ซอย/ถนน/ย่าน) for areas without a gauge: our server asks OpenStreetMap Nominatim (Bangkok region
// only, cached, ≤ 1 request/s) and the result opens the point check. No AI needed: OSM knows sois by name.
async function placeSearch(q) {
  const box = document.querySelector("#list .placeres");
  if (!box) return;
  box.innerHTML = "<p class='muted'>กำลังค้นหา…</p>";
  try {
    const d = await getJSON(`/api/geocode?q=${encodeURIComponent(q)}`);
    box.innerHTML = d.results.length
      ? d.results.map((r, i) => `<button type="button" class="btn placehit" data-i="${i}">📌 ${esc(r.name)} <span class="muted">${esc(r.area)}</span></button>`).join("")
        + "<p class='muted'>© ผู้ร่วมสร้าง OpenStreetMap</p>"
      : "<p class='muted'>ไม่พบสถานที่นี้ในกรุงเทพฯ และปริมณฑล ลองชื่อซอย ถนน หรือแตะบนแผนที่แทน</p>";
    box.querySelectorAll(".placehit").forEach((b) => b.addEventListener("click", () => {
      const r = d.results[+b.dataset.i];
      if (map) map.setView([r.lat, r.lon], 14);
      checkPoint(r.lat, r.lon, "pin", r.name);
    }));
  } catch (e) {
    box.innerHTML = `<p class='muted'>ค้นหาไม่สำเร็จ (${esc(e.message)}) ลองอีกครั้ง หรือแตะบนแผนที่แทน</p>`;
  }
}

/* ---------- map ---------- */
function renderMap() {
  if (!map) {
    map = L.map("map", { zoomControl: true }).setView([13.95, 100.55], 9);
    // Stations on top so they are always tappable; citizen-report cells below and non-interactive (owner
    // feedback: taps hit the Traffy circles first). A tap there opens the point check, which lists the counts.
    map.createPane("reports").style.zIndex = 350;
    map.createPane("stations").style.zIndex = 650;
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap" }).addTo(map);
    legend = L.control({ position: "bottomright" });
    legend.onAdd = () => {
      const d = L.DomUtil.create("div", "legend");
      d.innerHTML = Object.values(STATUS).map((s) => `<div><i style="background:${s.color}"></i>${esc(s.th)}</div>`).join("")
        + `<div><i style="background:#7b1fa2;opacity:.4"></i>รายงานประชาชน 6 ชม.</div>`;
      return d;
    };
    legend.addTo(map);
    const hint = L.control({ position: "topright" });
    hint.onAdd = () => { const d = L.DomUtil.create("div", "legend"); d.textContent = "👆 แตะจุดใดก็ได้บนแผนที่ เพื่อดูข้อมูลรอบจุดนั้น"; return d; };
    hint.addTo(map);
    const opts = L.control({ position: "bottomleft" });
    opts.onAdd = () => {
      const d = L.DomUtil.create("div", "legend");
      d.innerHTML = `<label><input type="checkbox" id="all-th"> แสดงสถานีทั่วประเทศ</label><div id="unplaced" class="muted"></div>`;
      L.DomEvent.disableClickPropagation(d);
      d.querySelector("#all-th").addEventListener("change", (e) => toggleNational(e.target.checked));
      return d;
    };
    opts.addTo(map);
    map.on("click", (e) => checkPoint(e.latlng.lat, e.latlng.lng, "pin"));
  }
  if (layer) layer.remove();
  layer = L.layerGroup().addTo(map);
  getJSON("/api/reports?hours=6").then((r) => r.cells.forEach(([lat, lon, n]) => {
    L.circle([lat, lon], { pane: "reports", interactive: false, radius: 150 + 50 * Math.min(n, 20), color: "#7b1fa2",
      weight: 0, fillOpacity: 0.14 }).addTo(layer);
  })).catch(() => {});
  stations.filter((s) => s.lat && s.lon).sort((a, b) => RANK[b.status] - RANK[a.status]).forEach((s) => {
    const st = STATUS[s.status] || STATUS.unknown;
    const approx = (s.notes || []).includes("approx_location");
    L.circleMarker([s.lat, s.lon], { pane: "stations", radius: s.status === "critical" ? 10 : 8, color: approx ? "#333" : "#fff",
      weight: 2, dashArray: approx ? "3 3" : null, fillColor: st.color, fillOpacity: s.stale ? 0.45 : 0.95, bubblingMouseEvents: false })
      .bindTooltip(`${esc(s.name_th)} — ${esc(st.th)} ${esc(freeboardText(s.freeboard_m))}${notesText(s) ? `<br><small>${esc(notesText(s))}</small>` : ""}`)
      .on("click", () => showDetail(s.code)).addTo(layer);
  });
  const unplaced = stations.filter((s) => !s.lat).length;
  document.getElementById("unplaced").textContent = unplaced ? `${unplaced} สถานีไม่มีพิกัด (ดูในรายการ)` : "";
}

/* ---------- whole HII network (optional layer; small markers) ---------- */
let national = null;
async function toggleNational(on) {
  if (national) { national.remove(); national = null; }
  if (!on) return;
  national = L.layerGroup().addTo(map);
  const d = await getJSON("/api/stations?scope=all");
  const focus = new Set(stations.map((s) => s.code));
  d.stations.filter((s) => s.lat && !focus.has(s.code)).forEach((s) => {
    const st = STATUS[s.status] || STATUS.unknown;
    L.circleMarker([s.lat, s.lon], { pane: "stations", radius: 5, color: "#fff", weight: 1, fillColor: st.color, fillOpacity: 0.8, bubblingMouseEvents: false })
      .bindTooltip(`${esc(s.name_th)} (${esc(s.province || "")}) — ${esc(st.th)}`).on("click", () => showDetail(s.code)).addTo(national);
  });
  map.setView([13.8, 100.9], 6);
}

/* ---------- Chao Phraya profile (1-D, gauges only; no interpolation between them) ---------- */
async function renderRiver() {
  const box = document.getElementById("view-river");
  box.innerHTML = "<p class='muted'>กำลังโหลด…</p>";
  try {
    const d = await getJSON("/api/profile");
    const rows = d.stations.map((s) => {
      const st = STATUS[s.status] || STATUS.unknown;
      const pct = s.pct_bank == null ? 0 : Math.max(2, Math.min(100, s.pct_bank));
      return `<div class="prow" data-code="${esc(s.code)}" role="button" tabindex="0">
        <span class="pname">${esc(s.name_th)} <small>${esc(s.province || "")}${s.chainage_km != null ? ` · ~${Math.round(s.chainage_km)} กม. จากปากแม่น้ำ` : ""}</small></span>
        <span class="pbar" title="ความลึกน้ำเทียบความลึกตลิ่ง ${esc(s.pct_bank ?? "-")}%"><span style="width:${pct}%;background:${st.color}"></span></span>
        <span class="pval" style="color:${st.color}">${s.freeboard_m == null ? "-" : esc(cm(-s.freeboard_m))}</span></div>`;
    }).join("");
    box.innerHTML = `<p class="muted">แม่น้ำเจ้าพระยา จากเหนือ (นครสวรรค์) ลงใต้ (ปากอ่าว) · แถบ = ความลึกน้ำเทียบตลิ่ง ·
      ตัวเลข = ระดับน้ำเทียบตลิ่ง (ติดลบ = ต่ำกว่าตลิ่ง) · ระยะทางตามลำน้ำจากปากแม่น้ำโดยประมาณ (คลาดเคลื่อนได้ ~10 กม.) ·
      ค่าระหว่างสถานีไม่ได้ประมาณ เพราะตลิ่งและคันกั้นน้ำแต่ละช่วงสูงไม่เท่ากัน</p>${rows}`;
    box.querySelectorAll(".prow").forEach((r) => {
      r.addEventListener("click", () => showDetail(r.dataset.code));
      r.addEventListener("keydown", (e) => { if (e.key === "Enter") showDetail(r.dataset.code); });
    });
  } catch (e) {
    box.innerHTML = `<p>โหลดข้อมูลไม่สำเร็จ (${esc(e.message)})</p>`;
  }
}

/* ---------- chart ---------- */
// Light midnight (Bangkok time) markers with a short date, so people can read rough times without detail.
function dayTicks(tmin, tmax, x, H) {
  const DAY = 864e5, ICT = 7 * 3600e3;
  const first = Math.ceil((tmin + ICT) / DAY) * DAY - ICT;
  const days = [];
  for (let t = first; t <= tmax; t += DAY) days.push(t);
  const step = days.length > 6 ? 2 : 1;
  return days.map((t, i) => `<line x1="${x(t).toFixed(1)}" x2="${x(t).toFixed(1)}" y1="14" y2="${H - 20}" stroke="#dde3ea" stroke-width=".8"/>`
    + (i % step ? "" : `<text x="${(x(t) + 2).toFixed(1)}" y="${H - 6}" font-size="10" fill="#5b6573">${esc(new Date(t).toLocaleDateString("th-TH", { ...TZ, day: "numeric", month: "short" }))}</text>`)).join("");
}

function chartSVG(obs, fc, bank) {
  const W = 400, H = 200, P = 34, GAP_MS = 90 * 60e3;  // gaps longer than 90 min are not bridged
  const pts = obs.filter((o) => o[1] != null).map((o) => [Date.parse(o[0]), o[1]]);
  if (pts.length < 2) return "<p class='muted'>ข้อมูลย้อนหลังไม่พอสำหรับกราฟ</p>";
  const t0 = pts[pts.length - 1][0];
  const band = (fc?.path || []).filter((p) => p.q).map((p) => [t0 + p.h * 3600e3, p.q]);
  const ys = pts.map((p) => p[1]).concat(band.flatMap((b) => [b[1][0], b[1][4]]), bank != null ? [bank] : []);
  const ymin = Math.min(...ys) - 0.1, ymax = Math.max(...ys) + 0.1;
  const tmin = pts[0][0], tmax = band.length ? band[band.length - 1][0] : t0;
  const x = (t) => P + ((t - tmin) / (tmax - tmin || 1)) * (W - P - 6);
  const y = (v) => H - 20 - ((v - ymin) / (ymax - ymin || 1)) * (H - 30);
  const line = pts.map((p, i) => `${i && p[0] - pts[i - 1][0] <= GAP_MS ? "L" : "M"}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
  const area = (lo, hi) => band.length ? `M${band.map((b) => `${x(b[0]).toFixed(1)},${y(b[1][lo]).toFixed(1)}`).join("L")}L${band.slice().reverse().map((b) => `${x(b[0]).toFixed(1)},${y(b[1][hi]).toFixed(1)}`).join("L")}Z` : "";
  const med = band.length ? `M${x(t0)},${y(pts[pts.length - 1][1])}` + band.map((b) => `L${x(b[0]).toFixed(1)},${y(b[1][2]).toFixed(1)}`).join("") : "";
  const bankLine = bank != null ? `<line x1="${P}" x2="${W - 6}" y1="${y(bank)}" y2="${y(bank)}" stroke="#c62828" stroke-dasharray="5 4"/><text x="${W - 8}" y="${y(bank) - 4}" text-anchor="end" font-size="11" fill="#c62828">ตลิ่ง ${bank.toFixed(2)}</text>` : "";
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="กราฟระดับน้ำย้อนหลังและคาดการณ์">
    <text x="4" y="${y(ymax - 0.1) + 4}" font-size="10" fill="#5b6573">${(ymax - 0.1).toFixed(2)}</text>
    <text x="4" y="${y(ymin + 0.1)}" font-size="10" fill="#5b6573">${(ymin + 0.1).toFixed(2)}</text>
    ${band.length ? `<path d="${area(0, 4)}" fill="#1565c0" opacity=".12"/><path d="${area(1, 3)}" fill="#1565c0" opacity=".22"/>` : ""}
    ${bankLine}<path d="${line}" fill="none" stroke="#0d3b66" stroke-width="1.6"/>
    ${med ? `<path d="${med}" fill="none" stroke="#1565c0" stroke-width="1.6" stroke-dasharray="4 3"/>` : ""}
    ${dayTicks(tmin, tmax, x, H)}
    <line x1="${x(t0)}" x2="${x(t0)}" y1="8" y2="${H - 20}" stroke="#555" stroke-width=".8"/>
    <text x="${x(t0)}" y="9" font-size="10" text-anchor="middle" fill="#333" font-weight="600">ตอนนี้</text></svg>
    <p class="muted">เส้นทึบ = ค่าตรวจวัด (ช่วงที่ขาดหายไม่ได้ลากเส้นเชื่อม) · เส้นประน้ำเงิน = ค่ากลางคาดการณ์ · แถบเข้ม/อ่อน = ช่วง 50%/90% · หน่วย ม.รทก.</p>`;
}

/* ---------- texts ---------- */
function recoveryText(rec) {
  if (!rec) return "";
  const at = (h) => fmtTime(new Date(Date.now() + h * 3600e3).toISOString());
  switch (rec.state) {
    case "forecast":
      return `⏱️ คาดว่าจะลดต่ำกว่าตลิ่ง: ประมาณ ${at(rec.hours_min)} – ${rec.hours_max ? at(rec.hours_max) : "หลัง 72 ชม."} <span class="muted">(หากไม่มีฝนตกหนักเพิ่ม)</span>`;
    case "extrapolated":
      return `⏱️ หากน้ำลดในอัตราเดิม อาจต่ำกว่าตลิ่งราว ${at(rec.hours_min)} – ${at(rec.hours_max)} <span class="muted">(ประมาณจากอัตราลดลง 24 ชม.ล่าสุด ความเชื่อมั่นต่ำ หากไม่มีฝนตกหนักเพิ่ม)</span>`;
    case "not_estimable":
      return rec.reason === "heavy_rain_forecast"
        ? `⏱️ ยังประเมินเวลาน้ำลดไม่ได้ — คาดว่ามีฝน ~${Math.round(rec.rain_next24_mm)} มม. ใน 24 ชม.`
        : "⏱️ ยังประเมินเวลาน้ำลดไม่ได้ (น้ำยังไม่ลดลง)";
    default: return "";
  }
}

function outlookText(fc, s) {
  const o = fc?.outlook24;
  if (!o) return "";
  const parts = [];
  if (o.varies && fc.issue_time) {
    const tp = Date.parse(fc.issue_time) + o.peak_h * 3600e3;
    parts.push(`ระดับสูงสุดใน 24 ชม. ข้างหน้า ช่วงประมาณ <b>${esc(fmtHour(tp - 3600e3))}–${esc(fmtHour(tp + 3600e3))} น.</b>
      ที่ราว ${o.peak_q[1].toFixed(2)}–${o.peak_q[3].toFixed(2)} ม.รทก.`);
  }
  if (o.bank_chance && s.status !== "critical") parts.push(`โอกาสที่น้ำจะถึงระดับตลิ่งใน 24 ชม.: <b>${esc(CHANCE[o.bank_chance] || o.bank_chance)}</b>`);
  return parts.length ? `<div class="box">🔭 ${parts.join("<br>")}</div>` : "";
}

function feedbackCounts(fb) {
  if (!fb || !fb.n) return "";
  const v = fb.verdict || {};
  const txt = Object.keys(VERDICT).filter((k) => v[k]).map((k) => `${VERDICT[k]} ${Number(v[k])}`).join(" · ");
  return `<p class="muted">ความเห็นผู้ใช้ 7 วัน: ${esc(txt || `${Number(fb.n)} รายการ`)}${fb.review ? " · ⚠️ ผู้ใช้หลายคนรายงานว่าไม่ตรง ทีมงานกำลังตรวจสอบ" : ""}</p>`;
}

function feedbackForm(code, loc) {
  return `<form class="feedback" data-code="${esc(code || "")}"${loc ? ` data-lat="${loc.lat}" data-lon="${loc.lon}" data-src="${esc(loc.src)}"` : ""}>
    <strong>${code ? "ข้อมูลนี้ตรงกับที่คุณเห็นไหม?" : "รายงานน้ำที่จุดของคุณ"}</strong>
    ${code ? `<div class="opts">${Object.entries(VERDICT).map(([k, t]) => `<button type="button" class="btn" data-verdict="${k}" aria-pressed="false">${t}</button>`).join("")}</div>` : ""}
    <label>น้ำที่จุดของคุณตอนนี้ (ไม่บังคับ)
      <select name="depth"><option value="">— ไม่ระบุ —</option>${Object.entries(DEPTH).map(([k, t]) => `<option value="${k}">${t}</option>`).join("")}</select></label>
    <label>ข้อมูลเพิ่มเติม (ไม่บังคับ, ไม่เกิน 280 ตัวอักษร)
      <textarea name="note" maxlength="280" placeholder="เช่น น้ำเริ่มเอ่อจากท่อในซอย / ประตูระบายน้ำปิด"></textarea></label>
    <label><input type="checkbox" name="loc"${loc ? " checked" : ""}> แนบตำแหน่ง${loc ? (loc.src === "pin" ? "ของหมุดนี้" : "ของคุณ") : ""}โดยประมาณ (ปัดเป็น ~100 ม.)</label>
    <input class="hp" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">
    <p class="muted">ไม่เก็บชื่อหรือเบอร์โทร · ข้อความไม่แสดงต่อสาธารณะ · ใช้ตรวจสอบและปรับปรุงการคาดการณ์เท่านั้น ·
      <b>ไม่ใช่ช่องทางขอความช่วยเหลือ</b> เหตุฉุกเฉินโทร 1784 / 1555</p>
    <button type="submit" class="btn primary">ส่งความเห็น</button> <span class="fb-msg muted" aria-live="polite"></span>
  </form>`;
}

function bindFeedback(form) {
  let verdict = null;
  form.querySelectorAll("[data-verdict]").forEach((b) => b.addEventListener("click", () => {
    verdict = verdict === b.dataset.verdict ? null : b.dataset.verdict;
    form.querySelectorAll("[data-verdict]").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.verdict === verdict)));
  }));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = form.querySelector(".fb-msg");
    const body = { code: form.dataset.code || null, verdict, depth: form.depth.value || null,
      note: form.note.value.trim() || null, website: form.website.value || null };
    if (!body.verdict && !body.depth && !body.note) { msg.textContent = "กรุณาเลือกอย่างน้อยหนึ่งข้อ"; return; }
    const send = async () => {
      try {
        const r = await getJSON("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        form.innerHTML = (r.urgent ? `<div class="urgent">🚨 หากมีผู้ตกอยู่ในอันตราย โทรทันที: <a href="tel:1669">1669</a> (เจ็บป่วยฉุกเฉิน) ·
          <a href="tel:1784">1784</a> (ปภ.) · <a href="tel:191">191</a> (ตำรวจ) — เว็บนี้ไม่มีเจ้าหน้าที่ตอบกลับหรือส่งความช่วยเหลือ</div>` : "")
          + "<p>🙏 ขอบคุณ ความเห็นของคุณช่วยให้การคาดการณ์แม่นยำขึ้น</p>";
      } catch (err) {
        msg.textContent = err.message === "429" ? "ส่งบ่อยเกินไป กรุณาลองใหม่ภายหลัง" : "ส่งไม่สำเร็จ กรุณาลองใหม่";
      }
    };
    if (form.loc.checked && form.dataset.lat) {
      body.lat = Number(form.dataset.lat); body.lon = Number(form.dataset.lon); body.loc_source = form.dataset.src;
      return send();
    }
    if (form.loc.checked) {
      const useLoc = (p) => { body.lat = p.lat; body.lon = p.lon; body.loc_source = "gps"; send(); };
      if (lastPos) return useLoc(lastPos);
      if (!navigator.geolocation) return send();
      msg.textContent = "กำลังหาตำแหน่ง…";
      navigator.geolocation.getCurrentPosition((pos) => useLoc({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => send(), { enableHighAccuracy: false, timeout: 10000 });
    } else send();
  });
}

/* ---------- detail sheet ---------- */
function closeDetail() {
  document.getElementById("sheet").hidden = true;
  if (location.hash) history.replaceState(null, "", location.pathname);
}

async function showDetail(code) {
  const sheet = document.getElementById("sheet"), box = document.getElementById("detail");
  sheet.hidden = false;
  box.innerHTML = "<p class='muted'>กำลังโหลด…</p>";
  history.replaceState(null, "", `#s=${encodeURIComponent(code)}`);
  try {
    const d = await getJSON(`/api/stations/${encodeURIComponent(code)}?days=5`);
    const s = d.station, st = STATUS[s.status] || STATUS.unknown, fc = d.forecast;
    const methods = fc ? [...new Set(Object.values(fc.skill || {}).map((k) => k.method))] : [];
    const skill12 = fc?.skill?.["12"];
    const bma = s.agency === "BMA", unit = bma ? "ม. (หมุด กทม.)" : "ม.รทก.";  // BMA datum unverified vs HII (KI-217)
    box.innerHTML = `<div class="tools"><button class="btn share" aria-label="แชร์">🔗 แชร์</button><button class="btn close" aria-label="ปิด">✕</button></div>
      <h2 id="sheet-title">${esc(s.name_th)} <span class="muted">${esc(s.code)}</span></h2>
      <div class="muted">${esc(s.river || "")} · ${esc(s.amphoe || "")} ${esc(s.province || "")} · ${esc(s.agency || "")}</div>
      <p class="headline" style="color:${st.color}">${esc(st.long)}${s.freeboard_m != null ? ` · ${esc(freeboardText(s.freeboard_m))}` : ""}</p>
      <p class="muted">ระดับน้ำ ${s.level_msl?.toFixed(2) ?? "-"} ${unit} · ตลิ่ง ${s.bank_msl?.toFixed(2) ?? "ไม่ทราบ"} ${unit} ·
        ข้อมูล ${esc(fmtTime(s.obs_time))} (${esc(fmtAge(s.age_min))})${s.stale ? " ⚠️ ข้อมูลเก่า แหล่งข้อมูลอาจขัดข้องชั่วคราว" : ""}</p>
      ${notesText(s) ? `<div class="warnbox">ℹ️ ${esc(notesText(s))}</div>` : ""}
      ${bma ? `<div class="warnbox">ℹ️ สถานีของสำนักการระบายน้ำ กทม. ดึงผ่านเว็บ <a href="https://flood69.peoplesparty.or.th/#klong" target="_blank" rel="noopener">flood69 (พรรคประชาชน)</a> ซึ่งสำเนาข้อมูล กทม. ทุก 5 นาที ·
        ระดับอ้างอิงของ กทม. อาจต่างจากสถานี สสน. ที่อยู่ใกล้กัน 30–60 ซม. จึงเทียบกับตลิ่งของสถานีนี้เท่านั้น · ประวัติย้อนหลังเริ่มเก็บ 26 ก.ย.</div>` : ""}
      <p class="big">${esc(TREND[s.trend12] || TREND.unknown)}${s.delta12_median != null ? ` <span class="muted">(ค่ากลาง ${esc(cm(s.delta12_median))} ใน 12 ชม.)</span>` : ""}</p>
      ${outlookText(fc, s)}
      <p>${recoveryText(s.recovery)}</p>
      ${chartSVG(d.observations, fc, s.bank_msl)}
      <p class="muted">วิธีคาดการณ์: ${esc(methods.join(", ") || "ข้อมูลไม่พอ")}${skill12 ? ` · ที่ 12 ชม. ทดสอบย้อนหลัง ${skill12.n} ครั้ง` : ""}${fc && !fc.tide_fitted ? " · ยังไม่มีข้อมูลพอสำหรับคำนวณน้ำขึ้นน้ำลง" : ""}
        · ตลิ่งของสถานีอาจไม่เท่ากับระดับถนนหรือบ้านของคุณ</p>
      ${feedbackCounts(d.feedback7d)}
      ${feedbackForm(s.code)}`;
    box.querySelector(".close").addEventListener("click", closeDetail);
    box.querySelector(".share").addEventListener("click", () => share(s));
    bindFeedback(box.querySelector(".feedback"));
    if (s.lat && map) map.setView([s.lat, s.lon], 11);
    sheet.scrollTop = 0;
  } catch (e) {
    box.innerHTML = `<div class="tools"><button class="btn close" aria-label="ปิด">✕</button></div><p>โหลดข้อมูลไม่สำเร็จ (${esc(e.message)})</p>`;
    box.querySelector(".close").addEventListener("click", closeDetail);
  }
}

async function share(s) {
  const url = `${location.origin}/#s=${encodeURIComponent(s.code)}`;
  const text = `${s.name_th}: ${STATUS[s.status]?.long || ""} ${freeboardText(s.freeboard_m)} (BKK FloodWatch)`;
  try {
    if (navigator.share) await navigator.share({ title: "BKK FloodWatch", text, url });
    else { await navigator.clipboard.writeText(`${text} ${url}`); document.querySelector(".share").textContent = "✔ คัดลอกแล้ว"; }
  } catch (_) { /* user cancelled */ }
}

/* ---------- point check: a place with no gauge (D-021) ---------- */
const WARN = {
  no_gauge_at_point: "นี่<b>ไม่ใช่ระดับน้ำที่จุดนี้</b> สถานีวัดน้ำในคลองหรือแม่น้ำ ไม่ได้วัดบนถนนหรือในบ้าน",
  terrain_not_flat: "กรุงเทพฯ สูงต่ำไม่เท่ากัน จุดที่อยู่ใกล้กันอาจท่วมไม่เท่ากัน",
  walls_and_polders: "คันกั้นน้ำและประตูระบายน้ำแบ่งพื้นที่ ถ้าอยู่นอกคันริมแม่น้ำให้ดูสถานี “แม่น้ำ” ถ้าอยู่ด้านในให้ดูสถานี “คลอง”",
  gauges_far_or_disagree: "สถานีรอบ ๆ อยู่ไกลหรือให้ผลต่างกันมาก ใช้ประกอบเท่านั้น",
  nearest_gauge_far: "สถานีที่ใกล้ที่สุดอยู่ห่างเกิน 3 กม.",
};
const CONF = { medium: "ปานกลาง", low: "ต่ำ", very_low: "ต่ำมาก", none: "ประเมินไม่ได้" };
let pinMarker = null;

function pointHTML(d, src, place = "") {
  const a = d.area, ev = d.evidence;
  const area = a.category && a.confidence === "very_low"
    ? `<div class="box">ข้อมูลรอบจุดนี้<b>น้อยหรือขัดกัน</b> จึงไม่สรุปสภาพพื้นที่ · สถานีในรัศมี 8 กม. (${a.n} สถานี, ใกล้สุด ${a.nearest_km} กม.)
        อยู่ระหว่าง “${esc(STATUS[a.min].th)}” ถึง “${esc(STATUS[a.max].th)}” — ดูรายสถานีด้านล่างและรายงานจากประชาชนประกอบ</div>`
    : a.category
    ? `<div class="box">สภาพน้ำในคลอง/แม่น้ำ<b>รอบ</b>จุดนี้: <b style="color:${STATUS[a.category].color}">${esc(STATUS[a.category].long)}</b>
        <br><span class="muted">จาก ${a.n} สถานีในรัศมี 8 กม. (ใกล้สุด ${a.nearest_km} กม.) · สถานีรอบ ๆ อยู่ระหว่าง
        “${esc(STATUS[a.min].th)}” ถึง “${esc(STATUS[a.max].th)}” · ความเชื่อมั่น: ${esc(CONF[a.confidence])}</span></div>`
    : `<div class="box">ไม่มีสถานีที่ส่งข้อมูลล่าสุดในรัศมี 8 กม. — <b>ประเมินสภาพน้ำรอบจุดนี้ไม่ได้</b></div>`;
  const depths = Object.entries(ev.user_depth_reports_1km_24h || {}).map(([k, n]) => `${esc(DEPTH[k] || k)} ${Number(n)}`).join(" · ");
  return `<h2 id="sheet-title">${src === "gps" ? "📍 ตำแหน่งของคุณ" : place ? `📌 ${esc(place)}` : "📌 จุดที่เลือก"} <span class="muted">${d.lat}, ${d.lon}</span></h2>
    ${area}
    <div class="warnbox">${d.warnings.map((w) => `⚠️ ${WARN[w] || esc(w)}`).join("<br>")}</div>
    <p>👥 รอบจุดนี้ (~1 กม.): รายงานน้ำท่วม Traffy ${Number(ev.traffy_flood_reports_1km_6h)} เรื่องใน 6 ชม.
      ${depths ? ` · ผู้ใช้รายงานใน 24 ชม.: ${depths}` : " · ยังไม่มีผู้ใช้รายงานใน 24 ชม."}</p>
    ${d.rain_next24_mm != null ? `<p>🌧️ ฝนคาดการณ์ 24 ชม. บริเวณนี้ ~${Math.round(d.rain_next24_mm)} มม. <span class="muted">(Open-Meteo, ความละเอียดหยาบ)</span></p>` : ""}
    <p>🚗 ถนนที่ กทม. แจ้งให้เลี่ยง: <a href="https://claude.ai/artifact/N6umcENfSgoY6GMkhVKwZs" target="_blank" rel="noopener">หน้าของ กทม.</a> <span class="muted">(อัปเดตเป็นรอบ ตำแหน่งโดยประมาณ)</span></p>
    <strong>สถานีใกล้จุดนี้</strong>
    <ul class="list">${d.stations.map((s) => itemHTML(s, `<div class="meta">ห่าง ${esc(s.distance_km)} กม. · ${s.water_body === "river" ? "สถานีแม่น้ำ" : "สถานีคลอง"}</div>`)).join("") || "<li class='muted'>ไม่มีสถานีในรัศมี 15 กม.</li>"}</ul>
    ${feedbackForm(null, { lat: d.lat, lon: d.lon, src })}`;
}

async function checkPoint(lat, lon, src, place = "") {
  const sheet = document.getElementById("sheet"), box = document.getElementById("detail");
  sheet.hidden = false;
  box.innerHTML = "<p class='muted'>กำลังโหลด…</p>";
  if (src === "pin") history.replaceState(null, "", `#p=${lat.toFixed(4)},${lon.toFixed(4)}`);  // shareable, ~10 m
  if (map) {
    if (pinMarker) pinMarker.remove();
    pinMarker = L.marker([lat, lon], { title: src === "gps" ? "ตำแหน่งของคุณ" : "จุดที่เลือก" }).addTo(map);
  }
  try {
    const d = await getJSON(`/api/point?lat=${lat.toFixed(5)}&lon=${lon.toFixed(5)}`);
    box.innerHTML = `<div class="tools"><button class="btn close" aria-label="ปิด">✕</button></div>${pointHTML(d, src, place)}${place ? `<p class="muted">ตำแหน่งจากชื่อสถานที่ (OpenStreetMap) อาจคลาดเคลื่อนได้ แตะบนแผนที่เพื่อเลือกจุดที่ตรงกว่า</p>` : ""}`;
    bindItems(box);
    bindFeedback(box.querySelector(".feedback"));
  } catch (e) {
    box.innerHTML = `<div class="tools"><button class="btn close" aria-label="ปิด">✕</button></div><p>โหลดข้อมูลไม่สำเร็จ (${esc(e.message)})</p>`;
  }
  box.querySelector(".close").addEventListener("click", closeDetail);
  sheet.scrollTop = 0;
}

/* ---------- near me ---------- */
function locate() {
  const out = document.getElementById("near");
  if (!navigator.geolocation) { out.innerHTML = "<p class='muted'>อุปกรณ์ไม่รองรับการระบุตำแหน่ง แตะบนแผนที่เพื่อเลือกจุดแทนได้</p>"; return; }
  out.innerHTML = "<p class='muted'>กำลังหาตำแหน่ง…</p>";
  navigator.geolocation.getCurrentPosition((pos) => {
    lastPos = { lat: pos.coords.latitude, lon: pos.coords.longitude };
    out.innerHTML = "";
    if (map) map.setView([lastPos.lat, lastPos.lon], 12);
    checkPoint(lastPos.lat, lastPos.lon, "gps");
  }, () => { out.innerHTML = "<p class='muted'>ไม่ได้รับอนุญาตให้ใช้ตำแหน่ง แตะบนแผนที่เพื่อเลือกจุดแทนได้</p>"; }, { enableHighAccuracy: false, timeout: 10000 });
}

/* ---------- tabs ---------- */
function setTab(tab) {
  document.body.dataset.tab = tab;
  document.querySelectorAll(".tabs [data-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tab)));
  document.getElementById("view-list").hidden = tab === "river";
  document.getElementById("view-river").hidden = tab !== "river";
  if (tab === "river") renderRiver();
  if (tab === "map" && map) setTimeout(() => map.invalidateSize(), 50);
}

async function load() {
  try {
    const [d, st] = await Promise.all([getJSON("/api/stations?scope=focus"), getJSON("/api/stats").catch(() => null)]);
    stations = d.stations;
    const latest = stations.map((s) => s.obs_time).filter(Boolean).sort().pop();
    document.getElementById("updated").textContent = `ข้อมูลล่าสุด ${fmtTime(latest)} · ${stations.length} สถานี`;
    if (st) {
      renderSummary(st);
      document.querySelectorAll(".ver").forEach((e) => { e.textContent = `v${st.version}`; });
    }
    renderMap();
    renderList();
  } catch (e) {
    document.getElementById("updated").textContent = "โหลดข้อมูลไม่สำเร็จ กรุณาลองใหม่";
  }
}

function openFromHash() {
  const m = location.hash.match(/^#s=([^&]+)/);
  if (m) return showDetail(decodeURIComponent(m[1]));
  const p = location.hash.match(/^#p=(-?[\d.]+),(-?[\d.]+)/);
  if (p) checkPoint(Number(p[1]), Number(p[2]), "pin");
}

document.getElementById("q").addEventListener("input", renderList);
document.getElementById("q").addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); const v = e.target.value.trim(); if (v.length >= 2) placeSearch(v); }
});
document.getElementById("gps").addEventListener("click", locate);
document.querySelectorAll(".tabs [data-tab]").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.tab)));
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDetail(); });
window.addEventListener("hashchange", openFromHash);
const setTopH = () => document.documentElement.style.setProperty("--top-h", `${document.querySelector(".top").offsetHeight}px`);
window.addEventListener("resize", setTopH);
setTopH();
setTab("list");
load().then(openFromHash);
setInterval(load, 5 * 60 * 1000);
