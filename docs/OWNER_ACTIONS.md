# OWNER_ACTIONS.md — What the project needs from the owner

> **Single tracker** (D-026). Anything an AI harness or developer needs from the owner goes here, with the reason, the exact steps and how it will be verified. Last verified **2026-10-03 ~15:10 UTC** (v0.20.5, live; `scripts/owner_status.py`: GISTDA ✅, GFM ✅, EWDS ✅, WNEXT ⬜ (HTTP 404: Subscribe step), GFLOOD ⬜, RID ⬜).
> **Check the current status any time:** `python3 scripts/owner_status.py` (read-only; it never prints a secret). Open questions with their history are in [plan/OPEN_QUESTIONS.md](plan/OPEN_QUESTIONS.md).
> **Handing over secrets:** put them only in `/root/flood2026/.env` on the server. Never paste them in chat or commit them. Tell the agent the *key name* you set; it will check the value works without printing it.

## 1. Status now
| # | Item | Status | Priority |
|---|---|---|---|
| Q18 | `flood.autobahn.bot` challenged non-browser clients | ✅ **done** (owner turned Bot Fight Mode off, verified 17:33 UTC) | |
| **HYDROBASINS** | Download HydroBASINS (Asia) in a browser and copy it to the server | ✅ **done** 2026-10-02 (owner downloaded the lake version + ONWR's 22 basins; tested: no forecast gain, [research](../research/2026-10-02_catchment_rain.md)) | |
| **UPTIME** | An external uptime check that alerts you when `/api/health` fails (KI-246: a 4.5 h overload on 2026-09-30 went unnoticed) | ⬜ open — new 2026-09-30 | 1 |
| **SOCIAL** | Upload `docs/img/social-preview.png` as the GitHub repository social preview (**regenerated 2026-10-03 with the nationwide text, D-073**); optionally add the site to Google Search Console | ⬜ open — new 2026-09-30 | 3 |
| **RID** | RID gate coordinates for 15 unplaced + 14 approximate stations | ⬜ open | 2 |
| **GLM** | GLM API key (`GLM_API_KEY` in `.env`) for AI feedback triage | ✅ **works** (verified live with `glm-5.3-flash`, D-030) | |
| **GISTDA** | GISTDA key works for the flood-extent service | ✅ **works** (2026-09-27 10:05 UTC): the key was fine; our endpoint path and key placement were outdated (KI-510). Fixed from the docs link you sent | |
| **GFLOOD** | Google Flood Forecasting API key (`GOOGLE_FLOOD_API_KEY`) | ✅ done 2026-10-04 (key in `.env`; collector `google_floodhub`, D-087) | 2 |
| **WNEXT** | WeatherNext 3: Cloud project + BigQuery listing + read-only service-account key (research only, D-069) | ✅ **works** (2026-10-04): linked dataset `weathernext_3` subscribed, BigQuery Admin role granted, tables verified live | |
| **GFM** | GFM portal login in `.env` (optional: the maps are keyless) | ✅ **works** (2026-10-02 20:45 UTC, HTTP 200 + token) | |
| **EWDS** | EWDS token for archived GloFAS forecasts | ✅ **works** (HTTP 200), but **not needed now**: GloFAS failed its upper-bound test (D-069) | |
| **EGRESS** | A reliable Thai egress before any public national view (DWR, RID answer only from Thailand, KI-110) | ⬜ open — needed before national goes public (D-046) | 3 |
| **Q3+** | Courtesy/permission emails to HII, DWR, RID (drafts below) | ⬜ open — **more urgent since v0.16.0 (2026-09-30): every HII/RID/EGAT/พพภ. gauge is now public with forecasts (D-064, owner: "go public, send notes in parallel")**; HII first (we fetch a year per gauge, 733 requests once, then ~120 a day) | 2 |
| Q15b/Q16 | R2 off-site backups | 🚫 **disabled** (owner choice: keep disabled; D-029) | — |
| Q10 | Repository license | ✅ **closed** (MIT License added; D-043) | — |
| BMA | Courtesy note to the flood69 relay (and BMA) that we show their copy of BMA data, with attribution (D-031, KI-218) | ⬜ optional | 3 |
| Q19 / Q22 / Q7 / Q8 / Q11 / Q12 | Decisions and answers (no work) | 🖐️ open | see §3 |
| Q15a | Tunnel rights on the API token | ✅ works (verified 11:15 UTC) | |
| Q20 | Old tunnel `ecd8a7b9…` | ✅ deleted (verified) | |
| — | New tunnel token, main domain `flood.autobahn.bot`, OpenVPN file, Tunnel edits | ✅ done | |
| — | Repository made public (owner) | ✅ done; scanned, see Priority 5 | |

## 2. Actions in priority order

### ✅ Done · Q18 — non-browser clients reach flood.autobahn.bot (2026-09-26 17:33 UTC)
**Resolved:** Bot Fight Mode was the cause; the owner switched it off. curl, Facebook and LINE user agents now get HTTP 200; the API moved to the main domain (D-035). The text below is the history.
**Since 2026-09-26 16:58 UTC every old `flood.bejranonda.com` link redirects to the main domain (your "move all" request).** Visitors therefore meet the challenge page; a headless browser got the "Verify you are human" checkbox. For elderly users on slow phones that is a real barrier during a flood. One click fixes it (option A below). Rollback if needed: `REDIRECT_LEGACY_HOST=0` in `.env`, `docker compose up -d app`.
**Why:** LINE and Facebook link previews, uptime monitors and API users get Cloudflare's "Just a moment…" page (`cf-mitigated: challenge`). Phones with a normal browser pass after a few seconds, but a flood site should open instantly and be shareable.
**Evidence (2026-09-26):** `/` and `/api/*` are challenged, `/static/*` isn't, and the result depends on the client's TLS fingerprint. That fits **Bot Fight Mode**, the free zone-wide product. The zone hosts your other apps too (`shirt.`, `mutelu.`, `persona.`, … all proxied). Cloudflare's docs say Bot Fight Mode **can't be skipped with WAF rules or Page Rules**. This corrects my earlier advice about a Configuration Rule / WAF skip, which would not work for it ([KI-506](KNOWN_ISSUES.md)).
**What the token showed after you added Zone Settings / Firewall Services / Page Rules edit (2026-09-26 17:00 UTC, read-only):** security level **medium**, Browser Integrity Check **on**, challenge TTL 1800 s; **no** legacy firewall rules, IP access rules or UA rules; page rules: `www.autobahn.bot/*` → 301 and `*autobahn.bot/api/*` → cache bypass. Bot Fight Mode and WAF custom rules (rulesets) are still **not readable** with these permissions, so the source of the challenge is still unconfirmed.
**Option D (scoped, free, affects only flood):** a third page rule `flood.autobahn.bot/*` → *Security Level: Essentially Off* + *Browser Integrity Check: Off*. If the challenge comes from the security level (our tests run from a datacenter IP with a poor reputation), this removes it for flood only. If it comes from Bot Fight Mode, it won't help (page rules can't skip BFM) and option A remains. **Applied 2026-09-26 17:11 UTC on the owner's go-ahead** (page rule `4009f8dc…`, priority 3). **Result: no effect** — after 3 min curl, `facebookexternalhit` and `Line` user agents still get `403 cf-mitigated: challenge` on `/` and `/api/health`. So the challenge is **not** the security level or Browser Integrity Check; it is almost certainly **Bot Fight Mode** (or a WAF custom rule, which the token can't read). The rule is kept: once BFM is off it stops "medium" security from challenging visitors on low-reputation IPs (datacenters, some mobile CGNAT).
**➡️ Remaining step (yours): option A** — Security → Settings → Bot traffic → **Bot fight mode: Off** (affects all `*.autobahn.bot`), or give the token **Zone → Bot Management: Edit** (and **Zone → Zone WAF: Read**) so the agent can confirm the cause first. Then the agent redirects `/api/*` too, and only `flood.autobahn.bot` remains.
**Confirm first (30 s):** Cloudflare dashboard → `autobahn.bot` → **Security → Analytics → Events**, find a blocked request for `flood.autobahn.bot`, and read the **Service** field. It should say *Bot Fight Mode*.
**Options (pick one):**
| | What | Trade-off |
|---|---|---|
| **A** | **Turn Bot Fight Mode off** for the zone: Security → Settings → filter "Bot traffic" → Bot fight mode → **Off** | Free, one click. Affects **all** `*.autobahn.bot` sites, so decide whether your other apps rely on it |
| B | Upgrade the zone to **Pro** and use *Super Bot Fight Mode* with a Skip rule for `http.host eq "flood.autobahn.bot"` | Keeps protection elsewhere; costs a plan upgrade |
| C | ~~Share `flood.bejranonda.com`~~ | No longer possible: since D-034 its pages redirect to the main domain |
**Then tell the agent.** It will run `scripts/owner_status.py` (Q18 turns ✅), then also redirect `/api/*` from the alias (today excluded, D-034), and re-test link previews.

