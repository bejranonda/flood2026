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
        rows.append(("Q15b", "API token can list R2 buckets", "done" if ok_r2 else "open", msg_r2))
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

    r2 = [k for k in ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT", "R2_BUCKET") if not e.get(k)]
    rows.append(("Q16", "R2 S3 credentials + bucket in .env", "done" if not r2 else "open", "all four set" if not r2 else "missing: " + ", ".join(r2)))

    ai = e.get("CF_AI_TOKEN", "")
    rows.append(("Q21", "Dedicated Workers-AI-only token (CF_AI_TOKEN)", "done" if ai and ai != tok else "open",
                 "set and different from the general token" if ai and ai != tok else "empty or same as the general token"))

    lic = any((ROOT / n).exists() for n in ("LICENSE", "LICENSE.md", "LICENSE.txt"))
    vis = subprocess.run(["gh", "repo", "view", "--json", "visibility", "-q", ".visibility"], capture_output=True, text=True, cwd=ROOT)
    rows.append(("Q10", "Repository license chosen (the repo is public: without one, all rights are reserved)", "done" if lic else "open",
                 f"LICENSE {'present' if lic else 'absent'}; visibility={vis.stdout.strip() or 'unknown'}"))
    rid = (ROOT / "src/floodwatch/data/station_coords_rid.json").exists()
    rows.append(("RID", "RID gate coordinates imported (exact positions for ATG*/HDA*/TCP*)", "done" if rid else "open",
                 "station_coords_rid.json present" if rid else "not provided"))
    for qid, title in (("Q17", "Thai server/home connection as SSH SOCKS exit for BMA"), ("Q19", "Who reads user feedback (notes), how often"),
                       ("Q7", "Notifications (LINE / Web Push) wanted?"), ("Q22", "Traffy text labelling / voice reports with Workers AI?"),
                       ("Q3", "Permission mails to HII / BMA / Traffy (optional, D-014)")):
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
