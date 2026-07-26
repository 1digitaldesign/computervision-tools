"""satgis — stable-verb CLI.

    satgis doctor    environment and dependency preflight
    satgis acquire   fetch + hash the authoritative catalog snapshot
    satgis build     snapshot -> GeoPackage / GeoJSON / GeoParquet + xBOM
    satgis access    satellite-to-ground-station geometry (Spain + LATAM)
    satgis latam     LATAM imaging history back to the earliest catalogued record
    satgis verify    three independent methods + negative controls
    satgis package   bundle outputs + evidence for release

Verbs are detected from data, never from an IDE- or host-specific path. Every
verb is idempotent and every verb exits non-zero on a substantive failure, so
CI and a human get the same answer.
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

VERSION = "0.1.0"
REQUIRED = ("sgp4", "geopandas", "shapely", "pyproj", "pyogrio", "pyarrow",
            "pandas", "numpy", "requests", "cyclonedx-python-lib")


def _epoch(value: str | None) -> datetime:
    if value in (None, "", "now"):
        return datetime.now(timezone.utc).replace(microsecond=0)
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def cmd_doctor(args) -> int:
    print(f"satgis {VERSION}")
    print(f"python   {sys.version.split()[0]}  ({sys.executable})")
    bad = []
    for pkg in REQUIRED:
        try:
            print(f"  ok   {pkg}=={md.version(pkg)}")
        except md.PackageNotFoundError:
            print(f"  MISS {pkg}")
            bad.append(pkg)
    try:
        import pyogrio
        print(f"  ok   GDAL {pyogrio.__gdal_version_string__}")
        drivers = set(pyogrio.list_drivers(write=True))
        for d in ("GPKG", "GeoJSON"):
            mark = "ok  " if d in drivers else "MISS"
            print(f"  {mark} driver {d}")
            if d not in drivers:
                bad.append(f"driver:{d}")
    except Exception as exc:  # noqa: BLE001
        print(f"  MISS pyogrio/GDAL: {exc}")
        bad.append("gdal")
    raw = Path(args.raw)
    snap = raw / "acquisition-manifest.json"
    print(f"  {'ok  ' if snap.exists() else 'none'} snapshot {snap}")
    print("\nDOCTOR: " + ("PASS" if not bad else f"FAIL ({', '.join(bad)})"))
    return 0 if not bad else 1


def cmd_acquire(args) -> int:
    from .acquire import acquire_all
    m = acquire_all(Path(args.raw), refresh=getattr(args, "refresh", False))
    print(f"\nsources={len(m['sources'])} failures={len(m['failures'])} states={m['states']}")
    return 0 if not m["failures"] else 2


def cmd_build(args) -> int:
    from .build import build
    from .emit import emit
    from .xbom import build_xbom, write_xbom

    epoch = _epoch(args.epoch)
    raw, out = Path(args.raw), Path(args.out)
    print(f"epoch      {epoch.isoformat()}")
    print(f"snapshot   {raw}")
    built = build(raw, epoch, elev_mask_deg=args.elevation_mask,
                  track_points=args.track_points, ring_points=args.ring_points)
    c = built["metadata"]["counts"]
    print(f"satellites {c['satellites_layer']}  footprints {c['footprints_layer']}  "
          f"tracks {c['ground_tracks_layer']}")
    a = built["metadata"]["agency"]
    print(f"agency     {a['by_agency_lead']}  (rules {a['rules_matched']}/{a['rules_total']})")
    if a["rules_unmatched"]:
        print(f"  WARNING unmatched attribution rules: {a['rules_unmatched']}")
    manifest = emit(built, out)
    print(f"artifacts  {manifest['artifact_count']} files, "
          f"{manifest['total_bytes']/1e6:.1f} MB")
    xb = build_xbom(built["metadata"]["acquisition_manifest"], manifest,
                    built["metadata"])
    write_xbom(xb, out / "xbom.cdx.json")
    print(f"xbom       {len(xb['components'])} components -> xbom.cdx.json")
    return 0


def cmd_access(args) -> int:
    """Ground-station access: every satellite against every Spain + LATAM station."""
    import geopandas as gpd
    from .build_access import build_access
    from .emit_access import emit_access, rehash
    from .xbom import build_xbom, write_xbom

    epoch = _epoch(args.epoch)
    raw, out = Path(args.raw), Path(args.out)
    gpkg = out / "satgis_orbital_catalog.gpkg"
    if not gpkg.exists():
        print(f"ERROR: {gpkg} not found — run `satgis build` first.")
        return 2
    res = build_access(raw, epoch, hours=args.hours, step_s=args.step,
                       block=args.block)
    sats = gpd.read_file(gpkg, layer="satellites")
    emit_access(res, sats, out)
    man = rehash(out)
    bm = json.loads((out / "build-metadata.json").read_text())
    am = json.loads((raw / "acquisition-manifest.json").read_text())
    write_xbom(build_xbom(am, man, bm), out / "xbom.cdx.json")
    print(f"artifacts  {man['artifact_count']} files, {man['total_bytes']/1e6:.1f} MB")
    return 0


def cmd_latam(args) -> int:
    """LATAM imaging history, back to the earliest catalogued record."""
    import os
    import geopandas as gpd, pandas as pd
    from .latam import build_history
    from .emit_access import rehash
    from .xbom import build_xbom, write_xbom

    raw, out = Path(args.raw), Path(args.out)
    bm_path = out / "build-metadata.json"
    if not bm_path.exists():
        print(f"ERROR: {bm_path} not found — run `satgis build` first.")
        return 2
    h = build_history(raw, Path(args.crosswalk))
    df = pd.DataFrame(h["rows"])
    df.to_parquet(out / "latam_imaging_history.parquet", index=False)

    gpkg = out / "satgis_orbital_catalog.gpkg"
    if gpkg.exists():
        sats = gpd.read_file(gpkg, layer="satellites")
        dupes = [c for c in df.columns if c in sats.columns and c != "norad_cat_id"]
        cur = sats.merge(df.drop(columns=dupes), on="norad_cat_id", how="inner")
        stamp = json.loads(bm_path.read_text())["propagation_epoch_utc"]
        stamp = stamp.replace("+00:00", "").rstrip("Z") + ".000Z"
        os.environ["OGR_CURRENT_DATE"] = stamp
        try:
            import pyogrio; pyogrio.set_gdal_config_options({"OGR_CURRENT_DATE": stamp})
        except Exception:  # noqa: BLE001
            pass
        cur.to_file(gpkg, layer="latam_imaging_current", driver="GPKG")
        cur.to_file(out / "latam_imaging_current.geojson", driver="GeoJSON")
        cur.to_parquet(out / "latam_imaging_current.parquet", index=False)
        print(f"on-orbit LATAM payloads with a current element set: {len(cur)}")

    (out / "latam-history-metadata.json").write_text(
        json.dumps({"schema": h["schema"], "summary": h["summary"]},
                   indent=2, sort_keys=True, default=str) + "\n")
    man = rehash(out)
    bm = json.loads(bm_path.read_text())
    am = json.loads((raw / "acquisition-manifest.json").read_text())
    write_xbom(build_xbom(am, man, bm), out / "xbom.cdx.json")
    s = h["summary"]
    print(f"payloads {s['payloads_total']}  imaging yes/partial/no/unclassified "
          f"{s['imaging_yes']}/{s['imaging_partial']}/{s['imaging_no']}/{s['unclassified']}")
    print(f"earliest imaging: {s['earliest_imaging_strict']}")
    print(f"artifacts  {man['artifact_count']} files, {man['total_bytes']/1e6:.1f} MB")
    return 0


def cmd_verify(args) -> int:
    from .verify import verify_all
    out = Path(args.out)
    report = verify_all(out, Path(args.raw), Path(args.crosswalk))
    for c in report["checks"] + report["negative_controls"]:
        print(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['method']:11s} "
              f"{c['check']:42s} {c['detail']}")
    dest = Path(args.evidence) / "verification-report.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"\nchecks {report['checks_passed']}/{report['checks_total']}  "
          f"controls {report['controls_passed']}/{report['controls_total']}  "
          f"VERDICT: {report['verdict']}")
    print(f"report -> {dest}")
    return 0 if report["verdict"] == "PASS" else 1


def cmd_package(args) -> int:
    out, ev = Path(args.out), Path(args.evidence)
    dest = Path(args.dist); dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = dest / f"satgis-orbital-catalog-{stamp}"
    staging = dest / "_staging"
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(out, staging / "out")
    if ev.exists():
        shutil.copytree(ev, staging / "evidence")
    archive = shutil.make_archive(str(base), "zip", staging)
    shutil.rmtree(staging)
    print(f"packaged -> {archive} ({Path(archive).stat().st_size/1e6:.1f} MB)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="satgis", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"satgis {VERSION}")
    sub = p.add_subparsers(dest="verb", required=True)

    def common(sp):
        sp.add_argument("--raw", default="data/raw")
        sp.add_argument("--out", default="data/out")
        sp.add_argument("--evidence", default="evidence")
        return sp

    common(sub.add_parser("doctor")).set_defaults(func=cmd_doctor)
    ac = common(sub.add_parser("acquire"))
    ac.add_argument("--refresh", action="store_true",
                    help="force re-fetch even when the frozen artifact is intact")
    ac.set_defaults(func=cmd_acquire)

    b = common(sub.add_parser("build"))
    b.add_argument("--epoch", default="now",
                   help="ISO-8601 UTC propagation epoch, or 'now'")
    b.add_argument("--elevation-mask", type=float, default=0.0,
                   help="footprint elevation mask in degrees (0 = horizon)")
    b.add_argument("--track-points", type=int, default=60)
    b.add_argument("--ring-points", type=int, default=72)
    b.set_defaults(func=cmd_build)

    ax = common(sub.add_parser("access"))
    ax.add_argument("--epoch", default="now")
    ax.add_argument("--hours", type=float, default=24.0)
    ax.add_argument("--step", type=float, default=60.0,
                    help="time-grid step in seconds")
    ax.add_argument("--block", type=int, default=100,
                    help="satellites per GEMM block (memory/throughput tradeoff)")
    ax.set_defaults(func=cmd_access)

    lt = common(sub.add_parser("latam"))
    lt.add_argument("--crosswalk", default="data/latam_imaging_crosswalk.json")
    lt.set_defaults(func=cmd_latam)

    v = common(sub.add_parser("verify"))
    v.add_argument("--crosswalk", default="data/latam_imaging_crosswalk.json")
    v.set_defaults(func=cmd_verify)
    pk = common(sub.add_parser("package"))
    pk.add_argument("--dist", default="dist")
    pk.set_defaults(func=cmd_package)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
