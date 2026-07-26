"""Deterministic acquisition: fetch -> hash -> freeze.

Every artifact is written once with a SHA-256 and an RFC 3339 retrieval
timestamp. Downstream stages read only from the frozen snapshot, never the
network, so a build is reproducible from the manifest alone.

Snapshot semantics
------------------
A frozen snapshot is the unit of provenance, so `acquire` is idempotent by
default: a source already on disk whose bytes still hash to its recorded digest
is *reused*, not re-fetched. Two reasons, both learned the hard way here.

  1. Re-running acquire hammers upstream. CelesTrak began returning 403 after
     repeated full-catalog pulls during development — correct behaviour on
     their part, and a caller that keeps retrying is the bug.
  2. A failed refresh must never destroy provenance. Before this, a 403 on
     `celestrak.gp.active` left the original file intact on disk but moved its
     manifest entry into `failures`, so the snapshot silently lost the
     authority, licence and retrieval timestamp of its single most important
     source while the data it described was still sitting there.

So on a refresh failure the prior manifest entry is carried forward verbatim
and annotated, rather than dropped. Use `--refresh` to force re-fetch.
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
EXT = {"csv": "csv", "json": "json", "text": "tf", "zip": "zip"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _dest(src: Source, raw_dir: Path) -> Path:
    return raw_dir / f"{src.key}.{EXT[src.kind]}"


def _count(body: bytes, kind: str, key: str) -> int:
    if kind == "json":
        parsed = json.loads(body.decode("utf-8"))
        if not isinstance(parsed, list):
            raise ValueError(f"{key}: expected a JSON array, got {type(parsed).__name__}")
        return len(parsed)
    if kind == "csv":
        return max(0, body.decode("utf-8", "replace").count("\n") - 1)
    if kind == "text":
        return body.decode("utf-8", "replace").count("\n")
    return 0


def fetch(src: Source, raw_dir: Path, session: requests.Session) -> dict:
    dest = _dest(src, raw_dir)
    t0 = time.monotonic()
    resp = session.get(src.url, timeout=TIMEOUT_S)
    resp.raise_for_status()
    body = resp.content
    n = _count(body, src.kind, src.key)
    dest.write_bytes(body)
    return {
        "key": src.key, "url": src.url, "group": src.group,
        "authority": src.authority, "license": src.license,
        "description": src.description, "path": dest.name,
        "bytes": len(body), "records": n, "sha256": sha256_file(dest),
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "http_status": resp.status_code,
        "elapsed_s": round(time.monotonic() - t0, 3),
        "state": "fetched",
    }


def _prior(raw_dir: Path) -> dict:
    mp = raw_dir / "acquisition-manifest.json"
    if not mp.exists():
        return {}
    try:
        doc = json.loads(mp.read_text())
    except json.JSONDecodeError:
        return {}
    return {e["key"]: e for e in doc.get("sources", [])}


def acquire_all(raw_dir: Path, refresh: bool = False) -> dict:
    raw_dir.mkdir(parents=True, exist_ok=True)
    prior = _prior(raw_dir)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})

    entries, failures = [], []
    srcs = all_sources()
    fetched_any = False
    for i, src in enumerate(srcs):
        dest = _dest(src, raw_dir)
        p = prior.get(src.key)

        # Reuse an intact frozen artifact unless a refresh was asked for.
        if not refresh and dest.exists() and p and sha256_file(dest) == p.get("sha256"):
            e = dict(p); e["state"] = "reused"
            entries.append(e)
            print(f"[{i+1:2d}/{len(srcs)}] {src.key:34s} {e['records']:>6d} rec  "
                  f"{e['sha256'][:12]}  reused")
            continue

        if fetched_any:
            time.sleep(POLITE_DELAY_S)
        try:
            e = fetch(src, raw_dir, session)
            fetched_any = True
            entries.append(e)
            print(f"[{i+1:2d}/{len(srcs)}] {src.key:34s} {e['records']:>6d} rec  "
                  f"{e['sha256'][:12]}  fetched")
        except Exception as exc:  # noqa: BLE001 — recorded, never swallowed
            err = f"{type(exc).__name__}: {exc}"
            fetched_any = True
            if dest.exists() and p:
                # Refresh failed but the frozen bytes are still here. Carry the
                # prior provenance forward rather than dropping it.
                e = dict(p)
                e["state"] = "retained_after_failed_refresh"
                e["refresh_error"] = err
                e["sha256"] = sha256_file(dest)
                entries.append(e)
                print(f"[{i+1:2d}/{len(srcs)}] {src.key:34s} {e['records']:>6d} rec  "
                      f"{e['sha256'][:12]}  RETAINED ({type(exc).__name__})")
            else:
                failures.append({"key": src.key, "url": src.url, "error": err})
                print(f"[{i+1:2d}/{len(srcs)}] {src.key:34s} FAILED  {err}")

    manifest = {
        "schema": "satgis.acquisition-manifest/2",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "refresh_requested": refresh,
        "states": {s: sum(1 for e in entries if e.get("state") == s)
                   for s in ("fetched", "reused", "retained_after_failed_refresh")},
        "sources": sorted(entries, key=lambda e: e["key"]),
        "failures": failures,
    }
    (raw_dir / "acquisition-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw")
    m = acquire_all(out, refresh="--refresh" in sys.argv)
    print(f"\nsources={len(m['sources'])} failures={len(m['failures'])} states={m['states']}")
