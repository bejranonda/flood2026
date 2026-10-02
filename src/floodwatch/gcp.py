"""Google Cloud access with the standard library + the openssl binary (no Google client libraries), D-069.

Used only for research reads of WeatherNext through BigQuery: a service-account JSON key (GOOGLE_APPLICATION_CREDENTIALS,
kept in git-ignored certs/) -> a signed JWT -> an OAuth access token -> BigQuery REST `jobs.query`. Never logs the key,
the token or query results; WeatherNext real-time rain must not be shown or served (D-069).
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

TOKEN_URI = "https://oauth2.googleapis.com/token"
BQ_SCOPE = "https://www.googleapis.com/auth/bigquery.readonly"
BQ = "https://bigquery.googleapis.com/bigquery/v2"


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def jwt(sa: dict, scope: str, now: int | None = None) -> str:
    """RS256 JWT for the OAuth 'jwt-bearer' grant, valid one hour. The key goes to openssl on stdin, never to disk."""
    now = int(time.time()) if now is None else now
    head = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps({"iss": sa["client_email"], "scope": scope, "aud": sa.get("token_uri", TOKEN_URI),
                            "iat": now, "exp": now + 3600}, separators=(",", ":")).encode())
    msg = f"{head}.{body}".encode()
    with tempfile.TemporaryDirectory() as d:  # the message (not secret) needs a file; removed on exit
        path = os.path.join(d, "msg")
        with open(path, "wb") as f:
            f.write(msg)
        sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", "/dev/stdin", path],
                             input=sa["private_key"].encode(), capture_output=True, check=True).stdout
    return f"{head}.{body}.{_b64(sig)}"


def _post(url: str, data: bytes, headers: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def access_token(key_path: str, scope: str = BQ_SCOPE, timeout: float = 30) -> str:
    with open(key_path) as f:
        sa = json.load(f)
    form = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                   "assertion": jwt(sa, scope)}).encode()
    return _post(sa.get("token_uri", TOKEN_URI), form, {"Content-Type": "application/x-www-form-urlencoded"},
                 timeout)["access_token"]


def project_of(key_path: str) -> str:
    with open(key_path) as f:
        return json.load(f).get("project_id", "")


def bq_query(sql: str, token: str, billing_project: str, timeout_ms: int = 60_000) -> dict:
    """Run a standard-SQL query; returns BigQuery's `jobs.query` response (schema, rows, totalBytesProcessed)."""
    body = json.dumps({"query": sql, "useLegacySql": False, "timeoutMs": timeout_ms}).encode()
    return _post(f"{BQ}/projects/{billing_project}/queries", body,
                 {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout_ms / 1000 + 30)


def bq_rows(resp: dict) -> list[dict]:
    """Flatten a `jobs.query` response into dicts (top-level fields only; nested records stay raw)."""
    names = [f["name"] for f in resp.get("schema", {}).get("fields", [])]
    return [{n: c.get("v") for n, c in zip(names, r["f"])} for r in resp.get("rows", [])]
