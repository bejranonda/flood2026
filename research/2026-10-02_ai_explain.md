# AI help for ordinary residents (GLM) — rules tell the story, AI retells it on request after a check

**Date:** 2026-10-02 · **Owner:** "ลองให้คนทั่วไปใช้ เขาไม่เข้าใจง่ายๆ … อยากให้มีฟังก์ชันการแปลความ เช่น ให้ ai แปลเป็นความเข้าใจง่ายๆ … think more than just translation … be careful about UX … You can use GLM"; "validate and test also the AI assistance, think about the users who are common people"; on v0.18.0: "AI สรุปดูไม่ได้ข้อมูลอะไรเท่าไหร่ แม้มีตัวเลขด้านล่างเยอะแยะ ควรเล่าหรืออธิบายให้ดีกว่านี้ ว่าสถานีที่ใกล้เคียง แต่อยู่ไกล เป็นยังไง". Decision: D-068.
**Scripts:** [scripts/ai_explain_validate.py](../scripts/ai_explain_validate.py) (real places × six questions; fresh GLM call each) · answers of the final run: [2026-10-02_ai_explain_validation.json](2026-10-02_ai_explain_validation.json).

## 1. Model facts (GLM API, from the app container)
- `glm-5.3-flash` always reasons: `thinking: disabled` → error 1210; default effort 8–10 s per answer and ~850–1,400 reasoning characters; `reasoning_effort: "low"` → ~1–5 s, no reasoning text. `glm-4-flash` → error 1211 (gone).
- Our wrapper returned `reasoning_content` when `content` was empty (a cut-off answer): English reasoning could have reached residents (KI-260, fixed).

## 2. Probes — what a free AI answer does (16 answers, 4 places × 4 resident questions, 11:20–12:10 UTC)
With the panel's facts and a strict prompt, 13/16 passed a naive check, but reading them showed:
- **A go-verdict:** "พาลูกไปโรงเรียนพรุ่งนี้เช้าได้ไหม" → "ได้ครับ ข้อมูลระบุว่าแนวโน้มน้ำอีก 24 ชม. ทรงตัว…".
- **"ปกติ" where the panel cannot judge** (Pak Kret, no gauge close enough; first probe).
- **Invented causes and claims** ("ลดลงเนื่องจากฝนเล็กน้อย"; "ข้อมูลในแอปยังไม่มีตัวเลขระดับน้ำ").
- Good honest refusals too ("ข้อมูลที่มียังไม่พอจะบอกได้ว่าบ้านคุณจะท่วมหรือไม่").
→ Rules must decide every answer; AI may not judge safety, travel or moving a car.

## 3. Rewording whole rule answers (v0.18.0 design; 176 answers, 12:44–13:00 UTC)
43 % passed the checker (too long 73, direction changed 26); median 4.5 s. On the owner's Ko Kret pin the template itself was wrong — it called a gauge 6 km away "คลองแถวนี้" (KI-261) — and the AI's friendly text said little.

## 4. Rule lines + one short AI sentence (final design)
Rule lines carry the story with the panel's numbers (gauge, distance — far is said — how full now, last 24/48 h, the rows in words, rain, reports, limits, what to do), shown at once. GLM may add one sentence below; `explain.check` gates it.

