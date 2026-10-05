"""Access to /impact (owner 2026-10-05: "One shared password in the app"; D-099). The password and the signing secret come
only from .env (IMPACT_PASSWORD, IMPACT_SESSION_SECRET); nothing here logs or returns them."""
from __future__ import annotations

import hashlib
import hmac
import time

COOKIE = "fw_impact"
SESSION_S = 12 * 3600


def _digest(s: str) -> bytes:
    return hashlib.sha256(s.encode()).digest()


def password_ok(given: str, password: str) -> bool:
    """Constant-time; an unset password lets nobody in."""
    return bool(password) and hmac.compare_digest(_digest(given or ""), _digest(password))


def make_token(secret: str, password: str, exp: int) -> str:
    """'<expiry>.<hmac>' — the HMAC binds the expiry and the password, so a new password ends every session."""
    msg = f"impact|{exp}|{hashlib.sha256(password.encode()).hexdigest()[:16]}".encode()
    return f"{exp}.{hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()}"


def check_token(token: str | None, secret: str, password: str, now: float | None = None) -> bool:
    if not token or not secret or not password or "." not in token:
        return False
    exp_s, _ = token.split(".", 1)
    if not exp_s.isdigit() or int(exp_s) < (time.time() if now is None else now):
        return False
    return hmac.compare_digest(token, make_token(secret, password, int(exp_s)))


class LoginLimiter:
    """Failed tries per client (hashed address) in a sliding window. In memory, per app worker (2 workers → up to 2×)."""

    def __init__(self, max_failures: int = 5, window_s: int = 900):
        self.max, self.window, self.fails = max_failures, window_s, {}

    def _recent(self, who: str, now: float) -> list:
        self.fails[who] = [t for t in self.fails.get(who, []) if now - t < self.window]
        return self.fails[who]

    def allowed(self, who: str, now: float | None = None) -> bool:
        return len(self._recent(who, time.time() if now is None else now)) < self.max

    def fail(self, who: str, now: float | None = None) -> None:
        now = time.time() if now is None else now
        self._recent(who, now).append(now)
        if len(self.fails) > 10000:
            self.fails = {k: v for k, v in self.fails.items() if v and now - v[-1] < self.window}
