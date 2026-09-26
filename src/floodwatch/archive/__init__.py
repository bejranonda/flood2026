"""Immutable raw archive: every payload stored exactly as received, gzip + SHA-256 (ARCHITECTURE §3.1)."""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import os
import shutil
from pathlib import Path

from floodwatch.config import settings


def store(source: str, url: str, status: int, body: bytes, ext: str = "json") -> tuple[str, str]:
    """Write the payload once (write-once; identical content is stored only once). Returns (sha256, path)."""
    sha = hashlib.sha256(body).hexdigest()
    now = dt.datetime.now(dt.timezone.utc)
    root = Path(settings.archive_path)
    day_dir = root / source / now.strftime("%Y/%m/%d")
    index = root / source / "sha_index"
    index.mkdir(parents=True, exist_ok=True)
    marker = index / sha[:2] / sha
    if marker.exists():  # already archived: reference the existing object
        return sha, marker.read_text()
    day_dir.mkdir(parents=True, exist_ok=True)
    path = day_dir / f"{now.strftime('%Y%m%dT%H%M%SZ')}_{sha[:12]}.{ext}.gz"
    with gzip.open(path, "wb", compresslevel=6) as f:
        f.write(body)
    meta = {"source": source, "url": url, "http_status": status, "fetched_at": now.isoformat(),
            "sha256": sha, "bytes": len(body)}
    path.with_suffix(path.suffix + ".meta.json").write_text(json.dumps(meta))
    marker.parent.mkdir(exist_ok=True)
    marker.write_text(str(path))
    return sha, str(path)


def free_disk_gb() -> float:
    root = Path(settings.archive_path)
    root.mkdir(parents=True, exist_ok=True)
    return shutil.disk_usage(root).free / 1e9


def archive_size_gb() -> float:
    total = 0
    for dirpath, _, files in os.walk(settings.archive_path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total / 1e9