### ✅ Done · GISTDA — the key reaches the flood-extent service (KI-510, 2026-09-27)
**Resolved without an owner step:** the owner sent the API documentation (`disaster.gistda.or.th/services/open-api`). Its OpenAPI spec uses `https://api-gateway.gistda.or.th/api/2.0/resources` + `/features/flood/{1day,3days,7days,30days}` and `/features/flood-freq`, with the key in the **`API-Key` header**. Our `.env` still had an older path with the key as a query parameter, which answered 404. `GISTDA_API_ENDPOINT` now points at `/features/flood/7days`; `owner_status.py` reports ✅ (49,761 flood cells over 7 days).

### Priority 2 · Google Flood Forecasting API (Flood Hub) — you chose to apply
**Why:** Google's AI river forecasts and flood status cover Thai rivers, including places without HII gauges; they are a benchmark and a virtual-gauge source (research §6.1). **Evidence (2026-09-27):** the API answers **403** without a key.
**Steps:** 1. Apply for access via the Flood Forecasting API page linked from `sites.research.google/floods` (Google reviews pilot requests; describe a volunteer, non-commercial Thai flood-information site). 2. When accepted: Google Cloud Console → a project → enable the Flood Forecasting API → **Credentials → API key**, restricted to that API. 3. Put it in `.env` as `GOOGLE_FLOOD_API_KEY=`. **Verify:** the GFLOOD row in `owner_status.py` turns ✅ (one tiny request, key never printed). Nothing uses it until a decision on how to show it.

