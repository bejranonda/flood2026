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

  const state = { authed: false, cases: [], dams: null, sel: "dams", kase: {}, loadedAt: 0, notice: "", customs: [], selPlan: null, day: null };
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
    // the state rebuilds hourly: a page left open reloads what it shows after 30 minutes
    if (state.authed && Date.now() - state.loadedAt > 30 * 60 * 1000) { state.authed = false; state.kase = {}; }
    if (!state.authed && !(await loadAll())) return;
    render();
  }

  async function loadAll() {
    let r;
    try { r = await api("/api/impact/cases"); } catch (e) { msg("เชื่อมต่อไม่ได้ ลองใหม่อีกครั้ง"); return false; }
    if (r.status === 401) { showLogin(state.notice || ""); state.notice = ""; return false; }
    if (r.status === 503) { msg("หน้านี้ยังไม่ได้ตั้งค่า (ผู้ดูแลระบบต้องตั้งรหัสผ่านก่อน)"); return false; }
    if (!r.ok) { msg("โหลดข้อมูลไม่สำเร็จ (" + r.status + ")"); return false; }
    state.cases = (await r.json()).cases || [];
    state.authed = true;
    state.loadedAt = Date.now();
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
    state.customs = []; state.selPlan = null; state.day = null;
    for (const k of Object.keys(layers)) { if (layers[k]) { layers[k].remove(); layers[k] = null; } }
    clearOnwr();  // ONWR's layers and a plan's map legend leave with the session too
    if (reachLegend) { reachLegend.remove(); reachLegend = null; }
    state.notice = "ออกจากระบบแล้ว";  // shown by the session check that setTab starts (no race with a second form)
    setTab("impact");
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
      clearOnwr();
      if (reachLegend) { reachLegend.remove(); reachLegend = null; }
      renderDams();
    } else renderCase(state.sel);
  }

  /* ---------- national dams at risk — the station list's grammar: groups with ⓘ, two-line rows, tap → sheet ---------- */
  const GROUPS = [["above", "เหนือเส้นควบคุมบน", "warning", "ปริมาตรสูงกว่าเส้นควบคุมบน (rule curve ของ สสน.) ของวันที่รายงาน"],
    ["between", "อยู่ระหว่างเส้นควบคุม", "normal", "ปริมาตรอยู่ระหว่างเส้นควบคุมบนและล่างของวันที่รายงาน"],
    ["below", "ต่ำกว่าเส้นควบคุมล่าง", "below", "ปริมาตรต่ำกว่าเส้นควบคุมล่างของวันที่รายงาน — น้ำน้อยกว่าแผน"],
    [null, "ไม่มีเส้นควบคุม", "unknown", "สสน. ไม่มีเส้นควบคุมของเขื่อนนี้ (เช่น เขื่อนทดน้ำหรือเขื่อนน้ำไหลผ่าน)"]];
  const info = (tip, label) => (typeof infoBtn === "function" ? infoBtn(tip, label)
    : '<button type="button" class="conf-badge" title="' + esc(tip) + '" aria-label="' + esc(label) + '">ⓘ</button>');
  const qn = (x) => (x == null ? "–" : num(x, Math.abs(x) >= 1 ? 1 : 2));  // ล้าน ลบ.ม.(/วัน): 1 decimal, 2 below 1
  const bare = (n) => esc(String(n || "").replace(/^เขื่อน/, ""));

  function damPct(x, storage) {
    const n = x.normal_mcm;
    return n ? (100 * storage) / n : null;
  }

  function renderDams() {
    const body = $("#imp-body"), d = state.dams;
    if (!d || !d.dams || !d.dams.length) { body.innerHTML = '<p class="muted">ยังไม่มีข้อมูลเขื่อน — ระบบคำนวณใหม่ทุกชั่วโมง</p>'; return; }
    const dates = d.dams.map((x) => (x.records[0] || {}).dam_date).filter(Boolean);
    const latest = dates.slice().sort().pop();
    const withOutlook = d.dams.filter((x) => x.outlook).length;
    const noCurve = d.records - d.curves;
    const head = '<p class="sumline">' + num(d.dams.length, 0) + " เขื่อน · ข้อมูลรายวัน " + day(latest) + " · ล้าน ลบ.ม.(/วัน) " +
      info("ข้อมูลรายวันจาก สสน. (กรมชลประทาน, กฟผ.) · เส้นควบคุมของ สสน." + (noCurve > 0 ? " — " + num(noCurve, 0) + " ระเบียนไม่มีเส้นควบคุมที่ต้นทาง" : "") +
        " · แนวโน้ม 7 วัน " + num(withOutlook, 0) + " เขื่อน (แบบจำลองที่ผ่านการทดสอบ หรือ * คงค่าวันนี้) · ตัวเลขบนการ์ด: เข้า = น้ำไหลเข้า, ออก = ระบาย, % = ปริมาตรเทียบปริมาตรปกติ" +
        " · * = ถ้าไหลเข้าและระบายเท่าวันนี้ (ยังไม่มีแบบจำลองที่ผ่านการทดสอบ) · % = ปริมาตร ÷ ปริมาตรที่ระดับเก็บกักปกติของหน่วยงานนั้น" +
        " (ชป. รายงานแบบนี้; % ที่ กฟผ. รายงานเป็น 0 หรือนิยามต่างกัน จึงไม่ใช้) · ⏳ = ข้อมูลของวันก่อนหน้า · ชป. และ กฟผ. แยกกัน ไม่รวมตัวเลข", "ที่มาและวิธีอ่าน") + "</p>";
    let html = head, i = 0;
    const index = [];
    for (const [pos, title, cls, tip] of GROUPS) {
      const members = d.dams.map((x, k) => [x, k]).filter(([x]) => (x.position || null) === pos);
      if (!members.length) continue;
      html += '<section class="wgrp imp-grp"><div class="wgrp-h"><b>' + title + '</b> <small class="muted">' + num(members.length, 0) + "</small> " +
        info(tip, title) + '</div><ul class="list imp-dams">' + members.map(([x, k]) => damItem(x, k, cls, latest)).join("") + "</ul></section>";
      i += members.length;
      index.push(...members.map(([, k]) => k));
    }
    body.innerHTML = html;
    body.querySelectorAll("[data-dam]").forEach((li) => {
      const open = (e) => { if (e.target.closest(".conf-badge, [data-case]")) return; openDamSheet(Number(li.dataset.dam), true); };
      li.addEventListener("click", open);
      li.addEventListener("keydown", (e) => { if (e.key === "Enter") open(e); });
    });
    body.querySelectorAll("[data-case]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); state.sel = b.dataset.case; render(); }));
  }

  function damItem(x, i, cls, latest) {
    const r = x.records[0] || {};
    const pct = r.pct_normal;
    const o = x.outlook && x.outlook.days && x.outlook.days.length ? x.outlook.days[6] : null;
    const first = x.outlook && x.outlook.days ? x.outlook.days[0] : null;
    let trend = "";
    if (o && first) {
      const p7 = damPct(x, o.storage);
      // the arrow agrees with the two numbers shown (badge now, % in 7 days); in ล้าน ลบ.ม. only when there is no %
      const arrow = pct != null && p7 != null ? (Math.round(p7) > Math.round(pct) ? "↗" : Math.round(p7) < Math.round(pct) ? "↘" : "→")
        : o.storage > (r.storage_mcm || 0) + 0.5 ? "↗" : o.storage < (r.storage_mcm || 0) - 0.5 ? "↘" : "→";
      const held = x.outlook.test && x.outlook.test.model === false;
      trend = " · อีก 7 วัน " + arrow + " " + (p7 != null ? num(p7, 0) + " %" : num(o.storage, 0)) + (held ? "*" : "");
    }
    const stale = r.dam_date && latest && r.dam_date < latest ? ' <small class="muted">⏳ ' + dayShort(r.dam_date) + "</small>" : "";
    const meta = r.no_data ? "ไม่มีข้อมูล (แหล่งข้อมูลรายงานเป็น 0)" : "เข้า " + qn(r.inflow_mcm) + " · ออก " + qn(r.released_mcm) + trend;
    return '<li class="item s-' + cls + ' imp-dam" data-dam="' + i + '" tabindex="0"><div class="row"><span class="name">' + bare(x.name_th) + stale +
      (x.case ? ' <button type="button" class="imp-case-tag" data-case="' + esc(x.case) + '">กรณีวิเคราะห์ ›</button>' : "") +
      '</span><span class="badge b-' + cls + '">' + (pct != null ? num(pct, 0) + " %" : "–") + "</span></div>" +
      '<div class="meta">' + meta + "</div></li>";
  }

  function recLine(r) {
    if (r.no_data) return agency(r.agency) + " " + day(r.dam_date) + ": ไม่มีข้อมูล (แหล่งข้อมูลรายงานเป็น 0)";
    return agency(r.agency) + " " + day(r.dam_date) + ": " + num(r.storage_mcm, 0) + (r.pct_normal != null ? " (" + num(r.pct_normal, 0) + " %)" : "") + " · ระบาย " +
      qn(r.released_mcm) + (r.released_mcm == null ? "" : " (≈ " + num(toCms(r.released_mcm), 0) + " ลบ.ม./วินาที)");
  }

  function damSheetHtml(x) {
    const r = x.records[0] || {};
    const g = GROUPS.find((gg) => gg[0] === (x.position || null)) || GROUPS[3];
    const up = r.rule && r.rule.upper != null ? r.rule.upper : null;
    const chip = (label, val, sub) => '<span class="chip imp-chip-static">' + label + " <b>" + val + "</b>" + (sub ? ' <small class="muted">' + sub + "</small>" : "") + "</span>";
    const chips = r.no_data ? '<p class="muted">ไม่มีข้อมูล — แหล่งข้อมูลรายงานปริมาตร น้ำไหลเข้า และระบายเป็น 0</p>' :
      '<div class="chips imp-chips-num">' + chip("ปริมาตร", num(r.storage_mcm, 0), r.pct_normal != null ? num(r.pct_normal, 0) + " %" : "") +
      (up != null && r.storage_mcm != null ? chip(r.storage_mcm > up ? "เหนือเส้นควบคุม" : "ใต้เส้นควบคุม", (r.storage_mcm > up ? "+" : "−") + num(Math.abs(r.storage_mcm - up), 0), "") : "") +
      chip("ไหลเข้า", qn(r.inflow_mcm), "") + chip("ระบาย", qn(r.released_mcm), r.released_mcm != null ? "≈ " + num(toCms(r.released_mcm), 0) + " ลบ.ม./วิ" : "") + "</div>";
    const o = x.outlook;
    let out = "";
    if (o && o.days && o.days.length) {
      const d7 = o.days[6];
      const modelled = o.test && o.test.model !== false;
      const gains = [[1, o.test && o.test.gain_1d], [3, o.test && o.test.gain_3d], [7, o.test && o.test.gain_7d]].filter((g) => g[1] != null);
      // the note names each day range's model and rain; the gains are the tested ones (each horizon its own test window)
      const tip = modelled ? (o.note || "") + (gains.length ? " · ทดสอบกับฝนคาดการณ์จริงย้อนหลัง: ดีกว่าคงค่าวันนี้ " +
        gains.map((g) => num(g[1], 0) + " % ที่ " + g[0] + " วัน").join(", ") : "") +
        (o.rain7_mm != null ? " · ฝนในลุ่มน้ำ 7 วัน " + num(o.rain7_mm, 0) + " มม." : "") : (o.note || "");
      const p = { storage: o.days.map((d) => d.storage), storage_low: o.days.map((d) => d.storage_lo), storage_high: o.days.map((d) => d.storage_hi) };
      const c = { upper: o.days.map((d) => d.upper), normal: x.normal_mcm, dates: o.days.map((d) => d.date) };
      out = '<h3 class="imp-h3">7 วันข้างหน้า' + (modelled ? "" : ' <small class="muted">ถ้าเท่าวันนี้</small>') + " " + info(tip, "ที่มาของแนวโน้ม") + "</h3>" +
        '<p class="imp-line">อ่าง ' + num(r.storage_mcm, 0) + " → <b>" + num(d7.storage, 0) + "</b> <small class=\"muted\">(" + num(d7.storage_lo, 0) + "–" + num(d7.storage_hi, 0) + ")</small>" +
        (d7.above_upper === true ? " · ยังเหนือเส้นควบคุม" : d7.above_upper === false ? " · ใต้เส้นควบคุม" : "") + (modelled ? " · ระบายเท่าวันนี้" : "") + "</p>" +
        chartSvg(p, c) +
        '<details><summary>รายวัน</summary><div class="imp-scroll"><table><thead><tr><th scope="col">วัน</th><th scope="col">ไหลเข้า</th><th scope="col">อ่าง (ช่วง)</th><th scope="col">เส้นบน</th></tr></thead><tbody>' +
        o.days.map((dd) => '<tr><th scope="row">' + esc(dayShort(dd.date)) + "</th><td>" + qn(dd.inflow) + (dd.method === "model" ? "" : "*") + "</td><td>" + num(dd.storage, 0) +
          " <small>" + num(dd.storage_lo, 0) + "–" + num(dd.storage_hi, 0) + "</small></td><td" + (dd.above_upper ? ' class="imp-neg"' : "") + ">" + num(dd.upper, 0) + "</td></tr>").join("") +
        '</tbody></table></div><p class="muted">* คงค่าวันนี้ (' + (modelled ? "แบบจำลองไม่ผ่านเกณฑ์ที่ช่วงนี้" : "ยังไม่มีแบบจำลองที่ผ่านการทดสอบ") + ")</p></details>";
    } else {
      out = '<p class="muted">ยังไม่มีแนวโน้ม 7 วัน — แบบจำลองน้ำไหลเข้าของเขื่อนนี้ยังไม่ผ่านการทดสอบ หรือยังไม่มีประวัติน้ำไหลเข้า</p>';
    }
    const others = x.records.slice(1).map((rr) => '<p class="imp-line muted">' + recLine(rr) + "</p>").join("");
    const note = x.records.map((rr) => rr.release_note).filter(Boolean)[0];
    return '<div class="imp-dam-sheet"><h2>' + damName(x.name_th) + '</h2><p class="muted">' + agency(r.agency) + " " + day(r.dam_date) + " · ล้าน ลบ.ม.(/วัน)" +
      ' · <span class="badge b-' + g[2] + '">' + g[1] + "</span></p>" + chips + out + others +
      (note ? '<p class="imp-line">📌 ' + esc(note.split(" —")[0].split(";")[0]) + " " + info(note, "ที่มาของข้อสังเกต") + "</p>" : "") +
      '<div class="imp-actions"><button type="button" class="btn" data-map="1">🗺️ ดูบนแผนที่</button>' +
      (x.case ? '<button type="button" class="btn primary" data-case-open="' + esc(x.case) + '">เปิดกรณีวิเคราะห์ ›</button>' : "") + "</div></div>";
  }

  function openDamSheet(i, pan) {
    const x = state.dams && state.dams.dams[i];
    if (!x) return;
    openSheet(damSheetHtml(x), (box) => {
      box.querySelector("[data-map]").addEventListener("click", () => {
        document.getElementById("sheet").hidden = true;
        if (narrow()) setTab("map");
        setTimeout(() => { if (mapRef) mapRef.setView([x.lat, x.lon], 10); }, narrow() ? 120 : 0);
      });
      const cb = box.querySelector("[data-case-open]");
      if (cb) cb.addEventListener("click", () => { document.getElementById("sheet").hidden = true; state.sel = cb.dataset.caseOpen; setTab("impact"); render(); });
    });
    if (pan && mapRef) mapRef.setView([x.lat, x.lon], 9);  // as a station row does: the map follows, the tab stays
  }

  function drawDams() {
    if (!mapRef || !state.authed || !state.dams || !state.dams.dams) return;
    if (!mapRef.getPane("impact")) mapRef.createPane("impact").style.zIndex = 660;  // above the gauges: dams stay tappable
    if (layers.dams) layers.dams.remove();
    layers.dams = L.layerGroup();
    damMarkers = state.dams.dams.map((x, i) => {
      const pos = POS[x.position];
      const icon = L.divIcon({ className: "imp-dam-icon " + (pos ? pos[1] : "imp-unknown"), html: "◆", iconSize: [20, 20] });
      return L.marker([x.lat, x.lon], { icon, pane: "impact", title: "เขื่อน" + x.name_th, keyboard: true })
        .on("click", () => openDamSheet(i, false)).addTo(layers.dams);  // as a gauge marker does: the sheet, not a popup
    });
    layers.dams.addTo(mapRef);
  }



  /* ---------- a case (Kaeng Krachan first) — the app's grammar: chips, one ★ card, one-line rows, sheets ---------- */
  function openSheet(html, onOpen) {
    const sheet = document.getElementById("sheet"), box = document.getElementById("detail");
    if (!sheet || !box) return;
    box.innerHTML = '<div class="imp-sheet"><div class="tools"><button class="btn close" aria-label="ปิด">✕</button></div>' + html + "</div>";
    sheet.hidden = false;
    box.scrollTop = 0;
    box.querySelector(".close").addEventListener("click", () => { sheet.hidden = true; });
    if (onOpen) onOpen(box);
  }

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
    body.querySelectorAll("[data-sheet=dam]").forEach((b) => b.addEventListener("click", () => openSheet(damHtml(st))));
    body.querySelectorAll(".imp-node[data-code]").forEach((b) => b.addEventListener("click", () => {
      if (typeof showDetail === "function") showDetail(b.dataset.code);  // the station's own sheet, as on the list
    }));
    $("#imp-onmap", body).addEventListener("click", () => showCaseOnMap(st));
    body.querySelectorAll("[data-info]").forEach((b) => b.addEventListener("click", () => openInfo(st, b.dataset.info)));
    drawCase(st);
    if (!narrow()) showCaseOnMap(st, false);  // the map follows the case, as a dam row pans it (D-110)
    loadScenarios(st, body);
  }

  function marginClass(m) {
    return m == null ? "imp-m-unknown" : m < 0 ? "imp-m-critical" : m < 0.5 ? "imp-m-warning" : m < 1.0 ? "imp-m-watch" : "imp-m-normal";
  }

  function caseHtml(st) {
    const d = st.dam || {};
    const rc = d.rule_curve || {};
    const diff = d.storage_mcm != null && rc.upper != null ? d.storage_mcm - rc.upper : null;
    const chip = (label, val, sub, dot) => '<button type="button" class="chip" data-sheet="dam">' + (dot ? '<span class="dot ' + dot + '"></span>' : "") +
      label + " <b>" + val + "</b>" + (sub ? ' <small class="muted">' + sub + "</small>" : "") + "</button>";
    const chips = '<div class="chips imp-chips-num">' +
      chip("ปริมาตร", num(d.storage_mcm, 0), d.storage_pct != null ? num(d.storage_pct, 0) + " %" : "", diff != null && diff > 0 ? "imp-m-warning" : "imp-m-normal") +
      (diff != null ? chip(diff >= 0 ? "เหนือเส้นควบคุม" : "ใต้เส้นควบคุม", (diff >= 0 ? "+" : "−") + num(Math.abs(diff), 0), "", "") : "") +
      chip("ระบาย", num(d.released_mcm, 2), "", "") + chip("ไหลเข้า", num(d.inflow_mcm, 2), "", "") + "</div>" +
      '<p class="sumline">ล้าน ลบ.ม. (/วัน) · ' + agency(d.agency) + " " + day(d.dam_date) + " · แตะเพื่อดูเขื่อน" +
      ' <button type="button" class="conf-badge" title="ระดับเป็น ม.รทก. ตามหมุดของหน่วยงานผู้วัด · เวลาไทย · ข้อมูลถึง ' + esc(when(st.data_time)) + ' · คำนวณ ' + esc(when(st.built_at)) + '">ⓘ</button></p>';
    const nodes = st.points.map((p) => {
      const m = p.h_now != null && p.bank != null ? p.bank - p.h_now : null;
      const name = p.role === "city" ? "เมือง" : esc(p.code);
      return '<button type="button" class="imp-node ' + marginClass(m) + '" data-code="' + esc(p.code) + '" title="' + esc(p.name_th || p.code) + " · ห่างตลิ่ง " + num(m, 2) + ' ม."><span class="dot"></span><span class="imp-node-name">' + name + "</span><span class=\"imp-node-m\">" + num(m, 2) + "</span></button>";
    }).join('<span class="imp-arrow">→</span>');
    const strip = '<section class="imp-block"><h3>แม่น้ำเพชรบุรีตอนนี้ <small>ม. ห่างตลิ่ง · แตะสถานี</small>' +
      ' <button type="button" class="conf-badge" title="ห่างตลิ่ง = ตลิ่งของหน่วยงานผู้วัด − ระดับล่าสุด; สี: แดง เกินตลิ่ง · ส้ม < 0.5 ม. · เหลือง < 1 ม. · น้ำเงิน ≥ 1 ม.">ⓘ</button></h3>' +
      '<div class="imp-strip">' + nodes + "</div>" +
      '<button type="button" class="btn imp-onmap" id="imp-onmap">🗺️ ดูบนแผนที่</button></section>';
    const info = '<details class="imp-info"><summary>ℹ️ วิธีการ ข้อมูล และข้อจำกัด</summary><div class="imp-info-body">' +
      '<p class="muted">ข้อมูลสาธารณะ (สสน., ชป., กฟผ.) · อ่าง: สมดุลน้ำรายวันที่ตรวจกับข้อมูลจริง · ท้ายน้ำ: ' + (st && st.river7 ? "ทดสอบย้อนหลัง 7 วันแล้ว 🟠 คลาดเคลื่อนเพิ่มตามวัน" : "rating curve + เวลาเดินทาง 🔴 ยังไม่ผ่านการทดสอบ") + ' — ใช้เทียบระหว่างแผน</p>' +
      '<div class="imp-info-btns">' +
      '<button type="button" class="btn" data-info="val">ผลทดสอบย้อนหลัง</button>' +
      '<button type="button" class="btn" data-info="river">ตารางแม่น้ำ</button>' +
      '<button type="button" class="btn" data-info="matrix">เปรียบเทียบทุกผล</button>' +
      '<button type="button" class="btn" data-info="method">วิธีการ · rating curve</button>' +
      '<button type="button" class="btn" data-info="req">ข้อมูลที่ขอจาก สทนช.</button></div></div></details>';
    return '<h2 class="imp-title">' + esc(st.title) + "</h2>" + chips +
      '<section class="imp-block" id="imp-sc"><h3>แผนระบาย 7 วันข้างหน้า</h3><p class="muted">กำลังคำนวณ…</p></section>' + strip + info;
  }

  function openInfo(st, what) {
    const cmp = state.cmp;
    if (what === "val") openSheet("<h2>ทดสอบย้อนหลัง</h2>" + river7Html(st) + valHtml(st));
    else if (what === "river") openSheet("<h2>แม่น้ำเพชรบุรีตอนนี้</h2>" + riverHtml(st));
    else if (what === "method") openSheet("<h2>วิธีการและข้อจำกัด</h2>" + methodHtml(st) + (cmp ? scenarioNotes(cmp) : ""));
    else if (what === "req") openSheet("<h2>ข้อมูลที่ต้องการจาก สทนช. / กรมชลประทาน</h2>" + reqHtml(st));
    else if (what === "matrix") openSheet("<h2>เปรียบเทียบทุกผล</h2>" + (cmp ? matrixHtml(cmp) : '<p class="muted">ยังไม่มีผลการคำนวณ</p>'));
  }

  function drawCase(st) {
    if (!mapRef || !st || !st.points) return;
    if (!mapRef.getPane("impact")) mapRef.createPane("impact").style.zIndex = 660;
    if (layers.kase) layers.kase.remove();
    layers.kase = L.layerGroup();
    const reaches = st.river_reaches || [];
    for (const part of st.river_line || []) L.polyline(part, { color: "#1565c0", weight: reaches.length ? 2 : 4, opacity: reaches.length ? 0.5 : 0.8, interactive: false }).addTo(layers.kase);
    reachLayers = {};
    for (const r of reaches) {
      const line = L.polyline(r.line, { color: "#1565c0", weight: 6, opacity: 0.85, pane: "impact" }).bindTooltip(esc(r.code), { sticky: true });
      (reachLayers[r.code] = reachLayers[r.code] || []).push(line.addTo(layers.kase));
    }
    if (reachLegend) { reachLegend.remove(); reachLegend = null; }
    drawOnwr(st);
    for (const p of st.points) {
      if (p.lat == null || p.lon == null) continue;
      const lag = p.code === "B.18" ? "ใต้เขื่อน" : "~" + (p.lag_range ? p.lag_range[0] + "–" + p.lag_range[1] : p.lag_h) + " ชม. จาก B.18";
      // phones: the code only (the city gauges sit close together); the travel times are in the river table
      L.circleMarker([p.lat, p.lon], { radius: 7, color: "#fff", weight: 2, fillColor: "#0d3b66", fillOpacity: 1, pane: "impact" })
        .bindTooltip(esc(p.code) + (narrow() ? "" : " · " + esc(lag)), { permanent: true, direction: "right", className: "imp-tip" })
        .addTo(layers.kase);
    }
    layers.kase.addTo(mapRef);
  }

  // ONWR's flood layers over the case (owner 2026-10-06), dated and attributed — ONWR's areas, not results of a plan.
  // D-110: off by default, inside the app's one layer box (app.js builds it; its change handler ignores rows without
  // data-layer, so app.js stays as it is); the cells come clipped to the case box (KI-318)
  const ONWR_LAYERS = [["flood-warn", "พื้นที่เตือนวันนี้"], ["flood-forecast-d1", "คาดการณ์ +1 วัน"], ["flood-forecast-d2", "คาดการณ์ +2 วัน"],
    ["flood-forecast-d3", "คาดการณ์ +3 วัน"], ["flood-area-poly", "พื้นที่น้ำท่วมที่พบ"]];
  const ONWR_FILL = { 1: "#fdd835", 2: "#fb8c00", 3: "#e53935", obs: "#1e88e5" };
  let onwrGroups = {}, onwrBox = null;
  function clearOnwr() {
    for (const g of Object.values(onwrGroups)) g.remove();
    onwrGroups = {};
    if (onwrBox) { onwrBox.remove(); onwrBox = null; }
  }
  function drawOnwr(st) {
    clearOnwr();
    const o = st && st.onwr && st.onwr.layers;
    if (!mapRef || !o) return;
    for (const [lid, label] of ONWR_LAYERS) {
      const lay = o[lid];
      if (!lay) continue;
      const g = L.layerGroup();
      for (const f of lay.features || []) {
        const fill = lid === "flood-area-poly" ? ONWR_FILL.obs : (ONWR_FILL[f.cls] || ONWR_FILL[1]);
        L.polygon(f.rings, { stroke: false, fillColor: fill, fillOpacity: 0.45 })
          .bindTooltip("สทนช. · " + label + (f.cls ? " ระดับ " + f.cls : "") + (f.rai ? " · " + num(f.rai, 0) + " ไร่" : "") +
            (lay.updated ? " · ข้อมูล ณ " + when(lay.updated) : ""), { sticky: true }).addTo(g);
      }
      onwrGroups[lid] = g;  // not on the map until its box is ticked
    }
    // app.js adds its layer box right after announcing the map (fw:map): one tick later it is there
    if (document.querySelector(".legend.layers")) attachOnwrBox(o); else setTimeout(() => attachOnwrBox(o), 0);
  }
  function attachOnwrBox(o) {
    const box = document.querySelector(".legend.layers");
    if (!box || onwrBox || !Object.keys(onwrGroups).length) return;  // the browser check asserts the group sits in the app's box
    const div = document.createElement("div");
    div.className = "imp-onwr-grp";
    div.innerHTML = '<div class="imp-onwr-h"><b>สทนช.</b> · ไม่ขึ้นกับแผนระบาย ' +
      info("พื้นที่เตือน คาดการณ์ และพื้นที่น้ำท่วมที่พบของ สทนช. เฉพาะในกรอบของกรณีนี้ — ไม่ใช่ผลของแผนระบาย · ที่มา: สทนช.", "ชั้นข้อมูล สทนช.") + "</div>" +
      ONWR_LAYERS.filter(([lid]) => o[lid]).map(([lid, label]) => {
        const lay = o[lid], n = (lay.features || []).length;
        return '<label title="' + esc(lay.updated ? "ข้อมูล ณ " + when(lay.updated) : "") + '"><input type="checkbox" data-onwr="' + lid + '"' + (n ? "" : " disabled") + "> " +
          '<i class="sw ' + (lid === "flood-area-poly" ? "onwr-obs" : "onwr-c2") + '"></i> ' + label + ' <span class="lc">' + num(n, 0) + "</span></label>";
      }).join("") +
      '<p class="imp-onwr-key"><span class="sw onwr-c1"></span>1 <span class="sw onwr-c2"></span>2 <span class="sw onwr-c3"></span>3 ระดับความเสี่ยง</p>';
    div.addEventListener("change", (e) => {
      const lid = e.target && e.target.dataset ? e.target.dataset.onwr : null;
      const g = lid && onwrGroups[lid];
      if (!g) return;
      if (e.target.checked) g.addTo(mapRef); else g.remove();
    });
    box.appendChild(div);
    onwrBox = div;
  }

  // a plan's day on the map (owner 2026-10-06: a flood view per release scenario; D-019: the river, never land): each piece
  // of the river takes its nearest gauge's margin that day — red over the bank, orange inside that day's model error
  let reachLayers = {}, reachLegend = null;
  const REACH = { over: "#d32f2f", near: "#f57c00", ok: "#1565c0", none: "#9e9e9e" };
  function colorReaches(cmp, p, d) {
    if (!mapRef || !p || !p.downstream) return;
    for (const [code, lines] of Object.entries(reachLayers)) {
      const row = (p.downstream[code] || [])[d] || {};
      const k = row.status || "none", m = row.margin_m, rq = cmp.margin_req ? cmp.margin_req[code] : null;
      const req = Array.isArray(rq) ? rq[d] : rq;
      const vill = k === "near" || k === "over" ? villagesText(cmp, code) : "";
      const tip = esc(code) + " วันที่ " + (d + 1) + ": " + (m == null ? "ไม่มีข้อมูล" : m < 0 ? "เกินตลิ่ง " + num(-m, 2) + " ม." : "ห่างตลิ่ง " + num(m, 2) + " ม.") +
        (req != null ? " (คลาดเคลื่อน ±" + num(req, 2) + ")" : "") + (row.outside ? " · ⚠ นอกช่วงข้อมูล" : "") + (vill ? "<br>" + esc(vill) : "");
      for (const l of lines) { l.setStyle({ color: REACH[k], dashArray: row.outside ? "8 6" : null }); l.setTooltipContent(tip); }
    }
    if (reachLegend) reachLegend.remove();
    reachLegend = L.control({ position: "topright" });
    reachLegend.onAdd = () => {
      const div = L.DomUtil.create("div", "imp-reach-legend");
      div.innerHTML = "<b>" + esc(p.label || planWords(p)) + " · วันที่ " + (d + 1) + "</b><br>" +
        '<span class="lg lg-over">━</span> เกินตลิ่ง <span class="lg lg-near">━</span> ใกล้ตลิ่ง <span class="lg lg-ok">━</span> รับน้ำได้ ' +
        '<span class="lg lg-x">┅</span> นอกช่วงข้อมูล<br><small>สีแม่น้ำ = ห่างตลิ่งของสถานีที่ใกล้ที่สุด (ไม่เกิน 10 กม.) ไม่ใช่พื้นที่น้ำท่วม</small>';
      return div;
    };
    reachLegend.addTo(mapRef);
  }

  function showCaseOnMap(st, toMapTab = true) {
    if (!mapRef) return;
    const pts = [].concat(...(st.river_line || []), st.points.filter((p) => p.lat != null).map((p) => [p.lat, p.lon]),
      st.dam_latlon ? [st.dam_latlon] : []);
    if (narrow() && toMapTab) setTab("map");
    // desktop: keep clear of the legend box at the bottom right
    setTimeout(() => { if (pts.length) mapRef.fitBounds(L.latLngBounds(pts), { paddingTopLeft: [24, 24],
      paddingBottomRight: [narrow() ? 24 : 300, 24] }); }, narrow() ? 120 : 0);
  }

  /* ---------- 7-day release scenarios (D-101): plans found by search, judged on every effect, ★ by a stated rule ---------- */
  const EFFECT_TH = { city: "ปกป้องตัวเมือง", worst: "ห่างตลิ่งมากสุด", total: "ท่วมรวมน้อยสุด", dam: "ความปลอดภัยเขื่อน",
    curve: "กลับใต้เส้นควบคุมเร็ว", water: "เก็บน้ำไว้ใช้", warning: "เตือนล่วงหน้าได้" };
  const EFFECT_ICON = { city: "🏙️", worst: "🌊", total: "📏", dam: "🏞️", curve: "📉", water: "💧", warning: "⏱" };
  const CELL_TH = { ok: "รับน้ำได้", near: "ห่างตลิ่งน้อยกว่าความคลาดเคลื่อน", over: "เกินตลิ่ง", none: "ไม่มีข้อมูล" };
  const EFFECT_ROWS = [["city", "ห่างตลิ่งในเมืองต่ำสุด (ม.)", (e) => num(e.city_margin_min, 2)],
    ["worst", "ห่างตลิ่งต่ำสุดทุกจุด (ม.)", (e) => num(e.worst_margin_min, 2)],
    ["total", "เกินตลิ่งรวม (ม.·จุด·วัน)", (e) => num(e.overtop_sum, 2)],
    ["dam", "ปริมาตรสูงสุด (ล้าน ลบ.ม.) · วันเหนือปกติ", (e) => num(e.storage_peak, 0) + " · " + num(e.days_above_normal, 0)],
    ["curve", "กลับใต้เส้นควบคุมบน", (e) => (e.under_curve_day ? "วันที่ " + num(e.under_curve_day, 0) : "ไม่ใน 7 วัน")],
    ["water", "ปริมาตรวันที่ 7 (ล้าน ลบ.ม.)", (e) => num(e.storage_end, 0)],
    ["warning", "เปลี่ยนอัตราวันละไม่เกิน (ล้าน ลบ.ม.)", (e) => num(e.ramp_max, 1)]];

  function planWords(p) {
    const r = p.release, same = r.every((x) => x === r[0]);
    if (p.kind === "hold" || p.kind === "constant" || same) return num(r[0], 1) + " ล้าน ลบ.ม./วัน คงที่ 7 วัน" + (p.kind === "hold" ? " (เท่าวันนี้)" : "");
    if (p.kind === "ramp") return "ทยอย" + (r[6] > r[0] ? "เพิ่ม" : "ลด") + "จาก " + num(r[0], 1) + " เป็น " + num(r[6], 1) + " ล้าน ลบ.ม./วัน ใน 7 วัน";
    if (p.kind === "front") { const k = r.findIndex((x, i) => i > 0 && x !== r[0]); return num(r[0], 1) + " ล้าน ลบ.ม./วัน " + num(k, 0) + " วันแรก แล้ว " + num(r[k], 1); }
    return "รายวัน " + r.map((x) => num(x, 1)).join(", ") + " ล้าน ลบ.ม./วัน";
  }

  const RANK = { none: 0, ok: 1, near: 2, over: 3 };
  const worstDay = (p) => (p.days || []).reduce((b, d, i, a) => (RANK[d.status] > RANK[a[b].status] ||
    (RANK[d.status] === RANK[a[b].status] && (d.worst_margin == null ? 1e9 : d.worst_margin) < (a[b].worst_margin == null ? 1e9 : a[b].worst_margin)) ? i : b), 0);
  function dayRange(days) {  // [1,2,3,5] → "1–3, 5"
    const out = []; let s = null, p = null;
    for (const d of [...days].sort((x, y) => x - y)) {
      if (s === null) { s = p = d; } else if (d === p + 1) { p = d; } else { out.push(p > s ? s + "–" + p : String(s)); s = p = d; }
    }
    if (s !== null) out.push(p > s ? s + "–" + p : String(s));
    return out.join(", ");
  }
  const outsideText = (p) => "นอกช่วงข้อมูล: " + (p.outside_detail || []).map((o) => o.code + " " + num(o.flow_max, 0) +
    " ลบ.ม./วิ (เคยวัดสูงสุด " + num(o.qmax, 0) + ") วันที่ " + dayRange(o.days)).join(" · ");
  function villagesText(cmp, code) {  // "ริมแม่น้ำ B.16: บ้าน…, บ้าน… และอีก 3 (อ.บ้านลาด)" — at most 4 names (no long paragraph)
    const v = (cmp.places || {})[code] || [];
    if (!v.length) return "";
    const names = v.map((x) => x.village).filter(Boolean), amph = [...new Set(v.map((x) => x.amphoe).filter(Boolean))];
    return "ริมแม่น้ำ " + code + ": " + (names.length ? names.slice(0, 4).join(", ") + (names.length > 4 ? " และอีก " + (names.length - 4) : "") : "") +
      (amph.length ? " (อ." + amph.join(", อ.") + ")" : "");
  }
  const shortWhy = (p) => (p.effects.under_curve_day ? "กลับใต้เส้นควบคุมวันที่ " + num(p.effects.under_curve_day, 0) : "ลดอ่างได้มากสุด") +
    " ทุกจุดห่างตลิ่งเกินความคลาดเคลื่อน";
  const customParam = () => (state.customs.length ? "release=" + encodeURIComponent(state.customs.map((c) => c.join(",")).join(";")) : "");

  async function loadScenarios(st, body) {
    const sec = $("#imp-sc", body);
    if (!sec) return;
    sec.innerHTML = '<h3>แผนระบาย 7 วันข้างหน้า</h3><p class="muted">กำลังคำนวณ…</p>';
    const qp = customParam();
    let r;
    try { r = await api("/api/impact/case/" + encodeURIComponent(st.case) + "/scenarios" + (qp ? "?" + qp : "")); }
    catch (e) { sec.innerHTML = '<h3>แผนระบาย 7 วันข้างหน้า</h3><p class="imp-err">เชื่อมต่อไม่ได้</p>'; return; }
    if (r.status === 401) { state.authed = false; return showLogin("หมดเวลาเข้าสู่ระบบ กรุณาเข้าใหม่"); }
    if (r.status === 503) { sec.innerHTML = '<h3>แผนระบาย 7 วันข้างหน้า</h3><p class="muted">ยังไม่พร้อม: ต้องมีเส้นควบคุม น้ำไหลเข้า และปริมาตรปกติของวันนี้ (คำนวณใหม่ทุกชั่วโมง)</p>'; return; }
    if (!r.ok) { sec.innerHTML = '<h3>แผนระบาย 7 วันข้างหน้า</h3><p class="imp-err">คำนวณไม่ได้ (' + r.status + ")</p>"; return; }
    const cmp = await r.json();
    state.cmp = cmp;
    sec.innerHTML = scenariosHtml(cmp);
    bindGrid(sec, cmp, st);
  }

  const cmRange = (v) => (Array.isArray(v) ? num(v[0], 0) + "→" + num(v[v.length - 1], 0) : num(v, 0));
  function redPill(cmp) {  // the downstream model the plans used: tested per day (E-7D-DOWN) or the untested what-if
    const ds = cmp.downstream || {};
    if (ds.method === "hybrid") {
      const m = ds.mae_cm || {}, k = ds.keep_cm || {};
      const d1 = Math.max(...Object.values(m).map((v) => v[0] || 0)), d7 = Math.max(...Object.values(m).map((v) => v[v.length - 1] || 0));
      const tip = "ระดับท้ายน้ำ 7 วัน: B.18 ตาม rating curve เทียบระดับวันนี้ · จุดอื่น = ระดับวันนี้ + การตอบสนองต่อการระบายที่เรียนรู้ (ไม่ติดลบ)" +
        " · ทดสอบย้อนหลัง " + (ds.window ? day(ds.window[0]) + "–" + day(ds.window[1]) : "") + " (แต่ละเดือนใช้ค่าที่เรียนจากเดือนอื่น)" +
        " · คลาดเคลื่อนเฉลี่ยวันที่ 1→7 (ซม.): " + Object.keys(m).map((c) => c + " " + cmRange(m[c]) + " (คงระดับวันนี้ " + cmRange(k[c]) + ")").join(", ") +
        " · แผนต้องห่างตลิ่งมากกว่าค่านี้ในแต่ละวัน — ใช้เทียบระหว่างแผน ไม่ใช่ค่าพยากรณ์";
      return '<button type="button" class="conf-badge imp-text" title="' + esc(tip) + '" aria-label="ความคลาดเคลื่อนท้ายน้ำ">🟠 ท้ายน้ำ ±' + num(d1, 0) + "–" + num(d7, 0) + " ซม.</button>";
    }
    return '<button type="button" class="conf-badge imp-red" title="ระดับท้ายน้ำจาก rating curve + เวลาเดินทาง ยังไม่ผ่านการทดสอบย้อนหลัง (ความคลาดเคลื่อน ' +
      Object.entries(cmp.margin_req || {}).map(([c, m]) => esc(c) + " " + (Array.isArray(m) ? cmRange(m.map((x) => x * 100)) : num(m * 100, 0)) + " ซม.").join(", ") +
      ') — ใช้เทียบระหว่างแผน ไม่ใช่ค่าพยากรณ์">🔴 ท้ายน้ำยังไม่ผ่านการทดสอบ</button>';
  }

  function gridPlans(cmp) {  // ★, today, the engine's picks, the session's own plans; the ladder apart (D-110)
    const by = Object.fromEntries(cmp.plans.map((p) => [p.id, p]));
    const star = by[(cmp.optimal || {}).id], hold = cmp.plans.find((p) => p.kind === "hold");
    const picks = (cmp.picks || []).map((id) => by[id]).filter((p) => p && p !== star && p !== hold);
    const customs = cmp.plans.filter((p) => p.kind === "custom");
    const seen = new Set(), rows = [];
    for (const p of [star, hold, ...picks, ...customs]) if (p && !seen.has(p.id)) { seen.add(p.id); rows.push(p); }
    return { rows, ladder: (cmp.ladder || []).map((id) => by[id]).filter(Boolean), star };
  }

  function cellTitle(d, i) {
    return "วันที่ " + (i + 1) + ": " + CELL_TH[d.status] + (d.worst_code ? " · " + d.worst_code + " ห่างตลิ่ง " + num(d.worst_margin, 2) + " ม." +
      (d.worst_req != null ? " (คลาดเคลื่อน ±" + num(d.worst_req, 2) + ")" : "") : "") + (d.outside ? " · ⚠ นอกช่วงข้อมูล" : "") +
      (d.km ? " · แม่น้ำ " + num(d.km, 0) + " กม." : "");
  }

  function gridRow(p, isStar) {
    const e = p.effects, worst = e.worst_margin_min;
    const icons = (p.best_for || []).map((k) => '<span class="imp-gi" title="' + esc("เหมาะกับ" + EFFECT_TH[k]) + '" aria-label="' +
      esc("เหมาะกับ" + EFFECT_TH[k]) + '">' + EFFECT_ICON[k] + "</span>").join("");
    const out = p.outside_any ? '<span class="imp-out" title="' + esc(outsideText(p)) + '" aria-label="นอกช่วงข้อมูล">⚠</span>' : "";
    const cells = (p.days || []).map((d, i) => '<td class="imp-c imp-c-' + d.status + (d.outside ? " imp-c-x" : "") +
      (state.day === i ? " imp-dsel" : "") + '" data-day="' + i + '" title="' + esc(cellTitle(d, i)) + '"><span></span></td>').join("");
    return '<tr class="imp-gr' + (p.feasible ? "" : " imp-infeasible") + (p.kind === "custom" ? " imp-custom-row" : "") +
      (state.selPlan === p.id ? " imp-sel" : "") + '" data-plan="' + esc(p.id) + '" tabindex="0">' +
      '<th scope="row"><span class="imp-gl">' + (isStar ? "★ " : "") + esc(p.label) + "</span>" + icons + out +
      '<small class="imp-km-sub">' + (p.km_max ? num(p.km_max, 0) + " กม." : "") + "</small></th>" + cells +
      "<td>" + num(e.storage_end, 0) + "</td><td" + (worst != null && worst < 0 ? ' class="imp-neg"' : "") + ">" + num(worst, 2) + "</td>" +
      '<td class="imp-col-km">' + num(p.km_max || 0, 0) + "</td>" +
      '<td><button type="button" class="imp-open" aria-label="' + esc("รายละเอียด " + p.label) + '">›</button></td></tr>';
  }

  function scenariosHtml(cmp) {
    const { rows, ladder, star } = gridPlans(cmp);
    const opt = cmp.optimal || {};
    const head = '<thead><tr><th scope="col">แผน <small>ล้าน ลบ.ม./วัน</small></th>' +
      [0, 1, 2, 3, 4, 5, 6].map((i) => '<th scope="col" class="imp-dh' + (state.day === i ? " imp-dsel" : "") + '"><button type="button" data-dayh="' + i +
        '" aria-label="' + esc("วันที่ " + (i + 1) + " " + dayShort(cmp.dates ? cmp.dates[i] : null) + " บนแผนที่") + '">' + (i + 1) + "</button></th>").join("") +
      '<th scope="col">อ่าง<small>วันที่ 7</small></th><th scope="col">ห่างตลิ่ง<small>ม.</small></th><th scope="col" class="imp-col-km">กม.</th>' +
      '<th scope="col"><span class="imp-sr">เปิด</span></th></tr></thead>';
    const lad = ladder.length ? '<tbody><tr class="imp-ladder-t"><td colspan="12"><button type="button" class="imp-ladder-btn" aria-expanded="false">▸ ระบายคงที่ทุกระดับ (' +
      num(ladder[0].release[0], 0) + "–" + num(ladder[ladder.length - 1].release[0], 0) + ")</button></td></tr></tbody>" +
      '<tbody class="imp-ladder" hidden>' + ladder.map((p) => gridRow(p, star && p.id === star.id)).join("") + "</tbody>" : "";
    const why = !star ? esc(opt.reason || "ยังไม่มีแผนให้เปรียบเทียบ")
      : opt.constraints_met ? "★ ตามเกณฑ์: " + esc(shortWhy(star)) : "⚠️ ยังไม่มีแผนที่เข้าเกณฑ์ — ★ คือแผนที่ใกล้เคียงที่สุด";
    return '<h3>แผนระบาย 7 วันข้างหน้า ' + redPill(cmp) + "</h3>" +
      '<div class="imp-scroll"><table class="imp-grid">' + head + "<tbody>" + rows.map((p) => gridRow(p, star && p.id === star.id)).join("") + "</tbody>" + lad + "</table></div>" +
      '<p class="imp-key"><span class="imp-k imp-c-ok"></span>รับน้ำได้ <span class="imp-k imp-c-near"></span>ใกล้ตลิ่ง <span class="imp-k imp-c-over"></span>เกินตลิ่ง ' +
      '<span class="imp-k imp-c-ok imp-c-x"></span>นอกช่วงข้อมูล ' +
      info("สีของวัน = สถานีที่ห่างตลิ่งน้อยที่สุดในวันนั้น: น้ำเงิน รับน้ำได้ · ส้ม ห่างตลิ่งน้อยกว่าความคลาดเคลื่อนที่ทดสอบของวันนั้น · แดง เกินตลิ่ง · " +
        "ลาย = มีสถานีที่น้ำมากกว่าที่เคยวัดได้ (ระดับจากการต่อเส้นโค้งออกไป) · อ่าง = ปริมาตรวันที่ 7 (ล้าน ลบ.ม.) · ห่างตลิ่ง = ต่ำสุดทุกจุดทุกวัน (ม.) · " +
        "กม. = แม่น้ำช่วงที่สถานีใกล้หรือเกินตลิ่ง มากที่สุดในวันใดวันหนึ่ง · แตะเลขวันเพื่อดูวันนั้นบนแผนที่", "วิธีอ่านตาราง") + "</p>" +
      '<p class="imp-why">' + why + " " + info((opt.rule || "") + " · " + (opt.reason || "") + " · เข้าเกณฑ์ " + num(cmp.feasible, 0) +
        " จาก " + num(cmp.candidates, 0) + " แผน", "เกณฑ์ของ ★") + "</p>" +
      '<div class="imp-actions"><button type="button" class="btn" id="imp-custom-btn">➕ ลองแผนเอง</button>' + aiMenuHtml() + "</div>";
  }

  function bindGrid(sec, cmp, st) {
    const by = Object.fromEntries(cmp.plans.map((p) => [p.id, p]));
    const select = (id) => {
      if (!by[id]) return;
      state.selPlan = id;
      sec.querySelectorAll(".imp-gr").forEach((tr) => tr.classList.toggle("imp-sel", tr.dataset.plan === id));
      colorReaches(cmp, by[id], state.day != null ? state.day : worstDay(by[id]));
    };
    sec.querySelectorAll(".imp-gr").forEach((tr) => {
      const id = tr.dataset.plan;
      tr.addEventListener("click", (e) => {
        if (e.target.closest(".conf-badge, .imp-out, .imp-gi")) return;
        if (e.target.closest(".imp-open") || narrow()) { openPlanSheet(cmp, id); return; }
        select(id);
      });
      tr.addEventListener("keydown", (e) => { if (e.key === "Enter") openPlanSheet(cmp, id); });
    });
    sec.querySelectorAll("[data-dayh]").forEach((b) => b.addEventListener("click", () => {
      const d = Number(b.dataset.dayh);
      state.day = state.day === d ? null : d;  // a second click on the same day goes back to each plan's worst day
      sec.querySelectorAll(".imp-dh").forEach((th, i) => th.classList.toggle("imp-dsel", i === state.day));
      sec.querySelectorAll(".imp-c").forEach((td) => td.classList.toggle("imp-dsel", Number(td.dataset.day) === state.day));
      select(state.selPlan && by[state.selPlan] ? state.selPlan : (cmp.optimal || {}).id);
    }));
    const lb = $(".imp-ladder-btn", sec);
    if (lb) lb.addEventListener("click", () => {
      const tb = $(".imp-ladder", sec), open = tb.hidden;
      tb.hidden = !open;
      lb.setAttribute("aria-expanded", String(open));
      lb.textContent = (open ? "▾" : "▸") + lb.textContent.slice(1);
    });
    $("#imp-custom-btn", sec).addEventListener("click", () => openCustomSheet(st, sec.closest("#imp-body"), cmp));
    bindAi(sec, st);
    select(state.selPlan && by[state.selPlan] ? state.selPlan : (cmp.optimal || {}).id);  // the map shows the ★ until a row is picked
  }

  // AI entry points (Task 12 replaces these two stubs)
  function aiMenuHtml() { return ""; }
  function bindAi() { /* Task 12 */ }

  function matrixHtml(cmp) {
    const plans = cmp.plans.filter((p) => !(p.roles && p.roles.length === 1 && p.roles[0] === "ladder"));
    return '<div class="imp-scroll"><table><thead><tr><th scope="col">ผล</th>' +
      plans.map((p) => '<th scope="col">' + (p.optimal ? "★ " : "") + esc(planWords(p)) + "</th>").join("") + "</tr></thead><tbody>" +
      EFFECT_ROWS.map(([k, label2, fmt]) => '<tr><th scope="row">' + label2 + "</th>" + plans.map((p) => "<td" + (cmp.best_for[k] === p.id ? ' class="imp-best"' : "") + ">" + fmt(p.effects) + "</td>").join("") + "</tr>").join("") +
      "</tbody></table></div>" + scenarioNotes(cmp);
  }

  function scenarioNotes(cmp) {
    const inf = cmp.inflow || {}, inputs = cmp.inputs || {};
    const rain = inputs.rain7 && inputs.rain7.mm ? inputs.rain7.mm.reduce((a, b) => a + b, 0) : null;
    return '<ul class="imp-facts"><li>★ เกณฑ์: ' + esc(cmp.optimal.rule || "") + "</li>" +
      "<li>ค้นหาแผน " + num(cmp.candidates, 0) + " แบบ (คงที่ ทยอย และสองช่วง) ในช่วง 0–" + num(cmp.max_release, 0) + " ล้าน ลบ.ม./วัน — " + esc(inputs.release_cap_note || "") + "</li>" +
      "<li>เข้าเกณฑ์ " + num(cmp.feasible, 0) + " แบบ: " + (cmp.constraints || []).map(esc).join(" · ") + "</li>" +
      "<li>น้ำไหลเข้า: " + (inf.method === "model" ? "" : "คิดว่าเท่าวันนี้ต่อไป ") + "ช่วง 7 วัน " + num(inf.low[6], 1) + "–" + num(inf.high[6], 1) + " ล้าน ลบ.ม./วัน · " + esc(inf.note || "") + "</li>" +
      (rain != null ? "<li>☁️ ฝนคาดการณ์ในลุ่มน้ำเหนือเขื่อน 7 วัน รวม " + num(rain, 0) + " มม. (" + (inf.method === "model" ? "ใช้ในแบบจำลองน้ำไหลเข้า" : "ดูประกอบ ไม่ได้ใช้คำนวณ") + ")</li>" : "") +
      "<li>อ่าง: สมดุลน้ำรายวัน (ตรวจกับข้อมูล สสน. 2561–69: มัธยฐานของส่วนต่าง −0.15 ล้าน ลบ.ม./วัน) · ท้ายน้ำ: " + ((cmp.downstream || {}).method === "hybrid"
        ? "B.18 ตาม rating curve เทียบระดับวันนี้ จุดอื่น = ระดับวันนี้ + การตอบสนองต่อการระบายที่เรียนรู้ (ไม่ติดลบ) เวลาเดินทางเป็นวัน · ฝนในพื้นที่ท้ายเขื่อนไม่ช่วยในการทดสอบ จึงไม่ใช้"
        : "rating curve + เวลาเดินทางเป็นวัน น้ำท่าระหว่างทางและการผันที่เขื่อนเพชรคงที่") + "</li></ul>";
  }

  function openCustomSheet(st, body, cmp) {
    const today = (cmp.dam || {}).released_mcm != null ? cmp.dam.released_mcm : 10;
    openSheet('<h2>กำหนดแผนเอง</h2><p class="muted">ล้าน ลบ.ม./วัน วันที่ 1–7 · ผลจะปรากฏเป็นแถวในรายการแผน</p>' +
      '<form id="imp-custom" class="imp-custom">' + [1, 2, 3, 4, 5, 6, 7].map((i) => "<label>วันที่ " + i + '<input type="number" inputmode="decimal" step="0.1" min="0" max="200" value="' + esc(today) + '"></label>').join("") +
      '<button class="btn primary" type="submit">คำนวณ</button></form>', (box) => {
      const f = box.querySelector("#imp-custom");
      f.addEventListener("submit", (e) => {
        e.preventDefault();
        document.getElementById("sheet").hidden = true;
        loadScenarios(st, body, [...f.querySelectorAll("input")].map((i) => Number(i.value) || 0));
      });
    });
  }

  const dayShort = (ymd) => (ymd ? new Date(String(ymd).slice(0, 10) + "T12:00:00+07:00").toLocaleDateString("th-TH",
    { timeZone: "Asia/Bangkok", day: "numeric", month: "short" }) : "–");

  function chartSvg(p, cmp) {
    // storage (mid, band) against the upper rule curve and the normal storage, 7 days; SVG attributes only (no inline
    // styles). The y-range follows the data so a 50-unit fall is visible; ticks at the left, the legend in HTML below.
    const W = 340, H = 140, L = 46, R = 10, T = 10, B = 22, n = p.storage.length;
    // the axis follows the storage; a reference line far outside it (Pa Sak's curve 490 below) is named, not drawn —
    // stretching the axis to it flattened the 7-day path into a line at the top (v0.31 visitor check)
    const sv = [].concat(p.storage, p.storage_low, p.storage_high);
    let lo = Math.min(...sv), hi = Math.max(...sv);
    const span = Math.max(hi - lo, 20);
    const near = (v) => v != null && v >= lo - span && v <= hi + span;
    const hasUpper = (cmp.upper || []).length > 0 && cmp.upper.every((v) => v != null);
    const upperIn = hasUpper && cmp.upper.every(near);
    const normalIn = cmp.normal != null && near(cmp.normal);
    if (upperIn) { lo = Math.min(lo, ...cmp.upper); hi = Math.max(hi, ...cmp.upper); }
    if (normalIn) { lo = Math.min(lo, cmp.normal); hi = Math.max(hi, cmp.normal); }
    lo = Math.floor((lo - 5) / 10) * 10; hi = Math.ceil((hi + 5) / 10) * 10;
    const x = (i) => L + (i * (W - L - R)) / (n - 1), y = (v) => T + (H - T - B) - ((v - lo) * (H - T - B)) / (hi - lo);
    const line = (arr) => arr.map((v, i) => x(i).toFixed(1) + "," + y(v).toFixed(1)).join(" ");
    const band = line(p.storage_high) + " " + p.storage_low.map((v, i) => x(n - 1 - i).toFixed(1) + "," + y(p.storage_low[n - 1 - i]).toFixed(1)).join(" ");
    const tick = (v) => "<line x1=\"" + (L - 4) + "\" x2=\"" + (W - R) + "\" y1=\"" + y(v).toFixed(1) + "\" y2=\"" + y(v).toFixed(1) + "\" stroke=\"#e3e7ec\" stroke-width=\"1\"></line>" +
      "<text x=\"" + (L - 6) + "\" y=\"" + (y(v) + 3.5).toFixed(1) + "\" text-anchor=\"end\" font-size=\"10\" fill=\"#5b6573\">" + num(v, 0) + "</text>";
    const normal = normalIn ? "<line x1=\"" + L + "\" x2=\"" + (W - R) + "\" y1=\"" + y(cmp.normal).toFixed(1) + "\" y2=\"" + y(cmp.normal).toFixed(1) + "\" stroke=\"#c62828\" stroke-width=\"1.2\" stroke-dasharray=\"2 3\"></line>" : "";
    const days = [0, Math.floor((n - 1) / 2), n - 1].map((i) => "<text x=\"" + x(i).toFixed(1) + "\" y=\"" + (H - 6) + "\" text-anchor=\"" + (i === 0 ? "start" : i === n - 1 ? "end" : "middle") + "\" font-size=\"10\" fill=\"#5b6573\">" + esc(dayShort(cmp.dates ? cmp.dates[i] : null)) + "</text>").join("");
    return "<svg class=\"imp-svg\" viewBox=\"0 0 " + W + " " + H + "\" role=\"img\" aria-label=\"ปริมาตรอ่าง 7 วันเทียบเส้นควบคุม\">" +
      tick(lo) + tick(Math.round((lo + hi) / 20) * 10) + tick(hi) +
      "<polygon points=\"" + band + "\" fill=\"#1565c0\" fill-opacity=\"0.15\"></polygon>" +
      (upperIn ? "<polyline points=\"" + line(cmp.upper) + "\" fill=\"none\" stroke=\"#e46c0a\" stroke-width=\"2\" stroke-dasharray=\"4 3\"></polyline>" : "") + normal +
      "<polyline points=\"" + line(p.storage) + "\" fill=\"none\" stroke=\"#1565c0\" stroke-width=\"2.5\"></polyline>" + days + "</svg>" +
      "<p class=\"imp-legend\"><span class=\"lg lg-st\">ปริมาตรอ่าง (ช่วงน้ำไหลเข้าต่ำ–สูง)</span>" +
      (upperIn ? "<span class=\"lg lg-up\">เส้นควบคุมบน</span>" : hasUpper ? "<span class=\"lg lg-up\">เส้นควบคุมบน " + num(cmp.upper[0], 0) + "–" + num(cmp.upper[cmp.upper.length - 1], 0) +
        " (นอกกราฟ, " + (cmp.upper[0] < lo ? "ต่ำกว่า" : "สูงกว่า") + ")</span>" : "") +
      (normal ? "<span class=\"lg lg-no\">ปริมาตรปกติ " + num(cmp.normal, 0) + "</span>" : cmp.normal != null ? "<span class=\"lg lg-no\">ปริมาตรปกติ " + num(cmp.normal, 0) + " (นอกกราฟ)</span>" : "") + "</p>";
  }

  function askBox(label, heading) {  // the ✨ story card's markup (app.js bindAskUrl/fillStory), with our own words
    return '<div class="imp-ask"><button type="button" class="ai-btn" aria-expanded="false">' + esc(label) + "</button>" +
      '<div class="story" hidden><div class="story-h"><span>' + esc(heading) + '</span><button type="button" class="story-speak" title="ฟังเสียงอ่าน" aria-label="ฟังเสียงสรุป">🔊 ฟังเสียง</button></div>' +
      '<div class="story-body" aria-live="polite"></div></div></div>';
  }

  function outsideNote(st) {  // the ⓘ behind every outside label; the largest release on record comes from the state
    const ys = ((st && st.dam && st.dam.yearly_max) || []).filter((y) => y.max_mcm != null);
    const big = ys.reduce((b, y) => (!b || y.max_mcm > b.max_mcm ? y : b), null);
    return "นอกช่วงข้อมูล = น้ำที่สถานีมากกว่าที่เคยวัดได้ในข้อมูลที่ใช้หา rating curve ระดับวันนั้นจึงมาจากการต่อเส้นโค้งออกไป · " +
      "แบบจำลองท้ายน้ำเรียนจากช่วงที่เขื่อนทดน้ำเพชรรับการเปลี่ยนแปลงของการระบายไว้ น้ำที่เกินความจุคลองจะลงแม่น้ำ ระดับจริงจึงอาจสูงกว่าที่แสดง" +
      (big ? " · การระบายสูงสุดที่มีบันทึก " + num(big.max_mcm, 1) + " ล้าน ลบ.ม./วัน (" + day(big.date) + ") — สสน. ไม่มีข้อมูลระดับแม่น้ำปีนั้นให้ตรวจสอบ" : "");
  }

  function riverGridHtml(cmp, p, sel) {  // 5 gauges × 7 days: each cell the server's status, the margin in m, hatched outside
    const codes = Object.keys(p.downstream || {});
    const head = '<thead><tr><th scope="col">สถานี</th>' + p.release.map((r, i) => '<th scope="col">' + (i + 1) + "</th>").join("") + "</tr></thead>";
    const body = codes.map((c) => '<tr><th scope="row">' + esc(c) + "</th>" + p.downstream[c].map((r, i) => {
      const rq = cmp.margin_req ? cmp.margin_req[c] : null, req = Array.isArray(rq) ? rq[i] : rq;
      return '<td class="imp-m imp-rc-' + (r.status || "none") + (r.outside ? " imp-c-x" : "") + (i === sel ? " imp-dsel" : "") + '" data-day="' + i + '" title="' +
        esc(c + " วันที่ " + (i + 1) + ": " + CELL_TH[r.status || "none"] + (req != null ? " · คลาดเคลื่อน ±" + num(req, 2) : "") + (r.outside ? " · ⚠ นอกช่วงข้อมูล" : "")) +
        '">' + num(r.margin_m, 2) + "</td>";
    }).join("") + "</tr>").join("");
    return '<div class="imp-scroll"><table class="imp-rgrid">' + head + "<tbody>" + body + "</tbody></table></div>";
  }

  function coverageHtml(cmp, p) {  // river km near or over the bank, and the villages along those stretches (D-110)
    const days = (p.days || []).map((d, i) => [d, i]).filter(([d]) => d.km > 0);
    if (!days.length) return '<p class="imp-cover">🌊 ไม่มีช่วงใดของแม่น้ำใกล้ตลิ่งใน 7 วัน</p>';
    const codes = [...new Set(days.flatMap(([d]) => d.codes || []))];
    const vill = codes.map((c) => villagesText(cmp, c)).filter(Boolean);
    return '<p class="imp-cover">🌊 แม่น้ำใกล้/เกินตลิ่ง วันที่ ' + dayRange(days.map(([, i]) => i + 1)) + " ราว " + num(Math.max(...days.map(([d]) => d.km)), 0) +
      " กม. (" + codes.map(esc).join(", ") + ") " + info("กม. = ความยาวแม่น้ำช่วงที่สถานีที่ใกล้ที่สุด (ไม่เกิน 10 กม.) ใกล้หรือเกินตลิ่งในวันนั้น — " +
        "สถานีเดียวแทนทั้งช่วง จึงเป็นค่าหยาบ · หมู่บ้าน: © OpenStreetMap contributors · ไม่ใช่พื้นที่น้ำท่วม", "กม. และหมู่บ้าน") + "</p>" +
      (vill.length ? '<ul class="imp-cover-v">' + vill.map((v) => "<li>" + esc(v) + "</li>").join("") + "</ul>" : "");
  }

  function openPlanSheet(cmp, id) {
    const p = cmp.plans.find((x) => x.id === id);
    if (!p) return;
    const opt = cmp.optimal || {}, isStar = p.id === opt.id, e = p.effects;
    const kst = state.kase[state.sel];
    const sub = isStar ? (opt.constraints_met ? "★ ตามเกณฑ์ · " + shortWhy(p) : "⚠️ ยังไม่มีแผนที่เข้าเกณฑ์ — ใกล้เคียงที่สุด")
      : ((p.best_for || []).map((k) => "เหมาะกับ" + EFFECT_TH[k]).join(" · ") || (p.feasible ? "เข้าเกณฑ์" : "ไม่เข้าเกณฑ์"));
    let d0 = state.day != null ? state.day : worstDay(p);
    const daysBar = '<div class="chips imp-days" role="group" aria-label="วันบนแผนที่">' + p.release.map((r, i) =>
      '<button type="button" class="chip' + (i === d0 ? " on" : "") + '" data-day="' + i + '">' + (i + 1) + "</button>").join("") +
      '</div><p class="muted imp-small">สีแม่น้ำตามวันที่เลือก · ไม่ใช่พื้นที่น้ำท่วม</p>';
    const resRows = p.release.map((r, i) => '<tr><th scope="row">' + esc(dayShort(cmp.dates ? cmp.dates[i] : null)) + "</th><td>" + num(r, 1) + "</td><td>" +
      num(p.storage[i], 0) + " <small>(" + num(p.storage_low[i], 0) + "–" + num(p.storage_high[i], 0) + ")</small></td><td" +
      (p.storage[i] > cmp.upper[i] ? "" : ' class="imp-best"') + ">" + (p.storage[i] > cmp.upper[i] ? "+" : "") + num(p.storage[i] - cmp.upper[i], 0) + "</td></tr>").join("");
    const units = "ล้าน ลบ.ม./วัน · อ่างเป็นค่ากลาง (ช่วง = น้ำไหลเข้าต่ำ–สูง) · เทียบเส้นบน = ปริมาตร − เส้นควบคุมบนของวันนั้น · ห่างตลิ่ง = ตลิ่งของหน่วยงานผู้วัด − ระดับ · " +
      ((cmp.downstream || {}).method === "hybrid" ? "ท้ายน้ำทดสอบย้อนหลังแล้ว คลาดเคลื่อนรายวัน" : "ท้ายน้ำยังไม่ผ่านการทดสอบย้อนหลัง") +
      " · วันเหนือปริมาตรปกติ " + num(e.days_above_normal, 0) + " · เกินตลิ่งรวม " + num(e.overtop_sum, 2);
    const other = isStar ? cmp.plans.find((x) => x.kind === "hold") : cmp.plans.find((x) => x.id === opt.id);
    const cmpBox = other && other.id !== p.id ? askBox(isStar ? "✨ เทียบกับคงระบายเท่าวันนี้" : "✨ เทียบกับแผน ★", "✨ เทียบสองแผน") : "";
    openSheet("<h2>" + (isStar ? "★ " : "") + esc(planWords(p)) + (p.outside_any ? ' <span class="imp-out" title="' + esc(outsideText(p)) + '">⚠</span>' : "") + "</h2>" +
      '<p class="muted imp-sub">' + esc(sub) + " " + info(isStar ? (opt.reason || "") + " · " + (opt.rule || "") : planWords(p), "ที่มาของแผน") + "</p>" +
      daysBar + chartSvg(p, cmp) +
      '<div class="imp-scroll"><table><thead><tr><th scope="col">วัน</th><th scope="col">ระบาย</th><th scope="col">อ่าง (ช่วง)</th><th scope="col">เทียบเส้นบน</th></tr></thead><tbody>' +
      resRows + "</tbody></table></div>" +
      '<h3 class="imp-h3">ห่างตลิ่ง (ม.) <small>ตลิ่งของหน่วยงานผู้วัด</small> ' + info(units, "หน่วยและสมมติฐาน") + "</h3>" + riverGridHtml(cmp, p, d0) +
      coverageHtml(cmp, p) +
      (p.outside_any ? '<p class="imp-outline">⚠ นอกช่วงข้อมูล ' + info(outsideNote(kst), "นอกช่วงข้อมูลคืออะไร") + '</p><ul class="imp-out-list">' +
        (p.outside_detail || []).map((o) => "<li>" + esc(o.code + " " + num(o.flow_max, 0) + " ลบ.ม./วิ (เคยวัดสูงสุด " + num(o.qmax, 0) + ") วันที่ " +
          dayRange(o.days)) + "</li>").join("") + "</ul>" : "") +  // one gauge a line: five gauges in one paragraph ran past 160 characters
      '<div class="imp-actions">' + cmpBox + (narrow() ? '<button type="button" class="btn" data-map-plan="1">🗺️ ดูบนแผนที่</button>' : "") + "</div>", (box) => {
      const pick = (d) => {
        d0 = d;
        box.querySelectorAll(".imp-days [data-day]").forEach((x) => x.classList.toggle("on", Number(x.dataset.day) === d));
        box.querySelectorAll(".imp-rgrid td").forEach((td) => td.classList.toggle("imp-dsel", Number(td.dataset.day) === d));
        colorReaches(cmp, p, d);
      };
      box.querySelectorAll(".imp-days [data-day]").forEach((b) => b.addEventListener("click", () => pick(Number(b.dataset.day))));
      const mp = box.querySelector("[data-map-plan]");
      if (mp) mp.addEventListener("click", () => { document.getElementById("sheet").hidden = true; if (kst) showCaseOnMap(kst); else setTab("map"); });
      if (cmpBox && typeof bindAskUrl === "function") {
        bindAskUrl(box, "/api/impact/case/" + encodeURIComponent(st0(kst)) + "/explain?q=compare&a=" + encodeURIComponent(p.release.join(",")) +
          "&b=" + encodeURIComponent(other.release.join(",")));
      }
      pick(d0);
      if (kst && !narrow()) showCaseOnMap(kst, false);  // desktop: the coloured river beside the sheet
    });
  }
  const st0 = (kst) => (kst && kst.case) || state.sel;

  function damHtml(st) {
    const d = st.dam || {};
    if (d.released_mcm == null) return "<h2>" + damName(d.name_th) + '</h2><p class="muted">ยังไม่มีข้อมูลเขื่อน</p>';
    const box = (label, val, d2, unit, sub) => "<div><span>" + label + "</span><b>" + num(val, d2) + "</b> " + unit +
      (sub ? "<small>" + sub + "</small>" : "") + "</div>";
    const cms = (x) => (x == null ? "" : "≈ " + num(toCms(x), 0) + " ลบ.ม./วินาที");
    return "<h2>" + damName(d.name_th) + '</h2><p class="muted">' + agency(d.agency) + " · ข้อมูลรายวัน " + day(d.dam_date) + '</p><div class="imp-kv">' +
      box("ระบายรวม", d.released_mcm, 2, "ล้าน ลบ.ม./วัน", cms(d.released_mcm)) +
      box("น้ำไหลเข้าอ่าง", d.inflow_mcm, 2, "ล้าน ลบ.ม./วัน", cms(d.inflow_mcm)) +
      box("ปริมาตรอ่าง", d.storage_mcm, 1, "ล้าน ลบ.ม.", (d.storage_pct == null ? "" : num(d.storage_pct, 1) + " %") +
        (d.normal_mcm ? " · ปริมาตรปกติ " + num(d.normal_mcm, 0) : "")) +
      (d.rule_curve ? "<div><span>เส้นควบคุมวันนี้ (บน / ล่าง)</span><b>" + num(d.rule_curve.upper, 0) + " / " +
        num(d.rule_curve.lower, 0) + "</b> ล้าน ลบ.ม.<small>สสน.</small></div>" : "") +
      box("ระบายทางน้ำล้น", d.spilled_mcm, 2, "ล้าน ลบ.ม./วัน", "") + "</div>" + yearsHtml(d.yearly_max) +
      (st.dam_notes || []).map((n) => '<p class="imp-note">' + esc(n) + "</p>").join("");
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
        "<td>" + lag + "</td><td>" + (p.h_time ? when(p.h_time) : "ไม่มีข้อมูลใน 36 ชม.") + "</td></tr>";
    }).join("");
    const b10 = st.points.find((p) => p.code === "B.10") || {};
    return '<div class="imp-scroll"><table><thead><tr>' +
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
      "</ul>";
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
    return '<p class="muted"><b>' + (v.whatif_ready ? "ผ่านเกณฑ์" : "ยังไม่ผ่านเกณฑ์") + "</b> — หา rating curve เวลาเดินทาง และค่าตอบสนอง จากข้อมูลก่อน " + day(v.from) +
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
        " แต่ข้อมูลของเรายังไม่มีเหตุการณ์แบบนั้นให้ตรวจสอบ</p>");
  }

  function river7Html(st) {  // E-7D-DOWN: the 7-day method the plans use, its hindcast error per point and day
    const r = st.river7;
    if (!r || !r.errors) return "";
    const codes = st.points.map((p) => p.code).filter((c) => r.errors[c]);
    const cell = (e, k) => num(e.mae_m[k] * 100, 0) + '<small class="muted"> · ' + num(e.keep_mae_m[k] * 100, 0) + "</small>";
    return "<h3>7 วันข้างหน้า (ใช้ในแผนระบาย)</h3>" +
      '<p class="muted">B.18 ตาม rating curve เทียบระดับวันนี้ · จุดอื่น = ระดับวันนี้ + การตอบสนองต่อการระบายที่เรียนรู้ (ไม่ติดลบ) · ทดสอบย้อนหลัง ' +
      day(r.window[0]) + "–" + day(r.window[1]) + " แต่ละเดือนใช้ค่าที่เรียนจากเดือนอื่น · ตัวเลข = คลาดเคลื่อนเฉลี่ย (ซม.) · ตัวเล็ก = คงระดับวันนี้</p>" +
      '<div class="imp-scroll"><table><thead><tr><th scope="col">สถานี</th>' + [1, 2, 3, 4, 5, 6, 7].map((k) => '<th scope="col">วันที่ ' + k + "</th>").join("") +
      '<th scope="col">ซม./ลบ.ม.วิ วันที่ 7</th></tr></thead><tbody>' +
      codes.map((c) => '<tr><th scope="row">' + esc(c) + "</th>" + [0, 1, 2, 3, 4, 5, 6].map((k) => "<td>" + cell(r.errors[c], k) + "</td>").join("") +
        "<td>" + (c === "B.18" ? "rating" : num((r.gains_cm_per_cms[c] || [])[6], 2)) + "</td></tr>").join("") + "</tbody></table></div>";
  }

  function reqHtml(st) {
    const items = (st.data_request || []).map((x) => "<li><b>" + esc(x.th) + '</b><span class="imp-why">' + esc(x.why) +
      ' · <a href="/api/impact/template/' + encodeURIComponent(x.key) + '">แบบฟอร์ม CSV</a></span></li>').join("");
    return '<ol class="imp-req">' + items + "</ol>" +
      '<p class="muted">เวลาเป็นเวลาไทย ระดับเป็น ม.รทก. (ระบุหมุดของหน่วยงานในหมายเหตุ) ส่งเป็น CSV หรือ Excel' +
      " ให้ผู้ดูแลระบบที่ให้รหัสผ่านนี้</p>";
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
    return '<ul class="imp-facts">' +
      "<li>ข้อมูล: ระดับและปริมาณน้ำรายชั่วโมงย้อนหลัง 1 ปีจากสถานีของ ชป. และ สสน. และข้อมูลเขื่อนรายวัน (ชป., กฟผ.) — ทั้งหมดเป็นข้อมูลสาธารณะผ่าน สสน.</li>" +
      "<li>Rating curve ต่อสถานี h = h₀ + a·Qᵇ (ตารางด้านล่าง) ใช้ได้ในช่วงน้ำที่เคยวัดได้เท่านั้น เกินกว่านั้นคือการต่อเส้นโค้งออกไป</li>" +
      "<li>B.15 และ PCH001 (ในเมือง) ไม่มีปริมาณน้ำ จึงใช้น้ำไหลที่ B.16 ณ เวลาที่น้ำเดินทางถึง; ในเมืองระดับน้ำยังขึ้นกับน้ำขึ้นน้ำลงด้วย</li>" +
      releaseCheck(st.release_check) +
      "<li>PCH003 (สสน.) ไม่ได้ใช้: ระดับเปลี่ยนพร้อม B.18 แทบเท่ากันและไม่มีเวลาหน่วง จึงน่าจะอยู่ใกล้เขื่อน ไม่ใช่ในตัวท่ายาง ⚠️ ขอยืนยันตำแหน่ง</li>" +
      "<li>เวลาแสดงเป็นเวลาไทย (ระบบเก็บเป็น UTC); ข้อมูลเขื่อนเป็นรายวันตามวันที่หน่วยงานรายงาน; เส้นแม่น้ำจาก สสน.</li>" +
      '</ul><div class="imp-scroll"><table><thead><tr><th scope="col">สถานี</th><th scope="col">h₀ (ม.)</th><th scope="col">a</th>' +
      '<th scope="col">b</th><th scope="col">RMSE (ซม.)</th><th scope="col">Q ที่เคยวัด (ลบ.ม./วินาที)</th>' +
      '<th scope="col">จำนวนชั่วโมง</th></tr></thead><tbody>' + rows + "</tbody></table></div>";
  }

  // the page is for engineers: open on this tab unless a link points somewhere else (#s=…, #p=…)
  if (!location.hash) setTab("impact");
})();
