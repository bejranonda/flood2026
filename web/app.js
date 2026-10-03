"use strict";
// BKK FloodWatch frontend. Talks only to our API (D-001). Every external string goes through esc().

// Issue #6: each pin factor is one phrase ("น้ำในคลองล้นตลิ่ง"), not "title · word" (faster to read)
const CANAL_HEAD = { "ล้นตลิ่ง": "น้ำในคลองล้นตลิ่ง", "ใกล้ตลิ่ง/คลองเต็ม": "น้ำในคลองใกล้ถึงตลิ่ง/คลองเต็ม",
  "เฝ้าระวัง": "น้ำในคลองเริ่มสูง ควรเฝ้าระวัง", "ยังรับน้ำได้": "คลองยังรับน้ำได้", "ไม่ทราบ": "ยังไม่ทราบระดับน้ำในคลอง",
  "ไม่มีสถานีใกล้": "ไม่มีสถานีวัดน้ำคลองใกล้จุดนี้", "คลองรอบจุดต่างกันมาก": "คลองรอบจุดต่างกันมาก", "สถานีอยู่ไกล": "สถานีวัดน้ำคลองอยู่ไกล" };
const STATUS = {
  critical: { th: "ล้นตลิ่ง", long: "วิกฤต (ล้นตลิ่ง)", color: "#c62828" },
  warning: { th: "ใกล้ตลิ่ง/คลองเต็ม", long: "เตือนภัย (ใกล้ตลิ่ง)", color: "#e46c0a" },
  watch: { th: "เฝ้าระวัง", long: "เฝ้าระวัง", color: "#b58900" },
  // Not "ปกติ" (normal): a canal below its bank says nothing about the street, which can flood from rain the drains
  // can't take while BMA keeps canals pumped low (owner report 2026-09-26, D-036). Blue = water in the channel, not "safe".
  normal: { th: "ยังรับน้ำได้", long: "น้ำต่ำกว่าตลิ่ง", color: "#2f6fb0" },
  unknown: { th: "ไม่ทราบ", long: "ไม่ทราบสถานะ", color: "#8a94a3" },  // why (no bank, old data, erratic…) is in the notes
};
// BMA canal gauges are judged by BMA's own drainage levels (D-038): the words say what the canal can still take.
const BMA_LABEL = {
  critical: { th: "ล้นตลิ่ง", long: "ล้นตลิ่ง" },
  warning: { th: "คลองเต็ม", long: "คลองเต็ม" },
  watch: { th: "คลองเริ่มเต็ม", long: "คลองเริ่มเต็ม" },
  normal: { th: "คลองยังรับน้ำได้", long: "คลองยังรับน้ำได้" },
};
const BANK_LABEL = { warning: { th: "ใกล้ตลิ่ง" }, normal: { th: "ต่ำกว่าตลิ่ง" } };
// Bank-based watch/warning come from the share of channel depth (classify_status): CPY015 was "ใกล้ตลิ่ง" while 158 cm
// below its bank (91 % of an 18 m deep river). Say what is measured when the bank is still > 30 cm away (D-056).
const DEPTH_WORD = { warning: "เตือนภัย", watch: "เฝ้าระวัง" };
const stOf = (s) => {
  const base = { ...(STATUS[s.status] || STATUS.unknown),
    ...(s.status_basis === "bma_thresholds" ? BMA_LABEL[s.status] || {} : BANK_LABEL[s.status] || {}) };
  if (s.status_basis !== "bma_thresholds" && DEPTH_WORD[s.status] && s.pct_bank != null && (s.freeboard_m ?? 0) > 0.3) {
    const pct = Math.round(s.pct_bank);
    return { ...base, th: `เต็มลำน้ำ ${pct}%`, long: `${DEPTH_WORD[s.status]} (น้ำเต็มลำน้ำ ${pct}%)` };
  }
  return base;
};
// Right-hand number: BMA gauges over a BMA level show that margin; everything else cm to the bank.
const levelText = (s) => s.status_basis === "bma_thresholds" && s.over_bma_critical_m != null && s.over_bma_critical_m > 0 && s.status !== "critical"
  ? `เกินเกณฑ์ กทม. ${Math.round(s.over_bma_critical_m * 100)} ซม.` : freeboardText(s.freeboard_m);
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
// Rain-amount words of the Thai Meteorological Department (tmd.go.th "เกณฑ์อากาศ", read 2026-09-27), mirrored from
// point.py RAIN_* — change both together. Never write "~27 มม.": on phones the tilde reads as a minus (issue #1).
const RAIN_TMD = [[0.1, "ไม่มีฝน"], [10.0, "ฝนเล็กน้อย"], [35.0, "ฝนปานกลาง"], [90.0, "ฝนหนัก"], [Infinity, "ฝนหนักมาก"]];
const rainLabel = (mm) => RAIN_TMD.find(([max], i) => (i === 0 ? mm < max : mm <= max))[1];
const rainMm = (mm) => (mm < 1 || rainLabel(Math.round(mm)) !== rainLabel(mm)) ? mm.toFixed(1) : String(Math.round(mm));
// Colour + a 4-step mini scale say "how much" without a text legend (owner 2026-09-27: the legend line was too much).
const RAIN_COLOR = { "ไม่มีฝน": "#6b7280", "ฝนเล็กน้อย": "#0e7490", "ฝนปานกลาง": "#2563eb", "ฝนหนัก": "#7c3aed", "ฝนหนักมาก": "#be185d" };
const rainPill = (mm, approx = true) => {  // "ราว" for a forecast only; a measurement is not an estimate
  const label = rainLabel(mm), idx = RAIN_TMD.findIndex(([, l]) => l === label), c = RAIN_COLOR[label];
  // the panel's words ("ราว N มม."), no 4-square scale: the coloured word already says it (v0.16.8, one vocabulary)
  return `<span class="rain"><b style="color:${c}">${esc(label)}</b>${mm >= 0.1 ? ` ${approx ? "ราว " : ""}${esc(rainMm(mm))} มม.` : ""}</span>`;
};
// One rain block for the pin panel and the summary strip (owner 2026-10-02: the rain factor read as one long sentence,
// "Compare to the water level info, it is easier"). Same layout as the water rows: the forecast is a trend-row grid
// (horizon · coloured chip · "ราว N มม." · ⓘ), then what fell in the water's past-line style ("24 ชม. ที่ผ่านมา: …").
const infoBtn = (tip, label) => `<button type="button" class="conf-badge conf-low" title="${esc(tip)}" aria-label="${esc(label)}">ⓘ</button>`;
function rainRows(fcMm, fcTip, mm24, mm1h) {
  const fl = fcMm == null ? null : rainLabel(fcMm);
  const row = fl ? `<div class="tr-rows rain-rows"><span class="tr-h">อีก 24 ชม.</span><span class="chg" style="background:${RAIN_COLOR[fl]}">${esc(fl)}</span>`
    + `<span class="tr-r">${fcMm >= 0.1 ? `ราว ${esc(rainMm(fcMm))} มม.` : ""}</span>${fcTip ? infoBtn(fcTip, "ที่มาของฝนคาดการณ์") : "<span></span>"}</div>` : "";
  const ml = mm24 == null ? null : rainLabel(mm24);
  const past = ml ? `<div class="pf-obs">24 ชม. ที่ผ่านมา: <b style="color:${RAIN_COLOR[ml]}">${esc(ml)}</b>${mm24 >= 0.1 ? ` ${esc(rainMm(mm24))} มม.` : ""}</div>` : "";
  const hour = mm1h != null && mm1h >= 0.1 ? `<div class="pf-obs">ชั่วโมงล่าสุด: ${esc(rainMm(mm1h))} มม.</div>` : "";
  return row + past + hour;
}
// Change at a gauge in 12/24 h, five colour steps (D-047): blue = falling, grey = steady, orange/red = rising.
// Always "at this gauge", with the likely range in words and an honest confidence ("ปานกลาง" at best, never "สูง").
const CHANGE = {
  strong_fall: { th: "ลดลงมาก", icon: "⬇", color: "#1d4e89" }, fall: { th: "ลดลง", icon: "↘", color: "#2f6ba0" },
  small_fall: { th: "ลดลงเล็กน้อย", icon: "↘", color: "#2f6ba0" }, small_rise: { th: "เพิ่มขึ้นเล็กน้อย", icon: "↗", color: "#b45309" },
  steady: { th: "ทรงตัว", icon: "→", color: "#6b7280" },
  rise: { th: "เพิ่มขึ้น", icon: "↗", color: "#b45309" }, strong_rise: { th: "เพิ่มขึ้นมาก", icon: "⬆", color: "#c62828" },
};
const CONF_TH = { medium: "คาดการณ์ปานกลาง", low: "คาดการณ์เบื้องต้น" };
// Method codes from the backtest (forecast.evaluate) in plain Thai; "star" = D-052 (rain + upstream + dam release)
const METHOD_TH = { persistence: "ค่าคงที่", tide: "น้ำขึ้นน้ำลง", tide_trend: "น้ำขึ้นน้ำลง + แนวโน้ม", trend: "แนวโน้ม",
  star: "ฝนคาดการณ์ + น้ำจากต้นน้ำ" };
const CONF_WHY = {
  medium: "แบบจำลองทดสอบย้อนหลัง 45 วัน แม่นกว่าการถือว่าน้ำคงที่อย่างน้อย 30% และช่วงที่ให้ถูกราว 9 ใน 10 ครั้ง (ใช้น้ำขึ้นน้ำลง ฝนคาดการณ์ และน้ำจากต้นน้ำ/เขื่อนเจ้าพระยา ตามที่แต่ละสถานีทดสอบแล้วแม่นกว่า)",
  low: "แบบจำลองเบื้องต้น (อิงความคงที่หรือสถิติ 45 วัน) ตัวเลขเป็นกรอบความคลาดเคลื่อนจากการทดสอบย้อนหลัง",
};
// --- One trend format for list, panel and sheet (owner 2026-09-27, D-056) -------------------------------------------
// Aligned rows: horizon · chip · signed range · ⓘ. A direction only where a real model beat "no change" at that horizon
// (the backtest's own gate); "no change" itself can only ever say "steady", so it shows "? ไม่แน่ชัด" + its error range.
const agrees = (ch) => !ch.likely || (ch.dir === "falling" ? ch.likely[1] < 0 : ch.dir === "rising" ? ch.likely[0] > 0 : true);
const directional = (ch) => !!ch && ch.level !== "steady" && (ch.basis === "measured_trend" || (!!ch.method && ch.method !== "persistence" && agrees(ch)));
const signedCm = (x) => { const v = Math.round(x * 100); return `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v)}`; };
const rangeText = (ch) => ch.wide || !ch.likely ? "ช่วงกว้างเกินไป"
  : signedCm(ch.likely[0]) === signedCm(ch.likely[1]) ? `ราว ${signedCm(ch.likely[0])} ซม.` : `${signedCm(ch.likely[0])} ถึง ${signedCm(ch.likely[1])} ซม.`;