### WNEXT — Google WeatherNext 3 through BigQuery (accepted 2026-10-02; research only, D-069)
**Why:** DeepMind's hourly AI rain forecasts (64 members, 5–10 km) might beat our Open-Meteo rain in the 48 h model. **Terms (read 2026-10-02, PDF of 3 Sep 2026):** data ≥ 1 h old is CC BY 4.0 (fine for a backtest); now/future rain may **not** be shown or served, even recoloured or cropped; a forecast built on it must carry Google's "experimental … not approved for real world use" notice, and the terms exclude Japan, South Korea and Indonesia. So: backtest first, nothing public (D-069).
**Steps (about 15 min, no billing needed — the BigQuery sandbox gives 1 TB of queries per month):**
1. Sign in at **console.cloud.google.com** with the e-mail Google accepted → **Create project** (e.g. `floodwatch-research`). The same project can later hold the Flood Hub key (GFLOOD).
2. **BigQuery → Analytics Hub** (or *Sharing*) → search **WeatherNext 3** → **Subscribe** → pick the project; note the **linked dataset** name it creates.
3. **IAM & Admin → Service accounts → Create**, e.g. `floodwatch-reader`; roles **BigQuery Job User** and **BigQuery Data Viewer**. Then **Keys → Add key → JSON** (downloads one file).
4. Copy the file to the server as `/root/flood2026/certs/weathernext-reader.json` (`certs/` is git-ignored; `chmod 600`). Never paste it in chat.
5. In `.env`: `GOOGLE_APPLICATION_CREDENTIALS=/certs/weathernext-reader.json`, `WEATHERNEXT_PROJECT=<project id>`, `WEATHERNEXT_DATASET=<linked dataset>`.
**Status 2026-10-04 18:33 UTC:** ✅ **All steps complete.** Linked dataset `weathernext_3` subscribed in BigQuery, service account granted `BigQuery Admin` role. Live queries and table listings verified via `scripts/owner_status.py` (HTTP 200, 2 tables). Sample spatial query for Bangkok completed (17.3 MB processed).

### GFM — Copernicus Global Flood Monitoring account (2026-10-02; optional)
**Why:** the satellite flood maps are readable **without** an account (keyless STAC, verified 2026-10-02); the account adds the `api.gfm.eodc.eu/v2` API (areas of interest, product lists, e-mail alerts). **Steps:** put your portal login in `.env` as `GFM_EMAIL=` and `GFM_PASSWORD=` (you registered with e-mail + password). **Verify:** `owner_status.py` → **GFM ✅** (HTTP 200, token received).

