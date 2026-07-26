"""Emit stage for the ground-station access layers.

Container split, stated rather than silent: the GeoPackage carries the layers a
GIS user opens and draws — the six orbital/station layers — while the 7.7 M-row
(satellite, station) pair table lives in Parquet only. Writing 7.7 M rows into
SQLite would multiply the .gpkg several-fold and slow every read of the layers
people actually render, for a table that is an analytical join target, not a
map layer. Both are hashed in the same manifest, so nothing is unaccounted for.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .emit import sha256_file
from .summarize import regional_rollup, satellite_summary, station_summary

SPATIAL_LAYERS = ("ground_stations", "station_access_summary")
PARQUET_ONLY = ("access_windows",)


def emit_access(res: dict, sats, out_dir: Path, log=print) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    st_sum = station_summary(res, sats)
    sat_sum = satellite_summary(res, sats)
    roll = regional_rollup(st_sum, sat_sum, res)

    # Same determinism rule as the orbital build: pin GDAL's clock so the
    # GeoPackage hashes reproducibly instead of embedding wall-time.
    stamp = res["params"]["epoch_utc"].replace("+00:00", "").rstrip("Z") + ".000Z"
    os.environ["OGR_CURRENT_DATE"] = stamp
    try:
        import pyogrio
        pyogrio.set_gdal_config_options({"OGR_CURRENT_DATE": stamp})
    except Exception:  # noqa: BLE001
        pass

    gpkg = out_dir / "satgis_orbital_catalog.gpkg"
    res["ground_stations"].to_file(gpkg, layer="ground_stations", driver="GPKG")
    st_sum.to_file(gpkg, layer="station_access_summary", driver="GPKG")

    res["ground_stations"].to_parquet(out_dir / "ground_stations.parquet", index=False)
    res["ground_stations"].to_file(out_dir / "ground_stations.geojson", driver="GeoJSON")
    st_sum.to_parquet(out_dir / "station_access_summary.parquet", index=False)
    st_sum.to_file(out_dir / "station_access_summary.geojson", driver="GeoJSON")
    sat_sum.to_parquet(out_dir / "satellite_access_summary.parquet", index=False)
    res["access_epoch"].to_parquet(out_dir / "access_epoch.parquet", index=False)
    res["access_windows"].to_parquet(out_dir / "access_windows.parquet", index=False)

    doc = {
        "schema": "satgis.access-metadata/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "params": res["params"],
        "precision": res["precision"],
        "container_policy": {
            "geopackage_layers": list(SPATIAL_LAYERS),
            "parquet_only": list(PARQUET_ONLY),
            "reason": ("the pair table is an analytical join target, not a map "
                       "layer; keeping it out of SQLite keeps the .gpkg small "
                       "and fast for the layers that are actually rendered"),
        },
        "regional_rollup": roll,
    }
    (out_dir / "access-metadata.json").write_text(
        json.dumps(doc, indent=2, sort_keys=True, default=str) + "\n")
    log(f"stations {roll['stations']} / {roll['countries']} countries; "
        f"contacts {roll['total_contact_events_24h']:,}; "
        f"access {roll['total_access_hours_24h']:,} station-hours")
    return {"station_summary": st_sum, "satellite_summary": sat_sum, "rollup": roll}


def rehash(out_dir: Path) -> dict:
    """Recompute the output manifest over everything currently in out_dir."""
    skip = {"SHA256SUMS", "SHA256SUMS.json", "xbom.cdx.json"}
    fmt = {".gpkg": "OGC GeoPackage", ".parquet": "GeoParquet",
           ".geojson": "GeoJSON", ".json": "JSON"}
    arts = []
    for p in sorted(out_dir.iterdir()):
        if p.is_dir() or p.name in skip:
            continue
        arts.append({"path": p.name, "format": fmt.get(p.suffix, "binary"),
                     "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    man = {
        "schema": "satgis.output-manifest/2",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artifact_count": len(arts),
        "total_bytes": sum(a["bytes"] for a in arts),
        "artifacts": arts,
    }
    (out_dir / "SHA256SUMS.json").write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
    (out_dir / "SHA256SUMS").write_text(
        "".join(f"{a['sha256']}  {a['path']}\n" for a in arts))
    return man