const UNPROVEN_TIP = "ยังไม่แน่ชัด: ช่วงที่ระดับน้ำอาจเปลี่ยนกว้างเกิน ±5 ซม. จึงไม่บอกทิศทาง ตัวเลขคือช่วงที่เกิดขึ้นครึ่งหนึ่งของครั้งที่ผ่านมา";
const STEADY_TIP = "ทรงตัว: ครึ่งหนึ่งของครั้งที่ผ่านมา ระดับน้ำเปลี่ยนไม่เกิน ±5 ซม. ในช่วงเวลานี้";
const STEADY_M = 0.05;  // "ทรงตัว" only when the likely range stays within ±5 cm: a few cm matter in a flood (D-060)
const narrow = (ch) => !!ch.likely && !ch.wide && Math.max(Math.abs(ch.likely[0]), Math.abs(ch.likely[1])) <= STEADY_M;
// One row: horizon · chip · range · ⓘ. `unsure` = a shorter horizon was already "?": a longer one is never surer (D-060).
function trendRow(ch, hours, unsure = false) {
  if (!ch) return { html: "", unsure };
  const dirn = directional(ch), steady = !dirn && !unsure && narrow(ch), c = CHANGE[ch.level] || CHANGE.steady;
  const chip = dirn ? `<span class="chg" style="background:${c.color}">${c.icon} ${esc(c.th)}</span>`
    : steady ? `<span class="chg" style="background:${CHANGE.steady.color}">→ ${esc(CHANGE.steady.th)}</span>`
    : `<span class="chg chg-unproven">? ไม่แน่ชัด</span>`;
  const measured = ch.basis === "measured_trend";  // D-060: the word follows the measured trend; numbers go in the ⓘ
  const tip = measured
    ? `ถ้าเป็นไปตามแนวโน้มที่วัดได้ (ชะลอลงตามเวลา) ไม่ใช่แบบจำลอง${ch.hit != null ? ` · ในอดีตเป็นแบบนี้ต่อ ${Math.round(ch.hit * 10)} ใน 10 ครั้ง` : ""}`
    : dirn ? `${CONF_TH[ch.confidence] || ""}: ${CONF_WHY[ch.confidence] || ""}` : steady ? STEADY_TIP : UNPROVEN_TIP;
  const cls = dirn && ch.basis !== "measured_trend" ? `conf-${esc(ch.confidence)}` : "conf-low";
  const html = `<span class="tr-h">อีก ${hours} ชม.</span>${chip}<span class="tr-r">${esc(rangeText(ch))}</span><button type="button" class="conf-badge ${cls}" title="${esc(tip)}" aria-label="ความมั่นใจของการคาดการณ์">ⓘ</button>`;
  return { html, unsure: unsure || (!dirn && !steady) };
}
function trendRows(s, hours) {
  // Every view walks 12 → 24 → 48 h, printing only `hours`, so a list showing only 24 h says what the sheet says
  // (VLGE20: list "→ ทรงตัว", sheet "? ไม่แน่ชัด" after its 12 h "?", consistency check C1).
  let unsure = false;
  const rows = [12, 24, 48].filter((h) => h <= Math.max(...hours)).map((h) => {
    const r = trendRow(s[`change${h}`], h, unsure); unsure = r.unsure; return hours.includes(h) ? r.html : ""; }).filter(Boolean).join("");
  return rows ? `<div class="tr-rows">${rows}</div>` : "";
}

// What the level did over the last 24 h, measured (qc.observed24; D-058). A few cm matter in a flood (owner 2026-09-28),
// so small steady changes get their own words; the words follow the rounded cm shown (< 2 ทรงตัว · 2-4 เล็กน้อย · 5-19 ·
// ≥ 20 มาก). It replaced "ยังไม่เห็นแนวโน้มลดลงใน 24 ชม. ข้างหน้า", which the "no change" model printed at 26 gauges that
// had clearly fallen (e.g. WL.CKS.01 −91 cm, BKK021 −5 cm), KI-240.
const OBS = { steady: "ทรงตัว", small_fall: "ลดลงเล็กน้อย", fall: "ลดลง", strong_fall: "ลดลงมาก",
  small_rise: "เพิ่มขึ้นเล็กน้อย", rise: "เพิ่มขึ้น", strong_rise: "เพิ่มขึ้นมาก", mixed: "ขึ้นลงสลับกัน" };
const obsDir = (o) => !o ? "" : o.level.endsWith("fall") ? "fall" : o.level.endsWith("rise") ? "rise" : "flat";
const obsLine = (s) => {
  const o = s.observed24;
  if (!o || !OBS[o.level]) return "";
  const cm = ["steady", "mixed"].includes(o.level) ? (o.level === "steady" ? " (เปลี่ยนไม่ถึง 2 ซม.)" : "") : ` ${Math.abs(o.change_cm)} ซม.`;
  return `<div class="pf-obs obs-${obsDir(o)}">${o.hours || 24} ชม. ที่ผ่านมา: <b>${esc(OBS[o.level])}</b>${esc(cm)}</div>`;
};
// Water from upstream (owner 2026-10-02, basin data): the first upstream gauge, its measured 24 h change in the list's
// own words (obsLine), and how long its changes usually take to arrive here (learned lag). One line; why behind an ⓘ.
const upstreamLine = (s) => {
  const u = (s.upstream || [])[0], us = u && stations.find((x) => x.code === u.code);
  if (!us || us.stale) return "";
  const o = obsLine(us).replace(/^<div class="pf-obs[^"]*">/, "").replace(/<\/div>$/, "");
  if (!o) return "";
  const tip = `${us.name_th} (${us.code}) อยู่ต้นน้ำของสถานีนี้ในลุ่มน้ำและระบบแม่น้ำเดียวกัน`
    + (u.lag_h ? ` · จากข้อมูลย้อนหลัง 1 ปี ระดับน้ำที่นั่นมักเปลี่ยนก่อนที่นี่ราว ${u.lag_h} ชม.` : " · ตามลำน้ำเจ้าพระยา")
    + " · เป็นข้อมูลที่วัดได้ ไม่ใช่การพยากรณ์";
  return `<div class="pf-obs pf-up">ต้นน้ำ: ${esc(us.name_th)} · ${o}${u.lag_h ? ` · มักถึงที่นี่ในราว ${esc(u.lag_h)} ชม.` : ""} <button type="button" class="conf-badge conf-low" title="${esc(tip)}" aria-label="ต้นน้ำของสถานีนี้">ⓘ</button></div>`;
};
// When will it drop? The station's recovery estimate in dates/hours (never minutes, KI-231); shared by panel and sheet
const dropText = (s) => {
  const r = s.recovery || {};
  // Always with its conditions (D-005; the v0.10 rewrite had dropped them, KI-239)
  if (r.state === "forecast") return `คาดว่าจะต่ำกว่าตลิ่ง: ${r.hours_max ? whenText(r.hours_min, r.hours_max) : `${whenText(r.hours_min ?? r.hours_mid, r.hours_mid)} หรือนานกว่า 3 วัน`} (หากไม่มีฝนตกหนักเพิ่ม)`;
  if (r.state === "extrapolated") return `หากลดในอัตราเดิมและไม่มีฝนหนัก อาจต่ำกว่าตลิ่ง: ${whenText(r.hours_min, r.hours_max)} (ประมาณคร่าว ๆ ความเชื่อมั่นต่ำ)`;
  if (r.state === "not_estimable" && ["warning", "critical"].includes(s.status))
    return r.reason === "heavy_rain_forecast" ? "ยังประเมินเวลาน้ำลดไม่ได้ (คาดฝนหนัก)"
      : obsDir(s.observed24) === "fall" ? "ยังประเมินเวลาน้ำลดไม่ได้ (ลดลงช้าเกินกว่าจะประมาณ)" : "ยังประเมินเวลาน้ำลดไม่ได้ (น้ำยังไม่ลดลง)";
  return "";
};
// Measured 24 h line first, then "when it drops": one block shared by panel and sheet.
const changeLines = (s) => `${obsLine(s)}${dropText(s) ? `<div class="pf-nofall">${esc(dropText(s))}</div>` : ""}`;

// Round first: -0.4 cm used to render as "ต่ำกว่าตลิ่ง 0 ซม." next to an "overflowing" badge (BKK009, 2026-09-26).
// The bank distance 24 h ago, when the level moved steadily and stayed on the same side of the bank (D-060)
const ydayText = (s) => {
  const o = s.observed24;
  if (s.freeboard_m == null || !o || (o.hours || 24) !== 24 || ["steady", "mixed"].includes(o.level)) return "";
  const now = Math.round(s.freeboard_m * 100), then = now + o.change_cm;
  return Math.sign(now) === Math.sign(then) && then !== 0 ? `\u00a0(เมื่อวาน\u00a0${Math.abs(then)})` : "";
};
const freeboardText = (fb) => {
  if (fb == null) return "";
  const c = Math.round(fb * 100);
  return c === 0 ? "ระดับเท่าตลิ่ง" : c < 0 ? `สูงกว่าตลิ่ง ${-c} ซม.` : `ต่ำกว่าตลิ่ง ${c} ซม.`;
};
// Region chips (D-064): the API gives each gauge its region (src/floodwatch/regions.py, the six official regions with
// central split into กทม. / ปริมณฑล / เหนือ กทม.). Every view — counts, list, map — follows the chosen chip.
const REGION_TH = { bkk: "กทม.", metro: "ปริมณฑล", up: "เหนือ กทม.", north: "ภาคเหนือ", northeast: "อีสาน",
  east: "ตะวันออก", west: "ตะวันตก", south: "ใต้" };
const REGIONS = Object.fromEntries([...Object.entries(REGION_TH).map(([k, th]) => [k, { th, test: (s) => s.region === k }]),
  ["all", { th: "ทั้งประเทศ", test: () => true }]]);
const inRegion = (s) => REGIONS[region].test(s);
const AGENCY_TH = { BMA: "สำนักการระบายน้ำ กทม.", RID: "กรมชลประทาน", HII: "สสน.", EGAT: "กฟผ.",
  FOP: "มูลนิธิอาสาเพื่อนพึ่ง (ภาฯ) ยามยาก สภากาชาดไทย" };
