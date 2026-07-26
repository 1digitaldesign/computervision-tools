"""SGP4 propagation and derivation of GIS geometry.

Reference frames, stated explicitly because they are the main correctness risk:

  SGP4 emits position in **TEME** (True Equator, Mean Equinox), not J2000 and
  not ECEF. TEME → PEF is a single rotation about Z by GMST (IAU-82). PEF →
  ITRF additionally requires polar motion (x_p, y_p), which is a sub-metre to
  few-metre effect and is deliberately *not* applied here: the EOP series is an
  extra authority dependency and the residual is far below the accuracy of the
  SGP4 element sets themselves (~1 km at epoch, degrading km/day). This is
  recorded in the build metadata as `polar_motion_applied: false` so the
  omission is auditable rather than hidden.

  Geodetic conversion is delegated to PROJ (EPSG:4978 geocentric → EPSG:4979
  geographic 3D) rather than a hand-rolled Bowring iteration, so the datum
  realisation has one canonical owner.

  Footprints are the classic spherical-Earth visibility cap:
      rho    = Re / (Re + h)
      lambda = arccos(rho * cos(eps)) - eps
  swept as a geodesic circle of great-circle radius Re*lambda about the
  subsatellite point. Spherical cap on an ellipsoidal Earth: sub-km error at
  LEO, acceptable for coverage cartography and recorded as such.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np
from pyproj import Geod, Transformer
from sgp4 import omm
from sgp4.api import Satrec, SatrecArray

WGS84_A = 6378137.0            # semi-major axis, m
TWOPI = 2.0 * math.pi
DEG = 180.0 / math.pi

_ECEF_TO_GEOD = Transformer.from_crs("EPSG:4978", "EPSG:4979", always_xy=True)
_GEOD = Geod(ellps="WGS84")


def gmst82(jd_ut1: float) -> float:
    """Greenwich Mean Sidereal Time (IAU-82), radians in [0, 2pi)."""
    t = (jd_ut1 - 2451545.0) / 36525.0
    sec = (
        -6.2e-6 * t**3
        + 0.093104 * t**2
        + (876600.0 * 3600.0 + 8640184.812866) * t
        + 67310.54841
    )
    theta = math.radians(sec / 240.0) % TWOPI   # 240 s of time == 1 degree
    return theta + TWOPI if theta < 0 else theta


def jday(dt: datetime) -> tuple[float, float]:
    """UTC datetime → (jd, fr) split, matching sgp4's convention."""
    dt = dt.astimezone(timezone.utc)
    y, m, d = dt.year, dt.month, dt.day
    if m <= 2:
        y, m = y - 1, m + 12
    b = 2 - y // 100 + (y // 100) // 4
    jd = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5
    fr = (dt.hour + dt.minute / 60.0 + (dt.second + dt.microsecond / 1e6) / 3600.0) / 24.0
    return jd, fr


def teme_to_ecef(r_teme_km: np.ndarray, jd: float, fr: float) -> np.ndarray:
    """Rotate TEME → ECEF (PEF) about Z by GMST. Input/output shape (..., 3), km."""
    th = gmst82(jd + fr)
    c, s = math.cos(th), math.sin(th)
    x, y, z = r_teme_km[..., 0], r_teme_km[..., 1], r_teme_km[..., 2]
    return np.stack([c * x + s * y, -s * x + c * y, z], axis=-1)


