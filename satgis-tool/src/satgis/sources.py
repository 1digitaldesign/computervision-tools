"""Canonical source registry for the satgis orbital→GIS compilation.

One canonical owner for every external datum. Nothing else in the codebase may
hard-code a URL. Each entry carries the authority, license, and retrieval
contract required by the evidence gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

CELESTRAK = "https://celestrak.org"


@dataclass(frozen=True)
class Source:
    key: str
    url: str
    kind: str            # "csv" | "json"
    authority: str       # who is materially responsible for the datum
    license: str
    description: str
    group: str | None = None


# --- Satellite catalog (identity, ownership, launch, orbital status) ---------
SATCAT = Source(
    key="celestrak.satcat",
    url=f"{CELESTRAK}/pub/satcat.csv",
    kind="csv",
    authority="CelesTrak (T.S. Kelso), redistributing USSF 18th/19th SDS catalog data",
    license="US Government work (uncopyrightable, 17 U.S.C. §105) as redistributed by CelesTrak",
    description="Full SATCAT: NORAD ID, COSPAR ID, object type, owner code, launch/decay dates, orbital regime.",
)

# --- General Perturbations element sets (orbital state) ----------------------
# GROUP=active is the superset actually propagated. The remaining groups are
# pulled for *independent corroboration* of agency attribution: a satellite is
# attributed to NOAA/NASA/USGS only when the .gov roster and CelesTrak group
# membership agree.
GP_GROUPS: tuple[str, ...] = (
    "active",       # superset — every tracked object with a current element set
    "weather",      # meteorological (carries NOAA-20/21 + Suomi NPP; the former
                    #   CelesTrak GROUP=noaa was retired upstream after the
                    #   NOAA-15/18/19 POES fleet was decommissioned — probing it
                    #   returns: 'Invalid query ... (GROUP=noaa not found)')
    "goes",         # NOAA GOES geostationary
    "resource",     # Earth resources — includes Landsat (USGS)
    "sarsat",       # search & rescue payloads (NOAA-hosted)
    "dmc",          # disaster monitoring
    "tdrss",        # NASA Tracking & Data Relay
    "argos",        # Argos data collection (NOAA-hosted)
    "science",      # space & earth science
    "geodetic",     # geodetic
    "engineering",  # engineering
    "education",    # education
    "stations",     # crewed / space stations
    "planet",       # Planet Labs
    "spire",        # Spire Global
)


def gp_source(group: str) -> Source:
    return Source(
        key=f"celestrak.gp.{group}",
        url=f"{CELESTRAK}/NORAD/elements/gp.php?GROUP={group}&FORMAT=json",
        kind="json",
        authority="CelesTrak (T.S. Kelso), redistributing USSF 18th/19th SDS orbital data",
        license="US Government work (uncopyrightable, 17 U.S.C. §105) as redistributed by CelesTrak",
        description=f"OMM/GP element sets for CelesTrak group '{group}'.",
        group=group,
    )


def all_sources() -> list[Source]:
    return [SATCAT] + [gp_source(g) for g in GP_GROUPS]
