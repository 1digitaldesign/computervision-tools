"""Deterministic acquisition: fetch → hash → freeze.

Every artifact is written once with a SHA-256 and an RFC 3339 retrieval
timestamp. Downstream stages read only from the frozen snapshot, never the
network, so a build is reproducible from the manifest alone.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from .sources import Source, all_sources

USER_AGENT = (
    "satgis/0.1 (+https://github.com/1digitaldesign/computervision-tools) "
    "nonprofit-research; contact via repo issues"
)
POLITE_DELAY_S = 2.0
TIMEOUT_S = 120


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(src: Source, raw_dir: Path, session: requests.Session) -> dict:
    ext = "csv" if src.kind == "csv" else "json"
    dest = raw_dir / f"{src.key}.{ext}"
    t0 = time.monotonic()
    resp = session.get(src.url, timeout=TIMEOUT_S)
    resp.raise_for_status()
    body = resp.content
    if src.kind == "json":
        # Fail loudly on an HTML error page served with 200.
        parsed = json.loads(body.decode("utf-8"))
        if not isinstance(parsed, list):
            raise ValueError(f"{src.key}: expected a JSON array, got {type(parsed).__name__}")
        n = len(parsed)
    else:
        n = max(0, body.decode("utf-8", "replace").count("\n") - 1)
    dest.write_bytes(body)
    return {
        "key": src.key,
        "url": src.url,
        "group": src.group,
        "authority": src.authority,
        "license": src.license,
        "description": src.description,
        "path": dest.name,
        "bytes": len(body),
        "records": n,
        "sha256": sha256_file(dest),
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "http_status": resp.status_code,
        "elapsed_s": round(time.monotonic() - t0, 3),
    }


def acquire_all(raw_dir: Path) -> dict:
    raw_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
    entries, failures = [], []
    srcs = all_sources()
    for i, src in enumerate(srcs):
        try:
            entry = fetch(src, raw_dir, session)
            entries.append(entry)
            print(f"[{i+1:2d}/{len(srcs)}] {src.key:34s} {entry['records']:>6d} rec  {entry['sha256'][:12]}")
        except Exception as exc:  # noqa: BLE001 — recorded, not swallowed
            failures.append({"key": src.key, "url": src.url, "error": f"{type(exc).__name__}: {exc}"})
            print(f"[{i+1:2d}/{len(srcs)}] {src.key:34s} FAILED  {type(exc).__name__}: {exc}")
        if i < len(srcs) - 1:
            time.sleep(POLITE_DELAY_S)

    manifest = {
        "schema": "satgis.acquisition-manifest/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": entries,
        "failures": failures,
    }
    (raw_dir / "acquisition-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


if __name__ == "__main__":
    import sys

    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw")
    m = acquire_all(out)
    print(f"\nsources={len(m['sources'])} failures={len(m['failures'])}")
