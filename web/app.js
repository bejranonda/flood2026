"use strict";
// BKK FloodWatch MVP frontend. Talks only to our API (D-001). All external strings are escaped.

const STATUS = {
  normal: { th: "ปกติ", color: "#2e9d5b" },
  watch: { th: "เฝ้าระวัง", color: "#d9a400" },
  warning: { th: "เตือนภัย (ใกล้ตลิ่ง)", color: "#e46c0a" },
  critical: { th: "วิกฤต (ล้นตลิ่ง)", color: "#c62828" },
  unknown: { th: "ไม่ทราบ", color: "#8a94a3" },
};
const TREND = { rising: "📈 มีแนวโน้มเพิ่มขึ้น", falling: "📉 มีแนวโน้มลดลง", steady: "➖ ทรงตัว", unknown: "ยังไม่มีข้อมูลพอสำหรับคาดการณ์" };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtTime = (iso) => iso ? new Date(iso).toLocaleString("th-TH", { timeZone: "Asia/Bangkok", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "-";
const fmtAge = (m) => m == null ? "-" : m < 60 ? `${Math.round(m)} นาทีที่แล้ว` : m < 1440 ? `${Math.round(m / 60)} ชม.ที่แล้ว` : `${Math.round(m / 1440)} วันที่แล้ว`;
const cm = (m) => m == null ? "-" : `${m > 0 ? "+" : ""}${Math.round(m * 100)} ซม.`;

let stations = [];
let map, layer;

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

function recoveryText(rec, s) {
  if (!rec) return "";
  const at = (h) => fmtTime(new Date(Date.now() + h * 3600e3).toISOString());
  switch (rec.state) {
    case "below_bank": return "✅ ขณะนี้ระดับน้ำต่ำกว่าตลิ่ง";
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

function itemHTML(s) {
  const st = STATUS[s.status] || STATUS.unknown;
  const fb = s.freeboard_m == null ? "" : s.freeboard_m < 0 ? `สูงกว่าตลิ่ง ${Math.abs(Math.round(s.freeboard_m * 100))} ซม.` : `ต่ำกว่าตลิ่ง ${Math.round(s.freeboard_m * 100)} ซม.`;
  return `<li class="item s-${esc(s.status)} ${s.stale ? "stale" : ""}" data-code="${esc(s.code)}">
    <div class="row"><span class="name">${esc(s.name_th)} <span class="muted">${esc(s.code)}</span></span>
    <span class="badge b-${esc(s.status)}">${esc(st.th)}</span></div>
    <div class="meta">${esc(s.amphoe || "")} ${esc(s.province || "")} · ${s.level_msl?.toFixed(2) ?? "-"} ม.รทก. ${esc(fb)}</div>
    <div class="meta">${esc(TREND[s.trend12] || TREND.unknown)}${s.delta12_median != null && s.trend12 !== "steady" ? " " + esc(cm(s.delta12_median)) + " ใน 12 ชม." : ""}
      · ข้อมูล ${esc(fmtAge(s.age_min))}${s.stale ? " ⚠️ ข้อมูลเก่า" : ""}</div></li>`;
}

function renderList() {
  const f = document.getElementById("filter").value;
  const rank = { critical: 0, warning: 1, watch: 2, normal: 3, unknown: 4 };
  const rows = stations.filter((s) => f === "all" || ["critical", "warning", "watch"].includes(s.status))
    .sort((a, b) => (rank[a.status] - rank[b.status]) || ((a.freeboard_m ?? 99) - (b.freeboard_m ?? 99)));
  const ul = document.getElementById("list");
  ul.innerHTML = rows.map(itemHTML).join("") || "<li class='muted'>ไม่มีสถานีตามเงื่อนไข</li>";
  ul.querySelectorAll(".item").forEach((li) => li.addEventListener("click", () => showDetail(li.dataset.code)));
}

function renderMap() {
  if (!map) {
    map = L.map("map", { zoomControl: true }).setView([13.95, 100.55], 9);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap" }).addTo(map);
  }
  if (layer) layer.remove();
  layer = L.layerGroup().addTo(map);
  getJSON("/api/reports?hours=6").then((r) => r.cells.forEach(([lat, lon, n]) => {
    L.circle([lat, lon], { radius: 300 + 120 * Math.min(n, 20), color: "#7b1fa2", weight: 0, fillOpacity: 0.18 })
      .bindTooltip(`รายงานน้ำท่วมจากประชาชน ${Number(n)} รายการ ใน 6 ชม. (Traffy Fondue)`).addTo(layer);
  })).catch(() => {});
  stations.filter((s) => s.lat && s.lon).forEach((s) => {
    const st = STATUS[s.status] || STATUS.unknown;
    L.circleMarker([s.lat, s.lon], { radius: s.status === "critical" ? 9 : 7, color: "#fff", weight: 1.5, fillColor: st.color, fillOpacity: s.stale ? 0.45 : 0.95 })
      .bindTooltip(`${esc(s.name_th)} (${esc(s.code)}) — ${esc(st.th)}`)
      .on("click", () => showDetail(s.code)).addTo(layer);
  });
}

function chartSVG(obs, fc, bank) {
  const W = 400, H = 200, P = 34;
  const pts = obs.filter((o) => o[1] != null).map((o) => [Date.parse(o[0]), o[1]]);
  if (pts.length < 2) return "<p class='muted'>ข้อมูลย้อนหลังไม่พอสำหรับกราฟ</p>";
  const t0 = pts[pts.length - 1][0];
  const band = (fc?.path || []).filter((p) => p.q).map((p) => [t0 + p.h * 3600e3, p.q]);
  const ys = pts.map((p) => p[1]).concat(band.flatMap((b) => [b[1][0], b[1][4]]), bank != null ? [bank] : []);
  const ymin = Math.min(...ys) - 0.1, ymax = Math.max(...ys) + 0.1;
  const tmin = pts[0][0], tmax = band.length ? band[band.length - 1][0] : t0;
  const x = (t) => P + ((t - tmin) / (tmax - tmin || 1)) * (W - P - 6);
  const y = (v) => H - 20 - ((v - ymin) / (ymax - ymin || 1)) * (H - 30);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
  const area = (lo, hi) => band.length ? `M${band.map((b) => `${x(b[0]).toFixed(1)},${y(b[1][lo]).toFixed(1)}`).join("L")}L${band.slice().reverse().map((b) => `${x(b[0]).toFixed(1)},${y(b[1][hi]).toFixed(1)}`).join("L")}Z` : "";
  const med = band.length ? `M${x(t0)},${y(pts[pts.length - 1][1])}` + band.map((b) => `L${x(b[0]).toFixed(1)},${y(b[1][2]).toFixed(1)}`).join("") : "";
  const bankLine = bank != null ? `<line x1="${P}" x2="${W - 6}" y1="${y(bank)}" y2="${y(bank)}" stroke="#c62828" stroke-dasharray="5 4"/><text x="${W - 8}" y="${y(bank) - 4}" text-anchor="end" font-size="11" fill="#c62828">ตลิ่ง ${bank.toFixed(2)}</text>` : "";
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="กราฟระดับน้ำ">
    <text x="4" y="${y(ymax - 0.1) + 4}" font-size="10" fill="#5b6573">${(ymax - 0.1).toFixed(2)}</text>
    <text x="4" y="${y(ymin + 0.1)}" font-size="10" fill="#5b6573">${(ymin + 0.1).toFixed(2)}</text>
    ${band.length ? `<path d="${area(0, 4)}" fill="#1565c0" opacity=".12"/><path d="${area(1, 3)}" fill="#1565c0" opacity=".22"/>` : ""}
    ${bankLine}<path d="${line}" fill="none" stroke="#0d3b66" stroke-width="1.6"/>
    ${med ? `<path d="${med}" fill="none" stroke="#1565c0" stroke-width="1.6" stroke-dasharray="4 3"/>` : ""}
    <line x1="${x(t0)}" x2="${x(t0)}" y1="8" y2="${H - 20}" stroke="#999" stroke-width=".6"/>
    <text x="${x(t0) + 3}" y="${H - 6}" font-size="10" fill="#5b6573">ตอนนี้</text></svg>
    <p class="muted">เส้นทึบ = ค่าตรวจวัด · เส้นประน้ำเงิน = ค่ากลางคาดการณ์ · แถบเข้ม/อ่อน = ช่วง 50%/90% · หน่วย ม.รทก.</p>`;
}

async function showDetail(code) {
  const box = document.getElementById("detail");
  box.hidden = false;
  box.innerHTML = "<p class='muted'>กำลังโหลด…</p>";
  try {
    const d = await getJSON(`/api/stations/${encodeURIComponent(code)}?days=5`);
    const s = d.station, st = STATUS[s.status] || STATUS.unknown, fc = d.forecast;
    const methods = fc ? [...new Set(Object.values(fc.skill || {}).map((k) => k.method))] : [];
    const skill12 = fc?.skill?.["12"];
    box.innerHTML = `<button class="btn close" aria-label="ปิด">✕</button>
      <h2>${esc(s.name_th)} <span class="muted">${esc(s.code)}</span></h2>
      <div class="muted">${esc(s.river || "")} · ${esc(s.amphoe || "")} ${esc(s.province || "")} · ${esc(s.agency || "")}</div>
      <p class="big"><span class="badge b-${esc(s.status)}">${esc(st.th)}</span>
        ${s.level_msl?.toFixed(2) ?? "-"} ม.รทก. (ตลิ่ง ${s.bank_msl?.toFixed(2) ?? "-"})</p>
      <p>ข้อมูลล่าสุด ${esc(fmtTime(s.obs_time))} (${esc(fmtAge(s.age_min))})${s.stale ? " ⚠️ ข้อมูลเก่า แหล่งข้อมูลอาจขัดข้องชั่วคราว" : ""}</p>
      <p class="big">${esc(TREND[s.trend12] || TREND.unknown)}${s.delta12_median != null ? ` <span class="muted">(ค่ากลาง ${esc(cm(s.delta12_median))} ใน 12 ชม.)</span>` : ""}</p>
      <p>${recoveryText(s.recovery, s)}</p>
      ${chartSVG(d.observations, fc, s.bank_msl)}
      <p class="muted">วิธีคาดการณ์: ${esc(methods.join(", ") || "ข้อมูลไม่พอ")}${skill12 ? ` · ที่ 12 ชม. ทดสอบย้อนหลัง ${skill12.n} ครั้ง` : ""}${fc && !fc.tide_fitted ? " · ยังไม่มีข้อมูลพอสำหรับคำนวณน้ำขึ้นน้ำลง" : ""}</p>`;
    box.querySelector(".close").addEventListener("click", () => { box.hidden = true; });
    if (s.lat && map) map.setView([s.lat, s.lon], 11);
    box.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    box.innerHTML = `<p>โหลดข้อมูลไม่สำเร็จ (${esc(e.message)})</p>`;
  }
}

function locate() {
  const out = document.getElementById("near");
  if (!navigator.geolocation) { out.innerHTML = "<p class='muted'>อุปกรณ์ไม่รองรับการระบุตำแหน่ง</p>"; return; }
  out.innerHTML = "<p class='muted'>กำลังหาตำแหน่ง…</p>";
  navigator.geolocation.getCurrentPosition(async (pos) => {
    const { latitude: lat, longitude: lon } = pos.coords;
    const d = await getJSON(`/api/near?lat=${lat}&lon=${lon}&n=3`);
    out.innerHTML = `<div class="near-box"><strong>สถานีใกล้คุณ</strong> <span class="muted">(ตามระยะทาง ยังไม่ได้พิจารณาแนวคันกั้นน้ำ/พื้นที่ปิดล้อม)</span>
      <ul class="list">${d.stations.map((s) => itemHTML(s).replace("</li>", `<div class="meta">ห่าง ${s.distance_km} กม.</div></li>`)).join("")}</ul></div>`;
    out.querySelectorAll(".item").forEach((li) => li.addEventListener("click", () => showDetail(li.dataset.code)));
    if (map) { L.circleMarker([lat, lon], { radius: 6, color: "#1565c0" }).addTo(map).bindTooltip("ตำแหน่งของคุณ"); map.setView([lat, lon], 11); }
  }, () => { out.innerHTML = "<p class='muted'>ไม่ได้รับอนุญาตให้ใช้ตำแหน่ง</p>"; }, { enableHighAccuracy: false, timeout: 10000 });
}

async function load() {
  try {
    const d = await getJSON("/api/stations?scope=focus");
    stations = d.stations;
    const latest = stations.map((s) => s.obs_time).filter(Boolean).sort().pop();
    const crit = stations.filter((s) => s.status === "critical").length;
    document.getElementById("updated").textContent = `ข้อมูลล่าสุด ${fmtTime(latest)} · ${stations.length} สถานี · ล้นตลิ่ง ${crit} สถานี`;
    renderMap();
    renderList();
  } catch (e) {
    document.getElementById("updated").textContent = "โหลดข้อมูลไม่สำเร็จ กรุณาลองใหม่";
  }
}

document.getElementById("filter").addEventListener("change", renderList);
document.getElementById("gps").addEventListener("click", locate);
load();
setInterval(load, 5 * 60 * 1000);