### EWDS — archived GloFAS forecasts for the 3–7 day outlook backtest (2026-10-02; optional)
**Why:** Open-Meteo serves GloFAS reanalysis and today's forecast, not forecasts as issued; an honest outlook backtest needs the archive (`cems-glofas-forecast`, 2019-11 → yesterday, checked 2026-10-02). **Steps:** 1. Register at **ewds.climate.copernicus.eu** (ECMWF account). 2. Open the dataset *River discharge and related forecasted data by the Global Flood Awareness System* → **Download** tab → accept the **CEMS-FLOODS** licence. 3. Profile → copy the **API token** → `.env` `EWDS_API_KEY=`. **Verify:** `owner_status.py` → **EWDS ✅** (HTTP 200). Only worth it if the upper-bound test says GloFAS can help ([research](../research/2026-10-02_glofas_outlook.md)).

### Before national goes public · EGRESS and agency notes (D-046)
**Thai egress:** DWR EWS (2,275 village stations) and RID Telerid (921) time out from Germany and answer only via the public VPN Gate relay, which is flaky and untrusted (KI-505). For a public service you need something stable: a small Thai VPS or a proxy on a machine in Thailand you control, used only for public pages (D-014). Tell the agent the proxy URL key name in `.env` (e.g. `THAI_EGRESS_PROXY`).
**Agency notes (drafts; send from your own address):**
- **HII** (สสน., info_thaiwater@hii.or.th): "BKK FloodWatch (flood.autobahn.bot) is a volunteer, non-commercial site. We read your public api-v3 JSON (water level, dams, BMA canal and road sensors via your API) and FEWS files every 10–60 min from one server with the User-Agent `BKK-FloodWatch/…`, cache them and credit สสน. on every page. May we extend this to the national feeds, and is there an official access route or rate you prefer?"
- **DWR** (กรมทรัพยากรน้ำ, EWS): same text for `ews.dwr.go.th` station data (hourly, one request), asking also what `status = 9` means.
- **RID** (กรมชลประทาน, Telerid): same text for the station list and readings.