const agencyTh = (a) => AGENCY_TH[a] || a || "";
// Default "bkk" (owner, 2026-09-26: "Bangkok as default this week"; revisit 2026-10-03). A tapped choice is remembered.
const DEFAULT_REGION = "bkk";
let region = (() => { try { return REGIONS[localStorage.getItem("region")] ? localStorage.getItem("region") : DEFAULT_REGION; } catch { return DEFAULT_REGION; } })();
const NOTE = {
  datum_suspect: "ค่าระดับน้ำของสถานีนี้ไม่ได้อยู่ในหน่วย ม.รทก. (ตรวจพบค่าผิดปกติ) จึงไม่แสดงค่า",
  erratic: "ระดับน้ำขึ้นลงเร็วผิดปกติใน 24 ชม.ล่าสุด (อาจมีการสูบน้ำใกล้จุดวัด หรือเครื่องวัดขัดข้อง) จึงไม่แสดงระดับน้ำและแนวโน้ม",
  stuck: "ค่าระดับน้ำค้างที่ค่าเดิมตลอด 24 ชม. (เครื่องวัดอาจขัดข้อง) จึงไม่แสดงระดับน้ำและแนวโน้ม",
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
let streetSrc = null;       // {hours, km, last_update_age_min} of the street-report layer (Traffy)
let forecastOnly = false;   // list chip: only gauges with a tested forecast
let showNoData = false;     // map: gauges without data for 24 h are hidden unless asked for
const hasForecast = (s) => ["rising", "falling", "steady"].includes(s.trend12);
// Observed change from readings (1-3 h), shown when there is no forecast yet: a trend, not a prediction.
const observedText = (s) => {
  if (s.change_m == null || s.change_hours == null) return "";
  const c = Math.round(s.change_m * 100), h = s.change_hours >= 1.5 ? `${Math.round(s.change_hours)} ชม.` : "1 ชม.";
  return Math.abs(c) <= 2 ? `➖ ทรงตัวใน ${h}ที่ผ่านมา` : c > 0 ? `↗️ สูงขึ้น ${c} ซม. ใน ${h}ที่ผ่านมา` : `↘️ ลดลง ${-c} ซม. ใน ${h}ที่ผ่านมา`;
};
const trendLine = (s) => hasForecast(s)
  ? `${TREND[s.trend12]}${s.delta12_median != null && s.trend12 !== "steady" ? ` ${cm(s.delta12_median)} ในอีก 12 ชม.` : ""}`
  : observedText(s) || (isNew(s) ? `🆕 สถานีใหม่ เริ่มเก็บข้อมูล ${new Date(s.history_since).toLocaleDateString("th-TH", { day: "numeric", month: "short", timeZone: "Asia/Bangkok" })}` : TREND.unknown);
const STREET_MIN = 3;       // street-flood reports within 1 km worth showing on a gauge
const streetAge = () => streetSrc?.last_update_age_min != null && streetSrc.last_update_age_min > 60
  ? ` (ข้อมูล Traffy ล่าสุด ${fmtAge(streetSrc.last_update_age_min)})` : "";
let map, layer, legend;
let lastPos = null;

async function getJSON(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

/* ---------- summary strip ---------- */
// Rain for the chosen region (owner 2026-10-01: "There is no rain in panel anymore?" — v0.16.0 showed it for กทม.
// and ปริมณฑล only): the wettest forecast point in the next 24 h and the wettest HII rain gauge in the last 24 h.
// v0.18.9 (owner 2026-10-02: "it used too much space again!! … specifically for Bangkok, for what?" → "Only when
// heavy"): nothing unless the region expects or measured heavy rain (TMD heavy from 35.1 mm, point.py bands), then ONE
// line; everyday rain is told where it is about a place (pin panel, station sheet).
let rainRegions = null;
const SUMMARY_RAIN_MIN_MM = 35.1;
function rainSummary(bkkRain) {
  const r = rainRegions?.[region], where = region === "all" ? "ทั่วประเทศ" : REGIONS[region].th;
  const fc = r?.forecast_mm24 ?? (region === "bkk" ? bkkRain : null), m = r?.measured;
  const mm24 = m ? Number(m.rain_24h) : null;
  const fcHeavy = fc != null && fc >= SUMMARY_RAIN_MIN_MM, mHeavy = mm24 != null && mm24 >= SUMMARY_RAIN_MIN_MM;
  if (!fcHeavy && !mHeavy) return "";
  const tip = [fcHeavy ? "คาดการณ์: Open-Meteo จุดที่ฝนมากที่สุดในพื้นที่" : "",
    mHeavy ? `วัดจริง: สถานีวัดฝน ${m.name_th}${m.province ? ` (${m.province})` : ""} · สสน.` : ""].filter(Boolean).join(" · ");
  const parts = [fcHeavy ? `อีก 24 ชม. ${rainPill(fc)}` : "", mHeavy ? `24 ชม. ที่ผ่านมา ${rainPill(mm24, false)}` : ""];
  return `<p class="sumline sumrain">🌧️ ${esc(where)}: ${parts.filter(Boolean).join(" · ")} ${infoBtn(tip, "ที่มาของข้อมูลฝน")}</p>`;
}
let lastStats = null;
function renderSummary(st) {
  lastStats = st;
  const f = st.focus, n = st.network;
  const mine = stations.filter(inRegion);  // D-064: the counts follow the region chip, like the list and the map
  const cnt = (k) => mine.filter((s) => s.status === k).length;
  const tr = (k) => mine.filter((s) => s.trend12 === k).length;
  const chips = ["critical", "warning", "watch", "normal", "unknown"].map((k) =>
    `<button class="chip" data-status="${k}" aria-pressed="${statusFilter === k}" title="แสดงเฉพาะ${esc(STATUS[k].long)}">
      <span class="dot" style="background:${STATUS[k].color}"></span>${esc(STATUS[k].th)} <b>${cnt(k)}</b></button>`).join("");
  const bar = (x) => `<span class="fresh" aria-hidden="true">
    <span style="width:${(100 * x.h1) / x.total}%;background:#2e9d5b"></span>
    <span style="width:${(100 * (x.h3 - x.h1)) / x.total}%;background:#9ccc65"></span>
    <span style="width:${(100 * (x.h24 - x.h3)) / x.total}%;background:#f4d35e"></span></span>`;
  const pct = (a, b) => Math.round((100 * a) / (b || 1));
  const rain = st.rain_bkk_next24_mm_max;
  // When a source stops upstream (2026-10-01: all BMA canal readings stuck at 00:10 ICT for hours), the counts above
  // are old values: say so in one line, the why behind an ⓘ.
  const staleN = mine.filter((s) => s.stale && s.status !== "unknown").length;
  const staleLast = mine.filter((s) => s.stale && s.obs_time).map((s) => s.obs_time).sort().pop();
  const staleLine = staleN >= 5 && staleN * 2 >= mine.length
    ? `<p class="sumline warn-line">⚠️ ${staleN} สถานีไม่อัปเดตเกิน 3 ชม. (ล่าสุด ${esc(fmtTime(staleLast))}) <button type="button" class="conf-badge conf-low" title="แหล่งข้อมูลหยุดส่งชั่วคราว ตัวเลขเป็นค่าล่าสุดที่ได้รับ ไม่ใช่สถานการณ์ตอนนี้ ระบบจะอัปเดตเองเมื่อข้อมูลกลับมา" aria-label="ทำไมข้อมูลไม่อัปเดต">ⓘ</button></p>` : "";
  document.getElementById("summary").innerHTML = `<div class="chips">${chips}</div>${staleLine}
    ${rainSummary(rain)}
    <details class="sumdetails"><summary>รายละเอียดข้อมูล</summary>
    <p class="sumline">${esc(TREND.rising)} <b>${tr("rising")}</b> · ${esc(TREND.falling)} <b>${tr("falling")}</b> สถานี${region === "all" ? "" : ` ใน${esc(REGIONS[region].th)}`} (คาดการณ์อีก 12 ชม.)</p>
    <div class="sumline">📡 ส่งข้อมูลภายใน 1 ชม. <b>${f.h1}</b> · 3 ชม. <b>${f.h3}</b> · 24 ชม. <b>${f.h24}</b> จาก ${f.total} สถานี${bar(f)}
      <details><summary>ทั้งประเทศ</summary> เครือข่าย สสน. ${n.total} สถานี: ภายใน 1 ชม. ${n.h1} (${pct(n.h1, n.total)}%) ·
        3 ชม. ${n.h3} (${pct(n.h3, n.total)}%) · 24 ชม. ${n.h24} (${pct(n.h24, n.total)}%) · เกิน 24 ชม./ไม่มีข้อมูล ${n.older + n.never}
        · ในพื้นที่ติดตาม ${f.no_coords} สถานีไม่มีพิกัด, ${f.no_bank} สถานีไม่มีระดับตลิ่ง</details></div></details>`;
  document.querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => {
    statusFilter = statusFilter === b.dataset.status ? null : b.dataset.status;
    document.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c.dataset.status === statusFilter)));
    setTab("list");
    renderList();
  }));
}

/* ---------- list ---------- */
function itemHTML(s, extra = "") {
  const st = stOf(s);
  return `<li class="item s-${esc(s.status)} ${s.stale ? "stale" : ""}" data-code="${esc(s.code)}" tabindex="0">
    <div class="row"><span class="name">${esc(s.name_th)} <span class="muted">${esc(s.code)}</span></span>
      <span class="badge b-${esc(s.status)}">${esc(st.th)}</span></div>
    <div class="row"><span class="meta">${esc(s.amphoe || s.river || "")} ${esc(s.province || "")}${s.agency === "BMA" ? " · ข้อมูล กทม." : ""}${hasRiverView(s) ? ` · 〰️ ${esc(s.river)}` : ""}</span><span class="fb">${esc(levelText(s))}</span></div>
    ${(s.change24 || s.change12) ? `${trendRows(s, [s.change24 ? 24 : 12])}${obsLine(s)}
    <div class="meta">ข้อมูลล่าสุด ${esc(fmtAge(s.age_min))}${s.stale ? " ⚠️ ข้อมูลเก่า" : ""}</div>`
      : `${obsLine(s)}<div class="meta">${esc(trendLine(s))} · ${esc(fmtAge(s.age_min))}${s.stale ? " ⚠️ ข้อมูลเก่า" : ""}</div>`}${(s.street_reports_6h || 0) >= STREET_MIN
        ? `<div class="meta street">🚗 ถนนรอบ ๆ (1 กม.) มีรายงานน้ำท่วม ${s.street_reports_6h} เรื่องใน 6 ชม.${esc(streetAge())}</div>` : ""}${notesText(s) ? `<div class="meta note">ℹ️ ${esc(notesText(s))}</div>` : ""}${extra}</li>`;
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
    const n = stations.filter((s) => r.test(s)).length;
    return n ? `<button type="button" class="rchip" data-region="${k}" aria-pressed="${k === region}">${esc(r.th)} <b>${n}</b></button>` : "";
  }).join("") + `<button type="button" class="rchip fchip" aria-pressed="${forecastOnly}" title="ซ่อนสถานีที่ยังคาดการณ์ไม่ได้ (เช่น สถานีใหม่)">📈 เฉพาะที่คาดการณ์ได้</button>`;
  el.querySelector(".fchip").addEventListener("click", () => { forecastOnly = !forecastOnly; renderList(); });
  el.querySelectorAll(".rchip[data-region]").forEach((b) => b.addEventListener("click", () => {
    region = b.dataset.region;
    try { localStorage.setItem("region", region); localStorage.setItem("regionSource", "user"); } catch { /* private mode */ }
    if (lastStats) renderSummary(lastStats);
    renderList();
    fitRegion();
  }));
}

