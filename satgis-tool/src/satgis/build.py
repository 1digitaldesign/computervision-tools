"""Build stage: frozen snapshot → attributed, geo-referenced feature tables."""
from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from . import agencies as ag
from .geometry import ring_to_polygon, track_to_line
from .propagate import (build_satrecs, footprint_ring, ground_track,
                        orbit_class, propagate_epoch)

RADIUS_EARTH_KM = 6378.135   # WGS-72, the datum SGP4 itself is defined on
CRS = "EPSG:4326"


def load_snapshot(raw_dir: Path) -> tuple[list[dict], dict, dict]:
    gp = json.loads((raw_dir / "celestrak.gp.active.json").read_text())
    manifest = json.loads((raw_dir / "acquisition-manifest.json").read_text())
    satcat: dict[int, dict] = {}
    with (raw_dir / "celestrak.satcat.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                satcat[int(row["NORAD_CAT_ID"])] = row
            except (TypeError, ValueError):
                continue
    return gp, satcat, manifest


def _f(x, default=float("nan")) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def build(raw_dir: Path, epoch: datetime, elev_mask_deg: float = 0.0,
          track_points: int = 60, ring_points: int = 72) -> dict:
    gp, satcat, manifest = load_snapshot(raw_dir)
    sats, kept, rejected = build_satrecs(gp)
    prop = propagate_epoch(sats, epoch)

    cross = ag.resolve(kept)
    by_id = {r["norad_cat_id"]: r for r in cross["crosswalk"]}

    rows, track_rows, fp_rows = [], [], []
    prop_failures = 0

    for i, (sat, rec) in enumerate(zip(sats, kept)):
        if prop["error"][i] != 0:
            prop_failures += 1
            continue
        nid = int(rec["NORAD_CAT_ID"])
        lon, lat = float(prop["lon"][i]), float(prop["lat"][i])
        alt_m = float(prop["alt_m"][i])
        apogee_km = _f(sat.alta) * RADIUS_EARTH_KM
        perigee_km = _f(sat.altp) * RADIUS_EARTH_KM
        ecc = _f(rec.get("ECCENTRICITY"), 0.0)
        incl = _f(rec.get("INCLINATION"), 0.0)
        mm = _f(rec.get("MEAN_MOTION"), 0.0)
        period_min = 1440.0 / mm if mm > 0 else float("nan")
        sc = satcat.get(nid, {})
        agency = by_id.get(nid)

        elem_epoch = rec.get("EPOCH")
        try:
            age_days = (epoch - datetime.fromisoformat(elem_epoch).replace(
                tzinfo=timezone.utc)).total_seconds() / 86400.0
        except Exception:  # noqa: BLE001
            age_days = float("nan")

        verts, central_deg, radius_km = footprint_ring(
            lon, lat, alt_m, elev_mask_deg, ring_points)

        rows.append({
            "norad_cat_id": nid,
            "object_id": rec.get("OBJECT_ID"),
            "object_name": rec.get("OBJECT_NAME"),
            "element_epoch_utc": elem_epoch,
            "element_age_days": round(age_days, 4) if math.isfinite(age_days) else None,
            "inclination_deg": incl,
            "raan_deg": _f(rec.get("RA_OF_ASC_NODE")),
            "eccentricity": ecc,
            "arg_perigee_deg": _f(rec.get("ARG_OF_PERICENTER")),
            "mean_anomaly_deg": _f(rec.get("MEAN_ANOMALY")),
            "mean_motion_rev_day": mm,
            "bstar": _f(rec.get("BSTAR")),
            "rev_at_epoch": _f(rec.get("REV_AT_EPOCH")),
            "element_set_no": _f(rec.get("ELEMENT_SET_NO")),
            "classification": rec.get("CLASSIFICATION_TYPE"),
            "period_min": period_min,
            "apogee_alt_km": apogee_km,
            "perigee_alt_km": perigee_km,
            "orbit_class": orbit_class(apogee_km, perigee_km, ecc, incl),
            "lat_deg": lat,
            "lon_deg": lon,
            "alt_km": alt_m / 1000.0,
            "speed_km_s": float(prop["speed_km_s"][i]),
            "footprint_central_angle_deg": central_deg,
            "footprint_radius_km": radius_km,
            "elevation_mask_deg": elev_mask_deg,
            "agency_lead": (agency or {}).get("agency_lead"),
            "agencies": ";".join((agency or {}).get("agencies", [])) or None,
            "program": (agency or {}).get("program"),
            "mission_class": (agency or {}).get("mission_class"),
            "agency_evidence_url": (agency or {}).get("evidence_url"),
            "satcat_object_type": sc.get("OBJECT_TYPE"),
            "satcat_ops_status": sc.get("OPS_STATUS_CODE"),
            "satcat_owner": sc.get("OWNER"),
            "satcat_launch_date": sc.get("LAUNCH_DATE") or None,
            "satcat_launch_site": sc.get("LAUNCH_SITE"),
            "satcat_rcs_m2": _f(sc.get("RCS"), None) if sc.get("RCS") else None,
            "satcat_orbit_center": sc.get("ORBIT_CENTER"),
            "satcat_orbit_type": sc.get("ORBIT_TYPE"),
            "geometry": Point(lon, lat),
        })

        poly = ring_to_polygon(verts, lat, radius_km)
        if poly is not None:
            fp_rows.append({
                "norad_cat_id": nid, "object_name": rec.get("OBJECT_NAME"),
                "orbit_class": rows[-1]["orbit_class"],
                "agency_lead": rows[-1]["agency_lead"], "program": rows[-1]["program"],
                "alt_km": alt_m / 1000.0, "elevation_mask_deg": elev_mask_deg,
                "central_angle_deg": central_deg, "radius_km": radius_km,
                "geometry": poly,
            })

        pts, per = ground_track(sat, epoch, track_points)
        line = track_to_line(pts)
        if line is not None:
            track_rows.append({
                "norad_cat_id": nid, "object_name": rec.get("OBJECT_NAME"),
                "orbit_class": rows[-1]["orbit_class"],
                "agency_lead": rows[-1]["agency_lead"], "program": rows[-1]["program"],
                "period_min": per, "n_samples": len(pts),
                "geometry": line,
            })

    sat_gdf = gpd.GeoDataFrame(rows, crs=CRS).sort_values("norad_cat_id").reset_index(drop=True)
    fp_gdf = gpd.GeoDataFrame(fp_rows, crs=CRS).sort_values("norad_cat_id").reset_index(drop=True)
    tr_gdf = gpd.GeoDataFrame(track_rows, crs=CRS).sort_values("norad_cat_id").reset_index(drop=True)

    meta = {
        "schema": "satgis.build-metadata/1",
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "propagation_epoch_utc": epoch.isoformat(timespec="seconds"),
        "frame_chain": "SGP4 TEME -> Rz(GMST82) -> ECEF (PEF) -> PROJ EPSG:4978->EPSG:4979 (WGS84)",
        "polar_motion_applied": False,
        "polar_motion_note": "x_p/y_p omitted; residual << SGP4 element-set error. Auditable, not hidden.",
        "footprint_model": "spherical visibility cap, lambda = acos(Re/(Re+h) * cos(eps)) - eps",
        "elevation_mask_deg": elev_mask_deg,
        "ring_points": ring_points,
        "track_points_per_rev": track_points,
        "counts": {
            "gp_records_in_snapshot": len(gp),
            "satrec_initialised": len(sats),
            "satrec_rejected": len(rejected),
            "propagation_failures_at_epoch": prop_failures,
            "satellites_layer": len(sat_gdf),
            "footprints_layer": len(fp_gdf),
            "ground_tracks_layer": len(tr_gdf),
            "satcat_records": len(satcat),
        },
        "agency": {k: v for k, v in cross.items() if k != "crosswalk"},
        "satrec_rejected_detail": rejected[:50],
        "acquisition_manifest": manifest,
    }
    return {"satellites": sat_gdf, "footprints": fp_gdf,
            "ground_tracks": tr_gdf, "metadata": meta, "crosswalk": cross}
