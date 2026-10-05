/* 💧 ผลกระทบ — the impact tab of the main app, served at /impact (owner 2026-10-05; D-099, D-100).
   Login inside the tab; then the national dams layer (risk) and the cases (impact; Kaeng Krachan first), drawn on the
   main map through app.js's two hooks (window.FW_TABS, the "fw:map" event). Data only from /api/impact/* after login.
   Every outside string is escaped; styles by class only. */
"use strict";
(function () {
  const view = document.getElementById("view-impact");
  if (!view) return;
  const $ = (s, el) => (el || document).querySelector(s);
  const AGENCY = { RID: "ชป.", HII: "สสน.", EGAT: "กฟผ." };
  const POS = { above: ["เหนือเส้นควบคุมบน", "imp-above"], between: ["อยู่ระหว่างเส้นควบคุม", "imp-between"],
    below: ["ต่ำกว่าเส้นควบคุมล่าง", "imp-below"] };
  const METHODS = [["keep", "คงระดับวันนี้"], ["absolute", "สมดุลมวล + rating curve"],
    ["anchored", "ระดับวันนี้ + ส่วนต่างจาก rating"], ["gain", "ระดับวันนี้ + ค่าตอบสนองที่เรียนรู้"]];

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (x, d) => (x == null || !isFinite(x) ? "–"
    : Number(x).toLocaleString("th-TH", { minimumFractionDigits: d, maximumFractionDigits: d }));
  const toCms = (mcm) => (mcm * 1e6) / 86400;
  const when = (iso) => (iso ? new Date(iso).toLocaleString("th-TH", { timeZone: "Asia/Bangkok", day: "numeric",
    month: "short", year: "2-digit", hour: "2-digit", minute: "2-digit" }) + " น." : "–");
  const day = (ymd) => (ymd ? new Date(String(ymd).slice(0, 10) + "T12:00:00+07:00").toLocaleDateString("th-TH",
    { timeZone: "Asia/Bangkok", day: "numeric", month: "short", year: "2-digit" }) : "–");
  const agency = (a) => esc(AGENCY[a] || a || "");  // station metadata comes from outside APIs: always escaped
  const damName = (n) => esc(String(n || "").startsWith("เขื่อน") ? n : "เขื่อน" + (n || ""));
  const api = (path, opts) => fetch(path, Object.assign({ credentials: "same-origin", cache: "no-store" }, opts || {}));
  const narrow = () => window.innerWidth <= 800;

  const state = { authed: false, cases: [], dams: null, sel: "dams", kase: {} };
  const layers = { dams: null, kase: null };
  let damMarkers = [];
  // app.js's map: it may exist already (a classic script's top-level binding) or announce itself later
  let mapRef = (typeof map !== "undefined" && map) || null;
  document.addEventListener("fw:map", (e) => { mapRef = e.detail; drawDams(); if (state.sel !== "dams") drawCase(state.kase[state.sel]); });
  window.FW_TABS = Object.assign(window.FW_TABS || {}, { impact: { show } });

  // the header says which page this is, and offers logout once logged in
  const brand = $(".brand strong");
  if (brand) brand.insertAdjacentHTML("beforeend", ' <span class="imp-badge">เจ้าหน้าที่</span>');
  const top = $("header.top");
  if (top) top.insertAdjacentHTML("beforeend", '<button type="button" id="imp-logout" class="imp-logout" hidden>ออกจากระบบ</button>');
  $("#imp-logout").addEventListener("click", logout);

  function msg(text) { view.innerHTML = '<p class="imp-card">' + esc(text) + "</p>"; }

  async function show() {
    if (!state.authed && !(await loadAll())) return;
    render();
  }

  async function loadAll() {
    let r;
    try { r = await api("/api/impact/cases"); } catch (e) { msg("เชื่อมต่อไม่ได้ ลองใหม่อีกครั้ง"); return false; }
    if (r.status === 401) { showLogin(""); return false; }
    if (r.status === 503) { msg("หน้านี้ยังไม่ได้ตั้งค่า (ผู้ดูแลระบบต้องตั้งรหัสผ่านก่อน)"); return false; }
    if (!r.ok) { msg("โหลดข้อมูลไม่สำเร็จ (" + r.status + ")"); return false; }
    state.cases = (await r.json()).cases || [];
    state.authed = true;
    $("#imp-logout").hidden = false;
    try { const d = await api("/api/impact/dams"); state.dams = d.ok ? await d.json() : null; } catch (e) { state.dams = null; }
    drawDams();
    return true;
  }

  function showLogin(text) {
    $("#imp-logout").hidden = true;
    view.innerHTML = '<form id="imp-login" class="imp-card imp-login">' +
      "<h2>💧 ความเสี่ยงและผลกระทบ</h2>" +
      '<p class="muted">สำหรับเจ้าหน้าที่ที่ได้รับรหัสผ่าน · แท็บอื่นใช้ได้ตามปกติ</p>' +
      '<label for="imp-pw">รหัสผ่าน</label>' +
      '<input id="imp-pw" name="password" type="password" autocomplete="current-password" required maxlength="200">' +
      '<button class="btn primary" type="submit">เข้าสู่ระบบ</button>' +
      '<p class="imp-err" role="alert">' + esc(text) + "</p></form>";
    const f = $("#imp-login");
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      $("button", f).disabled = true;
      let r;
      try {
        r = await api("/api/impact/login", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: f.password.value }) });
      } catch (err) { return showLogin("เชื่อมต่อไม่ได้ ลองใหม่อีกครั้ง"); }
      if (r.ok) return show();
      showLogin(r.status === 429 ? "ใส่รหัสผิดหลายครั้ง กรุณารอ 15 นาทีแล้วลองใหม่"
        : r.status === 503 ? "หน้านี้ยังไม่ได้ตั้งค่า" : "รหัสผ่านไม่ถูกต้อง");
    });
  }

  async function logout() {
    try { await api("/api/impact/logout", { method: "POST" }); } catch (e) { /* the cookie expires by itself */ }
    state.authed = false; state.dams = null; state.kase = {}; state.sel = "dams";
    for (const k of Object.keys(layers)) { if (layers[k]) { layers[k].remove(); layers[k] = null; } }
    setTab("impact");
    showLogin("ออกจากระบบแล้ว");
  }

  function render() {
    const chips = ['<button type="button" class="rchip" data-imp="dams" aria-pressed="' + (state.sel === "dams") + '">🏞️ เขื่อนทั่วประเทศ</button>']
      .concat(state.cases.map((c) => '<button type="button" class="rchip" data-imp="' + esc(c.id) + '" aria-pressed="' +
        (state.sel === c.id) + '">' + damName(c.dam_name) + " (นำร่อง)</button>"));
    view.innerHTML = '<div class="imp"><p class="imp-head"><b>💧 ความเสี่ยงและผลกระทบ</b> ' +
      '<span class="muted">สำหรับเจ้าหน้าที่ · ข้อมูลสาธารณะ</span></p>' +
      '<div class="regions imp-chips" role="group" aria-label="เลือกเรื่อง">' + chips.join("") + '</div><div id="imp-body"></div></div>';
    view.querySelectorAll("[data-imp]").forEach((b) => b.addEventListener("click", () => { state.sel = b.dataset.imp; render(); }));
    if (state.sel === "dams") {
      if (layers.kase) { layers.kase.remove(); layers.kase = null; }
      renderDams();
    } else renderCase(state.sel);
  }

  /* ---------- national dams at risk ---------- */
  function renderDams() {
    const body = $("#imp-body"), d = state.dams;
    if (!d || !d.dams || !d.dams.length) { body.innerHTML = '<p class="muted">ยังไม่มีข้อมูลเขื่อน — ระบบคำนวณใหม่ทุกชั่วโมง</p>'; return; }
    const count = (p) => d.dams.filter((x) => x.position === p).length;
    const latest = d.dams.map((x) => (x.records[0] || {}).dam_date).filter(Boolean).sort().pop();
    body.innerHTML = '<p class="imp-sum">เขื่อนขนาดใหญ่ ' + num(d.dams.length, 0) + " แห่ง · เหนือเส้นควบคุมบน <b>" +
      num(count("above"), 0) + "</b> · ต่ำกว่าเส้นควบคุมล่าง " + num(count("below"), 0) + " · ข้อมูลรายวันจาก สสน. " + day(latest) + "</p>" +
      (d.curves < d.records ? '<p class="muted">เส้นควบคุมยังโหลดไม่ครบ (' + num(d.curves, 0) + " จาก " + num(d.records, 0) +
        " ระเบียน — ทยอยดึงจาก สสน. ชั่วโมงละไม่เกิน 10 ครั้ง)</p>" : "") +
      '<ul class="list imp-dams">' + d.dams.map(damItem).join("") + "</ul>" +
      '<p class="muted">ตำแหน่งเทียบเส้นควบคุมระดับน้ำ (rule curve) ของ สสน. ณ วันที่รายงาน — เป็นข้อเท็จจริง ไม่ใช่คำเตือน;' +
      " ชป. และ กฟผ. แสดงแยกกัน ไม่รวมตัวเลข</p>";
    body.querySelectorAll("[data-dam]").forEach((li) => li.addEventListener("click", (e) => {
      if (e.target.closest("[data-case]")) return;
      focusDam(Number(li.dataset.dam));
    }));
    body.querySelectorAll("[data-case]").forEach((b) => b.addEventListener("click", () => { state.sel = b.dataset.case; render(); }));
  }

  function recLine(r) {
    return '<span class="imp-rec">' + agency(r.agency) + " " + day(r.dam_date) + ": " + num(r.storage_pct, 0) + " % · ระบาย " +
      num(r.released_mcm, 2) + " ล้าน ลบ.ม./วัน" + (r.released_mcm == null ? "" : " (≈ " + num(toCms(r.released_mcm), 0) + " ลบ.ม./วินาที)") + "</span>";
  }

  function damItem(x, i) {
    const pos = POS[x.position];
    const note = x.records.map((r) => r.release_note).filter(Boolean)[0];
    return '<li class="item imp-dam ' + (pos ? pos[1] : "imp-unknown") + '" data-dam="' + i + '" tabindex="0">' +
      '<div class="imp-dam-head"><b>' + damName(x.name_th) + '</b><span class="imp-pos">' + (pos ? pos[0] : "ยังไม่มีเส้นควบคุม") +
      '</span></div><div class="meta">' + x.records.map(recLine).join("") + "</div>" +
      (note ? '<div class="imp-small">' + esc(note) + "</div>" : "") +
      (x.case ? '<button type="button" class="btn imp-case-btn" data-case="' + esc(x.case) + '">เปิดกรณีวิเคราะห์ ›</button>' : "") + "</li>";
  }

  function damPopup(x) {
    const pos = POS[x.position];
    return '<div class="imp-pop"><b>' + damName(x.name_th) + "</b>" + (pos ? '<div class="imp-pop-pos ' + pos[1] + '">' + pos[0] + "</div>" : "") +
      x.records.map((r) => '<div class="imp-pop-rec"><b>' + agency(r.agency) + "</b> · " + day(r.dam_date) +
        "<br>ปริมาตร " + num(r.storage_mcm, 0) + " ล้าน ลบ.ม. (" + num(r.storage_pct, 1) + " %)" +
        (r.rule ? "<br>เส้นควบคุมบน / ล่าง " + num(r.rule.upper, 0) + " / " + num(r.rule.lower, 0) : "") +
        "<br>ระบาย " + num(r.released_mcm, 2) + " ล้าน ลบ.ม./วัน" + (r.released_mcm == null ? "" : " ≈ " + num(toCms(r.released_mcm), 0) + " ลบ.ม./วินาที") +
        (r.inflow_mcm != null ? "<br>ไหลเข้า " + num(r.inflow_mcm, 2) + " ล้าน ลบ.ม./วัน" : "") +
        (r.release_note ? '<div class="imp-small">' + esc(r.release_note) + "</div>" : "") + "</div>").join("") +
      '<div class="muted">ที่มา: สสน. (ชป., กฟผ.)</div></div>';
  }

  function drawDams() {
    if (!mapRef || !state.authed || !state.dams || !state.dams.dams) return;
    if (!mapRef.getPane("impact")) mapRef.createPane("impact").style.zIndex = 660;  // above the gauges: dams stay tappable
    if (layers.dams) layers.dams.remove();
    layers.dams = L.layerGroup();
    damMarkers = state.dams.dams.map((x) => {
      const pos = POS[x.position];
      const icon = L.divIcon({ className: "imp-dam-icon " + (pos ? pos[1] : "imp-unknown"), html: "◆", iconSize: [20, 20] });
      return L.marker([x.lat, x.lon], { icon, pane: "impact", title: "เขื่อน" + x.name_th, keyboard: true })
        .bindPopup(damPopup(x), { maxWidth: 280 }).addTo(layers.dams);
    });
    layers.dams.addTo(mapRef);
  }

  function focusDam(i) {
    const x = state.dams && state.dams.dams[i];
    if (!mapRef || !x) return;
    if (narrow()) setTab("map");
    setTimeout(() => { mapRef.setView([x.lat, x.lon], 10); if (damMarkers[i]) damMarkers[i].openPopup(); }, narrow() ? 120 : 0);
  }

  /* ---------- a case (Kaeng Krachan first) ---------- */
  async function renderCase(id) {
    const body = $("#imp-body");
    let st = state.kase[id];
    if (!st) {
      body.innerHTML = '<p class="muted">กำลังโหลด…</p>';
      let r;
      try { r = await api("/api/impact/case/" + encodeURIComponent(id)); } catch (e) { body.innerHTML = '<p class="imp-err">เชื่อมต่อไม่ได้</p>'; return; }
      if (r.status === 401) { state.authed = false; return showLogin("หมดเวลาเข้าสู่ระบบ กรุณาเข้าใหม่"); }
      if (!r.ok) { body.innerHTML = '<p class="imp-err">โหลดไม่สำเร็จ (' + r.status + ")</p>"; return; }
      st = state.kase[id] = await r.json();
    }
    if (state.sel !== id) return;  // the user moved on while it loaded
    if (!st.points || !st.points.length) { body.innerHTML = '<p class="muted">ยังไม่มีข้อมูล — ระบบคำนวณใหม่ทุกชั่วโมง</p>'; return; }
    body.innerHTML = caseHtml(st);
    $("#imp-onmap", body).addEventListener("click", () => showCaseOnMap(st));
    bindWhatif(st);
    drawCase(st);
  }

  function caseHtml(st) {
    const v = st.validation || {};
    const gate = v.whatif_ready
      ? '<div class="imp-gate ok">ผลทดสอบย้อนหลังผ่านเกณฑ์ — ใช้ <a href="#imp-whatif">ตาราง what-if</a> ได้ (อ่านข้อจำกัดก่อนใช้)</div>'
      : '<div class="imp-gate no"><b>ยังไม่เปิดตาราง what-if</b> — ทดสอบย้อนหลังแล้ว ยังไม่มีวิธีใดทำนายระดับน้ำท้ายน้ำได้ดีกว่า' +
        " “คงระดับวันนี้ไว้” · <a href=\"#imp-val\">ผลทดสอบ</a> · <a href=\"#imp-req\">ข้อมูลที่ต้องการ</a></div>";
    return '<h2 class="imp-title">' + esc(st.title) + "</h2>" +
      '<p class="muted">ข้อมูลถึง ' + when(st.data_time) + " · คำนวณ " + when(st.built_at) +
      " · เวลาไทย · ระดับ ม.รทก. ตามหมุดของหน่วยงานผู้วัด</p>" +
      '<button type="button" class="btn imp-onmap" id="imp-onmap">🗺️ ดูแม่น้ำ เขื่อน และสถานีบนแผนที่</button>' + gate +
      damHtml(st) + riverHtml(st) + valHtml(st) + whatifHtml(st) + reqHtml(st) + methodHtml(st);
  }

  function drawCase(st) {
    if (!mapRef || !st || !st.points) return;
    if (!mapRef.getPane("impact")) mapRef.createPane("impact").style.zIndex = 660;
    if (layers.kase) layers.kase.remove();
    layers.kase = L.layerGroup();
    for (const part of st.river_line || []) L.polyline(part, { color: "#1565c0", weight: 4, opacity: 0.8, interactive: false }).addTo(layers.kase);
    for (const p of st.points) {
      if (p.lat == null || p.lon == null) continue;
      const lag = p.code === "B.18" ? "ใต้เขื่อน" : "~" + (p.lag_range ? p.lag_range[0] + "–" + p.lag_range[1] : p.lag_h) + " ชม. จาก B.18";
      L.circleMarker([p.lat, p.lon], { radius: 7, color: "#fff", weight: 2, fillColor: "#0d3b66", fillOpacity: 1, pane: "impact" })
        .bindTooltip(esc(p.code) + " · " + esc(lag), { permanent: true, direction: "right", className: "imp-tip" })
        .addTo(layers.kase);
    }
    layers.kase.addTo(mapRef);
  }

  function showCaseOnMap(st) {
    if (!mapRef) return;
    const pts = [].concat(...(st.river_line || []), st.points.filter((p) => p.lat != null).map((p) => [p.lat, p.lon]),
      st.dam_latlon ? [st.dam_latlon] : []);
    if (narrow()) setTab("map");
    setTimeout(() => { if (pts.length) mapRef.fitBounds(L.latLngBounds(pts), { padding: [24, 24] }); }, narrow() ? 120 : 0);
  }

  function damHtml(st) {
    const d = st.dam || {};
    if (d.released_mcm == null) return '<section class="imp-card"><h3>' + damName(d.name_th) + '</h3><p class="muted">ยังไม่มีข้อมูลเขื่อน</p></section>';
    const box = (label, val, d2, unit, sub) => "<div><span>" + label + "</span><b>" + num(val, d2) + "</b> " + unit +
      (sub ? "<small>" + sub + "</small>" : "") + "</div>";
    const cms = (x) => (x == null ? "" : "≈ " + num(toCms(x), 0) + " ลบ.ม./วินาที");
    return '<section class="imp-card" id="imp-dam"><h3>' + damName(d.name_th) + " <small>" + agency(d.agency) + " · ข้อมูลรายวัน " +
      day(d.dam_date) + '</small></h3><div class="imp-kv">' +
      box("ระบายรวม", d.released_mcm, 2, "ล้าน ลบ.ม./วัน", cms(d.released_mcm)) +
      box("น้ำไหลเข้าอ่าง", d.inflow_mcm, 2, "ล้าน ลบ.ม./วัน", cms(d.inflow_mcm)) +
      box("ปริมาตรอ่าง", d.storage_mcm, 1, "ล้าน ลบ.ม.", (d.storage_pct == null ? "" : num(d.storage_pct, 1) + " %") +
        (d.normal_mcm ? " · ปริมาตรปกติ " + num(d.normal_mcm, 0) : "")) +
      (d.rule_curve ? "<div><span>เส้นควบคุมวันนี้ (บน / ล่าง)</span><b>" + num(d.rule_curve.upper, 0) + " / " +
        num(d.rule_curve.lower, 0) + "</b> ล้าน ลบ.ม.<small>สสน.</small></div>" : "") +
      box("ระบายทางน้ำล้น", d.spilled_mcm, 2, "ล้าน ลบ.ม./วัน", "") + "</div>" + yearsHtml(d.yearly_max) +
      (st.dam_notes || []).map((n) => '<p class="imp-note">' + esc(n) + "</p>").join("") + "</section>";
  }

  function yearsHtml(rows) {
    if (!rows || !rows.length) return "";
    const body = rows.map((r) => '<tr><th scope="row">' + esc(r.year + 543) + (r.days < 300 ? "<small>ถึงวันนี้</small>" : "") +
      "</th><td>" + num(r.max_mcm, 2) + "</td><td>" + num(toCms(r.max_mcm), 0) + "</td><td>" + day(r.date) + "</td></tr>").join("");
    return '<details><summary>ระบายสูงสุดในแต่ละปี (ข้อมูลรายวันจาก สสน.)</summary><div class="imp-scroll"><table><thead><tr>' +
      '<th scope="col">ปี</th><th scope="col">สูงสุด (ล้าน ลบ.ม./วัน)</th><th scope="col">≈ ลบ.ม./วินาที</th><th scope="col">วันที่</th>' +
      "</tr></thead><tbody>" + body + "</tbody></table></div></details>";
  }

  function riverHtml(st) {
    const rows = st.points.map((p) => {
      const margin = p.h_now != null && p.bank != null ? p.bank - p.h_now : null;
      const lag = p.code === "B.18" ? "ใต้เขื่อน ~" + num(st.dam_km, 0) + " กม."
        : (p.lag_range && p.lag_range[0] !== p.lag_range[1] ? num(p.lag_range[0], 0) + "–" + num(p.lag_range[1], 0)
          : num(p.lag_h, 0)) + " ชม." + (p.lag_r != null ? " <small>r " + num(p.lag_r, 2) + "</small>" : "");
      return '<tr><th scope="row">' + esc(p.code) + "<small>" + esc(p.name_th || "") + " · " + agency(p.agency) + "</small></th>" +
        "<td" + (margin != null && margin < 0 ? ' class="imp-neg"' : "") + ">" + num(margin, 2) + "</td>" +
        "<td>" + num(p.h_now, 2) + "</td><td>" + num(p.bank, 2) + "</td><td>" + num(p.q_now, 0) + "</td>" +
        "<td>" + lag + "</td><td>" + (p.h_time ? when(p.h_time) : "ไม่มีข้อมูลใน 6 ชม.") + "</td></tr>";
    }).join("");
    const b10 = st.points.find((p) => p.code === "B.10") || {};
    return '<section class="imp-card" id="imp-river"><h3>แม่น้ำเพชรบุรีตอนนี้</h3><div class="imp-scroll"><table><thead><tr>' +
      '<th scope="col">สถานี</th><th scope="col">ห่างตลิ่ง (ม.)</th><th scope="col">ระดับ (ม.รทก.)</th>' +
      '<th scope="col">ตลิ่ง (ม.รทก.)</th><th scope="col">น้ำไหล (ลบ.ม./วินาที)</th>' +
      '<th scope="col">น้ำจาก B.18 ถึงใน</th><th scope="col">วัดเมื่อ</th></tr></thead><tbody>' + rows + "</tbody></table></div>" +
      '<ul class="imp-facts">' +
      "<li>ห่างตลิ่ง = ตลิ่งของหน่วยงานผู้วัด − ระดับล่าสุด (ไม่นำระดับต่างหน่วยงานมาเทียบกัน เพราะหมุดอาจต่างกัน)</li>" +
      "<li>เวลาเดินทางหาจากการเปลี่ยนแปลงรอบ 24 ชม. ในข้อมูล 1 ปี ช่วงตัวเลข = ค่าจากช่วงแรกของปีกับทั้งปี;" +
      " r = ท้ายน้ำเปลี่ยนตาม B.18 มากน้อยเพียงใด (1 = ตามทั้งหมด, ใกล้ 0 = แทบไม่ตาม)</li>" +
      "<li>จากเขื่อนถึง B.18 สมมติ " + num(st.dam_to_first_h[0], 0) + "–" + num(st.dam_to_first_h[1], 0) +
      " ชม. (ยังไม่มีข้อมูลการระบายรายชั่วโมง)</li>" +
      "<li>น้ำที่ B.10 น้อยกว่าน้ำที่ B.18 เมื่อ ~" + num(b10.lag_h, 0) + " ชม. ก่อน ประมาณ " + num(st.diversion_default, 0) +
      " ลบ.ม./วินาที (มัธยฐาน 3 วันล่าสุด) — น่าจะเป็นน้ำที่ผันเข้าคลองที่เขื่อนทดน้ำเพชร ⚠️ ยังไม่ได้ยืนยันกับข้อมูลการเปิดประตู</li>" +
      "</ul></section>";
  }

  function valTable(P, key, order) {
    const body = order.map((code) => {
      const p = P[code], ms = p[key];
      if (!ms) return "";
      const best = Math.min.apply(null, METHODS.map((m) => ms[m[0]]));
      return '<tr><th scope="row">' + esc(code) + "</th>" + METHODS.map((m) => "<td" +
        (ms[m[0]] === best ? ' class="imp-best"' : "") + ">" + num(ms[m[0]], 1) + "</td>").join("") +
        "<td>" + num(key === "methods" ? p.n : p.n_big, 0) + "</td></tr>";
    }).join("");
    return '<div class="imp-scroll"><table><thead><tr><th scope="col">สถานี</th>' +
      METHODS.map((m) => '<th scope="col">' + m[1] + "</th>").join("") +
      '<th scope="col">จำนวนครั้ง</th></tr></thead><tbody>' + body + "</tbody></table></div>";
  }

  function valHtml(st) {
    const v = st.validation || {};
    const P = v.points || {};
    const order = st.points.map((p) => p.code).filter((c) => P[c]);  // down the river, not alphabetical
    const gains = order.map((c) => esc(c) + " " + num(P[c].gain_cm_per_cms, 2)).join(", ");
    const b18 = st.points.find((p) => p.code === "B.18") || {};
    const qmax = b18.rating ? b18.rating.qmax : null;
    return '<section class="imp-card" id="imp-val"><h3>ทดสอบย้อนหลัง <small>' + (v.whatif_ready ? "ผ่านเกณฑ์" : "ยังไม่ผ่านเกณฑ์") +
      "</small></h3>" +
      '<p class="muted">หา rating curve เวลาเดินทาง และค่าตอบสนอง จากข้อมูลก่อน ' + day(v.from) +
      " แล้วทดสอบกับช่วงหลังจากนั้น (ทุก 3 ชม.) โดยใช้น้ำที่วัดได้ที่ B.18 แทนการระบาย ตัวเลข = ความคลาดเคลื่อนเฉลี่ยของระดับน้ำ (ซม.)" +
      " ณ เวลาที่น้ำเดินทางถึง ช่องสีเขียว = ดีที่สุด</p>" + valTable(P, "methods", order) +
      "<details><summary>เฉพาะช่วงที่น้ำที่ B.18 เปลี่ยน ≥ 15 ลบ.ม./วินาที</summary>" + valTable(P, "methods_big", order) + "</details>" +
      '<ul class="imp-facts"><li>ค่าตอบสนองที่เรียนรู้ (ซม. ต่อ 1 ลบ.ม./วินาทีที่ B.18): ' + gains + "</li>" +
      "<li>เกณฑ์เปิดตาราง what-if: วิธีใดวิธีหนึ่งต้องคลาดเคลื่อนน้อยกว่า “คงระดับวันนี้” อย่างน้อย 10 % ทั้งที่ B.10 และ B.16" +
      " (รวมช่วงน้ำเปลี่ยนมาก เมื่อมีอย่างน้อย 30 ครั้ง) — คำนวณใหม่ทุกชั่วโมง</li></ul>" +
      (v.whatif_ready ? "" : '<p class="imp-note">อ่านผล: ในปีที่ผ่านมาน้ำที่ B.18 ไม่เกิน ' + num(qmax, 0) +
        " ลบ.ม./วินาที และเมื่อน้ำที่ B.18 เปลี่ยน ระดับท้ายน้ำแทบไม่เปลี่ยนตาม — น่าจะเพราะเขื่อนทดน้ำเพชรรับไว้และผันเข้าคลอง" +
        " (⚠️ ยังไม่ได้ยืนยัน) ระดับท้ายน้ำจึงขึ้นกับการบริหารเขื่อนเพชร ฝนในพื้นที่ และน้ำขึ้นน้ำลง (ในเมือง)" +
        " มากกว่าการระบายจากแก่งกระจาน การระบายขนาดใหญ่ที่เกินความจุคลองจะต้องผ่านลงแม่น้ำ" +
        " แต่ข้อมูลของเรายังไม่มีเหตุการณ์แบบนั้นให้ตรวจสอบ</p>") + "</section>";
  }

  function whatifHtml(st) {
    const v = st.validation || {};
    if (!v.whatif_ready) {
      return '<section class="imp-card imp-off" id="imp-whatif"><h3>ตาราง what-if <small>ปิดอยู่</small></h3>' +
        '<p class="muted">“ถ้าเขื่อนระบาย X ล้าน ลบ.ม./วัน น้ำจะถึงแต่ละจุดเมื่อไร สูงเท่าไร ล้นตลิ่งหรือไม่” จะเปิดเองเมื่อผลทดสอบย้อนหลังผ่านเกณฑ์' +
        " — เร็วที่สุดเมื่อได้ข้อมูลเขื่อนทดน้ำเพชรและเหตุการณ์ในอดีต (ด้านล่าง)</p></section>";
    }
    const d = st.dam || {};
    return '<section class="imp-card" id="imp-whatif"><h3>ตาราง what-if</h3><form class="imp-wf" id="imp-wf">' +
      '<label>ระบายจากเขื่อน (ล้าน ลบ.ม./วัน)<input name="release" type="number" inputmode="decimal" step="0.1" min="0" max="200" value="' +
      esc(d.released_mcm != null ? d.released_mcm : 10) + '" required></label>' +
      '<label>ผันน้ำที่เขื่อนเพชร (ลบ.ม./วินาที)<input name="div" type="number" inputmode="decimal" step="1" min="0" max="2000" value="' +
      esc(st.diversion_default) + '"></label>' +
      '<button class="btn primary" type="submit">คำนวณ</button><span class="muted" id="imp-rcms"></span></form>' +
      '<div id="imp-wres"></div></section>';
  }

  function bindWhatif(st) {
    const f = $("#imp-wf");
    if (!f) return;
    const showCms = () => { $("#imp-rcms").textContent = "≈ " + num(toCms(Number(f.release.value) || 0), 0) + " ลบ.ม./วินาที"; };
    f.release.addEventListener("input", showCms);
    showCms();
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const q = new URLSearchParams({ release_mcm: f.release.value });
      if (f.div.value !== "") q.set("diversion_cms", f.div.value);
      const r = await api("/api/impact/" + encodeURIComponent(st.case) + "/whatif?" + q.toString());
      if (r.status === 401) { state.authed = false; return showLogin("หมดเวลาเข้าสู่ระบบ กรุณาเข้าใหม่"); }
      if (!r.ok) { $("#imp-wres").innerHTML = '<p class="imp-err">คำนวณไม่ได้ (' + r.status + ")</p>"; return; }
      $("#imp-wres").innerHTML = whatifTable(await r.json());
    });
  }

  function whatifTable(w) {
    const over = { yes: "ถึงตลิ่ง", possible: "ขอบบนถึงตลิ่ง", no: "ต่ำกว่าตลิ่ง" };
    const rows = w.rows.map((r) => '<tr><th scope="row">' + esc(r.code) + "<small>" + esc(r.name_th || "") + "</small></th>" +
      "<td>" + (r.arrival_h ? num(r.arrival_h[0], 0) + "–" + num(r.arrival_h[1], 0) : "–") + "</td><td>" + num(r.flow_cms, 0) + "</td>" +
      "<td>" + (r.level ? num(r.level[0], 2) + "–" + num(r.level[2], 2) : "–") + "</td>" +
      "<td" + (r.margin_m != null && r.margin_m < 0 ? ' class="imp-neg"' : "") + ">" + num(r.margin_m, 2) + "</td>" +
      "<td>" + (over[r.overflow] || "–") + "</td><td>" + (r.outside ? "เกินช่วงข้อมูล 1 ปี" : "") + "</td></tr>").join("");
    return '<p class="muted">ระบาย ' + num(w.release_mcm, 2) + " ล้าน ลบ.ม./วัน (≈ " + num(w.release_cms, 0) +
      " ลบ.ม./วินาที) · ผันที่เขื่อนเพชร " + num(w.diversion_cms, 0) + " ลบ.ม./วินาที" + (w.diversion_default ? " (จากข้อมูล)" : "") +
      '</p><div class="imp-scroll"><table><thead><tr><th scope="col">สถานี</th><th scope="col">ถึงใน (ชม. จากเขื่อน)</th>' +
      '<th scope="col">น้ำไหล (ลบ.ม./วินาที)</th><th scope="col">ระดับ (ม.รทก.)</th><th scope="col">ห่างตลิ่ง (ม.)</th>' +
      '<th scope="col">ตลิ่ง</th><th scope="col">หมายเหตุ</th></tr></thead><tbody>' + rows + "</tbody></table></div>" +
      '<ul class="imp-facts">' + w.assumptions.map((a) => "<li>" + esc(a) + "</li>").join("") + "</ul>";
  }

  function reqHtml(st) {
    const items = (st.data_request || []).map((x) => "<li><b>" + esc(x.th) + '</b><span class="imp-why">' + esc(x.why) +
      ' · <a href="/api/impact/template/' + encodeURIComponent(x.key) + '">แบบฟอร์ม CSV</a></span></li>').join("");
    return '<section class="imp-card" id="imp-req"><h3>ข้อมูลที่ต้องการจาก สทนช. / กรมชลประทาน</h3><ol class="imp-req">' + items + "</ol>" +
      '<p class="muted">เวลาเป็นเวลาไทย ระดับเป็น ม.รทก. (ระบุหมุดของหน่วยงานในหมายเหตุ) ส่งเป็น CSV หรือ Excel' +
      " ให้ผู้ดูแลระบบที่ให้รหัสผ่านนี้</p></section>";
  }

  function releaseCheck(k) {
    if (!k) return "";
    return "<li>ตรวจแล้ว (" + num(k.days, 0) + " วัน, " + day(k.first) + "–" + day(k.last) + "): น้ำเฉลี่ยรายวันที่ B.18 = ระบายของ ชป. + ~" +
      num(k.median_diff_cms, 0) + " ลบ.ม./วินาที (มัธยฐาน: น้ำท่าระหว่างทางและความต่างของการวัด), r " + num(k.r, 2) +
      "; การเปลี่ยนแปลงรายวันสัมพันธ์กันในวันเดียวกัน r " + num(k.lag0_r, 2) + " วันถัดไป r " + num(k.lag1_r, 2) +
      (k.lag0_r != null && k.lag1_r != null && k.lag0_r > k.lag1_r ? " — น้ำจากเขื่อนถึง B.18 ภายในวันเดียวกัน" : "") + "</li>";
  }

  function methodHtml(st) {
    const rows = st.points.filter((p) => p.rating).map((p) => {
      const r = p.rating;
      return '<tr><th scope="row">' + esc(p.code) + (p.rating_from ? "<small>ใช้น้ำไหลที่ " + esc(p.rating_from) + "</small>" : "") +
        "</th><td>" + num(r.h0, 2) + "</td><td>" + num(r.a, 3) + "</td><td>" + num(r.b, 2) + "</td><td>" + num(r.rmse * 100, 1) +
        "</td><td>" + num(r.qmin, 0) + "–" + num(r.qmax, 0) + "</td><td>" + num(r.n, 0) + "</td></tr>";
    }).join("");
    return '<section class="imp-card" id="imp-method"><details><summary>วิธีการและข้อจำกัด</summary>' +
      '<ul class="imp-facts">' +
      "<li>ข้อมูล: ระดับและปริมาณน้ำรายชั่วโมงย้อนหลัง 1 ปีจากสถานีของ ชป. และ สสน. และข้อมูลเขื่อนรายวัน (ชป., กฟผ.) — ทั้งหมดเป็นข้อมูลสาธารณะผ่าน สสน.</li>" +
      "<li>Rating curve ต่อสถานี h = h₀ + a·Qᵇ (ตารางด้านล่าง) ใช้ได้ในช่วงน้ำที่เคยวัดได้เท่านั้น เกินกว่านั้นคือการต่อเส้นโค้งออกไป</li>" +
      "<li>B.15 และ PCH001 (ในเมือง) ไม่มีปริมาณน้ำ จึงใช้น้ำไหลที่ B.16 ณ เวลาที่น้ำเดินทางถึง; ในเมืองระดับน้ำยังขึ้นกับน้ำขึ้นน้ำลงด้วย</li>" +
      releaseCheck(st.release_check) +
      "<li>PCH003 (สสน.) ไม่ได้ใช้: ระดับเปลี่ยนพร้อม B.18 แทบเท่ากันและไม่มีเวลาหน่วง จึงน่าจะอยู่ใกล้เขื่อน ไม่ใช่ในตัวท่ายาง ⚠️ ขอยืนยันตำแหน่ง</li>" +
      "<li>เวลาแสดงเป็นเวลาไทย (ระบบเก็บเป็น UTC); ข้อมูลเขื่อนเป็นรายวันตามวันที่หน่วยงานรายงาน; เส้นแม่น้ำจาก สสน.</li>" +
      '</ul><div class="imp-scroll"><table><thead><tr><th scope="col">สถานี</th><th scope="col">h₀ (ม.)</th><th scope="col">a</th>' +
      '<th scope="col">b</th><th scope="col">RMSE (ซม.)</th><th scope="col">Q ที่เคยวัด (ลบ.ม./วินาที)</th>' +
      '<th scope="col">จำนวนชั่วโมง</th></tr></thead><tbody>' + rows + "</tbody></table></div></details></section>";
  }

  // the page is for engineers: open on this tab unless a link points somewhere else (#s=…, #p=…)
  if (!location.hash) setTab("impact");
})();
