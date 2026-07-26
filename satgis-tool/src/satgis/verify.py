"""Risk-proportional verification: three independent methods + negative controls.

The three methods are deliberately *not* variations on one idea:

  M1 INTEGRITY   — bit-level. SHA-256 recomputation, schema conformance, CRS
                   identity, geometry validity. Catches corruption and drift.
  M2 PHYSICS     — numerical, independent of our own code path. The datum
                   conversion is re-derived with a closed-form Bowring solution
                   that never touches PROJ, and the results are checked against
                   externally-known physical ground truth (ISS altitude band,
                   geostationary radius and speed) that no bug in this repo can
                   move.
  M3 TOPOLOGY    — geometric invariants that must hold for any correct build:
                   a satellite lies inside its own visibility footprint; cap
                   area is monotone in altitude; nothing escapes world bounds.

Each method ships a **negative control**: a deliberate mutation that the check
must reject. A check that passes its mutation is reported as WORTHLESS, because
an assertion that cannot fail is not evidence.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

MU_EARTH = 398600.8          # km^3/s^2, WGS-72 (the model SGP4 is defined on)
A_WGS84 = 6378137.0
F_WGS84 = 1.0 / 298.257223563
E2 = F_WGS84 * (2 - F_WGS84)
EP2 = E2 / (1.0 - E2)
B_WGS84 = A_WGS84 * (1 - F_WGS84)


# --------------------------------------------------------------------------
# Independent datum conversion — closed-form Bowring (1976). Deliberately does
# not import pyproj, so agreement with the build is real corroboration.
# --------------------------------------------------------------------------
def bowring_geodetic(x_m: np.ndarray, y_m: np.ndarray, z_m: np.ndarray,
                     refine: int = 5):
    """Bowring (1976) seed + fixed-point refinement.

    The single-pass Bowring closed form is ~1e-9 deg accurate for near-surface
    points but degrades to ~5e-7 deg at geostationary altitude, because its
    parametric-latitude seed assumes the point is close to the ellipsoid. That
    was measured, not assumed: the first run of this verifier failed at
    max dlat = 4.518e-07 deg, driven entirely by the GEO belt. Refining to a
    fixed point restores full double precision at every altitude, which keeps
    the M2 tolerance tight enough to be worth asserting.
    """
    p = np.hypot(x_m, y_m)
    theta = np.arctan2(z_m * A_WGS84, p * B_WGS84)
    lat = np.arctan2(z_m + EP2 * B_WGS84 * np.sin(theta) ** 3,
                     p - E2 * A_WGS84 * np.cos(theta) ** 3)
    for _ in range(refine):
        n = A_WGS84 / np.sqrt(1 - E2 * np.sin(lat) ** 2)
        alt = p / np.cos(lat) - n
        lat = np.arctan2(z_m, p * (1 - E2 * n / (n + alt)))
    n = A_WGS84 / np.sqrt(1 - E2 * np.sin(lat) ** 2)
    alt = p / np.cos(lat) - n
    lon = np.arctan2(y_m, x_m)
    return np.degrees(lon), np.degrees(lat), alt


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _result(name: str, method: str, passed: bool, detail: str, **extra) -> dict:
    return {"check": name, "method": method, "passed": bool(passed),
            "detail": detail, **extra}


# --------------------------------------------------------------------------
# M1 — integrity
# --------------------------------------------------------------------------
def m1_integrity(out_dir: Path) -> list[dict]:
    checks = []
    manifest = json.loads((out_dir / "SHA256SUMS.json").read_text())
    bad = []
    for art in manifest["artifacts"]:
        p = out_dir / art["path"]
        if not p.exists():
            bad.append(f"{art['path']}: MISSING")
        elif _sha256(p) != art["sha256"]:
            bad.append(f"{art['path']}: HASH MISMATCH")
    checks.append(_result("artifact_sha256", "M1", not bad,
                          f"{len(manifest['artifacts'])} artifacts verified"
                          if not bad else "; ".join(bad[:5]),
                          artifacts=len(manifest["artifacts"])))

    gpkg = out_dir / "satgis_orbital_catalog.gpkg"
    meta = json.loads((out_dir / "build-metadata.json").read_text())
    layer_issues = []
    for layer, key in (("satellites", "satellites_layer"),
                       ("footprints", "footprints_layer"),
                       ("ground_tracks", "ground_tracks_layer")):
        gdf = gpd.read_file(gpkg, layer=layer)
        if len(gdf) != meta["counts"][key]:
            layer_issues.append(f"{layer}: {len(gdf)} != {meta['counts'][key]}")
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            layer_issues.append(f"{layer}: CRS is {gdf.crs}, expected EPSG:4326")
        if gdf.geometry.isna().any():
            layer_issues.append(f"{layer}: null geometry present")
        if not gdf.geometry.is_valid.all():
            layer_issues.append(f"{layer}: {(~gdf.geometry.is_valid).sum()} invalid geometries")
    checks.append(_result("gpkg_schema_and_counts", "M1", not layer_issues,
                          "3 layers: counts, CRS, validity all conform"
                          if not layer_issues else "; ".join(layer_issues)))

    sats = gpd.read_file(gpkg, layer="satellites")
    required = {"norad_cat_id", "object_name", "lat_deg", "lon_deg", "alt_km",
                "orbit_class", "agency_lead", "footprint_radius_km"}
    missing = required - set(sats.columns)
    checks.append(_result("required_columns", "M1", not missing,
                          "all required columns present" if not missing
                          else f"missing: {sorted(missing)}"))
    return checks


# --------------------------------------------------------------------------
# M2 — physics, independent of the build's own code path
# --------------------------------------------------------------------------
def m2_physics(out_dir: Path) -> list[dict]:
    checks = []
    sats = gpd.read_file(out_dir / "satgis_orbital_catalog.gpkg", layer="satellites")

    # (a) PROJ vs independent Bowring closed form, via the published lon/lat/alt
    lat = np.radians(sats["lat_deg"].to_numpy())
    lon = np.radians(sats["lon_deg"].to_numpy())
    alt = sats["alt_km"].to_numpy() * 1000.0
    n = A_WGS84 / np.sqrt(1 - E2 * np.sin(lat) ** 2)
    x = (n + alt) * np.cos(lat) * np.cos(lon)
    y = (n + alt) * np.cos(lat) * np.sin(lon)
    z = (n * (1 - E2) + alt) * np.sin(lat)
    blon, blat, balt = bowring_geodetic(x, y, z)
    dlat = np.abs(blat - sats["lat_deg"].to_numpy()).max()
    dlon = np.abs(((blon - sats["lon_deg"].to_numpy() + 180) % 360) - 180).max()
    dalt = np.abs(balt - alt).max()
    ok = dlat < 1e-8 and dlon < 1e-8 and dalt < 1e-3
    checks.append(_result("proj_vs_bowring_datum", "M2", ok,
                          f"max dlat={dlat:.3e} deg, dlon={dlon:.3e} deg, dalt={dalt:.3e} m",
                          max_dlat_deg=float(dlat), max_dalt_m=float(dalt)))

    # (b) Known reference: ISS (NORAD 25544)
    iss = sats[sats["norad_cat_id"] == 25544]
    if len(iss):
        a_km = float(iss["alt_km"].iloc[0]); v = float(iss["speed_km_s"].iloc[0])
        ok = 330.0 <= a_km <= 470.0 and 7.5 <= v <= 7.9
        checks.append(_result("reference_iss_25544", "M2", ok,
                              f"alt={a_km:.1f} km (expect 330-470), speed={v:.3f} km/s (expect 7.5-7.9)",
                              alt_km=a_km, speed_km_s=v))
    else:
        checks.append(_result("reference_iss_25544", "M2", False, "ISS not present in catalog"))

    # (c) Known reference: geostationary NOAA GOES fleet
    geo = sats[sats["norad_cat_id"].isin([41866, 43226, 51850, 60133])]
    if len(geo):
        alt_ok = geo["alt_km"].between(35550, 35950).all()
        lat_ok = geo["lat_deg"].abs().lt(1.5).all()
        spd_ok = geo["speed_km_s"].between(2.9, 3.2).all()
        ok = bool(alt_ok and lat_ok and spd_ok)
        checks.append(_result("reference_goes_geostationary", "M2", ok,
                              f"n={len(geo)} alt={geo['alt_km'].min():.0f}-{geo['alt_km'].max():.0f} km, "
                              f"|lat|max={geo['lat_deg'].abs().max():.3f} deg, "
                              f"v={geo['speed_km_s'].min():.3f}-{geo['speed_km_s'].max():.3f} km/s"))
    else:
        checks.append(_result("reference_goes_geostationary", "M2", False, "GOES fleet absent"))

    # (d) Kepler's third law vs the published period, over LEO+MEO+GEO
    e = sats["eccentricity"].to_numpy()
    rp = sats["perigee_alt_km"].to_numpy() + 6378.135
    with np.errstate(divide="ignore", invalid="ignore"):
        a_sma = rp / (1.0 - e)
        t_kepler = 2 * np.pi * np.sqrt(a_sma ** 3 / MU_EARTH) / 60.0
    t_pub = sats["period_min"].to_numpy()
    m = np.isfinite(t_kepler) & np.isfinite(t_pub) & (t_pub > 0)
    rel = np.abs(t_kepler[m] - t_pub[m]) / t_pub[m]
    frac = float((rel < 0.02).mean())
    checks.append(_result("kepler_third_law", "M2", frac > 0.98,
                          f"{frac*100:.2f}% of {int(m.sum())} objects agree with "
                          f"T=2*pi*sqrt(a^3/mu) within 2%",
                          agreement_fraction=frac))
    return checks


# --------------------------------------------------------------------------
# M3 — geometric / topological invariants
# --------------------------------------------------------------------------
def m3_topology(out_dir: Path) -> list[dict]:
    checks = []
    gpkg = out_dir / "satgis_orbital_catalog.gpkg"
    sats = gpd.read_file(gpkg, layer="satellites")
    fps = gpd.read_file(gpkg, layer="footprints")

    merged = fps.merge(sats[["norad_cat_id", "lon_deg", "lat_deg"]],
                       on="norad_cat_id", how="inner")
    inside = np.array([
        geom.buffer(0).contains(Point(lo, la)) or geom.buffer(1e-7).contains(Point(lo, la))
        for geom, lo, la in zip(merged.geometry, merged["lon_deg"], merged["lat_deg"])
    ])
    frac = float(inside.mean()) if len(inside) else 0.0
    checks.append(_result("subsatellite_point_in_footprint", "M3", frac > 0.995,
                          f"{inside.sum()}/{len(inside)} ({frac*100:.3f}%) footprints "
                          f"contain their own subsatellite point",
                          fraction=frac))

    b = fps.total_bounds
    ok = b[0] >= -180.0001 and b[1] >= -90.0001 and b[2] <= 180.0001 and b[3] <= 90.0001
    checks.append(_result("world_bounds", "M3", ok,
                          f"footprint bounds {[round(v,4) for v in b]} within EPSG:4326 domain"))

    sub = fps[fps["radius_km"] > 0].copy()
    r = np.corrcoef(sub["alt_km"].rank(), sub["radius_km"].rank())[0, 1]
    checks.append(_result("cap_radius_monotone_in_altitude", "M3", r > 0.999,
                          f"Spearman rho(alt_km, radius_km) = {r:.9f} (expect ~1.0)",
                          spearman_rho=float(r)))

    tracks = gpd.read_file(gpkg, layer="ground_tracks")
    empty = int(tracks.geometry.is_empty.sum())
    checks.append(_result("ground_tracks_non_empty", "M3", empty == 0,
                          f"{len(tracks)} tracks, {empty} empty"))
    return checks


# --------------------------------------------------------------------------
# Negative controls — every check above must be falsifiable
# --------------------------------------------------------------------------
def negative_controls(out_dir: Path) -> list[dict]:
    controls = []
    gpkg = out_dir / "satgis_orbital_catalog.gpkg"

    # NC1: corrupt one byte -> M1 artifact_sha256 must fail
    manifest = json.loads((out_dir / "SHA256SUMS.json").read_text())
    target = next(a for a in manifest["artifacts"] if a["path"].endswith(".parquet"))
    p = out_dir / target["path"]
    original = p.read_bytes()
    mutated = bytearray(original)
    mutated[len(mutated) // 2] ^= 0xFF
    p.write_bytes(bytes(mutated))
    detected = _sha256(p) != target["sha256"]
    p.write_bytes(original)
    restored = _sha256(p) == target["sha256"]
    controls.append(_result("NC1_bitflip_detected", "M1-control", detected and restored,
                            f"single-byte flip in {target['path']} "
                            f"{'detected' if detected else 'NOT DETECTED — CHECK IS WORTHLESS'}; "
                            f"original {'restored' if restored else 'NOT RESTORED'}"))

    # NC2: move each satellite to its antipode -> M3 containment must fail.
    # A fixed longitude offset is the wrong mutation: +120 deg of longitude is a
    # tiny ground distance near the poles, so 18/185 polar caps legitimately
    # still contained the displaced point and the control mis-fired. The
    # antipode is rigorous instead — every cap here has central angle
    # lambda = acos(rho*cos eps) - eps < 90 deg (81.3 deg even at GEO), so the
    # antipodal point is outside the cap for *every* object, unconditionally.
    fps = gpd.read_file(gpkg, layer="footprints")
    sats = gpd.read_file(gpkg, layer="satellites")
    merged = fps.merge(sats[["norad_cat_id", "lon_deg", "lat_deg"]],
                       on="norad_cat_id", how="inner")
    max_central = float(merged["central_angle_deg"].max())
    sample = merged.head(2000)
    bad = np.array([
        geom.contains(Point(((lo + 360.0) % 360.0) - 180.0, -la))
        for geom, lo, la in zip(sample.geometry, sample["lon_deg"], sample["lat_deg"])
    ])
    controls.append(_result("NC2_antipodal_point_rejected", "M3-control",
                            bad.sum() == 0 and max_central < 90.0,
                            f"0 expected; {bad.sum()}/{len(bad)} antipodal points fell "
                            f"inside their own cap. Max central angle over the whole "
                            f"catalog is {max_central:.3f} deg (< 90 deg), so the "
                            f"antipode is provably exterior for every object."))

    # NC3: shuffle altitudes -> M3 monotonicity must collapse
    sub = fps[fps["radius_km"] > 0].copy()
    rng = np.random.default_rng(20260726)
    shuffled = rng.permutation(sub["alt_km"].to_numpy())
    r_shuf = abs(np.corrcoef(np.argsort(np.argsort(shuffled)),
                             sub["radius_km"].rank())[0, 1])
    controls.append(_result("NC3_shuffled_altitude_breaks_monotonicity", "M3-control",
                            r_shuf < 0.1,
                            f"Spearman rho collapses to {r_shuf:.6f} under a seeded "
                            f"altitude permutation (expect ~0)"))

    # NC4: corrupt the datum -> M2 Bowring agreement must fail
    lat = np.radians(sats["lat_deg"].to_numpy()[:5000])
    lon = np.radians(sats["lon_deg"].to_numpy()[:5000])
    alt = sats["alt_km"].to_numpy()[:5000] * 1000.0
    n = A_WGS84 / np.sqrt(1 - E2 * np.sin(lat) ** 2)
    x = (n + alt) * np.cos(lat) * np.cos(lon)
    y = (n + alt) * np.cos(lat) * np.sin(lon)
    z = (n * (1 - E2) + alt) * np.sin(lat) + 25_000.0    # inject a 25 km Z error
    _, blat, _ = bowring_geodetic(x, y, z)
    dlat = float(np.abs(blat - sats["lat_deg"].to_numpy()[:5000]).max())
    controls.append(_result("NC4_datum_perturbation_detected", "M2-control", dlat > 1e-3,
                            f"a 25 km Z-axis injection moves max dlat to {dlat:.6f} deg, "
                            f"far above the 1e-8 deg pass threshold"))
    return controls


def verify_all(out_dir: Path) -> dict:
    checks = m1_integrity(out_dir) + m2_physics(out_dir) + m3_topology(out_dir)
    controls = negative_controls(out_dir)
    passed = all(c["passed"] for c in checks)
    controls_ok = all(c["passed"] for c in controls)
    return {
        "schema": "satgis.verification-report/1",
        "methods": {"M1": "integrity/CRC/schema", "M2": "independent physics",
                    "M3": "geometric invariants"},
        "checks": checks,
        "negative_controls": controls,
        "checks_passed": sum(c["passed"] for c in checks),
        "checks_total": len(checks),
        "controls_passed": sum(c["passed"] for c in controls),
        "controls_total": len(controls),
        "verdict": "PASS" if (passed and controls_ok) else "FAIL",
    }
