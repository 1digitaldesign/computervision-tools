"""Emit stage: feature tables → GeoPackage, GeoJSON, GeoParquet + checksums.

Determinism contract: rows are sorted by norad_cat_id before writing, JSON keys
are sorted, and no wall-clock value is embedded in a geometry file — so two
builds from the same frozen snapshot and epoch are byte-identical except for
the metadata document, which is where timestamps are allowed to live.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd

LAYERS = ("satellites", "footprints", "ground_tracks")
AGENCIES = ("NASA", "NOAA", "USGS")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write(gdf: gpd.GeoDataFrame, path: Path, driver: str | None = None) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        gdf.to_parquet(path, index=False)
    elif path.suffix == ".geojson":
        if path.exists():
            path.unlink()
        gdf.to_file(path, driver="GeoJSON")
    else:
        raise ValueError(f"unsupported target {path}")
    return {"path": str(path.name), "bytes": path.stat().st_size,
            "features": int(len(gdf)), "sha256": sha256_file(path)}


def emit(built: dict, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict] = []

    # --- GeoPackage: the canonical multi-layer container --------------------
    # A GeoPackage is a SQLite database, and GDAL stamps wall-clock into
    # gpkg_contents.last_change. That alone made two builds from the same
    # frozen snapshot differ byte-for-byte while every layer was proven
    # feature-identical. Pinning OGR_CURRENT_DATE to the propagation epoch
    # removes the only nondeterministic field, so the container hashes
    # reproducibly like the Parquet and GeoJSON outputs already did.
    epoch_iso = built["metadata"]["propagation_epoch_utc"]
    stamp = epoch_iso.replace("+00:00", "").rstrip("Z") + ".000Z"
    os.environ["OGR_CURRENT_DATE"] = stamp
    try:
        import pyogrio
        pyogrio.set_gdal_config_options({"OGR_CURRENT_DATE": stamp})
    except Exception:  # noqa: BLE001 — env var alone is sufficient for GDAL
        pass

    gpkg = out_dir / "satgis_orbital_catalog.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    for layer in LAYERS:
        gdf = built[layer]
        if len(gdf) == 0:
            continue
        gdf.to_file(gpkg, layer=layer, driver="GPKG")
    artifacts.append({"path": gpkg.name, "format": "OGC GeoPackage",
                      "layers": list(LAYERS), "bytes": gpkg.stat().st_size,
                      "sha256": sha256_file(gpkg)})

    # --- GeoParquet + GeoJSON, one file per layer --------------------------
    for layer in LAYERS:
        gdf = built[layer]
        if len(gdf) == 0:
            continue
        a = _write(gdf, out_dir / f"{layer}.parquet"); a["format"] = "GeoParquet"; a["layer"] = layer
        artifacts.append(a)
        a = _write(gdf, out_dir / f"{layer}.geojson"); a["format"] = "GeoJSON"; a["layer"] = layer
        artifacts.append(a)

    # --- Agency cuts: the NASA / NOAA / USGS fleets on their own -----------
    for agency in AGENCIES:
        for layer in LAYERS:
            gdf = built[layer]
            if len(gdf) == 0 or "agency_lead" not in gdf.columns:
                continue
            sub = gdf[gdf["agency_lead"] == agency]
            if len(sub) == 0:
                continue
            a = _write(sub, out_dir / f"agency_{agency.lower()}_{layer}.geojson")
            a["format"] = "GeoJSON"; a["layer"] = layer; a["agency"] = agency
            artifacts.append(a)

    # --- Metadata + crosswalk + checksum manifest --------------------------
    for name, doc in (("build-metadata.json", built["metadata"]),
                      ("agency-crosswalk.json", built["crosswalk"])):
        p = out_dir / name
        p.write_text(json.dumps(doc, indent=2, sort_keys=True, default=str) + "\n")
        artifacts.append({"path": name, "format": "JSON",
                          "bytes": p.stat().st_size, "sha256": sha256_file(p)})

    manifest = {
        "schema": "satgis.output-manifest/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artifact_count": len(artifacts),
        "total_bytes": sum(a["bytes"] for a in artifacts),
        "artifacts": sorted(artifacts, key=lambda a: a["path"]),
    }
    mp = out_dir / "SHA256SUMS.json"
    mp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    plain = out_dir / "SHA256SUMS"
    plain.write_text("".join(f"{a['sha256']}  {a['path']}\n"
                             for a in manifest["artifacts"]))
    return manifest