function renderList() {
  const q = norm(document.getElementById("q").value);
  renderRegions();
  const rows = stations
    .filter((s) => q || inRegion(s))  // a search looks in every region
    .filter((s) => !statusFilter || s.status === statusFilter)
    .filter((s) => !forecastOnly || hasForecast(s))
    .filter((s) => !q || norm([s.name_th, s.code, s.amphoe, s.province, s.river].join(" ")).includes(q))
    .sort((a, b) => (RANK[a.status] - RANK[b.status]) || ((a.freeboard_m ?? 99) - (b.freeboard_m ?? 99)));
  // Gauges without data for 24 h say nothing about now: collapsed at the end instead of mixed in (D-036).
  // Still shown when the user asks for them (the "ไม่ทราบ" chip) or searches by name.
  const keepAll = statusFilter === "unknown" || q;
  const live = keepAll ? rows : rows.filter((s) => s.status !== "unknown");
  const dead = keepAll ? [] : rows.filter((s) => s.status === "unknown");
  // Nearest first once the location is known (D-065 follow-up): the 3 nearest fresh gauges within 15 km on top, the rest
  // by severity as before (v0.15 concept); no repeats. Not while searching or filtering by status.
  let nearTop = "";
  if (lastPos && !q && !statusFilter) {
    const km = (s) => Math.hypot((s.lat - lastPos.lat) * 111, (s.lon - lastPos.lon) * 111 * Math.cos(lastPos.lat * Math.PI / 180));
    const near = live.filter((s) => s.lat != null && s.lon != null && km(s) <= 15).sort((a, b) => km(a) - km(b)).slice(0, 3);
    if (near.length) {
      const codes = new Set(near.map((s) => s.code));
      live.splice(0, live.length, ...live.filter((s) => !codes.has(s.code)));
      nearTop = `<li class="sec-heading"><span>📍 ใกล้คุณ</span></li>${near.map((s) => itemHTML(s, `<div class="meta">ห่าง ${esc(km(s).toFixed(1))} กม.</div>`)).join("")}<li class="sec-heading"><span>ทั้งหมด${region === "all" ? "ทั่วประเทศ" : `ใน${esc(REGIONS[region].th)}`}</span></li>`;
    }
  }
  const ul = document.getElementById("list");
  const raw = document.getElementById("q").value.trim();
  const place = raw.length >= 2 ? `<li class="placeq"><button type="button" class="btn placebtn">🔎 ค้นหาสถานที่ “${esc(raw)}” (ซอย ถนน ย่าน)</button><div class="placeres"></div></li>` : "";
  const tail = dead.length ? `<li class="nodata"><details><summary>สถานีที่ไม่มีข้อมูลล่าสุด ${dead.length} สถานี (ไม่ได้ส่งข้อมูลเกิน 24 ชม.)</summary>
    <ul class="list">${dead.map((s) => itemHTML(s)).join("")}</ul></details></li>` : "";
  ul.innerHTML = place + nearTop + (live.map((s) => itemHTML(s)).join("") || (dead.length ? "" : "<li class='muted'>ไม่พบสถานีชื่อนี้ ลองค้นหาเป็นสถานที่ด้านบน</li>")) + tail;
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
      : "<p class='muted'>ไม่พบสถานที่นี้ ลองชื่อซอย ถนน อำเภอ หรือแตะบนแผนที่แทน</p>";
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
    // canvas: ~1,000 gauge markers stay fast on phones (v0.16.1: the map shows every gauge in Thailand)
    map = L.map("map", { zoomControl: true, preferCanvas: true }).setView([13.76, 100.56], 11);
    setTimeout(fitRegion, 0);
    // Stations on top so they are always tappable; citizen-report cells below and non-interactive (owner
    // feedback: taps hit the Traffy circles first). A tap there opens the point check, which lists the counts.
    map.createPane("reports").style.zIndex = 350;
    map.createPane("stations").style.zIndex = 650;
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap" }).addTo(map);
    legend = L.control({ position: "bottomright" });
    legend.onAdd = () => {
      const d = L.DomUtil.create("div", "legend");
      d.innerHTML = Object.values(STATUS).map((s) => `<div><i style="background:${s.color}"></i>${esc(s.th)}</div>`).join("")
        + `<div><i style="background:#7b1fa2;opacity:.4"></i>น้ำท่วมบนถนน (Traffy) 6 ชม.<span id="street-age"></span></div>`;
      return d;
    };
    legend.addTo(map);
    const hint = L.control({ position: "topright" });
    hint.onAdd = () => { const d = L.DomUtil.create("div", "legend"); d.textContent = "👆 แตะจุดใดก็ได้บนแผนที่ เพื่อดูข้อมูลรอบจุดนั้น"; return d; };
    hint.addTo(map);
    const opts = L.control({ position: "topleft" });  // bottom-left sat under the legend and below the fold at 390 px
    opts.onAdd = () => {
      const d = L.DomUtil.create("div", "legend");
      d.innerHTML = `<label><input type="checkbox" id="nodata"> แสดงสถานีที่ยังคาดการณ์ไม่ได้ <span id="hidden-n"></span></label><div id="unplaced" class="muted"></div>`;
      L.DomEvent.disableClickPropagation(d);
      d.querySelector("#nodata").addEventListener("change", (e) => { showNoData = e.target.checked; renderMap(); });
      return d;
    };
    opts.addTo(map);
    map.on("click", (e) => checkPoint(e.latlng.lat, e.latlng.lng, "pin"));
  }
  if (layer) layer.remove();
  layer = L.layerGroup().addTo(map);
  getJSON("/api/reports?hours=6").then((r) => r.cells.forEach(([lat, lon, n]) => {
    L.circle([lat, lon], { pane: "reports", interactive: false, radius: 150 + 50 * Math.min(n, 20), color: "#6a1b9a",
      weight: 1, opacity: 0.5, fillColor: "#7b1fa2", fillOpacity: Math.min(0.30 + n * 0.03, 0.55) }).addTo(layer);
  })).catch(() => {});
  const sa = document.getElementById("street-age");
  if (sa) sa.textContent = streetAge();
  // Map default: gauges with a tested forecast and fresh data (owner, 2026-09-26: "separate the non-predictable from
  // the map, with an option to show"). The list and the point check still use every gauge.
  // The map shows every gauge in Thailand; the region chip only moves the view (v0.16.1: filtering the map by the chip
  // hid every gauge outside Bangkok, even after panning to Chiang Mai).
  const onMap = (s) => showNoData || (hasForecast(s) && s.status !== "unknown");
  const hn = document.getElementById("hidden-n");
  if (hn) hn.textContent = `(${stations.filter((s) => s.lat && !onMap(s)).length})`;
  stations.filter((s) => s.lat && s.lon && onMap(s)).sort((a, b) => RANK[b.status] - RANK[a.status]).forEach((s) => {
    const st = stOf(s);
    const approx = (s.notes || []).includes("approx_location");
    L.circleMarker([s.lat, s.lon], { pane: "stations", radius: s.status === "critical" ? 10 : 8, color: approx ? "#333" : "#fff",
      weight: 2, dashArray: approx ? "3 3" : null, fillColor: st.color, fillOpacity: s.stale ? 0.45 : 0.95, bubblingMouseEvents: false })
      .bindTooltip(`${esc(s.name_th)} — ${esc(st.th)} ${esc(levelText(s))}${notesText(s) ? `<br><small>${esc(notesText(s))}</small>` : ""}`)
      .on("click", () => showDetail(s.code)).addTo(layer);
  });
  const unplaced = stations.filter((s) => !s.lat && inRegion(s)).length;
  document.getElementById("unplaced").textContent = unplaced ? `${unplaced} สถานีไม่มีพิกัด (ดูในรายการ)` : "";
}

// Map view follows the region chip: Bangkok at street level, any other region fitted to its gauges (D-064). The
// markers do not follow it: every gauge stays on the map.
let fitPending = false;  // on a phone the map sits in a hidden tab (0×0): fit again when it is shown
function fitRegion() {
  if (!map) return;
  fitPending = map.getSize().x === 0;
  if (fitPending) return;
  if (region === "bkk") { map.setView([13.76, 100.56], 11); return; }
  const pts = stations.filter((s) => s.lat && s.lon && inRegion(s)).map((s) => [s.lat, s.lon]);
  if (pts.length) map.fitBounds(pts, { padding: [24, 24], maxZoom: 11 });
}

/* ---------- river views (1-D, gauges only; no interpolation between them) ---------- */
// v0.20.0 (owner 2026-10-03, D-072): every river ordered along HII's river line, each gauge with the list's 24 h row.
// v0.20.1 (owner: "visitors can be people around Thailand … might not found their river … search their position by
// ภาค … add tag แม่น้ำ to each station … Is necessary to show ระยะห่างจากปลายน้ำ?" → chose all four, "one line:
// Province & river", upstream at the top; D-074): ~62 waterways with >= 3 gauges, one line of two pickers, a river tag
// on every station that has a view, no river km in the rows.
let riverList = null, riverSet = new Set(), river = null, riverPicked = false, rvProv = "", rvFocus = null;
const riverShort = (r) => r.replace(/^แม่น้ำ/, "");
async function loadRivers() {
  if (!riverList) {
    riverList = (await getJSON("/api/rivers")).rivers;
    riverSet = new Set(riverList.map((r) => r.river));
  }
  return riverList;
}
const hasRiverView = (s) => s.agency !== "BMA" && riverSet.has(s.river);
const riverTag = (s) => hasRiverView(s)
  ? `<button type="button" class="rv-tag" data-river="${esc(s.river)}" data-prov="${esc(s.province || "")}" data-code="${esc(s.code)}">〰️ ดู${esc(s.river)}ทั้งสาย ›</button>` : "";
function defaultRiver(list) {
  // the region chip's biggest river (the list is sorted by gauges), else the Chao Phraya
  const mine = ["bkk", "metro", "up", "all"].includes(region) ? null : list.find((r) => r.region === region);
  return (mine || list[0]).river;
}
async function renderRiver() {
  const box = document.getElementById("view-river");
  box.innerHTML = "<p class='muted'>กำลังโหลด…</p>";
  try {
    await loadRivers();
    if (!riverList.length) { box.innerHTML = "<p class='muted'>ยังไม่มีข้อมูลแม่น้ำ</p>"; return; }
    const inProv = rvProv ? riverList.filter((r) => (r.provinces || []).includes(rvProv)) : riverList;
    if (!riverPicked || !inProv.some((r) => r.river === river)) river = rvProv ? inProv[0].river : defaultRiver(riverList);
    const d = await getJSON(`/api/profile?river=${encodeURIComponent(river)}`);
    const provs = [...new Set(riverList.flatMap((r) => r.provinces || []))].sort((a, b) => a.localeCompare(b, "th"));
    const pick = `<div class="rv-pick">
      <select id="rv-prov" aria-label="จังหวัด"><option value="">ทุกจังหวัด</option>${provs.map((p) => `<option value="${esc(p)}"${p === rvProv ? " selected" : ""}>${esc(p)}</option>`).join("")}</select>
      <select id="rv-river" aria-label="แม่น้ำ">${inProv.map((r) => `<option value="${esc(r.river)}"${r.river === river ? " selected" : ""}>${esc(r.river)} (${r.n})</option>`).join("")}</select></div>`;
    // upstream at the top: the water flows down the screen (owner 2026-10-03); the API lists upstream first
    const rows = d.stations.map((s) => {
      const st = stOf(s), old = s.stale || s.status === "unknown";
      const pct = old || s.pct_bank == null ? 0 : Math.max(2, Math.min(100, s.pct_bank));
      const val = old ? `<span class="pval muted">ไม่อัปเดต</span>`
        : `<span class="pval" style="color:${st.color}">${s.freeboard_m == null ? "-" : esc(cm(-s.freeboard_m))}</span>`;
      const here = rvProv && s.province === rvProv;
      return `<div class="prow${here ? " here" : ""}${s.code === rvFocus ? " focus" : ""}" data-code="${esc(s.code)}" role="button" tabindex="0">
        <span class="pname">${esc(s.name_th)} <small>${esc(s.province || "")}</small></span>
        <span class="pbar" title="ความลึกน้ำเทียบความลึกตลิ่ง ${esc(s.pct_bank ?? "-")}%"><span style="width:${pct}%;background:${old ? "#d1d5db" : st.color}"></span></span>
        ${val}${old ? "" : `<div class="pfc">${trendRows(s, [24])}</div>`}</div>`;
    }).join("");
    const byBank = riverList.find((r) => r.river === river)?.has_km === false;
    box.innerHTML = `${pick}
      <p class="muted">อ่านจากบนลงล่าง: ต้นน้ำ → ปลายน้ำ · ตัวเลข = ระดับน้ำเทียบตลิ่ง (ติดลบ = ต่ำกว่าตลิ่ง)
      <details class="sumdetails"><summary>อ่านกราฟนี้</summary>แถบ = ความลึกน้ำเทียบตลิ่ง ·
      ${byBank ? "สายนี้ไม่มีแนวลำน้ำในแผนที่ของ สสน. จึงเรียงตามความสูงของตลิ่ง (ตลิ่งสูงอยู่ทางต้นน้ำ)" : "เรียงตามแนวลำน้ำในแผนที่ของ สสน."} ·
      "อีก 24 ชม." แสดงเฉพาะสถานีที่ทดสอบย้อนหลังผ่าน · ค่าระหว่างสถานีไม่ได้ประมาณ เพราะตลิ่งและคันกั้นน้ำแต่ละช่วงสูงไม่เท่ากัน · สถานีของ กทม. ดูได้ในรายการและแผนที่</details></p>
      <div class="rv-end">↑ ต้นน้ำ</div>${rows}<div class="rv-end">↓ ปลายน้ำ</div>`;
    box.querySelector("#rv-prov").addEventListener("change", (e) => { rvProv = e.target.value; rvFocus = null; riverPicked = false; renderRiver().then(scrollRiver); });
    box.querySelector("#rv-river").addEventListener("change", (e) => { river = e.target.value; riverPicked = true; rvFocus = null; renderRiver().then(scrollRiver); });
    box.querySelectorAll(".prow").forEach((r) => {
      r.addEventListener("click", (e) => { if (!e.target.closest(".conf-badge")) showDetail(r.dataset.code); });
      r.addEventListener("keydown", (e) => { if (e.key === "Enter") showDetail(r.dataset.code); });
    });
  } catch (e) {
    box.innerHTML = `<p>โหลดข้อมูลไม่สำเร็จ (${esc(e.message)})</p>`;
  }
}
// after a pick or a tag: show the station (or the first gauge in the chosen province), not the top of the river
function scrollRiver() {
  const el = document.querySelector("#view-river .prow.focus") || document.querySelector("#view-river .prow.here");
  if (el) el.scrollIntoView({ block: "center", behavior: "smooth" });
}
document.addEventListener("click", (e) => {
  const b = e.target.closest(".rv-tag");
  if (!b) return;
  river = b.dataset.river; riverPicked = true; rvProv = b.dataset.prov || ""; rvFocus = b.dataset.code;
  closeDetail();
  setTab("river");
});

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

