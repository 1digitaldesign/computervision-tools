"""Ground-station registry for the Spain + Latin America region.

Three tiers, deliberately ordered by how strong the provenance is:

  T1 SPICE frame kernels — ESA ESTRACK (`estrack_v03.tf`) and NASA/NAIF DSN
     (`earth_topo_*.tf`). These are the operators' own machine-readable
     geodesy, published for spacecraft navigation. Station position is encoded
     in the topocentric frame definition as
         TKFRAME_<f>_ANGLES = ( -longitude, -colatitude, 180 )
     so latitude = 90 + angle2 and longitude = -angle1. Parsed, not scraped.

  T2 SatNOGS Network API — the open ground-station registry. Operator-reported
     coordinates for community and university stations.

  T3 Curated institutional stations — only entries whose coordinates were
     verified against a citable source at build time. Nothing is asserted from
     memory; an unverifiable station is omitted rather than guessed.

Country is assigned by point-in-polygon against Natural Earth Admin-0 rather
than by trusting any name field, so the regional filter is geometric.

Station altitude: the SPICE FKs carry only the topocentric *orientation*; the
height sits in the companion SPK. Heights are therefore 0 for T1 stations. The
effect on access geometry is bounded and small — a 1 km height error perturbs
the elevation angle to a 500 km LEO target by well under 0.2 deg — and is
recorded per station in `height_known` so it is auditable, not hidden.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Spain + the twenty Latin American states, by ISO 3166-1 alpha-3.
# Haiti is included (francophone Latin America). Non-sovereign territories are
# excluded from the sovereign list and handled separately below.
SPAIN = ("ESP",)
LATAM = (
    "ARG", "BOL", "BRA", "CHL", "COL", "CRI", "CUB", "DOM", "ECU", "SLV",
    "GTM", "HTI", "HND", "MEX", "NIC", "PAN", "PRY", "PER", "URY", "VEN",
)
# Latin-American territory that is not an independent state but is squarely in
# the region operationally: French Guiana hosts Europe's Spaceport and the ESA
# Kourou station. Natural Earth folds it into France, so it is matched by
# geometry and relabelled.
TERRITORIES = {"GUF": "French Guiana (FRA)"}

REGION_ISO = set(SPAIN) | set(LATAM)


@dataclass
class Station:
    station_id: str
    name: str
    lat_deg: float
    lon_deg: float
    height_m: float
    height_known: bool
    operator: str
    network: str
    tier: str
    purpose: str
    source_key: str
    evidence_url: str
    country_iso3: str = ""
    country: str = ""
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# T1 — SPICE topocentric frame kernels
# --------------------------------------------------------------------------
_ANGLES_NAMED = re.compile(
    r"TKFRAME_(\w+?)_TOPO_ANGLES\s*=\s*\(\s*([-\d.Ee+]+)\s*,\s*([-\d.Ee+]+)\s*,\s*([-\d.Ee+]+)\s*\)",
    re.S,
)
_FRAME_ID = re.compile(r"FRAME_([A-Za-z0-9_\-]+?)_TOPO\s*=\s*(\d+)")
_ANGLES_ID = re.compile(
    r"TKFRAME_(\d+)_ANGLES\s*=\s*\(\s*([-\d.Ee+]+)\s*,\s*([-\d.Ee+]+)\s*,\s*([-\d.Ee+]+)\s*\)",
    re.S,
)


def _wrap180(lon: float) -> float:
    return ((lon + 180.0) % 360.0) - 180.0


def _from_angles(a1: float, a2: float) -> tuple[float, float]:
    """SPICE topocentric ANGLES = (-lon, -colat, 180) -> (lat, lon)."""
    return 90.0 + a2, _wrap180(-a1)


def parse_estrack(path: Path) -> list[Station]:
    txt = path.read_text(errors="replace")
    out = []
    for m in _ANGLES_NAMED.finditer(txt):
        name = m.group(1)
        lat, lon = _from_angles(float(m.group(2)), float(m.group(3)))
        out.append(Station(
            station_id=f"ESTRACK:{name}",
            name=name.replace("_", " ").title(),
            lat_deg=lat, lon_deg=lon, height_m=0.0, height_known=False,
            operator="ESA", network="ESTRACK", tier="T1-spice",
            purpose="deep space / LEO tracking",
            source_key="esa.estrack_v03.tf",
            evidence_url="https://spiftp.esac.esa.int/data/SPICE/JUICE/kernels/fk/estrack_v03.tf",
        ))
    return out


def parse_naif_dsn(path: Path) -> list[Station]:
    txt = path.read_text(errors="replace")
    id_to_name = {mid: nm for nm, mid in _FRAME_ID.findall(txt)}
    out = []
    for m in _ANGLES_ID.finditer(txt):
        fid = m.group(1)
        name = id_to_name.get(fid)
        if not name:
            continue
        lat, lon = _from_angles(float(m.group(2)), float(m.group(3)))
        out.append(Station(
            station_id=f"DSN:{name}",
            name=name,
            lat_deg=lat, lon_deg=lon, height_m=0.0, height_known=False,
            operator="NASA JPL", network="Deep Space Network", tier="T1-spice",
            purpose="deep space tracking",
            source_key=path.name,
            evidence_url=("https://naif.jpl.nasa.gov/pub/naif/generic_kernels/"
                          f"fk/stations/{path.name.split('nasa.naif.')[-1]}"),
        ))
    return out


# --------------------------------------------------------------------------
# T2 — SatNOGS open network
# --------------------------------------------------------------------------
def parse_satnogs(path: Path) -> list[Station]:
    data = json.loads(path.read_text())
    out = []
    for r in data:
        lat, lon = r.get("lat"), r.get("lng")
        if lat is None or lon is None:
            continue
        alt = r.get("altitude")
        out.append(Station(
            station_id=f"SATNOGS:{r['id']}",
            name=str(r.get("name") or f"station {r['id']}"),
            lat_deg=float(lat), lon_deg=_wrap180(float(lon)),
            height_m=float(alt) if alt is not None else 0.0,
            height_known=alt is not None,
            operator=str(r.get("owner") or "unknown"),
            network="SatNOGS", tier="T2-open-registry",
            purpose="VHF/UHF/S-band reception",
            source_key="satnogs.stations.json",
            evidence_url=f"https://network.satnogs.org/stations/{r['id']}/",
            extra={"status": r.get("status"),
                   "min_horizon_deg": r.get("min_horizon"),
                   "observations": r.get("observations")},
        ))
    return out


def load_all(raw_dir: Path) -> list[Station]:
    stations: list[Station] = []
    est = raw_dir / "esa.estrack_v03.tf"
    if est.exists():
        stations += parse_estrack(est)
    for naif in sorted(raw_dir.glob("nasa.naif.*.tf")):
        stations += parse_naif_dsn(naif)
    sn = raw_dir / "satnogs.stations.json"
    if sn.exists():
        stations += parse_satnogs(sn)
    return stations
