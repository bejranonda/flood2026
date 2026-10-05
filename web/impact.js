/* /impact — impact analysis for partner engineers, pilot Kaeng Krachan (owner 2026-10-05, D-099).
   The page shell holds no data: everything comes from /api/impact/* after login. No inline script or style (CSP). */
"use strict";
(function () {
  const $ = (s, el) => (el || document).querySelector(s);
  const main = $("#main");
  const AGENCY = { RID: "ชป.", HII: "สสน.", EGAT: "กฟผ." };
  const METHODS = [["keep", "คงระดับวันนี้"], ["absolute", "สมดุลมวล + rating curve"],
    ["anchored", "ระดับวันนี้ + ส่วนต่างจาก rating"], ["gain", "ระดับวันนี้ + ค่าตอบสนองที่เรียนรู้"]];

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (x, d) => (x == null || !isFinite(x) ? "–"
    : Number(x).toLocaleString("th-TH", { minimumFractionDigits: d, maximumFractionDigits: d }));
  const toCms = (mcm) => (mcm * 1e6) / 86400;
  const when = (iso) => (iso ? new Date(iso).toLocaleString("th-TH", { timeZone: "Asia/Bangkok", day: "numeric",
    month: "short", year: "2-digit", hour: "2-digit", minute: "2-digit" }) + " น." : "–");
  const day = (ymd) => (ymd ? new Date(ymd.slice(0, 10) + "T12:00:00+07:00").toLocaleDateString("th-TH",
    { timeZone: "Asia/Bangkok", day: "numeric", month: "short", year: "2-digit" }) : "–");
  const agency = (a) => esc(AGENCY[a] || a || "");  // station metadata comes from outside APIs: always escaped
  const api = (path, opts) => fetch(path, Object.assign({ credentials: "same-origin", cache: "no-store" }, opts || {}));
  const note = (text) => { main.innerHTML = '<p class="card">' + esc(text) + "</p>"; };

  async function load() {
    let r;
    try { r = await api("/api/impact/kaeng-krachan"); } catch (e) { return note("เชื่อมต่อไม่ได้ ลองใหม่อีกครั้ง"); }
    if (r.status === 401) return showLogin("");
    if (r.status === 503) return note("หน้านี้ยังไม่ได้ตั้งค่า (ผู้ดูแลระบบต้องตั้งรหัสผ่านก่อน)");
    if (!r.ok) return note("โหลดข้อมูลไม่สำเร็จ (" + r.status + ")");
    const st = await r.json();
    $("#logout").hidden = false;
    if (!st.points || !st.points.length) return note("ยังไม่มีข้อมูล — ระบบคำนวณใหม่ทุกชั่วโมง ลองอีกครั้งภายหลัง");
    main.innerHTML = render(st);
    bindWhatif(st);
  }

  function showLogin(msg) {
    $("#logout").hidden = true;
    main.innerHTML = '<form id="login" class="card login">' +
      "<h1>วิเคราะห์ผลกระทบการระบายน้ำ</h1>" +
      '<p class="muted">เขื่อนแก่งกระจาน → แม่น้ำเพชรบุรี (นำร่อง) · สำหรับวิศวกรที่ได้รับรหัสผ่าน</p>' +
      '<label for="pw">รหัสผ่าน</label>' +
      '<input id="pw" name="password" type="password" autocomplete="current-password" required maxlength="200">' +
      '<button class="btn primary" type="submit">เข้าสู่ระบบ</button>' +
      '<p class="err" role="alert">' + esc(msg) + "</p></form>";
    const f = $("#login");
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      $("button", f).disabled = true;
      let r;
      try {
        r = await api("/api/impact/login", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: f.password.value }) });
      } catch (err) { return showLogin("เชื่อมต่อไม่ได้ ลองใหม่อีกครั้ง"); }
      if (r.ok) return load();
      showLogin(r.status === 429 ? "ใส่รหัสผิดหลายครั้ง กรุณารอ 15 นาทีแล้วลองใหม่"
        : r.status === 503 ? "หน้านี้ยังไม่ได้ตั้งค่า" : "รหัสผ่านไม่ถูกต้อง");
    });
    $("#pw").focus();
  }

  $("#logout").addEventListener("click", async () => {
    try { await api("/api/impact/logout", { method: "POST" }); } catch (e) { /* the cookie expires by itself */ }
    showLogin("ออกจากระบบแล้ว");
  });

  function render(st) {
    const v = st.validation || {};
    const gate = v.whatif_ready
      ? '<div class="gate ok">ผลทดสอบย้อนหลังผ่านเกณฑ์ — ใช้ <a href="#whatif">ตาราง what-if</a> ได้ (อ่านข้อจำกัดก่อนใช้)</div>'
      : '<div class="gate no"><b>ยังไม่เปิดตาราง what-if</b> — ทดสอบย้อนหลังแล้ว ยังไม่มีวิธีใดทำนายระดับน้ำท้ายน้ำได้ดีกว่า' +
        " “คงระดับวันนี้ไว้” · <a href=\"#val\">ผลทดสอบ</a> · <a href=\"#req\">ข้อมูลที่ต้องการ</a></div>";
    return "<h1>" + esc(st.title) + "</h1>" +
      '<p class="muted">ข้อมูลถึง ' + when(st.data_time) + " · คำนวณ " + when(st.built_at) +
      " · เวลาไทย · ระดับ ม.รทก. ตามหมุดของหน่วยงานผู้วัด</p>" + gate +
      damHtml(st) + riverHtml(st) + valHtml(st) + whatifHtml(st) + reqHtml(st) + methodHtml(st);
  }

  function damHtml(st) {
    const d = st.dam || {};
    if (d.released_mcm == null) return '<section class="card"><h2>เขื่อนแก่งกระจาน</h2><p class="muted">ยังไม่มีข้อมูลเขื่อน</p></section>';
    const box = (label, val, d2, unit, sub) => "<div><span>" + label + "</span><b>" + num(val, d2) + "</b> " + unit +
      (sub ? "<small>" + sub + "</small>" : "") + "</div>";
    const cms = (x) => (x == null ? "" : "≈ " + num(toCms(x), 0) + " ลบ.ม./วินาที");
    return '<section class="card" id="dam"><h2>เขื่อนแก่งกระจาน <small>' + agency(d.agency) + " · ข้อมูลรายวัน " +
      day(d.dam_date) + "</small></h2><div class=\"kv\">" +
      box("ระบายรวม", d.released_mcm, 2, "ล้าน ลบ.ม./วัน", cms(d.released_mcm)) +
      box("น้ำไหลเข้าอ่าง", d.inflow_mcm, 2, "ล้าน ลบ.ม./วัน", cms(d.inflow_mcm)) +
      box("ปริมาตรอ่าง", d.storage_mcm, 1, "ล้าน ลบ.ม.", (d.storage_pct == null ? "" : num(d.storage_pct, 1) + " %") +
        (d.normal_mcm ? " · ปริมาตรปกติ " + num(d.normal_mcm, 0) : "")) +
      (d.rule_curve ? "<div><span>เส้นควบคุมวันนี้ (บน / ล่าง)</span><b>" + num(d.rule_curve.upper, 0) + " / " +
        num(d.rule_curve.lower, 0) + "</b> ล้าน ลบ.ม.<small>สสน.</small></div>" : "") +
      box("ระบายทางน้ำล้น", d.spilled_mcm, 2, "ล้าน ลบ.ม./วัน", "") + "</div>" + yearsHtml(d.yearly_max) +
      (st.dam_notes || []).map((n) => '<p class="note">' + esc(n) + "</p>").join("") + "</section>";
  }

  function yearsHtml(rows) {
    if (!rows || !rows.length) return "";
    const body = rows.map((r) => '<tr><th scope="row">' + num(r.year + 543, 0).replace(",", "") + (r.days < 300 ? "<small>ถึงวันนี้</small>" : "") +
      "</th><td>" + num(r.max_mcm, 2) + "</td><td>" + num(toCms(r.max_mcm), 0) + "</td><td>" + day(r.date) + "</td></tr>").join("");
    return "<details><summary>ระบายสูงสุดในแต่ละปี (ข้อมูลรายวันจาก สสน.)</summary><div class=\"scroll\"><table><thead><tr>" +
      '<th scope="col">ปี</th><th scope="col">สูงสุด (ล้าน ลบ.ม./วัน)</th><th scope="col">≈ ลบ.ม./วินาที</th><th scope="col">วันที่</th>' +
      "</tr></thead><tbody>" + body + "</tbody></table></div></details>";
  }

  function riverHtml(st) {
    const rows = st.points.map((p) => {
      const margin = p.h_now != null && p.bank != null ? p.bank - p.h_now : null;
      const lag = p.code === "B.18" ? "ใต้เขื่อน ~" + num(st.dam_km, 0) + " กม."
        : (p.lag_range && p.lag_range[0] !== p.lag_range[1] ? num(p.lag_range[0], 0) + "–" + num(p.lag_range[1], 0)
          : num(p.lag_h, 0)) + " ชม." +
          (p.lag_r != null ? " <small>r " + num(p.lag_r, 2) + "</small>" : "");
      return "<tr><th scope=\"row\">" + esc(p.code) + "<small>" + esc(p.name_th || "") + " · " + agency(p.agency) + "</small></th>" +
        "<td" + (margin != null && margin < 0 ? ' class="neg"' : "") + ">" + num(margin, 2) + "</td>" +
        "<td>" + num(p.h_now, 2) + "</td><td>" + num(p.bank, 2) + "</td><td>" + num(p.q_now, 0) + "</td>" +
        "<td>" + lag + "</td><td>" + (p.h_time ? when(p.h_time) : "ไม่มีข้อมูลใน 6 ชม.") + "</td></tr>";
    }).join("");
    const b10 = st.points.find((p) => p.code === "B.10") || {};
    return '<section class="card" id="river"><h2>แม่น้ำเพชรบุรีตอนนี้</h2><div class="scroll"><table><thead><tr>' +
      '<th scope="col">สถานี</th><th scope="col">ห่างตลิ่ง (ม.)</th><th scope="col">ระดับ (ม.รทก.)</th>' +
      '<th scope="col">ตลิ่ง (ม.รทก.)</th><th scope="col">น้ำไหล (ลบ.ม./วินาที)</th>' +
      '<th scope="col">น้ำจาก B.18 ถึงใน</th><th scope="col">วัดเมื่อ</th></tr></thead><tbody>' + rows + "</tbody></table></div>" +
      '<ul class="facts">' +
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
      return "<tr><th scope=\"row\">" + esc(code) + "</th>" + METHODS.map((m) => "<td" +
        (ms[m[0]] === best ? ' class="best"' : "") + ">" + num(ms[m[0]], 1) + "</td>").join("") +
        "<td>" + num(key === "methods" ? p.n : p.n_big, 0) + "</td></tr>";
    }).join("");
    return '<div class="scroll"><table><thead><tr><th scope="col">สถานี</th>' +
      METHODS.map((m) => '<th scope="col">' + m[1] + "</th>").join("") +
      '<th scope="col">จำนวนครั้ง</th></tr></thead><tbody>' + body + "</tbody></table></div>";
  }

  function valHtml(st) {
    const v = st.validation || {};
    const P = v.points || {};
    const b18 = st.points.find((p) => p.code === "B.18") || {};
    const qmax = b18.rating ? b18.rating.qmax : null;
    const order = st.points.map((p) => p.code).filter((c) => P[c]);  // down the river, not alphabetical
    const gains = order.map((c) => esc(c) + " " + num(P[c].gain_cm_per_cms, 2)).join(", ");
    return '<section class="card" id="val"><h2>ทดสอบย้อนหลัง <small>' + (v.whatif_ready ? "ผ่านเกณฑ์" : "ยังไม่ผ่านเกณฑ์") +
      "</small></h2>" +
      '<p class="muted">หา rating curve เวลาเดินทาง และค่าตอบสนอง จากข้อมูลก่อน ' + day(v.from) +
      " แล้วทดสอบกับช่วงหลังจากนั้น (ทุก 3 ชม.) โดยใช้น้ำที่วัดได้ที่ B.18 แทนการระบาย ตัวเลข = ความคลาดเคลื่อนเฉลี่ยของระดับน้ำ (ซม.)" +
      " ณ เวลาที่น้ำเดินทางถึง ช่องสีเขียว = ดีที่สุด</p>" + valTable(P, "methods", order) +
      "<details><summary>เฉพาะช่วงที่น้ำที่ B.18 เปลี่ยน ≥ 15 ลบ.ม./วินาที</summary>" + valTable(P, "methods_big", order) + "</details>" +
      '<ul class="facts"><li>ค่าตอบสนองที่เรียนรู้ (ซม. ต่อ 1 ลบ.ม./วินาทีที่ B.18): ' + gains + "</li>" +
      "<li>เกณฑ์เปิดตาราง what-if: วิธีใดวิธีหนึ่งต้องคลาดเคลื่อนน้อยกว่า “คงระดับวันนี้” อย่างน้อย 10 % ทั้งที่ B.10 และ B.16" +
      " (รวมช่วงน้ำเปลี่ยนมาก เมื่อมีอย่างน้อย 30 ครั้ง) — คำนวณใหม่ทุกชั่วโมง</li></ul>" +
      (v.whatif_ready ? "" : '<p class="note">อ่านผล: ในปีที่ผ่านมาน้ำที่ B.18 ไม่เกิน ' + num(qmax, 0) +
        " ลบ.ม./วินาที และเมื่อน้ำที่ B.18 เปลี่ยน ระดับท้ายน้ำแทบไม่เปลี่ยนตาม — น่าจะเพราะเขื่อนทดน้ำเพชรรับไว้และผันเข้าคลอง" +
        " (⚠️ ยังไม่ได้ยืนยัน) ระดับท้ายน้ำจึงขึ้นกับการบริหารเขื่อนเพชร ฝนในพื้นที่ และน้ำขึ้นน้ำลง (ในเมือง)" +
        " มากกว่าการระบายจากแก่งกระจาน การระบายขนาดใหญ่ที่เกินความจุคลองจะต้องผ่านลงแม่น้ำ" +
        " แต่ข้อมูลของเรายังไม่มีเหตุการณ์แบบนั้นให้ตรวจสอบ</p>") + "</section>";
  }

  function whatifHtml(st) {
    const v = st.validation || {};
    if (!v.whatif_ready) {
      return '<section class="card off" id="whatif"><h2>ตาราง what-if <small>ปิดอยู่</small></h2>' +
        '<p class="muted">“ถ้าเขื่อนระบาย X ล้าน ลบ.ม./วัน น้ำจะถึงแต่ละจุดเมื่อไร สูงเท่าไร ล้นตลิ่งหรือไม่” จะเปิดเองเมื่อผลทดสอบย้อนหลังผ่านเกณฑ์' +
        " — เร็วที่สุดเมื่อได้ข้อมูลเขื่อนทดน้ำเพชรและเหตุการณ์ในอดีต (ด้านล่าง)</p></section>";
    }
    const d = st.dam || {};
    return '<section class="card" id="whatif"><h2>ตาราง what-if</h2><form class="wf" id="wf">' +
      '<label>ระบายจากเขื่อน (ล้าน ลบ.ม./วัน)<input name="release" type="number" inputmode="decimal" step="0.1" min="0" max="200" value="' +
      esc(d.released_mcm != null ? d.released_mcm : 10) + '" required></label>' +
      '<label>ผันน้ำที่เขื่อนเพชร (ลบ.ม./วินาที)<input name="div" type="number" inputmode="decimal" step="1" min="0" max="2000" value="' +
      esc(st.diversion_default) + '"></label>' +
      '<button class="btn primary" type="submit">คำนวณ</button><span class="muted" id="rcms"></span></form>' +
      '<div id="wres"></div></section>';
  }

  function bindWhatif() {
    const f = $("#wf");
    if (!f) return;
    const show = () => { $("#rcms").textContent = "≈ " + num(toCms(Number(f.release.value) || 0), 0) + " ลบ.ม./วินาที"; };
    f.release.addEventListener("input", show);
    show();
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const q = new URLSearchParams({ release_mcm: f.release.value });
      if (f.div.value !== "") q.set("diversion_cms", f.div.value);
      const r = await api("/api/impact/kaeng-krachan/whatif?" + q.toString());
      if (r.status === 401) return showLogin("หมดเวลาเข้าสู่ระบบ กรุณาเข้าใหม่");
      if (!r.ok) { $("#wres").innerHTML = '<p class="err">คำนวณไม่ได้ (' + r.status + ")</p>"; return; }
      $("#wres").innerHTML = whatifTable(await r.json());
    });
  }

  function whatifTable(w) {
    const over = { yes: "ถึงตลิ่ง", possible: "ขอบบนถึงตลิ่ง", no: "ต่ำกว่าตลิ่ง" };
    const rows = w.rows.map((r) => "<tr><th scope=\"row\">" + esc(r.code) + "<small>" + esc(r.name_th || "") + "</small></th>" +
      "<td>" + (r.arrival_h ? num(r.arrival_h[0], 0) + "–" + num(r.arrival_h[1], 0) : "–") + "</td><td>" + num(r.flow_cms, 0) + "</td>" +
      "<td>" + (r.level ? num(r.level[0], 2) + "–" + num(r.level[2], 2) : "–") + "</td>" +
      "<td" + (r.margin_m != null && r.margin_m < 0 ? ' class="neg"' : "") + ">" + num(r.margin_m, 2) + "</td>" +
      "<td>" + (over[r.overflow] || "–") + "</td><td>" + (r.outside ? "เกินช่วงข้อมูล 1 ปี" : "") + "</td></tr>").join("");
    return '<p class="muted">ระบาย ' + num(w.release_mcm, 2) + " ล้าน ลบ.ม./วัน (≈ " + num(w.release_cms, 0) +
      " ลบ.ม./วินาที) · ผันที่เขื่อนเพชร " + num(w.diversion_cms, 0) + " ลบ.ม./วินาที" + (w.diversion_default ? " (จากข้อมูล)" : "") +
      '</p><div class="scroll"><table><thead><tr><th scope="col">สถานี</th><th scope="col">ถึงใน (ชม. จากเขื่อน)</th>' +
      '<th scope="col">น้ำไหล (ลบ.ม./วินาที)</th><th scope="col">ระดับ (ม.รทก.)</th><th scope="col">ห่างตลิ่ง (ม.)</th>' +
      '<th scope="col">ตลิ่ง</th><th scope="col">หมายเหตุ</th></tr></thead><tbody>' + rows + "</tbody></table></div>" +
      '<ul class="facts">' + w.assumptions.map((a) => "<li>" + esc(a) + "</li>").join("") + "</ul>";
  }

  function reqHtml(st) {
    const items = (st.data_request || []).map((x) => "<li><b>" + esc(x.th) + "</b><span class=\"why\">" + esc(x.why) +
      ' · <a href="/api/impact/template/' + encodeURIComponent(x.key) + '">แบบฟอร์ม CSV</a></span></li>').join("");
    return '<section class="card" id="req"><h2>ข้อมูลที่ต้องการจาก สทนช. / กรมชลประทาน</h2><ol class="req">' + items + "</ol>" +
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
      return "<tr><th scope=\"row\">" + esc(p.code) + (p.rating_from ? "<small>ใช้น้ำไหลที่ " + esc(p.rating_from) + "</small>" : "") +
        "</th><td>" + num(r.h0, 2) + "</td><td>" + num(r.a, 3) + "</td><td>" + num(r.b, 2) + "</td><td>" + num(r.rmse * 100, 1) +
        "</td><td>" + num(r.qmin, 0) + "–" + num(r.qmax, 0) + "</td><td>" + num(r.n, 0) + "</td></tr>";
    }).join("");
    return '<section class="card" id="method"><details><summary>วิธีการและข้อจำกัด</summary>' +
      '<ul class="facts">' +
      "<li>ข้อมูล: ระดับและปริมาณน้ำรายชั่วโมงย้อนหลัง 1 ปีจากสถานีของ ชป. และ สสน. และข้อมูลเขื่อนรายวัน (ชป., กฟผ.) — ทั้งหมดเป็นข้อมูลสาธารณะผ่าน สสน.</li>" +
      "<li>Rating curve ต่อสถานี h = h₀ + a·Qᵇ (ตารางด้านล่าง) ใช้ได้ในช่วงน้ำที่เคยวัดได้เท่านั้น เกินกว่านั้นคือการต่อเส้นโค้งออกไป</li>" +
      "<li>B.15 และ PCH001 (ในเมือง) ไม่มีปริมาณน้ำ จึงใช้น้ำไหลที่ B.16 ณ เวลาที่น้ำเดินทางถึง; ในเมืองระดับน้ำยังขึ้นกับน้ำขึ้นน้ำลงด้วย</li>" +
      releaseCheck(st.release_check) +
      "<li>PCH003 (สสน.) ไม่ได้ใช้: ระดับเปลี่ยนพร้อม B.18 แทบเท่ากันและไม่มีเวลาหน่วง จึงน่าจะอยู่ใกล้เขื่อน ไม่ใช่ในตัวท่ายาง ⚠️ ขอยืนยันตำแหน่ง</li>" +
      "<li>เวลาแสดงเป็นเวลาไทย (ระบบเก็บเป็น UTC); ข้อมูลเขื่อนเป็นรายวันตามวันที่หน่วยงานรายงาน</li>" +
      "</ul><div class=\"scroll\"><table><thead><tr><th scope=\"col\">สถานี</th><th scope=\"col\">h₀ (ม.)</th><th scope=\"col\">a</th>" +
      '<th scope="col">b</th><th scope="col">RMSE (ซม.)</th><th scope="col">Q ที่เคยวัด (ลบ.ม./วินาที)</th>' +
      '<th scope="col">จำนวนชั่วโมง</th></tr></thead><tbody>' + rows + "</tbody></table></div></details></section>";
  }

  load();
})();