// New gauges (history < 7 days, e.g. BMA from 26 Sep): say why the chart is short and when a forecast can start,
// so a short chart is not mistaken for lost data (owner, 2026-09-26).
function bmaNote(s) {
  if (s.status_basis !== "bma_thresholds") return { line: "", box: "" };
  const crit = s.bma_critical_msl != null ? `เกณฑ์วิกฤตของ กทม. ${s.bma_critical_msl.toFixed(2)} ม.` : "ไม่มีเกณฑ์ของ กทม.";
  const full = ["warning", "watch"].includes(s.status);
  return { line: `<p class="muted">${esc(freeboardText(s.freeboard_m))} · ${esc(crit)}</p>`, box: full
    ? `<div class="warnbox">น้ำในคลองสูงกว่าเกณฑ์ของ กทม. คลองจึง<b>รับน้ำจากท่อระบายบนถนนได้ช้า</b> ถนนรอบ ๆ อาจท่วมแม้คลองยังไม่ล้นตลิ่ง</div>` : "" };
}

function streetNote(s) {
  const n = s.street_reports_6h || 0;
  if (n < STREET_MIN) return "";
  const calm = s.status === "normal" || (s.status === "watch" && s.status_basis !== "bma_thresholds");
  return `<div class="warnbox"><strong>ถนนรอบสถานีนี้ (1 กม.) มีรายงานน้ำท่วม ${n} เรื่องใน 6 ชม.</strong>${esc(streetAge())} (Traffy Fondue)
    ${calm ? `<br>น้ำใน${s.water || "คลอง"}ยังต่ำกว่าตลิ่ง แต่ถนนท่วมได้ เพราะฝนตกหนักเกินกว่าท่อระบายน้ำจะรับไหว
      ${s.agency === "BMA" ? "และ กทม. มักพร่องน้ำในคลองไว้รับฝน " : ""}<b>สถานีนี้วัดน้ำใน${s.water || "คลอง"} ไม่ได้วัดน้ำบนถนน</b>` : ""}</div>`;
}

const NEW_DAYS = 7;
const isNew = (s) => s.history_days != null && s.history_days < NEW_DAYS;
function newGaugeNote(s, fc) {
  if (!isNew(s) || Object.keys(fc?.skill || {}).length) return "";  // a placeholder forecast exists without any tested skill
  // D-064: history is fetched from HII for every gauge; the forecast starts after its backtest, not on a fixed date
  return `<div class="warnbox"><strong>กำลังดึงข้อมูลย้อนหลังจาก สสน.</strong> เรามีข้อมูลสถานีนี้ตั้งแต่ ${esc(fmtTime(s.history_since))} ·
    กราฟจะยาวขึ้นเมื่อดึงข้อมูลย้อนหลังครบ 1 ปี · การคาดการณ์จะแสดงเมื่อทดสอบย้อนหลังแล้วแม่นกว่าการใช้ค่าล่าสุด</div>`;
}

function chartSVG(obs, fc, bank, crit = null) {
  const W = 400, H = 200, P = 34, GAP_MS = 90 * 60e3;  // gaps longer than 90 min are not bridged
  const pts = obs.filter((o) => o[1] != null).map((o) => [Date.parse(o[0]), o[1]]);
  if (pts.length < 2) return "<p class='muted'>ข้อมูลย้อนหลังไม่พอสำหรับกราฟ</p>";
  const t0 = pts[pts.length - 1][0];
  const band = (fc?.path || []).filter((p) => p.q).map((p) => [t0 + p.h * 3600e3, p.q]);
  const ys = pts.map((p) => p[1]).concat(band.flatMap((b) => [b[1][0], b[1][4]]), bank != null ? [bank] : [], crit != null ? [crit] : []);
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
    ${bankLine}${crit != null ? `<line x1="${P}" x2="${W - 6}" y1="${y(crit)}" y2="${y(crit)}" stroke="#e46c0a" stroke-dasharray="2 3"/><text x="${P + 4}" y="${y(crit) - 4}" font-size="11" fill="#e46c0a">เกณฑ์ กทม. ${crit.toFixed(2)}</text>` : ""}<path d="${line}" fill="none" stroke="#0d3b66" stroke-width="1.6"/>
    ${med ? `<path d="${med}" fill="none" stroke="#1565c0" stroke-width="1.6" stroke-dasharray="4 3"/>` : ""}
    ${dayTicks(tmin, tmax, x, H)}
    <line x1="${x(t0)}" x2="${x(t0)}" y1="8" y2="${H - 20}" stroke="#555" stroke-width=".8"/>
    <text x="${x(t0)}" y="9" font-size="10" text-anchor="middle" fill="#333" font-weight="600">ตอนนี้</text></svg>
    <details class="chart-legend"><summary>ℹ️ สัญลักษณ์กราฟ</summary><div class="legend-body">เส้นทึบ = ค่าตรวจวัดจริง (ช่วงที่ขาดหายไม่ได้ลากเส้นเชื่อม) · เส้นประน้ำเงิน = ค่ากลางคาดการณ์ · แถบเข้ม/อ่อน = ช่วง 50%/90% · หน่วย ม.รทก.</div></details>`;
}

/* ---------- texts ---------- */
// A time window without false precision (D-005): whole hours for a short window, dates only for a long one
// (a resident read "30 ก.ย. 01:12 – 2 ต.ค. 05:12" as exact, 2026-09-27 UX check).
function whenText(hMin, hMax) {
  const d = (h) => new Date(Date.now() + h * 3600e3);
  const day = (x) => x.toLocaleDateString("th-TH", { ...TZ, day: "numeric", month: "short" });
  const hr = (x) => x.toLocaleTimeString("th-TH", { ...TZ, hour: "2-digit" }).replace(/:\d\d.*$/, "");
  const a = d(hMin), b = hMax == null ? null : d(hMax);
  if (!b) return `หลัง ${day(a)}`;
  if (hMax - hMin >= 24) return day(a) === day(b) ? day(a) : `${day(a)} – ${day(b)}`;
  return day(a) === day(b) ? `${day(a)} ราว ${hr(a)}–${hr(b)} น.` : `${day(a)} ${hr(a)} น. – ${day(b)} ${hr(b)} น.`;
}


function outlookRows(fc, s) {
  const o = fc?.outlook24;
  if (!o) return "";
  const out = [];
  if (o.varies && o.peak_h >= 3 && fc.issue_time) {  // peak 1-2 h out = "highest now, falling after"
    const tp = Date.parse(fc.issue_time) + o.peak_h * 3600e3;
    out.push(`สูงสุดในอีก 24 ชม. ราว ${esc(fmtHour(tp - 3600e3))}–${esc(fmtHour(tp + 3600e3))} น.`);
  }
  if (o.bank_chance && s.status !== "critical") out.push(`โอกาสถึงตลิ่งในอีก 24 ชม.: ${esc(CHANCE[o.bank_chance] || o.bank_chance)}`);
  return out.length ? `<div class="muted">${out.join(" · ")}</div>` : "";
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
    <label><input type="checkbox" name="loc"${loc ? " checked" : ""}> แนบตำแหน่ง${loc ? (loc.src === "pin" ? "ของหมุดนี้" : "ของคุณ") : ""}โดยประมาณ (ปัดเป็นราว 100 ม.)</label>
    <input class="hp" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">
    <p class="muted">ไม่เก็บชื่อหรือเบอร์โทร · ข้อความไม่แสดงต่อสาธารณะ · ใช้ตรวจสอบและปรับปรุงการคาดการณ์เท่านั้น ·
      <b>ไม่ใช่ช่องทางขอความช่วยเหลือ</b> เหตุฉุกเฉินโทร 1784 / 1555</p>
    <button type="submit" class="btn primary">ส่งความเห็น</button> <span class="fb-msg muted" aria-live="polite"></span>
  </form>`;
}

// Issue #2: the report form opens from one button in a popup, so the panel stays short. Report counts before the
// change (2026-09-27): 57 in 24 h, 56 with a depth — compare after release (HANDOFF).
function reportButton(loc) {
  return `<button type="button" class="btn primary report-open">รายงานน้ำที่จุดของคุณ</button>
    <dialog class="report-dlg" aria-label="รายงานน้ำที่จุดของคุณ">
      <div class="tools"><button type="button" class="btn report-close" aria-label="ปิด">✕</button></div>
      ${feedbackForm(null, loc)}
    </dialog>`;
}

function bindReport(root) {
  const dlg = root.querySelector(".report-dlg"), open = root.querySelector(".report-open");
  if (!dlg || !open) return;
  open.addEventListener("click", () => (dlg.showModal ? dlg.showModal() : dlg.setAttribute("open", "")));
  dlg.querySelector(".report-close").addEventListener("click", () => (dlg.close ? dlg.close() : dlg.removeAttribute("open")));
  dlg.addEventListener("click", (e) => { if (e.target === dlg && dlg.close) dlg.close(); });  // tap outside closes
  bindFeedback(dlg.querySelector(".feedback"));
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
  if (updatePending) location.reload();  // a new release arrived while the panel was open
}

// A panel's gauges are fresher than the list (loaded up to 5 min ago, shared 60 s): the list takes them, so list,
// sheet and pin tell the same story once looked at (C1 findings 2026-10-01). Returns true when something changed.
function refreshListItems(rows) {
  let changed = false;
  for (const s of rows) {
    if (!s || !s.code) continue;
    const i = stations.findIndex((x) => x.code === s.code);
    if (i < 0) continue;
    const { distance_km, water_body, local, ...row } = s;  // point-panel extras are not station fields
    const merged = { ...stations[i], ...row };
    if (JSON.stringify(merged) !== JSON.stringify(stations[i])) { stations[i] = merged; changed = true; }
  }
  return changed;
}

