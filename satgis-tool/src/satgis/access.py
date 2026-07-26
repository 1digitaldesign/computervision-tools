"""Satellite-to-ground-station access geometry.

Topocentric ENU about each station:

    e = (-sin L,           cos L,          0     )
    n = (-sin B cos L,    -sin B sin L,    cos B )
    u = ( cos B cos L,     cos B sin L,    sin B )

    d         = r_sat - r_station          (ECEF, km)
    elevation = asin( (d . u) / |d| )
    azimuth   = atan2( d . e, d . n )

Why this is written as a matrix product rather than a loop
----------------------------------------------------------
A 24 h window over the whole catalog is 16,241 satellites x 1,440 one-minute
samples = 23.4 M positions. Evaluated naively against 458 stations that is
10.7 G (satellite, time, station) triples, and the cost is dominated by
re-reading the 561 MB position array once per station — roughly 257 GB of
memory traffic, tens of minutes.

Expanding the dot products removes the per-station pass over the data:

    d . u = P . u - (S . u)      <- second term is a scalar per station
    |d|^2 = |P|^2 - 2 (P . S) + |S|^2

so every station reduces to two projections of P onto a fixed 3-vector. Stack
the stations and both become a single GEMM, P (N,3) @ M.T (3,n_st), which BLAS
runs at full width on Apple silicon. Blocks are reduced to pass statistics
immediately so the (N, n_st) intermediate is never materialised whole.

Precision: the GEMM runs in float32 (a ~0.7 m position quantum at LEO radii,
far below the SGP4 element-set error). `check_precision` re-runs a sample in
float64 so the choice is measured rather than assumed.
"""
from __future__ import annotations

import numpy as np
from pyproj import Transformer

_GEOD_TO_ECEF = Transformer.from_crs("EPSG:4979", "EPSG:4978", always_xy=True)

DEG = 180.0 / np.pi


def station_frames(lat_deg: np.ndarray, lon_deg: np.ndarray,
                   height_m: np.ndarray) -> dict:
    """Station ECEF position (km) and ENU basis vectors."""
    x, y, z = _GEOD_TO_ECEF.transform(lon_deg, lat_deg, height_m)
    S = np.stack([x, y, z], axis=-1) / 1000.0            # km
    B = np.radians(lat_deg)
    L = np.radians(lon_deg)
    e = np.stack([-np.sin(L), np.cos(L), np.zeros_like(L)], axis=-1)
    n = np.stack([-np.sin(B) * np.cos(L), -np.sin(B) * np.sin(L), np.cos(B)], axis=-1)
    u = np.stack([np.cos(B) * np.cos(L), np.cos(B) * np.sin(L), np.sin(B)], axis=-1)
    return {"S": S, "e": e, "n": n, "u": u,
            "Su": np.einsum("ij,ij->i", S, u),
            "S2": np.einsum("ij,ij->i", S, S)}


def elevation_azimuth(P: np.ndarray, fr: dict, idx: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Full-precision elevation/azimuth/range of positions P (…,3) km from one station."""
    d = P - fr["S"][idx]
    rng = np.linalg.norm(d, axis=-1)
    up = d @ fr["u"][idx]
    east = d @ fr["e"][idx]
    north = d @ fr["n"][idx]
    with np.errstate(invalid="ignore", divide="ignore"):
        elev = np.degrees(np.arcsin(np.clip(up / rng, -1.0, 1.0)))
    az = np.degrees(np.arctan2(east, north)) % 360.0
    return elev, az, rng


def elevation_matrix(P: np.ndarray, fr: dict, dtype=np.float32) -> np.ndarray:
    """Elevation (deg) of every position in P (N,3) from every station -> (N, n_st)."""
    Pf = np.ascontiguousarray(P, dtype=dtype)
    U = np.ascontiguousarray(fr["u"].T, dtype=dtype)      # (3, n_st)
    S = np.ascontiguousarray(fr["S"].T, dtype=dtype)      # (3, n_st)
    up = Pf @ U                                            # (N, n_st)
    up -= fr["Su"].astype(dtype)
    ps = Pf @ S                                            # (N, n_st)
    p2 = np.einsum("ij,ij->i", Pf, Pf)[:, None]
    rng2 = p2 - 2.0 * ps + fr["S2"].astype(dtype)
    np.maximum(rng2, dtype(1e-9), out=rng2)
    np.sqrt(rng2, out=rng2)
    ratio = np.clip(up / rng2, dtype(-1.0), dtype(1.0))
    return np.degrees(np.arcsin(ratio))


def check_precision(P: np.ndarray, fr: dict, n: int = 20000, seed: int = 20260726) -> dict:
    """Measure the float32 GEMM against a float64 reference on a random sample."""
    rng = np.random.default_rng(seed)
    take = rng.choice(len(P), size=min(n, len(P)), replace=False)
    sub = P[take]
    e32 = elevation_matrix(sub, fr, dtype=np.float32)
    e64 = elevation_matrix(sub, fr, dtype=np.float64)
    d = np.abs(e32.astype(np.float64) - e64)
    return {"samples": int(sub.size // 3), "pairs": int(e32.size),
            "max_abs_deg": float(d.max()), "p99_abs_deg": float(np.percentile(d, 99)),
            "mean_abs_deg": float(d.mean())}


def pass_statistics(elev: np.ndarray, masks: tuple[float, ...],
                    step_minutes: float) -> dict:
    """Reduce an (n_sat, n_time, n_station) elevation block to per-mask statistics.

    A "pass" is a maximal run of consecutive samples at or above the mask, so
    the count is the number of rising edges — which is what an operator means
    by a contact opportunity, not the number of samples.
    """
    out = {}
    for mask in masks:
        vis = elev >= mask
        # rising edges along the time axis, with the first sample counted if
        # already visible (a pass in progress at window start).
        prev = np.concatenate(
            [np.zeros_like(vis[:, :1, :]), vis[:, :-1, :]], axis=1)
        starts = vis & ~prev
        out[mask] = {
            "passes": starts.sum(axis=1).astype(np.int32),                  # (n_sat, n_st)
            "minutes": vis.sum(axis=1).astype(np.float32) * step_minutes,
            "max_elev": np.where(vis.any(axis=1), elev.max(axis=1), np.nan).astype(np.float32),
        }
    return out
