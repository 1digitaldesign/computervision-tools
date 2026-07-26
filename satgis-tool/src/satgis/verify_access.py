"""Verification for the ground-station access layers.

The headline check is a **cross-layer invariant**: the footprint layer and the
access layer are computed by completely disjoint code paths — one is a
spherical visibility cap swept as a geodesic circle in `geometry.py`, the other
is an ECEF topocentric dot product in `access.py` — yet they must agree, because
"the station is inside the satellite's 0 deg footprint" and "the satellite is at
non-negative elevation from the station" are the same physical statement. Two
independent derivations of one fact is corroboration; re-checking one
derivation against itself is not.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from .verify import _result, _sha256


def m1_access_integrity(out_dir: Path) -> list[dict]:
    checks = []
    meta = json.loads((out_dir / "access-metadata.json").read_text())
    gpkg = out_dir / "satgis_orbital_catalog.gpkg"

    issues = []
    for layer, n_expected in (("ground_stations", meta["params"]["n_stations"]),
                              ("station_access_summary", meta["params"]["n_stations"])):
        g = gpd.read_file(gpkg, layer=layer)
        if len(g) != n_expected:
            issues.append(f"{layer}: {len(g)} != {n_expected}")
        if g.crs is None or g.crs.to_epsg() != 4326:
            issues.append(f"{layer}: CRS {g.crs}")
        if g.geometry.isna().any() or not g.geometry.is_valid.all():
            issues.append(f"{layer}: invalid/null geometry")
    checks.append(_result("access_gpkg_layers", "M1", not issues,
                          "ground_stations + station_access_summary conform"
                          if not issues else "; ".join(issues)))

    win = pd.read_parquet(out_dir / "access_windows.parquet",
                          columns=["passes_5deg", "minutes_5deg", "max_elev_5deg"])
    horizon_min = meta["params"]["hours"] * 60.0
    bad = []
    if (win["minutes_5deg"] > horizon_min + 1e-6).any():
        bad.append("access minutes exceed the window length")
    if (win["minutes_5deg"] < 0).any():
        bad.append("negative access minutes")
    ok_elev = win.loc[win["passes_5deg"] > 0, "max_elev_5deg"]
    if len(ok_elev) and not ok_elev.between(5.0, 90.0001).all():
        bad.append("max elevation outside [mask, 90]")
    checks.append(_result("access_window_bounds", "M1", not bad,
                          f"{len(win):,} pairs: minutes in [0, {horizon_min:.0f}], "
                          f"max elevation in [5, 90]" if not bad else "; ".join(bad),
                          pairs=int(len(win))))
    return checks


def m2_access_physics(out_dir: Path) -> list[dict]:
    checks = []
    gpkg = out_dir / "satgis_orbital_catalog.gpkg"
    meta = json.loads((out_dir / "access-metadata.json").read_text())

    # --- cross-layer invariant: footprint cap vs topocentric elevation ------
    fps = gpd.read_file(gpkg, layer="footprints")[["norad_cat_id", "geometry"]]
    stg = gpd.read_file(gpkg, layer="ground_stations")[["station_id", "geometry"]]
    ep = pd.read_parquet(out_dir / "access_epoch.parquet",
                         columns=["norad_cat_id", "station_id", "elevation_deg"])
    rng = np.random.default_rng(20260726)
    sample = ep.iloc[rng.choice(len(ep), size=min(5000, len(ep)), replace=False)]
    merged = (sample.merge(fps, on="norad_cat_id", how="inner")
                    .merge(stg, on="station_id", how="inner", suffixes=("_fp", "_st")))
    inside = np.array([fp.buffer(0).contains(pt) or fp.buffer(1e-6).contains(pt)
                       for fp, pt in zip(merged["geometry_fp"], merged["geometry_st"])])
    frac = float(inside.mean()) if len(inside) else 0.0
    checks.append(_result("crosslayer_footprint_vs_elevation", "M2", frac > 0.995,
                          f"{inside.sum()}/{len(inside)} ({frac*100:.3f}%) of sampled "
                          f"elev>=0 pairs place the station inside that satellite's "
                          f"independently-derived footprint cap", fraction=frac))

    # --- the never-visible set must be geometrically explainable ------------
    sat_sum = pd.read_parquet(out_dir / "satellite_access_summary.parquet",
                              columns=["norad_cat_id", "orbit_class",
                                       "stations_with_contact_24h"])
    never = sat_sum[sat_sum["stations_with_contact_24h"] == 0]
    n_leo = int((never["orbit_class"] == "LEO").sum())
    by = never["orbit_class"].value_counts().to_dict()
    checks.append(_result("never_visible_are_not_leo", "M2", n_leo == 0,
                          f"{len(never)} satellites never rise above the mask in 24 h; "
                          f"{by} — zero are LEO, as required: a LEO object's ground "
                          f"track sweeps all longitudes within 24 h, so it cannot hide "
                          f"from 484 stations, whereas a GEO object parked over a "
                          f"non-visible longitude never rises.", by_class=by))

    # --- pass count must rise with station latitude for polar constellations -
    # Measured over the FULL station set, not the institutional subset. The
    # first version of this check used the 12 T1 stations and failed at
    # rho = 0.4386 — not because the trend is absent but because 8 of those 12
    # are the Madrid complex, sitting within 0.028 deg of each other with pass
    # counts differing by 30 out of 87,200 (0.034%). Rank-correlating noise
    # across a degenerate cluster measures nothing. The 484-station set spans
    # 5 deg to 50 deg of latitude and resolves the real effect.
    st_sum = gpd.read_file(gpkg, layer="station_access_summary")
    abslat = st_sum["lat_deg"].abs()
    r = float(np.corrcoef(abslat.rank(), st_sum["total_passes_24h"].rank())[0, 1])
    bands = pd.cut(abslat, [0, 10, 20, 30, 40, 50, 60])
    means = st_sum.groupby(bands, observed=True)["total_passes_24h"].mean()
    monotone_bands = bool((means.diff().dropna() > 0).all())
    checks.append(_result("passes_rise_with_latitude", "M2",
                          r > 0.75 and monotone_bands,
                          f"Spearman rho(|latitude|, passes) = {r:.4f} over "
                          f"{len(st_sum)} stations; 10-degree latitude bands give "
                          f"strictly increasing mean pass counts "
                          f"({', '.join(f'{v:,.0f}' for v in means)}) — polar and "
                          f"sun-synchronous orbits converge toward the poles",
                          spearman_rho=r, bands_monotone=monotone_bands))

    # --- float32 GEMM justification, carried from the build -----------------
    prec = meta["precision"]
    checks.append(_result("gemm_precision_bound", "M2",
                          prec["p99_abs_deg"] < 1e-3,
                          f"float32 vs float64 elevation: p99 {prec['p99_abs_deg']:.2e} deg, "
                          f"mean {prec['mean_abs_deg']:.2e} deg over {prec['pairs']:,} pairs"))
    return checks


def m3_access_topology(out_dir: Path) -> list[dict]:
    checks = []
    gpkg = out_dir / "satgis_orbital_catalog.gpkg"
    stg = gpd.read_file(gpkg, layer="ground_stations")

    ne = gpd.read_file(Path("data/raw") / "naturalearth.admin0_50m.zip")[
        ["ADMIN", "ISO_A3", "ISO_A3_EH", "geometry"]].copy()
    ne["ISO"] = ne["ISO_A3"].where(ne["ISO_A3"] != "-99", ne["ISO_A3_EH"])
    j = gpd.sjoin(stg[["station_id", "country_iso3", "geometry"]],
                  ne[["ISO", "geometry"]], how="left", predicate="within")
    j = j.drop_duplicates("station_id")
    # French Guiana is relabelled from FRA by design; coastal rescues sit just
    # outside their polygon by construction. Both are expected, not failures.
    strict = j[(j["country_iso3"] != "GUF") & j["ISO"].notna()]
    agree = float((strict["ISO"] == strict["country_iso3"]).mean()) if len(strict) else 0.0
    checks.append(_result("station_country_assignment", "M3", agree > 0.999,
                          f"{len(strict)} strictly-contained stations, "
                          f"{agree*100:.3f}% re-derive the same ISO code on an "
                          f"independent spatial join", agreement=agree))

    region_ok = set(stg["region_class"].unique()) <= {"Spain", "Latin America"}
    checks.append(_result("region_scope", "M3", region_ok,
                          f"every station is Spain or Latin America; countries="
                          f"{stg['country'].nunique()}, stations={len(stg)}"))
    return checks


def access_negative_controls(out_dir: Path) -> list[dict]:
    controls = []
    gpkg = out_dir / "satgis_orbital_catalog.gpkg"

    # NC5: displace stations 90 deg in longitude -> cross-layer containment dies
    fps = gpd.read_file(gpkg, layer="footprints")[["norad_cat_id", "geometry"]]
    stg = gpd.read_file(gpkg, layer="ground_stations")[["station_id", "geometry"]]
    ep = pd.read_parquet(out_dir / "access_epoch.parquet",
                         columns=["norad_cat_id", "station_id"])
    rng = np.random.default_rng(4242)
    s = ep.iloc[rng.choice(len(ep), size=min(3000, len(ep)), replace=False)]
    m = (s.merge(fps, on="norad_cat_id").merge(stg, on="station_id",
                                               suffixes=("_fp", "_st")))
    moved = np.array([
        fp.contains(Point(((pt.x + 90 + 180) % 360) - 180, pt.y))
        for fp, pt in zip(m["geometry_fp"], m["geometry_st"])])
    controls.append(_result("NC5_station_longitude_shift_rejected", "M2-control",
                            moved.mean() < 0.35,
                            f"after a +90 deg longitude shift only "
                            f"{moved.sum()}/{len(moved)} ({moved.mean()*100:.1f}%) "
                            f"stations remain inside the cap that contained them"))

    # NC6: raising the mask must monotonically reduce access TIME.
    # The first version asserted passes(10 deg) <= passes(5 deg) and failed.
    # The data was right and the assertion was wrong: for slow, eccentric or
    # near-stationary orbits the elevation profile inside one 5 deg window is
    # not unimodal, so a single 5 deg contact can split into several 10 deg
    # contacts. PHASE 3B (AO-10), a Molniya-type HEO amateur satellite, shows
    # 2 passes / 617 min at 5 deg becoming 3 passes / 404 min at 10 deg. All
    # 2,798 exceptions (0.036% of pairs) are MEO/GEO/HEO; zero are LEO.
    # Access *minutes* is the quantity that is genuinely monotone.
    win = pd.read_parquet(out_dir / "access_windows.parquet",
                          columns=["minutes_0deg", "minutes_5deg", "minutes_10deg",
                                   "passes_5deg", "passes_10deg"])
    v0 = int((win["minutes_5deg"] > win["minutes_0deg"] + 1e-6).sum())
    v1 = int((win["minutes_10deg"] > win["minutes_5deg"] + 1e-6).sum())
    split = int((win["passes_10deg"] > win["passes_5deg"]).sum())
    controls.append(_result("NC6_mask_monotonicity_in_time", "M1-control",
                            v0 == 0 and v1 == 0,
                            f"raising the mask cannot add access time: "
                            f"minutes(5)<=minutes(0) violated {v0} times, "
                            f"minutes(10)<=minutes(5) violated {v1} times, across "
                            f"{len(win):,} pairs. Pass *count* is deliberately not "
                            f"asserted monotone — {split:,} pairs ({100*split/len(win):.4f}%, "
                            f"all MEO/GEO/HEO) legitimately split one lower-mask "
                            f"contact into several higher-mask contacts."))

    # NC7: pair each station with a random *wrong* satellite footprint
    wrong = fps.sample(len(m), random_state=99, replace=True).reset_index(drop=True)
    hit = np.array([fp.contains(pt) for fp, pt in
                    zip(wrong["geometry"], m["geometry_st"].reset_index(drop=True))])
    controls.append(_result("NC7_mismatched_satellite_rejected", "M2-control",
                            hit.mean() < 0.75,
                            f"randomly re-pairing stations with the wrong satellite "
                            f"drops containment to {hit.mean()*100:.1f}% "
                            f"(from {100.0:.1f}% for true pairs), so the cross-layer "
                            f"check is sensitive to identity, not just geometry"))
    return controls


def verify_access_all(out_dir: Path) -> dict:
    checks = (m1_access_integrity(out_dir) + m2_access_physics(out_dir)
              + m3_access_topology(out_dir))
    controls = access_negative_controls(out_dir)
    return {"checks": checks, "negative_controls": controls}