async function showDetail(code) {
  const sheet = document.getElementById("sheet"), box = document.getElementById("detail");
  sheet.hidden = false;
  box.innerHTML = "<p class='muted'>กำลังโหลด…</p>";
  history.replaceState(null, "", `#s=${encodeURIComponent(code)}`);
  try {
    const d = await getJSON(`/api/stations/${encodeURIComponent(code)}?days=5`);
    const s = d.station, st = stOf(s), fc = d.forecast;
    // The sheet is fresher than the list (loaded up to 5 min ago): the list takes the sheet's row, so both tell the
    // same story after you looked (C1 findings 2026-10-01: a forecast or QC update landed in between).
    const li = stations.findIndex((x) => x.code === s.code);
    if (refreshListItems([s])) renderList();
    const methods = fc ? [...new Set(Object.values(fc.skill || {}).map((k) => k.method))] : [];
    const skill12 = fc?.skill?.["12"];
    const bma = s.agency === "BMA", unit = bma ? "ม. (หมุด กทม.)" : "ม.รทก.";  // BMA datum unverified vs HII (KI-217)
    const hid = (s.notes || []).find((n) => n === "erratic" || n === "stuck"), erratic = !!hid;  // pumps at the sensor or a faulty sensor (D-057): the reason leads
    box.innerHTML = `<div class="tools"><button class="btn share" aria-label="แชร์">🔗 แชร์</button><button class="btn close" aria-label="ปิด">✕</button></div>
      <h2 id="sheet-title">${esc(s.name_th)} <span class="muted">${esc(s.code)}</span></h2>
      <div class="muted">${esc(s.river || "")} · ${esc(s.amphoe || "")} ${esc(s.province || "")} · ${esc(agencyTh(s.agency))}</div>
      ${riverTag(s)}
      ${s.twin ? `<p class="muted twin">อีกหน่วยงานวัดที่จุดเดียวกัน: <a href="#s=${encodeURIComponent(s.twin.code)}">${esc(s.twin.name_th)} (${esc(agencyTh(s.twin.agency))}) ›</a> · ตลิ่งและหมุดอ้างอิงของแต่ละหน่วยงานต่างกัน</p>` : ""}
      <p class="headline" style="color:${st.color}">${erratic ? (hid === "stuck" ? "ไม่แสดงระดับน้ำ (ค่าค้าง)" : "ไม่แสดงระดับน้ำ (ขึ้นลงผิดปกติ)") : s.status_basis === "bma_thresholds"
        ? `${esc(st.long)}${s.over_bma_critical_m != null && s.over_bma_critical_m > 0 && s.status !== "critical" ? ` · ${esc(levelText(s))}` : ""}`
        : s.status === "normal" && s.freeboard_m != null ? esc(`น้ำใน${s.water || "คลอง"}${freeboardText(s.freeboard_m)}`)
        : `${esc(st.long)}${s.freeboard_m != null ? ` · <span class="nowrap">${esc(freeboardText(s.freeboard_m) + ydayText(s))}</span>` : ""}`}</p>
      ${bmaNote(s).line}
      <p class="obs-time-row"><span>ข้อมูล ${esc(fmtTime(s.obs_time))} (${esc(fmtAge(s.age_min))})</span> <button type="button" class="msl-btn" title="${esc(`ระดับน้ำจริง: ${s.level_msl?.toFixed(2) ?? "-"} ${unit} · ตลิ่ง: ${s.bank_msl?.toFixed(2) ?? "ไม่ทราบ"} ${unit}${bma ? " · ข้อมูลสำนักการระบายน้ำ กทม. ผ่านเว็บ flood69 (พรรคประชาชน) และประวัติย้อนหลังจาก สสน. · ระดับอ้างอิงของ กทม. อาจต่างจากสถานี สสน. ใกล้กัน 30–60 ซม." : ""}`)}" aria-label="ระดับน้ำและที่มาข้อมูล">${bma ? "ข้อมูล กทม. ⓘ" : "ม.รทก. ⓘ"}</button>${s.stale ? ` <span class="warn-pill">ข้อมูลเก่า แหล่งข้อมูลอาจขัดข้องชั่วคราว</span>` : ""}</p>
      ${trendRows(s, [12, 24, 48]) ? `<div class="sheet-trend"><div class="pf-h">แนวโน้มที่สถานีนี้</div>${trendRows(s, [12, 24, 48])}
        ${changeLines(s)}${upstreamLine(s)}${outlookRows(fc, s)}</div>` : erratic ? `<div class="warnbox">${esc(NOTE[hid])}</div>` : obsLine(s) || `<p class="muted">${esc(observedText(s) || TREND.unknown)}</p>`}
      ${streetNote(s)}${newGaugeNote(s, fc)}${chartSVG(d.observations, fc, s.bank_msl, s.bma_critical_msl)}
      ${bmaNote(s).box}
      ${(() => { const t = notesText({ ...s, notes: (s.notes || []).filter((n) => n !== "erratic" && n !== "stuck") }); return t ? `<div class="warnbox">${esc(t)}</div>` : ""; })()}
      <details class="sumdetails"><summary>วิธีคาดการณ์</summary><p class="muted">${esc(erratic ? "ไม่คาดการณ์ (ค่าระดับน้ำไม่น่าเชื่อถือ)" : methods.map((m) => METHOD_TH[m] || m).join(", ") || "ข้อมูลไม่พอ")}${skill12 ? ` · ที่ 12 ชม. ทดสอบย้อนหลัง ${skill12.n} ครั้ง` : ""}${fc && !fc.tide_fitted ? " · ยังไม่มีข้อมูลพอสำหรับคำนวณน้ำขึ้นน้ำลง" : ""}
        · ตลิ่งของสถานีอาจไม่เท่ากับระดับถนนหรือบ้านของคุณ</p></details>
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
  const text = `${s.name_th}: ${stOf(s).long || ""} ${levelText(s)} (BKK FloodWatch)`;
  try {
    if (navigator.share) await navigator.share({ title: "BKK FloodWatch", text, url });
    else { await navigator.clipboard.writeText(`${text} ${url}`); document.querySelector(".share").textContent = "✔ คัดลอกแล้ว"; }
  } catch (_) { /* user cancelled */ }
}

// AI on request only (D-068; owner 2026-10-02: one "ask AI" button "to reduce unnecessary AI generated"). The panel
// shows the rule-written plain line; one tap opens a story card: GLM's retelling when it passes the server's check,
// else the rule story, with the numbers folded under "ดูตัวเลข". Nothing calls GLM until the button is tapped.
const askHTML = () => `<button type="button" class="ai-btn" aria-expanded="false">✨ ให้ AI สรุปให้ฟังง่าย ๆ</button>
  <div class="story" hidden><div class="story-h">✨ สรุปง่าย ๆ</div><div class="story-body" aria-live="polite"></div></div>`;
async function fillStory(body, url, isOpen) {
  try {
    const r = await getJSON(url);
    let text = r.story, by = "สรุปจากข้อมูลในแอป (AI ตอบไม่ได้ตอนนี้)";
    if (r.ai) {  // never wait longer than 7 s for GLM
      const g = await Promise.race([getJSON(`${url}&part=gist`).catch(() => null), new Promise((ok) => setTimeout(() => ok(null), 7000))]);
      if (g && g.gist) { text = g.gist; by = "✨ AI เล่าจากข้อมูลในแอป · ตัวเลขอยู่ใน “ดูตัวเลข”"; }
    }
    if (!isOpen() || !body.isConnected) return;
    body.innerHTML = `<p class="story-text">${esc(text)}</p><details class="story-more"><summary>ดูตัวเลข</summary>
      <div class="ask-lines">${r.lines.map((l) => `<p>${esc(l)}</p>`).join("")}</div></details><p class="ask-by">${by}</p>`;
  } catch (_) {
    if (isOpen() && body.isConnected) body.innerHTML = `<p class="muted">ตอนนี้สรุปไม่ได้ ลองแตะอีกครั้ง</p>`;
  }
}
function bindAsk(box, lat, lon) {
  const btn = box.querySelector(".ai-btn"), card = box.querySelector(".story");
  if (!btn || !card) return;
  const body = card.querySelector(".story-body"), open = () => btn.getAttribute("aria-expanded") === "true";
  btn.addEventListener("click", () => {
    const now = !open();
    btn.setAttribute("aria-expanded", String(now));
    card.hidden = !now;
    if (!now) return;  // a second tap closes it
    body.innerHTML = `<p class="story-text shimmer">กำลังสรุปให้…</p>`;
    fillStory(body, `/api/explain?lat=${lat.toFixed(5)}&lon=${lon.toFixed(5)}&q=simple`, open);
  });
}

/* ---------- point check: a place with no gauge (D-021) ---------- */
const WARN = {
  no_gauge_at_point: "นี่<b>ไม่ใช่ระดับน้ำที่จุดนี้</b> สถานีวัดน้ำในคลองหรือแม่น้ำ ไม่ได้วัดบนถนนหรือในบ้าน",
  terrain_not_flat: "กรุงเทพฯ สูงต่ำไม่เท่ากัน จุดที่อยู่ใกล้กันอาจท่วมไม่เท่ากัน",
  walls_and_polders: "คันกั้นน้ำและประตูระบายน้ำแบ่งพื้นที่ ถ้าอยู่นอกคันริมแม่น้ำให้ดูสถานี “แม่น้ำ” ถ้าอยู่ด้านในให้ดูสถานี “คลอง”",
  gauges_far_or_disagree: "สถานีรอบ ๆ อยู่ไกลหรือให้ผลต่างกันมาก ใช้ประกอบเท่านั้น",
  nearest_gauge_far: "สถานีที่ใกล้ที่สุดอยู่ห่างเกิน 3 กม.",
  street_flooding_despite_channels: "<b>มีรายงานน้ำท่วมขังบนถนนรอบจุดนี้</b> (น้ำรอระบาย) — โปรดระวังการเดินทาง แม้คลองใกล้เคียงยังไม่ล้น",
};
const CONF = { medium: "ปานกลาง", low: "ต่ำ", very_low: "ต่ำมาก", none: "ประเมินไม่ได้" };
let pinMarker = null;

function pointHTML(d, src, place = "") {
  const a = d.area, ev = d.evidence;
  const depths = Object.entries(ev.user_depth_reports_1km_24h || {}).map(([k, n]) => `${esc(DEPTH[k] || k)} ${Number(n)} ราย`).join(" · ");

  const fc = d.forecast || {};
  const nat = d.mode === "national", W = d.word || "คลอง";  // D-064: outside Bangkok the local channel is a river
  const head = (k) => nat ? ({ "ล้นตลิ่ง": `น้ำใน${W}ล้นตลิ่ง`, "ใกล้ตลิ่ง/คลองเต็ม": `น้ำใน${W}ใกล้ถึงตลิ่ง`,
    "เฝ้าระวัง": `น้ำใน${W}เริ่มสูง ควรเฝ้าระวัง`, "ยังรับน้ำได้": `${W}ยังรับน้ำได้`, "ไม่ทราบ": `ยังไม่ทราบระดับน้ำใน${W}`,
    "ไม่มีสถานีใกล้": "ไม่มีสถานีวัดน้ำใกล้จุดนี้", [`${W}รอบจุดต่างกันมาก`]: `${W}รอบจุดต่างกันมาก`, "สถานีอยู่ไกล": "สถานีวัดน้ำอยู่ไกล" }[k] || k)
    : (CANAL_HEAD[k] || k);
  const FC_RISK = {  // one icon, on the headline only (issue #3: fewer emojis)
    high: { cls: "risk-high", icon: "⚠️" }, moderate: { cls: "risk-mod", icon: "⚠️" },
    low: { cls: "risk-low", icon: "" }, info: { cls: "risk-info", icon: "" },
  };
  const fcR = FC_RISK[fc.risk] || FC_RISK.info;
  const FC_BASIS = { rain: "ฝนคาดการณ์ (Open-Meteo)", rain_measured: "ฝนที่วัดได้ (สถานีวัดฝน สสน.)", reports: "รายงานน้ำท่วมถนน (Traffy Fondue)", gauges: "สถานีวัดน้ำ (สสน. / กทม.)" };
  // Factor 1: canals (D-054). Lead with the nearest canal gauge — its state and 24/48 h change — then fold the rest.
  // The dot follows the confidence gate, now judged from the nearest gauges (≤ 3 within 3 km), not the whole 8 km.
  // Canal summary in plain words (owner 2026-09-27: the old "ใกล้จุด 3 แห่ง … ทั้งรัศมี 8 กม. …" was not understood)
  let canal;
  if (!a.category) {
    canal = { color: "#9ca3af", word: "ไม่มีสถานีใกล้", sub: "ไม่มีสถานีวัดน้ำในระยะ 8 กม." };
  } else if ((a.confidence === "very_low" || a.confidence === "none") && a.n_close) {
    canal = { color: "#9ca3af", word: nat ? `${W}รอบจุดต่างกันมาก` : "คลองรอบจุดต่างกันมาก",
      sub: `${nat ? "สถานี" : "คลอง"}ใกล้จุด ${a.n_close} แห่ง (ไม่เกิน 3 กม.) มีตั้งแต่ “${esc(STATUS[a.min].th)}” ถึง “${esc(STATUS[a.max].th)}” จึงสรุปรวมไม่ได้ ดูทีละสถานีด้านล่าง` };
  } else if (a.confidence === "very_low" || a.confidence === "none") {
    canal = { color: "#9ca3af", word: "สถานีอยู่ไกล", sub: `สถานีใกล้สุดห่าง ${a.nearest_km} กม.${nat ? " อาจอยู่คนละลำน้ำ" : " อาจอยู่คนละพื้นที่ปิดล้อม"}` };
  } else {
    canal = { color: STATUS[a.category].color, word: STATUS[a.category].th, sub: `สรุปจาก${nat ? "สถานี" : "คลอง"}ใกล้จุด ${a.n_close || a.n} แห่ง` };
  }
  // When will it drop? The station's recovery estimate in dates/hours (never minutes, KI-231)
  // Compact canal block (owner 2026-09-27: "too much text, collapse the not important"): one gauge with its trend rows and
  // one "when it drops" line; why/where details are folded. If the nearest canal has no forecast (relay-only BMA gauge),
  // it gets one line and the nearest canal with a forecast carries the trend (KI-232).
  const pill = (x) => `<span class="badge b-${esc(x.status)}">${esc(stOf(x).th)}</span>`;
  // One block per gauge, same structure for both (owner 2026-09-27: one name was bold, the other not, and the labels ran
  // into long lines): label on its own line → bold name · distance · status pill → that gauge's rows or "no forecast".
  const gBlock = (label, c, body) => `<div class="pf-gauge" data-code="${esc(c.station.code)}"><div class="pf-glabel">${label}</div>
    <div class="pf-gline"><span class="pf-gname">${esc(c.station.name_th)}</span><span class="muted">ห่าง ${esc(c.distance_km)} กม.${c.far ? " (ไกล)" : ""}</span>${stOf(c.station).th.includes(canal.word) ? "" : pill(c.station)}</div>${body}</div>`;
  const near = d.nearest_canal, withTrend = d.nearest_canal_trend;
  const main = near && near.station && (near.station.change24 || near.station.change12) ? near : withTrend;
  // 24/48 h rows; a gauge with only a 12 h forecast (short history) shows that row instead of nothing (KI-239)
  const trendBody = (x) => `${trendRows(x, [24, 48]) || trendRows(x, [12])}${changeLines(x)}${upstreamLine(x)}`;
  const noTrendLine = near && near.station && main !== near
    // what we know about it (its measured 24 h change, the rows' words) instead of jargon; the why behind an ⓘ
    // (owner 2026-10-02: "ห่าง 1.5 กม." + the block "can be improved")
    ? gBlock(nat ? "สถานีใกล้สุด" : "คลองใกล้สุด", near, `<div class="muted">ยังไม่มีคาดการณ์ ${infoBtn(`สถานีนี้ยังไม่ผ่านการทดสอบย้อนหลัง จึงยังไม่คาดการณ์ ดูคาดการณ์จาก${nat ? "สถานี" : "คลอง"}ใกล้เคียงด้านล่าง`, "ทำไมยังไม่มีคาดการณ์")}</div>${obsLine(near.station)}`) : "";
  const mainBlock = main && main.station
    ? gBlock(noTrendLine ? `คาดการณ์จาก${nat ? "สถานี" : "คลอง"}ใกล้เคียง` : nat ? "สถานีใกล้สุด" : "คลองใกล้สุด", main, trendBody(main.station)) : "";
  const detailBits = [canal.sub, main && main.far ? `สถานีที่ใช้อยู่ห่างเกิน 3 กม. ${nat ? "อาจอยู่คนละลำน้ำ" : "อาจอยู่คนละพื้นที่ปิดล้อม"} ใช้ประกอบเท่านั้น` : "",
    main && main.station ? `ข้อมูลจาก${agencyTh(main.station.agency)}${["HII", "BMA"].includes(main.station.agency) ? "" : " (ผ่าน สสน.)"}` : "",
    a.n > 1 ? `มีสถานีอื่นอีก ${a.n - 1} แห่งในระยะ 8 กม. (รายชื่อด้านล่าง)` : ""].filter(Boolean);
  // the why/where behind an ⓘ like the rain factor's (owner 2026-10-01: "Continue all suggestions" — one way per panel)
  const canalInfo = detailBits.length ? `<button type="button" class="conf-badge conf-low" title="${esc(detailBits.join(" · "))}" aria-label="ที่มาและรายละเอียดของสถานีวัดน้ำ">ⓘ</button>` : "";
  const canalGauges = `<div class="pf-gauges">${noTrendLine}${mainBlock}</div>`;

  // The river near a Bangkok pin: its own line, never canal evidence (D-059); riverside streets flood from it (v0.16.3)
  const nr = d.nearest_river?.station;
  const riverLine = nr ? `<li><span class="pf-dot" style="background:${stOf(nr).color}"></span><div><b class="pf-word">${esc(`แม่น้ำใกล้จุด: ${nr.freeboard_m != null ? freeboardText(nr.freeboard_m) : stOf(nr).th}`)}</b>
      <div class="pf-sub">${esc(nr.name_th)} ห่าง ${esc(d.nearest_river.distance_km)} กม. · ${esc(stOf(nr).th)} · มีผลกับบ้านริมแม่น้ำนอกคันกั้นน้ำ ไม่ใช่ระดับน้ำในคลอง</div></div></li>` : "";
  // Factor 2: rain (TMD words and colours). Factor 3: street reports (≥ 3 in 1 km / 6 h = the alert level, STREET_ALERT).
  const rain = d.rain_next24_mm;
  // Rain factor in the water factor's layout (owner 2026-10-02: "Text for rainfall info are one in a long sentence …
  // Compare to the water level info, it is easier"): a short bold state, then rainRows — the forecast row with its own ⓘ
  // and what fell in the past-line style; where it was measured is behind the ⓘ next to the state.
  const rm = d.rain_measured, rmMm = rm ? Number(rm.rain_24h) : null;
  const rk = (mm) => RAIN_TMD.findIndex(([, l]) => l === rainLabel(mm));
  const rainHead = rm && rmMm >= 0.1 ? "ฝนตกแล้ว" : rain != null && rain >= 0.1 ? "คาดว่าจะมีฝน"
    : rain != null || rm ? "ไม่มีฝน" : "ยังไม่มีข้อมูลฝน";
  const grid = String(d.rain_point || "").startsWith("f_") ? "ช่องคำนวณราว 8 กม." : String(d.rain_point || "").startsWith("g_") ? "ช่องคำนวณราว 55 กม." : "จุดคำนวณย่านนี้";
  const fcTip = rain != null ? `ฝนคาดการณ์จาก Open-Meteo (${grid}) ฝนจริงอาจต่างจากที่คาด โดยเฉพาะฝนฟ้าคะนอง` : "";
  const rainInfo = rm ? infoBtn(`วัดจริง: สถานีวัดฝน ${rm.name_th} (สสน.) ห่าง ${rm.distance_km} กม. · ข้อมูลถึง ${fmtTime(rm.obs_time)}`, "ที่มาของฝนที่วัดได้") : "";
  const rainBody = rainRows(rain, fcTip, rmMm, rm && rm.rain_1h != null ? Number(rm.rain_1h) : null);
  const rainColor = rm && rain != null && rk(rmMm) > rk(rain) ? RAIN_COLOR[rainLabel(rmMm)]
    : rain != null ? RAIN_COLOR[rainLabel(rain)] : rm ? RAIN_COLOR[rainLabel(rmMm)] : "#9ca3af";
  const nRep = Number(ev.traffy_flood_reports_1km_6h || 0);
  const streetF = nRep >= 3 ? { color: "#c62828", word: `มีแจ้ง ${nRep} เรื่อง` } : nRep > 0 ? { color: "#b45309", word: `มีแจ้ง ${nRep} เรื่อง` }
    : { color: "#9ca3af", word: "ยังไม่มีรายงาน" };
  const hasStreetFlood = (d.warnings || []).includes("street_flooding_despite_channels");
  // Satellite (Q45 yes, D-071): one line only when GISTDA's radar SAW flooding within 1 km; silence otherwise, because
  // radar is blind among buildings and trees (research/2026-10-02_satellite_flood.md: 61-71 % of central Bangkok).
  const satDates = (a, b) => {
    const f = (x, m) => new Date(`${x}T12:00:00+07:00`).toLocaleDateString("th-TH", { day: "numeric", ...(m ? { month: "short" } : {}), timeZone: "Asia/Bangkok" });
    if (!b) return "";
    if (!a || a === b) return f(b, true);
    return a.slice(0, 7) === b.slice(0, 7) ? `${f(a, false)}–${f(b, true)}` : `${f(a, true)}–${f(b, true)}`;
  };
  const sat = d.satellite;
  const satLine = sat ? (() => {
    const m = sat.nearest_m, where = m <= 200 ? "บริเวณจุดนี้" : m >= 1000 ? `ห่างราว ${Math.floor(m / 1000)} กม.` : `ห่างราว ${m} ม.`;
    const tip = "ภาพเรดาร์จากดาวเทียม (Sentinel-1, COSMO-SkyMed, Radarsat-2) ประมวลผลโดย GISTDA ช่วง 7 วัน · ดาวเทียมมองไม่เห็นน้ำในเขตเมืองหนาแน่นและใต้ต้นไม้ ไม่เห็นไม่ได้แปลว่าไม่มีน้ำท่วม · เป็นน้ำบนพื้นดิน ไม่ใช่ระดับน้ำในคลองหรือแม่น้ำ";
    const dates = satDates(sat.img_from, sat.img_to);
    return `<li><span class="pf-dot" style="background:${m <= 200 ? "#c62828" : "#b45309"}"></span><div><b class="pf-word">ดาวเทียมเห็นน้ำท่วม${esc(where)}</b>${infoBtn(tip, "ที่มาของภาพดาวเทียม")}
      <div class="pf-sub">${sat.area_rai >= 1 ? `รวมราว ${esc(String(sat.area_rai))} ไร่ในรัศมี 1 กม. · ` : ""}${dates ? `ภาพ ${esc(dates)} ` : ""}(GISTDA)</div></div></li>`;
  })() : "";

  // Everything that explains or qualifies goes behind one ⓘ (owner 2026-09-27: "everything into ⓘ", issue #3).
  const staticWarnings = (d.warnings || []).filter((w) => w !== "street_flooding_despite_channels");
  const infoBody = `<p><b>ข้อมูลที่ใช้:</b> ${esc((fc.basis || []).map((b) => FC_BASIS[b] || b).join(" · ") || "-")}</p>
    ${staticWarnings.map((w) => `<p>• ${WARN[w] || esc(w)}</p>`).join("")}
    <p>• ระดับน้ำที่สถานีคลองหรือแม่น้ำ ไม่ใช่ระดับน้ำที่จุดนี้ บนถนน หรือในบ้าน</p>
    <p>• ความมั่นใจของแต่ละสถานีดูได้ที่ปุ่ม ⓘ ข้างตัวเลข · คาดการณ์ 48 ชม. แสดงเฉพาะสถานีที่ทดสอบย้อนหลังผ่าน</p>`;

  const panel = `
    <section class="pf ${fcR.cls}" aria-labelledby="pf-title">
      <div class="pf-top"><span class="pf-h">คาดการณ์ข้างหน้า</span>
        <button type="button" class="pf-info-btn" aria-expanded="false" aria-controls="pf-info" aria-label="ที่มาและข้อจำกัดของข้อมูล">ⓘ</button></div>
      <div id="pf-info" class="pf-info" hidden>${infoBody}</div>
      ${fc.title ? `<h3 id="pf-title" class="pf-title">${fcR.icon ? `${fcR.icon} ` : ""}${esc(fc.title)}</h3>
      <p class="pf-desc">${esc(fc.plain || fc.desc)}</p>` : ""}
      ${askHTML()}
      <div class="pf-h pf-factors-h">ปัจจัยที่ใช้คาดการณ์</div>
      <ul class="pf-factors">
        <li><span class="pf-dot" style="background:${canal.color}"></span><div><b class="pf-word">${esc(head(canal.word))}</b>${canalInfo}
          ${canalGauges}</div></li>${riverLine}
        <li><span class="pf-dot" style="background:${rainColor}"></span><div><b class="pf-word">${esc(rainHead)}</b>${rainInfo}
          ${rainBody}</div></li>
        <li><span class="pf-dot" style="background:${streetF.color}"></span><div><b class="pf-word">${esc(nRep > 0 ? `มีแจ้งน้ำท่วมบนถนน ${nRep} เรื่อง` : "ยังไม่มีรายงานน้ำท่วมบนถนน")}</b>
          <div class="pf-sub">${hasStreetFlood ? `<b>น้ำรอระบายรอบจุดนี้ แม้${W}ใกล้เคียงยังไม่ล้น ระวังการเดินทาง</b> · ` : ""}ในรัศมี 1 กม. ช่วง 6 ชม. (จุดสีม่วงบนแผนที่)${depths ? ` · ผู้ใช้แจ้งระดับ: ${depths}` : ""}</div></div></li>${satLine}
      </ul>
    </section>`;

  // Categorize stations: predictable vs nearby
  const fcStations = d.stations_forecast || (d.stations || []).filter(hasForecast);
  const fcCodes = new Set(fcStations.map((s) => s.code));
  const nearbyStations = d.stations_nearby || (d.stations || []).filter((s) => !fcCodes.has(s.code));

  let stationListHTML = "";
  if (fcStations.length) {
    stationListHTML += `<div class="sec-heading"><span>สถานีที่มีการคาดการณ์</span> <span class="sub">แตะเพื่อดูกราฟ 72 ชม.</span></div>
      <ul class="list">${fcStations.map((s) => itemHTML(s, `<div class="meta">ห่าง ${esc(s.distance_km)} กม. · สถานี${esc(s.water || (s.water_body === "river" ? "แม่น้ำ" : "คลอง"))}</div>`)).join("")}</ul>`;
  }
  if (nearbyStations.length) {
    stationListHTML += `<div class="sec-heading"><span>สถานีใกล้จุดนี้</span> <span class="sub">ระดับน้ำล่าสุด</span></div>
      <ul class="list">${nearbyStations.map((s) => itemHTML(s, `<div class="meta">ห่าง ${esc(s.distance_km)} กม. · สถานี${esc(s.water || (s.water_body === "river" ? "แม่น้ำ" : "คลอง"))}</div>`)).join("")}</ul>`;
  }
  if (!fcStations.length && !nearbyStations.length) {
    stationListHTML = `<p class="muted">ไม่มีสถานีที่ส่งข้อมูลในรัศมี 15 กม.</p>`;
  }

  return `<h2 id="sheet-title">${src === "gps" ? "📍 ตำแหน่งของคุณ" : place ? `📌 ${esc(place)}` : `📌 พิกัด ${d.lat}, ${d.lon}`}</h2>
    <p class="pt-area" id="pt-area">${src === "pin" && !place ? "" : `<span class="muted">${d.lat}, ${d.lon}</span>`}</p>
    ${panel}
    ${reportButton({ lat: d.lat, lon: d.lon, src })}
    ${stationListHTML}`;
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
    if (refreshListItems([...(d.stations || []), d.nearest_canal?.station, d.nearest_canal_trend?.station, d.nearest_river?.station])) renderList();
    box.innerHTML = `<div class="tools"><button class="btn close" aria-label="ปิด">✕</button></div>${pointHTML(d, src, place)}${place ? `<p class="muted">ตำแหน่งจากชื่อสถานที่ (OpenStreetMap) อาจคลาดเคลื่อนได้ แตะบนแผนที่เพื่อเลือกจุดที่ตรงกว่า</p>` : ""}`;
    bindItems(box);
    bindReport(box);
    bindAsk(box, lat, lon);
    const info = box.querySelector(".pf-info-btn"), infoBox = box.querySelector("#pf-info");
    if (info && infoBox) info.addEventListener("click", () => { infoBox.hidden = !infoBox.hidden; info.setAttribute("aria-expanded", String(!infoBox.hidden)); });
    if ((src === "pin" || src === "gps") && !place) fillArea(lat, lon);
  } catch (e) {
    box.innerHTML = `<div class="tools"><button class="btn close" aria-label="ปิด">✕</button></div><p>โหลดข้อมูลไม่สำเร็จ (${esc(e.message)})</p>`;
  }
  box.querySelector(".close").addEventListener("click", closeDetail);
  sheet.scrollTop = 0;
}

// District line under the coordinates (issue #3). Filled in after the panel is shown, so a slow lookup never delays
// it; nothing is shown if it fails. The server rounds to ~1 km and never logs the position (D-032).
async function fillArea(lat, lon) {
  try {
    const r = await getJSON(`/api/reverse?lat=${lat.toFixed(4)}&lon=${lon.toFixed(4)}`);
    const el = document.getElementById("pt-area");
    if (el && r.area) el.textContent = r.area;
  } catch { /* the coordinates in the heading are enough */ }
}

/* ---------- near me ---------- */
// The region follows the user's location once they allow GPS (owner 2026-10-01, Q40 → D-065): the region of the
// nearest gauge within 60 km. Never a prompt on page load (browsers discourage it; a refused prompt sticks): only the
// 📍 button asks. With permission already granted, a later visit uses it silently unless a chip was tapped by hand.
const GPS_REGION_KM = 60;
function regionOfPlace(lat, lon) {
  let best = null, bd = Infinity;
  for (const s of stations) {
    if (!s.region || s.lat == null || s.lon == null) continue;
    const d = Math.hypot((s.lat - lat) * 111, (s.lon - lon) * 111 * Math.cos(lat * Math.PI / 180));
    if (d < bd) { bd = d; best = s.region; }
  }
  return bd <= GPS_REGION_KM ? best : null;
}
function applyGpsRegion(lat, lon) {
  const r = regionOfPlace(lat, lon);
  if (!r) return;
  try { localStorage.setItem("region", r); localStorage.setItem("regionSource", "gps"); } catch { /* private mode */ }
  if (r === region) return;
  region = r;
  if (lastStats) renderSummary(lastStats);
  renderList();
}
async function regionFromGrantedGps() {
  try {
    if (localStorage.getItem("regionSource") === "user" || !navigator.permissions || !navigator.geolocation) return;
    const st = await navigator.permissions.query({ name: "geolocation" });
    if (st.state !== "granted") return;  // "prompt" or "denied": never ask on load
    navigator.geolocation.getCurrentPosition((pos) => {
      lastPos = { lat: pos.coords.latitude, lon: pos.coords.longitude };  // also puts the nearest gauges on top of the list
      applyGpsRegion(pos.coords.latitude, pos.coords.longitude); renderList(); fitRegion(); },
      () => {}, { enableHighAccuracy: false, timeout: 10000, maximumAge: 30 * 60 * 1000 });
  } catch { /* private mode or no Permissions API */ }
}

function locate() {
  const out = document.getElementById("near");
  if (!navigator.geolocation) { out.innerHTML = "<p class='muted'>อุปกรณ์ไม่รองรับการระบุตำแหน่ง แตะบนแผนที่เพื่อเลือกจุดแทนได้</p>"; return; }
  out.innerHTML = "<p class='muted'>กำลังหาตำแหน่ง…</p>";
  navigator.geolocation.getCurrentPosition((pos) => {
    lastPos = { lat: pos.coords.latitude, lon: pos.coords.longitude };
    out.innerHTML = "";
    applyGpsRegion(lastPos.lat, lastPos.lon);  // counts, list and map follow where the user is (D-065)
    renderList();  // the nearest gauges on top, also when the region did not change
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
  if (tab === "river") renderRiver().then(scrollRiver);
  if (tab === "map" && map) setTimeout(() => { map.invalidateSize(); if (fitPending) fitRegion(); }, 50);
}

// A release must reach phones whose tab stays open for days (owner 2026-10-01: still v0.16.0 code after the fix).
// The server fills the version into the page; /api/stats tells the running one. Reload once per new version, never
// while a panel is open (then on close), and never twice for the same version (a stale cache cannot loop).
const PAGE_VERSION = (document.querySelector(".ver")?.textContent || "").trim();
let updatePending = false;
function maybeUpdate(v) {
  if (!v || !PAGE_VERSION.startsWith("v") || `v${v}` === PAGE_VERSION) return;
  try { if (sessionStorage.getItem("reloadedFor") === v) return; sessionStorage.setItem("reloadedFor", v); } catch { return; }
  if (document.getElementById("sheet").hidden) location.reload(); else updatePending = true;
}

async function load() {
  try {
    const [d, st, rn] = await Promise.all([getJSON("/api/stations"), getJSON("/api/stats").catch(() => null),
      getJSON("/api/rain").catch(() => null)]);
    rainRegions = rn?.by_region || null;
    stations = d.stations;
    streetSrc = d.street_source || null;
    if (!riverList) loadRivers().then(() => renderList()).catch(() => {});  // river tags on list rows and sheets (D-074)
    const latest = stations.map((s) => s.obs_time).filter(Boolean).sort().pop();
    document.getElementById("updated").textContent = `ข้อมูลล่าสุด ${fmtTime(latest)} · ${stations.length} สถานี`;
    if (st) {
      maybeUpdate(st.version);
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
load().then(() => { openFromHash(); regionFromGrantedGps(); });
setInterval(load, 5 * 60 * 1000);

// Issue #4: the grip promised a drag that did nothing. Pull down from the top of the sheet (only when it is scrolled to
// the top, so scrolling is never hijacked) to close; the ✕ stays for desktop, keyboard and screen-reader users.
(function sheetDrag() {
  const sheet = document.getElementById("sheet");
  if (!sheet) return;
  let y0 = null, dy = 0;
  const reset = () => { sheet.classList.remove("dragging"); sheet.style.transform = ""; y0 = null; dy = 0; };
  sheet.addEventListener("touchstart", (e) => {
    const top = sheet.getBoundingClientRect().top;
    reset();  // a gesture iOS cancelled must not leave a stale start point that blocks scrolling (KI-239)
    if (sheet.scrollTop > 0 || e.touches.length !== 1 || e.touches[0].clientY - top > 56) return;
    y0 = e.touches[0].clientY; dy = 0; sheet.classList.add("dragging");
  }, { passive: true });
  sheet.addEventListener("touchmove", (e) => {
    if (y0 == null) return;
    dy = Math.max(0, e.touches[0].clientY - y0);
    if (dy > 0) { sheet.style.transform = `translateY(${dy}px)`; if (e.cancelable) e.preventDefault(); }
  }, { passive: false });
  sheet.addEventListener("touchend", () => {
    if (y0 == null) return;
    sheet.classList.remove("dragging"); sheet.classList.add("snap");
    if (dy > 90) { closeDetail(); }
    sheet.style.transform = ""; y0 = null;
    setTimeout(() => sheet.classList.remove("snap"), 200);
  });
  sheet.addEventListener("touchcancel", reset);
})();

function showToast(msg) {
  let t = document.getElementById("toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "toast";
    t.className = "toast";
    t.setAttribute("role", "status");
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 3200);
}

// Capture phase: runs before the list item's own click handler, so tapping ⓘ shows the tip instead of opening
// the station (bug found in the v0.6.5 review).
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".conf-badge, .msl-btn, .canal-disclaimer-btn, .fc-basis-btn");
  if (btn) {
    e.stopPropagation();
    e.preventDefault();
    const tip = btn.getAttribute("title") || btn.getAttribute("aria-label");
    if (tip) showToast(tip);
  }
}, true);
