"""Google service-account login without Google libraries (D-069): a signed JWT, verified with openssl."""
import base64
import json
import subprocess

from floodwatch import gcp


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def test_jwt_is_rs256_signed_by_the_service_account_key(tmp_path):
    key = tmp_path / "k.pem"
    subprocess.run(["openssl", "genrsa", "-out", str(key), "2048"], check=True, capture_output=True)
    sa = {"client_email": "reader@p.iam.gserviceaccount.com", "private_key": key.read_text(),
          "token_uri": "https://oauth2.googleapis.com/token"}
    tok = gcp.jwt(sa, "https://www.googleapis.com/auth/bigquery.readonly", now=1_000)
    head, body, sig = tok.split(".")
    assert json.loads(_b64d(head)) == {"alg": "RS256", "typ": "JWT"}
    claims = json.loads(_b64d(body))
    assert claims == {"iss": "reader@p.iam.gserviceaccount.com", "scope": "https://www.googleapis.com/auth/bigquery.readonly",
                      "aud": "https://oauth2.googleapis.com/token", "iat": 1_000, "exp": 4_600}
    pub = tmp_path / "pub.pem"
    subprocess.run(["openssl", "rsa", "-in", str(key), "-pubout", "-out", str(pub)], check=True, capture_output=True)
    (tmp_path / "msg").write_bytes(f"{head}.{body}".encode())
    (tmp_path / "sig").write_bytes(_b64d(sig))
    r = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(pub), "-signature", str(tmp_path / "sig"),
                        str(tmp_path / "msg")], capture_output=True, text=True)
    assert "Verified OK" in r.stdout


def test_private_key_never_lands_in_a_temp_file_left_behind(tmp_path, monkeypatch):
    key = tmp_path / "k.pem"
    subprocess.run(["openssl", "genrsa", "-out", str(key), "2048"], check=True, capture_output=True)
    monkeypatch.setenv("TMPDIR", str(tmp_path / "t"))
    (tmp_path / "t").mkdir()
    gcp.jwt({"client_email": "a@b", "private_key": key.read_text()}, "s", now=0)
    assert list((tmp_path / "t").iterdir()) == []