| Run (198 answers each: 33 places × 6 questions; half Bangkok, half elsewhere + the owner's pins) | Passed | Median / p90 time |
|---|---|---|
| v0.18.1 prompt, first checker (13:02–13:16 UTC) | 121 (61 %) | 3.5 / 5.0 s |
| same answers, final checker (re-scored offline) | 164 (83 %) | — |
| **v0.18.2 prompt (no ครับ/ค่ะ), final checker (13:23–13:34 UTC)** | **170 (86 %)** | **3.1 / 4.4 s**, none > 8 s |

Pass by question (final run): ควรเตรียมอะไร 33/33, ตัวเลขหมายถึงอะไร 32/33, ควรย้ายรถไหม 29/33, พรุ่งนี้เดินทางได้ไหม 29/33, น้ำจะท่วมบ้านไหม 26/33, สรุปให้ฟังง่าย ๆ 21/33 (the longest stories; mostly "too long"). Rejections: too long 20, dropped "cannot tell" 6, past-as-future 1, verdict 1 — after this run, "ไม่สามารถ…" counts as "cannot tell" and "จะท่วม…หรือไม่" is not a verdict (tests from these cases).

## 5. Read like a resident — what the checker could not see, and what changed
- **Past told as future (fixed in the checker):** past line "เพิ่มขึ้นมาก 49 ซม." + forecast "เพิ่มขึ้นเล็กน้อย ราว 3 ซม." → AI "ช่วงหนึ่งวันสองวันนี้น้ำจะขึ้นค่อนข้างมาก" passed the first checker. Now: a direction only in the past line needs "ที่ผ่านมา"; a "มาก" stronger than the forecast lines is rejected.
- **Polite particles are not verdicts:** "ยังรับน้ำได้ค่ะ", "แอปบอกไม่ได้ค่ะ", "ยังบอกไม่ได้แน่นอน" were blocked; now allowed. "ได้ค่ะ ไปได้เลย" still blocked.
- **My own wording (fixed in the rules):** an unclear row with a one-sided range (+1 to +64 cm) was told "ยังบอกไม่ได้ว่าจะขึ้นหรือลง … เพิ่มขึ้น 1–64 ซม."; now "ยังบอกไม่ได้แน่ชัด". The plain line repeated "อีก 24 ชม." and "และ"; now "…มีฝนปานกลาง ต่อไปคาดว่ามีฝนเล็กน้อย".
- Remaining style issues in passing sentences (harmless): reports placed "แถวสถานี" instead of around the pin; occasional "ท่าน/คุณ" mix.

## 6. Story first, numbers folded (owner: "I got complicated info … they try to explain easily")
The owner compared v0.18.3's seven labelled lines ("ครึ่งหนึ่งของครั้งที่ผ่านมาอยู่ระหว่างลดลง 5 ซม. ถึงเพิ่มขึ้น 8 ซม.") with a weather app's AI card. New rule story `explain.narrative`: 3–4 everyday sentences, at most a couple of numbers; the lines go under "ดูตัวเลข". GLM retells the story (same checker, ≤ 320 chars).

| Run v0.18.5 (14:00–14:10 UTC, 198 answers, 33 places, exact production prompt via `explain.prompt`) | Result |
|---|---|
| Passed the checker | **180 (91 %)** — simple 26/33, home 31/33, car 28/33, travel 31/33, prepare 31/33, numbers 33/33 |
| Time | median 4.0 s, p90 5.4 s, none > 8 s |
| Rejected | too long 11, verdict 6, new number 1, direction 1 |

Example (Ko Kret, shown live): "แถวบ้านคุณไม่มีสถานีวัดน้ำใกล้ ๆ สถานีที่ใกล้ที่สุดอยู่ไกลราว 6 กม. ที่นั่นตอนนี้น้ำต่ำกว่าตลิ่งราว 31 ซม. ใกล้เต็มตลิ่ง ช่วงที่ผ่านมาน้ำขึ้นลงสลับกัน ส่วนวันข้างหน้ายังบอกไม่ได้ว่าจะขึ้นหรือลง คาดว่ามีฝนเล็กน้อย ช่วยสังเกตน้ำในคลองใกล้บ้านประกอบด้วยนะ".

## 7. Verdict — AI on request, one button
Owner: "AI assistant generated only when requested, single point for that is enough?" → one "ask AI" button "to reduce unnecessary AI generated". Shipped (v0.18.6): the plain line for everyone (template, instant); the button opens the story card — GLM's retelling when it passes (~91 %), else the rule story — and nothing calls GLM before the tap (checked live: 0 `/api/explain` requests on panel load). Re-run `scripts/ai_explain_validate.py` after any prompt, checker or template change and **read the passing answers**, not only the rate.

## 8. "? ไม่แน่ชัด" says what is possible (v0.18.7–v0.18.8)
Owner: "we can't say just no trend in everytime, user expected to hear what can be possible even in the far station" → chose "possible change + bank risk" (no direction where the backtest proved none, D-060). The story, the plain line and the numbers now give the size of the likely change (the rows' 50 % range) and the bank risk (the 24/48 h 90 % range against today's margin).

| Run v0.18.7 (16:13–16:24 UTC, 198 answers, 33 places) | Result |
|---|---|
| Passed the checker | 175 (88 %) — simple 26/33, home 27/33, car 29/33, travel 31/33, prepare 30/33, numbers 32/33 |
| Time | median 4.1 s, p90 5.7 s, 197/198 ≤ 8 s |

Read by hand: (a) my rule called a 1.3 km gauge "ไกล" because the area gauges disagreed — now "สถานีวัดน้ำรอบ ๆ ให้ผลต่างกัน สถานีที่ใกล้ที่สุดอยู่ห่าง 1.3 กม." (v0.18.8); (b) the AI turned "ยังไม่น่าจะถึงตลิ่ง" into "ไม่ขึ้นถึงตลิ่ง" — now a rejected verdict; (c) "จะได้ไม่ต้องตกใจ", "จะเดินทางได้ไหม" were wrongly blocked — now allowed. Typical passing retelling: "น้ำในคลองยังต่ำกว่าตลิ่งอยู่พอสมควร แปลว่ายังรับน้ำได้อีก … วันข้างหน้าน้ำน่าจะเปลี่ยนไม่มาก อาจลดหรือขึ้นเล็กน้อย".

