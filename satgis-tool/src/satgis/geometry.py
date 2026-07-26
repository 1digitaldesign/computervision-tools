"""Stitch unwrapped spherical vertices into valid EPSG:4326 geometry.

Two failure modes kill naive satellite cartography and both are handled here:

  1. **Antimeridian.** A ring or track spanning +180/-180 becomes a horizontal
     smear across the whole map if you just wrap longitudes. Fixed by building
     the geometry in unwrapped space and intersecting against the ±180 window
     and its ±360 translates, yielding a MultiPolygon / MultiLineString.

  2. **Pole enclosure.** A visibility cap containing a pole has no closed
     longitude ordering at all — the ring winds 360deg. Fixed by sorting the
     wrapped vertices by longitude and closing the ring over the pole edge.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

_WORLD = box(-180.0, -90.0, 180.0, 90.0)


def unwrap(lons: list[float]) -> list[float]:
    """Make a longitude sequence continuous (no ±360 jumps between neighbours)."""
    if not lons:
        return []
    out = [float(lons[0])]
    for lon in lons[1:]:
        prev = out[-1]
        d = float(lon) - (prev % 360.0 if False else prev)
        while d > 180.0:
            lon -= 360.0
            d = float(lon) - prev
        while d < -180.0:
            lon += 360.0
            d = float(lon) - prev
        out.append(float(lon))
    return out


def _split_at_antimeridian(geom: BaseGeometry) -> BaseGeometry:
    parts = []
    for shift in (-360.0, 0.0, 360.0):
        moved = _translate(geom, shift)
        if moved.is_empty:
            continue
        clipped = moved.intersection(_WORLD)
        if not clipped.is_empty:
            parts.append(clipped)
    if not parts:
        return geom
    return unary_union(parts)


def _translate(geom: BaseGeometry, dx: float) -> BaseGeometry:
    if dx == 0.0:
        return geom
    from shapely.affinity import translate
    return translate(geom, xoff=dx)


def ring_to_polygon(vertices: list[tuple[float, float]], lat0: float,
                    radius_km: float) -> BaseGeometry | None:
    """Visibility-cap vertices → valid EPSG:4326 Polygon/MultiPolygon."""
    if len(vertices) < 3:
        return None
    lons = unwrap([v[0] for v in vertices])
    lats = [v[1] for v in vertices]

    north_gap_km = (90.0 - lat0) * 111.19492664455873
    south_gap_km = (lat0 + 90.0) * 111.19492664455873
    covers_north = radius_km >= north_gap_km
    covers_south = radius_km >= south_gap_km

    if covers_north and covers_south:
        return _WORLD

    if covers_north or covers_south:
        pole_lat = 90.0 if covers_north else -90.0
        wrapped = sorted(((_wrap180(x), y) for x, y in zip(lons, lats)),
                         key=lambda p: p[0])
        ring = ([(-180.0, wrapped[0][1])] + wrapped + [(180.0, wrapped[-1][1])]
                + [(180.0, pole_lat), (-180.0, pole_lat)])
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly if not poly.is_empty else None

    poly = Polygon(list(zip(lons, lats)))
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return None
    if min(lons) < -180.0 or max(lons) > 180.0:
        poly = _split_at_antimeridian(poly)
    return poly if not poly.is_empty else None


def track_to_line(points: list[tuple[float, float]]) -> BaseGeometry | None:
    """Subsatellite points → LineString/MultiLineString split at the antimeridian."""
    if len(points) < 2:
        return None
    lons = unwrap([p[0] for p in points])
    lats = [p[1] for p in points]
    line = LineString(list(zip(lons, lats)))
    if min(lons) < -180.0 or max(lons) > 180.0:
        line = _split_at_antimeridian(line)
    if line.is_empty:
        return None
    if isinstance(line, (LineString, MultiLineString)):
        return line
    geoms = [g for g in getattr(line, "geoms", []) if isinstance(g, LineString)]
    return MultiLineString(geoms) if geoms else None


def _wrap180(lon: float) -> float:
    return ((float(lon) + 180.0) % 360.0) - 180.0