### Declined (D-029) · Q15b / Q16 — R2 off-site backups (kept for reference; a local backup is still missing, KI-511)
**Why:** everything (database and raw archive) lives on **one disk**. If it fails, the flood record is gone. R2 is the off-site copy.
**Evidence:** the API answers *"Please enable R2 through the Cloudflare Dashboard."* Cloudflare says R2 must be purchased/enabled before an S3 token can be created.
**Cost (measured 2026-09-26):** the raw archive grows about **3–5 MB/hour (~100 MB/day, ~3–4 GB/month)** in steady state (more during the one-off backfill); the database dump adds little. R2's free tier is **10 GB-month of storage, 1 M writes and 10 M reads per month, and egress is free**; beyond that storage is $0.015/GB-month. So it's free for roughly two months and then well under $1/month. ([R2 pricing](https://developers.cloudflare.com/r2/pricing/))
**Steps:**
1. Dashboard → **R2 Object Storage** → enable R2 (a payment method may be requested).
2. Create a bucket, e.g. `flood2026-backup`.
3. R2 → **Manage API tokens** → **Create Account API token** → permission **Object Read & Write**, scoped to that bucket → copy the **Access Key ID** and **Secret Access Key** (shown once).
4. On the server, add to `.env`:
   ```
   R2_ACCESS_KEY_ID=…
   R2_SECRET_ACCESS_KEY=…
   R2_BUCKET=flood2026-backup
   R2_ENDPOINT=https://<your-account-id>.r2.cloudflarestorage.com
   ```
   (the account id is `CLOUDFLARE_ACCOUNT_ID` in `.env`).
**Then tell the agent:** it will implement the nightly `pg_dump` and raw-archive replication ([ARCHITECTURE §9](ARCHITECTURE.md)), test a **restore**, and mark [KI-504](KNOWN_ISSUES.md) fixed.

### Priority 3 · Q21 — a Cloudflare token that can *only* run Workers AI
**Why:** the worker currently falls back to the general API token, which can also edit DNS and tunnels. If that container were compromised, the damage would be larger than needed ([KI-508](KNOWN_ISSUES.md)).
**Steps:** Dashboard → **AI → Workers AI → Use REST API → Create a Workers AI API Token** (the template selects the right permission; ⚠️ the exact button label may differ), then put it in `.env` as `CF_AI_TOKEN=…`.
**Verified by:** `scripts/owner_status.py` (Q21 and "AI inference works").

### Priority 4 · RID gate coordinates
**Why:** 15 gauges (mostly Ayutthaya gates: ATG011, ATG042, ATG051/052, ATG081/082, ATG091/092, ATG101, ATG111/112, FROC02, HDA002/003, TCP013) have no position anywhere, and 14 more are placed only approximately (±2–5 km, dashed markers). Point checks and "near me" rely on positions ([KI-207](KNOWN_ISSUES.md)).
**What to send:** a CSV `code,lat,lon` (WGS84) or any RID/HII list with gate coordinates. Save it as `src/floodwatch/data/station_coords_rid.json` or just give it to the agent, which will import it, replace the approximate positions and mark them exact.

### ✅ Done · Q10 — choose a license (MIT License applied, 2026-09-27)
The repository was updated to open source under the **MIT License** ([LICENSE](../LICENSE), [D-043](plan/DECISIONS.md)). Anyone may freely read, fork, modify, and integrate the code with simple attribution. Third-party data keeps its own terms ([SOURCES](SOURCES.md): Open-Meteo non-commercial, OSM ODbL).

### Optional · keep the host and the public history tidy
- **Server IP in old commits (KI-214):** 8 commits from earlier today still show it; it is gone from the current files. It is low risk because the site is only reachable through the Cloudflare Tunnel and no web ports are open. Removing it from history means `git filter-repo` plus a force-push, which rewrites history and breaks existing clones and forks. **Only do this if you want it; say so and I will.**
- **SSH:** 15,754 failed logins in 24 hours (normal scanning). Password login cannot succeed today (root is key-only; no other account has a password), but `PasswordAuthentication yes` is still set. If you want the log noise and the theoretical risk gone: `PasswordAuthentication no` in `/etc/ssh/sshd_config`, `sshd -t && systemctl reload ssh` (keep your current session open while testing a new key login), and `apt install fail2ban`. I did not touch this: it is a shared host and a lockout would be costly.

### UPTIME — alert when the site fails (new 2026-09-30, KI-246)
**Why:** on 2026-09-30 the database was saturated from ~01:00 to 05:44 UTC; visitors saw "โหลดข้อมูลไม่สำเร็จ" and nobody was told. The server cannot alert you by itself (no notification channel is configured).
**Steps (≈ 5 min, free tier ⚠️ check the provider's current limits):** create a free account at an uptime service (e.g. UptimeRobot or Better Stack) → new HTTP(S) monitor → URL `https://flood.autobahn.bot/api/health` → interval 5 min → alert contact: your e-mail and/or the provider's mobile app / LINE integration → save. **Also (v0.16.8):** if the service supports a keyword check, require the text `"stale_sources":[]` in the response — then it also alerts when a data source stops upstream while the site still answers (2026-10-01: all BMA canal readings stuck at 00:10 ICT for hours, KI-257).
**Verify:** the monitor shows "up"; optionally pause the app for a minute (`docker compose stop app`, then `start`) and check that the alert arrives. Tell us which service you used; nothing secret goes into the repo.

### HYDROBASINS — sub-basin maps for a better rain input (new 2026-10-02, D-066) · ✅ done 2026-10-02
**Why:** rain over each gauge's true upstream catchment may improve forecasts outside Bangkok (only ~a third of gauges earn a 48 h line). HII's 22 basins are too coarse; HydroBASINS has sub-basins with up/downstream links. Its download host shows a bot challenge to our server, which we do not bypass.
**Steps (≈ 5 min):** in a browser open https://www.hydrosheds.org/products/hydrobasins → "standard" format → Asia, levels 1–12 (`hybas_as_lev01-12_v1c.zip`) → download → copy it to the server, e.g. `scp hybas_as_lev01-12_v1c.zip <server>:/root/flood2026/data/` (the `data/` folder is not in git). Licence: free for scientific, educational and commercial use with attribution (Lehner & Grill 2013).
**Verify:** tell us it is there; we run the upstream-catchment experiment (research/2026-10-02_basins.py, variant C with true catchments) and adopt it only if it beats the placebo.
**Done 2026-10-02:** the owner put `hybas_lake_as_lev01-12_v1c.zip` (lake version, fine) and ONWR's legal 22-basin shapefile on the server; both now live in `data/basins/raw/` with tidy GeoJSON made by `scripts/prepare_basins.py`. Result: catchment rain = no gain on 296 gauges (placebo clearly worse); ONWR basins = HII's map (98.5 % same). Not adopted (D-067).

### SOCIAL — repository preview image and search console (new 2026-09-30, KI-248)
**Why:** links to the repo on LINE/Facebook/X show a picture only if the repository social preview is set; GitHub has no API for it. The site's own share image is already served (`/static/og-image.jpg`).
**Steps:** GitHub → repo Settings → General → Social preview → Edit → upload `docs/img/social-preview.png` (1280×640). Optional: Google Search Console → add `https://flood.autobahn.bot/` (DNS or HTML-tag verification; tell us which, the token goes in `web/index.html` only if it is a public meta tag) → submit `https://flood.autobahn.bot/sitemap.xml`.
**Verify:** paste the repo link in a chat app and see the picture; Search Console shows the sitemap as "Success".

## 3. Decisions (answers only, no work)
| # | Question | Default if you don't answer |
|---|---|---|
| **Q19** | Who reads user feedback notes, and how often? A password-protected review page, or is SQL/CLI enough? **Real reports have arrived:** 10 in ~4.5 h from 8 senders (7 "ankle", 3 "knee"; 7 from a map pin; 6 with a note, all classified street-level drainage by the AI triage, none urgent) | Notes stay private in the database; the operator queries SQL ([HANDOFF §3](../HANDOFF.md)) |
| **Q22** | Use Workers AI for **Traffy text labelling** or **Thai voice reports**? May need Workers Paid ($5/month) beyond 10,000 free neurons/day ([APPROACH §3.6](APPROACH_AND_METHODS.md)) | Not used |
| **Q7** | Alerts by **LINE** or **Web Push**? | No alerts |
| **Q8** | Show **Buddhist-era (พ.ศ.)** dates? | Day and month only |
| **Q11** | Budget and retention for R2 and the raw archive | Keep forever, within the free tier |
| **Q12** | Who is on call during a flood, and how many maintainers? | Nobody; alerts go to the log only |
| **Q3 / Q4 / Q6 / Q9** | Permission mails to HII / BMA / Traffy; TMD, GISTDA keys; commercial use; frontend framework | Public data only, non-commercial, plain JS |

## 4. Done (verified)
| When (UTC) | What | Evidence |
|---|---|---|
| 09:19 | New tunnel token (tunnel `d62b426d…`) | `cloudflared` registered 4 connections; both CNAMEs re-pointed |
| 09:19 | Main domain `flood.autobahn.bot` | DNS record created; site served (behind the challenge, Q18) |
| 17:33 | Bot Fight Mode off (Q18) | `owner_status.py` Q18 ✅; curl/Facebook/LINE UAs → 200 |
| ~17:00 | Token rights: Zone Settings, Firewall Services, Page Rules (edit) | zone settings readable; flood-only page rule created |
| ~11:15 | Tunnel rights on the API token | `scripts/owner_status.py` Q15a ✅ |
| ~11:15 | Old tunnel `ecd8a7b9…` deleted | Not in the tunnel list |
| by 15:20 | Repository visibility set to public | `gh repo view` → PUBLIC; history scan clean (KI-214) |
| earlier | OpenVPN file, Cloudflare account id fix | [HANDOFF](../HANDOFF.md) history |

## 5. For agents: how to use this file
1. **When you need something from the owner, add it here first** (why, steps, how you'll verify), then mention it briefly in chat.
2. Run `python3 scripts/owner_status.py` before asking, because the owner may already have done it. (2026-09-26: the owner had already deleted the old tunnel and fixed tunnel rights.)
3. When an item is done: move it to §4 with evidence, update [KNOWN_ISSUES](KNOWN_ISSUES.md) and [DECISIONS](plan/DECISIONS.md) if it changes behaviour, and add a step to [HANDOFF §5](../HANDOFF.md).
4. **Never trust a single client for a reachability check.** Cloudflare challenges depend on the TLS fingerprint. `scripts/owner_status.py` tests with curl and reads `cf-mitigated`, because Python's urllib once got HTTP 200 while curl, browsers and crawlers were challenged.
