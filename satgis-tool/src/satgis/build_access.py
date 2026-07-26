"""Access build: every catalogued satellite against every Spain + LATAM station."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from . import stations as st
from .access import (check_precision, elevation_azimuth, elevation_matrix,
                     pass_statistics, station_frames)
from .build import load_snapshot
from .propagate import build_satrecs, gmst82, jday

MASKS = (0.0, 5.0, 10.0)
FRENCH_GUIANA_BBOX = (-55.0, 2.0, -51.0, 6.0)   # lon_min, lat_min, lon_max, lat_max


def build_station_registry(raw_dir) -> gpd.GeoDataFrame:
    allst = st.load_all(raw_dir)
    gdf = gpd.GeoDataFrame(
        [{"station_id": s.station_id, "name": s.name, "network": s.network,
          "tier": s.tier, "operator": s.operator, "purpose": s.purpose,
          "lat_deg": s.lat_deg, "lon_deg": s.lon_deg, "height_m": s.height_m,
          "height_known": s.height_known, "source_key": s.source_key,
          "evidence_url": s.evidence_url,
          "status": s.extra.get("status"),
          "min_horizon_deg": s.extra.get("min_horizon")} for s in allst],
        geometry=[Point(s.lon_deg, s.lat_deg) for s in allst], crs="EPSG:4326")

    ne = gpd.read_file(raw_dir / "naturalearth.admin0_50m.zip")[
        ["ADMIN", "ISO_A3", "ISO_A3_EH", "geometry"]].copy()
    ne["ISO"] = ne["ISO_A3"].where(ne["ISO_A3"] != "-99", ne["ISO_A3_EH"])

    j = gpd.sjoin(gdf, ne[["ADMIN", "ISO", "geometry"]], how="left", predicate="within")
    j = j.drop(columns=[c for c in j.columns if c.startswith("index_")])

    # Coastal stations can fall just outside a 1:50m polygon. Rescue them by
    # nearest country within 25 km rather than silently dropping them.
    miss = j["ISO"].isna()
    if miss.any():
        near = gpd.sjoin_nearest(
            gdf.loc[miss.values, ["station_id", "geometry"]].to_crs(3857),
            ne[["ADMIN", "ISO", "geometry"]].to_crs(3857),
            how="left", max_distance=25_000, distance_col="dist_m")
        near = near.drop_duplicates("station_id").set_index("station_id")
        for col in ("ADMIN", "ISO"):
            j.loc[miss.values, col] = j.loc[miss.values, "station_id"].map(near[col])
        j["coastal_rescue"] = False
        j.loc[miss.values, "coastal_rescue"] = j.loc[miss.values, "ISO"].notna()
    else:
        j["coastal_rescue"] = False

    # French Guiana is folded into France by Natural Earth; relabel by geometry.
    lo0, la0, lo1, la1 = FRENCH_GUIANA_BBOX
    gf = (j["ISO"] == "FRA") & j["lon_deg"].between(lo0, lo1) & j["lat_deg"].between(la0, la1)
    j.loc[gf, "ISO"] = "GUF"
    j.loc[gf, "ADMIN"] = st.TERRITORIES["GUF"]

    keep = st.REGION_ISO | set(st.TERRITORIES)
    region = j[j["ISO"].isin(keep)].copy()
    region["region_class"] = np.where(region["ISO"] == "ESP", "Spain", "Latin America")
    region = region.rename(columns={"ADMIN": "country", "ISO": "country_iso3"})
    return region.sort_values("station_id").reset_index(drop=True)


def _teme_to_ecef_grid(r: np.ndarray, jd: np.ndarray, fr: np.ndarray) -> np.ndarray:
    """r (nb, T, 3) TEME km -> ECEF km, rotating each time sample by its GMST."""
    th = np.array([gmst82(a + b) for a, b in zip(jd, fr)])
    c, s = np.cos(th)[None, :], np.sin(th)[None, :]
    x, y, z = r[..., 0], r[..., 1], r[..., 2]
    return np.stack([c * x + s * y, -s * x + c * y, z], axis=-1)


def build_access(raw_dir, epoch: datetime, hours: float = 24.0,
                 step_s: float = 60.0, block: int = 100, log=print) -> dict:
    gp, _satcat, _m = load_snapshot(raw_dir)
    sats, kept, rejected = build_satrecs(gp)
    st_gdf = build_station_registry(raw_dir)
    n_st = len(st_gdf)
    log(f"stations in Spain + LATAM: {n_st}")

    frames = station_frames(st_gdf["lat_deg"].to_numpy(),
                            st_gdf["lon_deg"].to_numpy(),
                            st_gdf["height_m"].to_numpy())

    # ---- instantaneous access at the frozen epoch -------------------------
    jd0, fr0 = jday(epoch)
    from sgp4.api import SatrecArray
    e0, r0, _ = SatrecArray(sats).sgp4(np.array([jd0]), np.array([fr0]))
    ok0 = e0[:, 0] == 0
    P0 = _teme_to_ecef_grid(r0[:, :1, :], np.array([jd0]), np.array([fr0]))[:, 0, :]
    prec = check_precision(P0[ok0], frames)
    log(f"float32 GEMM vs float64: max {prec['max_abs_deg']:.2e} deg, "
        f"p99 {prec['p99_abs_deg']:.2e} deg")

    epoch_rows = []
    names = [k["OBJECT_NAME"] for k in kept]
    ids = np.array([int(k["NORAD_CAT_ID"]) for k in kept])
    for si in range(n_st):
        elev, az, rng = elevation_azimuth(P0[ok0], frames, si)
        vis = elev >= MASKS[0]
        if not vis.any():
            continue
        idx = np.nonzero(vis)[0]
        sid = st_gdf["station_id"].iloc[si]
        sub_ids = ids[ok0][idx]
        for k, gi in enumerate(idx):
            epoch_rows.append((int(sub_ids[k]), sid, float(elev[gi]),
                               float(az[gi]), float(rng[gi])))
    epoch_df = pd.DataFrame(epoch_rows, columns=[
        "norad_cat_id", "station_id", "elevation_deg", "azimuth_deg", "slant_range_km"])
    log(f"epoch access pairs (elev >= 0 deg): {len(epoch_df):,}")

    # ---- 24 h access windows ---------------------------------------------
    n_t = int(round(hours * 3600.0 / step_s))
    offs = np.arange(n_t) * (step_s / 86400.0)
    jds = np.full(n_t, jd0)
    frs = fr0 + offs
    log(f"window: {hours} h, {n_t} samples at {step_s:.0f} s, "
        f"{len(sats):,} satellites x {n_st} stations = "
        f"{len(sats)*n_t*n_st/1e9:.1f}G (sat,time,station) triples")

    agg = {m: {"passes": [], "minutes": [], "max_elev": []} for m in MASKS}
    sat_index = []
    t0 = time.monotonic()
    for b0 in range(0, len(sats), block):
        blk = sats[b0:b0 + block]
        e, r, _ = SatrecArray(blk).sgp4(jds, frs)
        P = _teme_to_ecef_grid(r, jds, frs)
        bad = e != 0
        if bad.any():
            P[bad] = np.nan
        nb = len(blk)
        E = elevation_matrix(P.reshape(-1, 3), frames).reshape(nb, n_t, n_st)
        E = np.nan_to_num(E, nan=-90.0)
        stats = pass_statistics(E, MASKS, step_s / 60.0)
        for m in MASKS:
            for k in ("passes", "minutes", "max_elev"):
                agg[m][k].append(stats[m][k])
        sat_index.append(ids[b0:b0 + block])
        del P, E, stats
        if (b0 // block) % 20 == 0:
            done = min(b0 + block, len(sats))
            el = time.monotonic() - t0
            log(f"  {done:>6,}/{len(sats):,} satellites  {el:6.1f}s  "
                f"eta {el/max(done,1)*(len(sats)-done):6.1f}s")
    log(f"window pass complete in {time.monotonic()-t0:.1f}s")

    sat_ids = np.concatenate(sat_index)
    out = {}
    for m in MASKS:
        for k in ("passes", "minutes", "max_elev"):
            out[(m, k)] = np.concatenate(agg[m][k], axis=0)   # (n_sat, n_st)

    has = out[(MASKS[0], "passes")] > 0
    si_idx, sj_idx = np.nonzero(has)
    win = pd.DataFrame({
        "norad_cat_id": sat_ids[si_idx],
        "station_id": st_gdf["station_id"].to_numpy()[sj_idx],
    })
    for m in MASKS:
        tag = f"{int(m)}deg"
        win[f"passes_{tag}"] = out[(m, "passes")][si_idx, sj_idx]
        win[f"minutes_{tag}"] = out[(m, "minutes")][si_idx, sj_idx]
        win[f"max_elev_{tag}"] = out[(m, "max_elev")][si_idx, sj_idx]
    log(f"access-window pairs with >=1 contact in {hours} h: {len(win):,}")

    name_by_id = dict(zip(ids, names))
    for df in (epoch_df, win):
        df.insert(1, "object_name", df["norad_cat_id"].map(name_by_id))

    return {
        "ground_stations": st_gdf,
        "access_epoch": epoch_df,
        "access_windows": win,
        "matrices": out,
        "sat_ids": sat_ids,
        "station_ids": st_gdf["station_id"].to_numpy(),
        "precision": prec,
        "params": {"epoch_utc": epoch.isoformat(timespec="seconds"),
                   "hours": hours, "step_s": step_s, "masks": list(MASKS),
                   "n_satellites": len(sats), "n_stations": n_st,
                   "n_time_samples": n_t, "satrec_rejected": len(rejected)},
    }
