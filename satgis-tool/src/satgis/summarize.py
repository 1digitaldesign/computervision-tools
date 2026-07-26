"""Aggregate the access matrices into the two tables people actually read."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

PRIMARY_MASK = 5.0     # operational default; 0 and 10 also carried


def station_summary(res: dict, sats: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    st = res["ground_stations"].copy()
    m = PRIMARY_MASK
    passes = res["matrices"][(m, "passes")]           # (n_sat, n_st)
    minutes = res["matrices"][(m, "minutes")]
    max_elev = res["matrices"][(m, "max_elev")]
    sat_ids = res["sat_ids"]

    cls = sats.set_index("norad_cat_id")["orbit_class"].reindex(sat_ids).to_numpy()
    agency = sats.set_index("norad_cat_id")["agency_lead"].reindex(sat_ids).to_numpy()
    name = sats.set_index("norad_cat_id")["object_name"].reindex(sat_ids).to_numpy()

    contact = passes > 0
    st["sats_with_contact_24h"] = contact.sum(axis=0)
    st["total_passes_24h"] = passes.sum(axis=0)
    st["total_access_minutes_24h"] = np.round(minutes.sum(axis=0), 1)
    with np.errstate(invalid="ignore"):
        st["median_max_elev_deg"] = np.round(np.nanmedian(
            np.where(contact, max_elev, np.nan), axis=0), 2)
        st["mean_pass_minutes"] = np.round(
            np.divide(minutes.sum(axis=0), passes.sum(axis=0),
                      out=np.zeros(passes.shape[1]), where=passes.sum(axis=0) > 0), 2)

    for oc in ("LEO", "MEO", "GEO", "HEO"):
        sel = cls == oc
        st[f"sats_{oc.lower()}"] = contact[sel].sum(axis=0) if sel.any() else 0
    for ag in ("NASA", "NOAA", "USGS"):
        sel = agency == ag
        st[f"sats_{ag.lower()}"] = contact[sel].sum(axis=0) if sel.any() else 0

    best = np.argmax(minutes, axis=0)
    st["top_satellite"] = name[best]
    st["top_satellite_minutes"] = np.round(minutes[best, np.arange(minutes.shape[1])], 1)

    ep = res["access_epoch"].groupby("station_id").size()
    st["sats_visible_at_epoch"] = st["station_id"].map(ep).fillna(0).astype(int)
    st["elevation_mask_deg"] = m
    return st


def satellite_summary(res: dict, sats: gpd.GeoDataFrame) -> pd.DataFrame:
    m = PRIMARY_MASK
    passes = res["matrices"][(m, "passes")]
    minutes = res["matrices"][(m, "minutes")]
    max_elev = res["matrices"][(m, "max_elev")]
    sat_ids = res["sat_ids"]
    station_ids = res["station_ids"]

    contact = passes > 0
    best = np.argmax(minutes, axis=1)
    meta = sats.set_index("norad_cat_id").reindex(sat_ids)

    with np.errstate(invalid="ignore"):
        peak = np.nanmax(np.where(contact, max_elev, np.nan), axis=1)

    df = pd.DataFrame({
        "norad_cat_id": sat_ids,
        "object_name": meta["object_name"].to_numpy(),
        "orbit_class": meta["orbit_class"].to_numpy(),
        "agency_lead": meta["agency_lead"].to_numpy(),
        "program": meta["program"].to_numpy(),
        "alt_km": np.round(meta["alt_km"].to_numpy(), 1),
        "inclination_deg": np.round(meta["inclination_deg"].to_numpy(), 3),
        "stations_with_contact_24h": contact.sum(axis=1),
        "total_passes_24h": passes.sum(axis=1),
        "total_access_minutes_24h": np.round(minutes.sum(axis=1), 1),
        "peak_elevation_deg": np.round(peak, 2),
        "top_station_id": station_ids[best],
        "top_station_minutes": np.round(minutes[np.arange(minutes.shape[0]), best], 1),
        "elevation_mask_deg": m,
    })
    return df.sort_values("norad_cat_id").reset_index(drop=True)


def regional_rollup(st_sum: gpd.GeoDataFrame, sat_sum: pd.DataFrame,
                    res: dict) -> dict:
    by_country = (st_sum.groupby(["region_class", "country"])
                  .agg(stations=("station_id", "count"),
                       sats_with_contact=("sats_with_contact_24h", "max"),
                       total_passes=("total_passes_24h", "sum"),
                       total_minutes=("total_access_minutes_24h", "sum"))
                  .reset_index().sort_values("total_passes", ascending=False))
    no_contact = int((sat_sum["stations_with_contact_24h"] == 0).sum())
    return {
        "elevation_mask_deg": PRIMARY_MASK,
        "stations": int(len(st_sum)),
        "countries": int(st_sum["country"].nunique()),
        "satellites_total": int(len(sat_sum)),
        "satellites_with_any_contact": int((sat_sum["stations_with_contact_24h"] > 0).sum()),
        "satellites_never_visible": no_contact,
        "total_contact_events_24h": int(sat_sum["total_passes_24h"].sum()),
        "total_access_hours_24h": round(float(sat_sum["total_access_minutes_24h"].sum()) / 60.0, 1),
        "by_country": by_country.to_dict("records"),
        "by_orbit_class": (sat_sum[sat_sum["stations_with_contact_24h"] > 0]
                           .groupby("orbit_class")
                           .agg(satellites=("norad_cat_id", "count"),
                                passes=("total_passes_24h", "sum"))
                           .reset_index().to_dict("records")),
    }