def ecef_to_geodetic(r_ecef_km: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """ECEF km → (lon_deg, lat_deg, alt_m) on WGS84 via PROJ."""
    m = np.asarray(r_ecef_km, dtype=float) * 1000.0
    lon, lat, alt = _ECEF_TO_GEOD.transform(m[..., 0], m[..., 1], m[..., 2])
    return np.asarray(lon), np.asarray(lat), np.asarray(alt)


def build_satrecs(records: list[dict]) -> tuple[list[Satrec], list[dict], list[dict]]:
    """OMM dicts → Satrec objects. Records that fail to initialise are reported."""
    sats, kept, rejected = [], [], []
    for rec in records:
        try:
            sat = Satrec()
            omm.initialize(sat, rec)
            if sat.error != 0:
                raise ValueError(f"sgp4 init error code {sat.error}")
            sats.append(sat)
            kept.append(rec)
        except Exception as exc:  # noqa: BLE001 — surfaced in build metadata
            rejected.append({
                "norad_cat_id": rec.get("NORAD_CAT_ID"),
                "object_name": rec.get("OBJECT_NAME"),
                "error": f"{type(exc).__name__}: {exc}",
            })
    return sats, kept, rejected


def propagate_epoch(sats: list[Satrec], when: datetime) -> dict:
    """Propagate every satellite to a single frozen epoch (vectorised)."""
    jd, fr = jday(when)
    arr = SatrecArray(sats)
    e, r, v = arr.sgp4(np.array([jd]), np.array([fr]))
    e, r, v = e[:, 0], r[:, 0, :], v[:, 0, :]
    ecef = teme_to_ecef(r, jd, fr)
    lon, lat, alt = ecef_to_geodetic(ecef)
    speed = np.linalg.norm(v, axis=-1)
    return {
        "jd": jd, "fr": fr, "error": e,
        "lon": lon, "lat": lat, "alt_m": alt,
        "speed_km_s": speed,
        "r_teme_km": r, "v_teme_km_s": v,
    }


def orbit_class(apogee_km: float, perigee_km: float, ecc: float, incl_deg: float) -> str:
    if not math.isfinite(apogee_km) or not math.isfinite(perigee_km):
        return "unknown"
    if ecc >= 0.25 and apogee_km > 25000:
        return "HEO"
    if perigee_km < 2000 and apogee_km < 2000:
        return "LEO"
    if 35586 <= perigee_km <= 35986 and 35586 <= apogee_km <= 35986 and incl_deg < 25:
        return "GEO"
    if apogee_km >= 2000 and perigee_km < 35586:
        return "MEO"
    return "HEO" if apogee_km > 35986 else "MEO"


def footprint_ring(lon0: float, lat0: float, alt_m: float,
                   elev_mask_deg: float = 0.0, n: int = 72) -> tuple[list, float, float]:
    """Geodesic visibility cap → ring vertices, central angle (deg), radius (km).

    Returns lon/lat vertex pairs with longitudes *unwrapped* (may exceed ±180);
    the caller stitches them into valid EPSG:4326 geometry.
    """
    eps = math.radians(elev_mask_deg)
    rho = WGS84_A / (WGS84_A + max(alt_m, 1.0))
    arg = min(1.0, max(-1.0, rho * math.cos(eps)))
    lam = math.acos(arg) - eps
    if lam <= 0:
        return [], 0.0, 0.0
    radius_m = WGS84_A * lam
    az = np.linspace(0.0, 360.0, n, endpoint=False)
    lons, lats, _ = _GEOD.fwd(
        np.full(n, lon0), np.full(n, lat0), az, np.full(n, radius_m)
    )
    return list(zip(lons.tolist(), lats.tolist())), lam * DEG, radius_m / 1000.0


def teme_to_ecef_series(r_km: np.ndarray, jd: np.ndarray, fr: np.ndarray) -> np.ndarray:
    """Vectorised TEME → ECEF with a per-sample GMST. r_km shape (n, 3)."""
    th = np.array([gmst82(a + b) for a, b in zip(jd, fr)])
    c, s = np.cos(th), np.sin(th)
    x, y, z = r_km[:, 0], r_km[:, 1], r_km[:, 2]
    return np.stack([c * x + s * y, -s * x + c * y, z], axis=-1)


def ground_track(sat: Satrec, when: datetime, n: int = 60) -> tuple[list, float]:
    """One full revolution of subsatellite points, unwrapped longitudes."""
    period_min = TWOPI / sat.no_kozai if sat.no_kozai > 0 else 0.0  # minutes
    if not math.isfinite(period_min) or period_min <= 0:
        return [], 0.0
    period_min = min(period_min, 3.0 * 1440.0)   # cap pathological elements at 3 days
    jd0, fr0 = jday(when)
    frs = fr0 + np.linspace(0.0, period_min, n) / 1440.0
    jds = np.full(n, jd0)
    e, r, _ = SatrecArray([sat]).sgp4(jds, frs)
    e, r = e[0], r[0]
    ok = e == 0
    if ok.sum() < 2:
        return [], period_min
    ecef = teme_to_ecef_series(r[ok], jds[ok], frs[ok])
    lon, lat, _ = ecef_to_geodetic(ecef)
    return list(zip(np.asarray(lon).tolist(), np.asarray(lat).tolist())), period_min
