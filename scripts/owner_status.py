#!/usr/bin/env python3
"""Which owner actions are done? Prints a status table for docs/OWNER_ACTIONS.md (D-026).

Read-only: HTTP GETs only, `.env` is parsed locally, and **no secret value is ever printed**. Standard library only.
Run on the server:  python3 scripts/owner_status.py        (add --json for machine-readable output)

Exit code 0 always; it reports, it doesn't gate anything. Items marked "manual" can't be checked by a script.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
UA = "BKK-FloodWatch/0.2 (+https://flood.autobahn.bot; owner-status check)"
CF = "https://api.cloudflare.com/client/v4"
URL_MAIN = "https://flood.autobahn.bot/api/health"
OLD_TUNNEL_PREFIX = "ecd8a7b9"  # tunnel replaced by the owner's new token on 2026-09-26 (Q20); prefix only, ids stay out of the public repo


def env() -> dict[str, str]:
    out: dict[str, str] = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip("\"'")
    return out


def http(url: str, token: str | None = None, timeout: int = 20) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(200_000).decode("utf-8", "replace")
    except Exception as e:  # DNS, timeout, TLS
        return 0, f"{type(e).__name__}"


def cf_ok(path: str, token: str) -> tuple[bool, str]:
    status, body = http(f"{CF}{path}", token)
    try:
        d = json.loads(body)
        return bool(d.get("success")), ", ".join(str(e.get("message")) for e in d.get("errors", [])) or f"HTTP {status}"
    except ValueError:
        return False, f"HTTP {status}"


def _post_status(url: str, data: bytes, headers: dict, timeout: int = 30) -> tuple[int | str, str]:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **headers}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as ex:
        return ex.code, ""
    except Exception as ex:  # DNS, timeout, TLS
        return type(ex).__name__, ""


def new_source_checks(e: dict[str, str]) -> list[tuple[str, str, str, str]]:
    """GFM account, WeatherNext via BigQuery, EWDS token (added 2026-10-02, D-069). One real request each; no value printed."""
    rows = []
    mail, pw = e.get("GFM_EMAIL", ""), e.get("GFM_PASSWORD", "")
    title = "GFM account logs in (GFM_EMAIL / GFM_PASSWORD; the maps themselves need no account)"
    if mail and pw:
        st, body = _post_status("https://api.gfm.eodc.eu/v2/auth/login", json.dumps({"email": mail, "password": pw}).encode(),
                                {"Content-Type": "application/json"})
        rows.append(("GFM", title, "done" if st == 200 else "open", f"HTTP {st}" + (" token received" if st == 200 and "token" in body else "")))
    else:
        rows.append(("GFM", title, "open", "GFM_EMAIL / GFM_PASSWORD empty in .env"))

    title = "WeatherNext readable in BigQuery (service-account key + linked dataset)"
    kp, proj, ds = e.get("GOOGLE_APPLICATION_CREDENTIALS", ""), e.get("WEATHERNEXT_PROJECT", ""), e.get("WEATHERNEXT_DATASET", "")
    if kp and proj and ds:
        local = ROOT / "certs" / pathlib.Path(kp).name if kp.startswith("/certs/") else pathlib.Path(kp)
        try:
            sys.path.insert(0, str(ROOT / "src"))
            from floodwatch import gcp  # stdlib + openssl only
            tok = gcp.access_token(str(local))
            st, body = http(f"{gcp.BQ}/projects/{proj}/datasets/{ds}/tables?maxResults=50", tok)
            names = [t["tableReference"]["tableId"] for t in json.loads(body).get("tables", [])] if st == 200 else []
            wn = [n for n in names if n.startswith("weathernext")]
            rows.append(("WNEXT", title, "done" if wn else "open", f"HTTP {st}, {len(wn)} WeatherNext table(s)"))
        except Exception as ex:
            rows.append(("WNEXT", title, "open", f"{type(ex).__name__} (key file at {local.name}?)"))
    else:
        rows.append(("WNEXT", title, "open", "GOOGLE_APPLICATION_CREDENTIALS / WEATHERNEXT_PROJECT / WEATHERNEXT_DATASET empty"))

    title = "EWDS token works (archived GloFAS forecasts for the outlook backtest)"
    ek = e.get("EWDS_API_KEY", "")
    if ek:
        st, _ = _post_status("https://ewds.climate.copernicus.eu/api/profiles/v1/account/verification/pat", b"", {"PRIVATE-TOKEN": ek})
        rows.append(("EWDS", title, "done" if st == 200 else "open", f"HTTP {st}"))
    else:
        rows.append(("EWDS", title, "open", "EWDS_API_KEY empty in .env"))
    return rows


def main() -> None:
    e = env()
    tok, acct = e.get("CLOUDFLARE_API_TOKEN", ""), e.get("CLOUDFLARE_ACCOUNT_ID", "")
    rows: list[tuple[str, str, str, str]] = []  # id, title, status, detail

    # Cloudflare's bot challenge depends on the client's TLS fingerprint: Python's urllib can pass while curl, browsers'
    # headless mode and link-preview crawlers are challenged. So test with curl and look for `cf-mitigated`.
    hdr = subprocess.run(["curl", "-s", "-D", "-", "-o", "/dev/null", "--max-time", "20", "-A", "curl/8", URL_MAIN],
                         capture_output=True, text=True).stdout
    code = next((ln.split()[1] for ln in hdr.splitlines() if ln.upper().startswith("HTTP/")), "0")
    challenged = "cf-mitigated" in hdr.lower()
    st, _ = http(URL_MAIN)
    rows.append(("Q18", "flood.autobahn.bot open to non-browser clients (bot check relaxed)",
                 "done" if code == "200" and not challenged else "open",
                 f"curl → HTTP {code}{' (cf-mitigated: challenge)' if challenged else ''}; python urllib → HTTP {st}"))

    if tok and acct:
        ok_tun, msg_tun = cf_ok(f"/accounts/{acct}/cfd_tunnel?per_page=50", tok)
        ok_r2, msg_r2 = cf_ok(f"/accounts/{acct}/r2/buckets", tok)
        rows.append(("Q15a", "API token can list/manage Tunnels", "done" if ok_tun else "open", msg_tun))
        rows.append(("Q15b", "R2 off-site backups", "manual", "disabled by owner choice (D-029); data stays on local VPS"))
        old = "unknown (needs Q15a)"
        if ok_tun:
            _, body = http(f"{CF}/accounts/{acct}/cfd_tunnel?per_page=50", tok)
            live = [t for t in json.loads(body).get("result", []) if str(t.get("id", "")).startswith(OLD_TUNNEL_PREFIX) and not t.get("deleted_at")]
            old = "open (still exists)" if live else "done (deleted)"
        rows.append(("Q20", "Old tunnel ecd8a7b9… removed if unused", "manual", old))
        # One tiny real inference (~1 neuron): listing models doesn't prove the token may *run* them.
        req = urllib.request.Request(f"{CF}/accounts/{acct}/ai/run/@cf/meta/llama-3.2-1b-instruct", method="POST",
                                     data=json.dumps({"messages": [{"role": "user", "content": "ok"}], "max_tokens": 1}).encode(),
                                     headers={"User-Agent": UA, "Content-Type": "application/json",
                                              "Authorization": f"Bearer {e.get('CF_AI_TOKEN') or tok}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                ok_ai, msg_ai = bool(json.loads(r.read()).get("success")), "inference ok"
        except urllib.error.HTTPError as ex:
            ok_ai, msg_ai = False, f"HTTP {ex.code}"
        except Exception as ex:
            ok_ai, msg_ai = False, type(ex).__name__
        rows.append(("AI", "Workers AI inference works with the configured token", "done" if ok_ai else "open", msg_ai))
    else:
        rows.append(("Q15", "Cloudflare token/account in .env", "open", "CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID missing"))

    glm_key = e.get("GLM_API_KEY", "").strip()
    rows.append(("GLM", "GLM API key for AI feedback triage (GLM_API_KEY in .env)", "done" if glm_key else "open",
                 "key configured" if glm_key else "empty (fill in later in .env, D-030)"))

    # /impact (D-099): one shared password; it must be a long passphrase before partner data are loaded. Length only.
    impact_pw = e.get("IMPACT_PASSWORD", "").strip()
    rows.append(("IMPACT", "/impact password is a long passphrase (≥ 16 characters) before ONWR/RID data are loaded",
                 "done" if len(impact_pw) >= 16 else "open",
                 "not set: /impact answers 503" if not impact_pw else "long enough" if len(impact_pw) >= 16
                 else "short test password (owner 2026-10-06: for testing only); set a long passphrase before partner data"))

    # A key that exists is not a key that works (KI-510): make one real request, never print the key or the URL.
    gistda_key = e.get("GISTDA_API_KEY", "").strip()
    if gistda_key:
        # Documented at disaster.gistda.or.th/services/open-api: key in the API-Key header (not a query parameter).
        ep = e.get("GISTDA_API_ENDPOINT", "").strip() or "https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/7days"
        req = urllib.request.Request(f"{ep}?limit=1", headers={"User-Agent": UA, "API-Key": gistda_key})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                status, body = r.status, r.read(200_000).decode("utf-8", "replace")
        except urllib.error.HTTPError as ex:
            status, body = ex.code, ex.read(2_000).decode("utf-8", "replace")
        except Exception as ex:  # DNS, timeout, TLS
            status, body = 0, type(ex).__name__
        try:
            d = json.loads(body)
            detail = f"{d['numberMatched']} flood cells (7 days)" if status == 200 else str(d.get("detail", ""))[:60]
        except Exception:
            detail = ""
        detail = detail.replace(gistda_key, "***")
        rows.append(("GISTDA", "GISTDA flood-extent service answers with the configured key",
                     "done" if status == 200 else "open",
                     f"HTTP {status}" + (f" {detail}" if detail else "") + ("" if status == 200 else " (KI-510; see OWNER_ACTIONS)")))
    else:
        rows.append(("GISTDA", "GISTDA flood-extent service answers with the configured key", "open",
                     "GISTDA_API_KEY empty in .env"))


    # Google Flood Forecasting API (owner applies, D-046): one real, tiny request once a key is set; key never printed.
    gkey = e.get("GOOGLE_FLOOD_API_KEY", "").strip()
    if gkey:
        req = urllib.request.Request(
            "https://floodforecasting.googleapis.com/v1/gauges:searchGaugesByArea?" + urllib.parse.urlencode({"key": gkey}),
            data=json.dumps({"regionCode": "TH", "pageSize": 1}).encode(), method="POST",
            headers={"User-Agent": UA, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                gstatus = r.status
        except urllib.error.HTTPError as ex:
            gstatus = ex.code
        except Exception as ex:  # DNS, timeout, TLS
            gstatus = type(ex).__name__
        rows.append(("GFLOOD", "Google Flood Forecasting API key works (GOOGLE_FLOOD_API_KEY)", "done" if gstatus == 200 else "open",
                     f"HTTP {gstatus}"))
    else:
        rows.append(("GFLOOD", "Google Flood Forecasting API key works (GOOGLE_FLOOD_API_KEY)", "open",
                     "not applied/configured yet (pilot application, OWNER_ACTIONS)"))

    rows += new_source_checks(e)

    has_license = (ROOT / "LICENSE").exists()
    rows.append(("Q3", "Permission mails to HII / BMA / Traffy, and DWR / RID (D-046)", "done", "handled by the owner (2026-10-06)"))
    rows.append(("Q10", "Repository license (open source, MIT)", "done" if has_license else "open",
                 "MIT License applied (LICENSE file present, D-043)" if has_license else "no LICENSE file"))
    rid = (ROOT / "src/floodwatch/data/station_coords_rid.json").exists()
    rows.append(("RID", "RID gate coordinates imported (exact positions for ATG*/HDA*/TCP*)", "done" if rid else "open",
                 "station_coords_rid.json present" if rid else "not provided"))
    for qid, title in (("Q19", "Who reads user feedback (notes), how often"),
                       ("Q7", "Notifications (LINE / Web Push) wanted?"), ("Q22", "Traffy text labelling / voice reports with Workers AI?"),
                       ("EGRESS", "Reliable Thai egress before a public national launch (KI-110, D-046)"),
                       ("BMA", "Courtesy note to the flood69 relay / BMA about showing their data (D-031)"),
                       ("FLOODMAP", "Flood-coverage maps by release level below Kaeng Krachan from ONWR/RID (D-105)"),
                       ("DEM", "Higher-resolution DEM (LiDAR) for the Phetchaburi lowland (D-105)")):
        rows.append((qid, title, "manual", "answer in chat or in docs/plan/OPEN_QUESTIONS.md"))

    if "--json" in sys.argv:
        print(json.dumps([dict(id=a, title=b, status=c, detail=d) for a, b, c, d in rows], ensure_ascii=False, indent=1))
        return
    icon = {"done": "✅", "open": "⬜", "manual": "🖐️"}
    w = max(len(r[1]) for r in rows)
    for a, b, c, d in rows:
        print(f"{icon[c]} {a:5s} {b:{w}s}  {c:6s} {d}")
    open_n = sum(r[2] == "open" for r in rows)
    print(f"\n{open_n} scripted item(s) open. Details and how-to: docs/OWNER_ACTIONS.md")


if __name__ == "__main__":
    main()
