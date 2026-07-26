"""NASA / NOAA / USGS fleet attribution.

Attribution is *derived*, not asserted: each rule is a name pattern resolved
against the frozen catalog snapshot, so every NORAD ID in the crosswalk is
provably present in the data actually propagated. A rule that matches nothing
is a coverage failure, not a silent no-op — see `resolve()`'s `unmatched`.

Roles follow the operating agency, which is not always the building agency
(Landsat 8/9 were built by NASA and are *operated* by USGS; GOES 14/15 were
transferred to USSF as EWS-G3/EWS-G2 and are therefore no longer NOAA).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

NASA, NOAA, USGS, USSF = "NASA", "NOAA", "USGS", "USSF"


@dataclass(frozen=True)
class Rule:
    pattern: str
    agencies: tuple[str, ...]   # operating agencies (order = lead first)
    program: str
    mission_class: str
    evidence: str


# Ordered most-specific → least. First match wins.
RULES: tuple[Rule, ...] = (
    # --- USGS -------------------------------------------------------------
    Rule(r"^LANDSAT 8$", (USGS, NASA), "Landsat", "land imaging",
         "https://www.usgs.gov/landsat-missions/landsat-satellite-missions"),
    Rule(r"^LANDSAT 9$", (USGS, NASA), "Landsat", "land imaging",
         "https://www.usgs.gov/landsat-missions/landsat-satellite-missions"),

    # --- NOAA -------------------------------------------------------------
    Rule(r"^GOES 1[6-9]$", (NOAA,), "GOES-R", "geostationary meteorology",
         "https://www.nesdis.noaa.gov/our-satellites/currently-flying"),
    Rule(r"^NOAA 2[01] \(JPSS-[12]\)$", (NOAA, NASA), "JPSS", "polar meteorology",
         "https://www.nesdis.noaa.gov/our-satellites/currently-flying/joint-polar-satellite-system"),
    Rule(r"^SUOMI NPP$", (NOAA, NASA), "JPSS", "polar meteorology",
         "https://www.nesdis.noaa.gov/our-satellites/currently-flying/joint-polar-satellite-system"),
    Rule(r"^JASON-3$", (NOAA, NASA), "Jason", "ocean altimetry",
         "https://www.nesdis.noaa.gov/our-satellites/currently-flying"),
    Rule(r"^SENTINEL-6[AB]$", (NOAA, NASA), "Sentinel-6", "ocean altimetry",
         "https://www.nesdis.noaa.gov/our-satellites/currently-flying"),
    Rule(r"^DMSP 5D-3 F1[678]\b", (NOAA, USSF), "DMSP", "polar meteorology",
         "https://www.nesdis.noaa.gov/our-satellites/currently-flying"),

    # --- USSF (formerly NOAA GOES — transferred, so explicitly NOT NOAA) ---
    Rule(r"^EWS-G[23]\b", (USSF,), "EWS-G (ex-GOES)", "geostationary meteorology",
         "CelesTrak GROUP=goes object naming; ex-GOES 14/15 transferred to USSF"),

    # --- NASA Earth science ----------------------------------------------
    Rule(r"^TERRA$", (NASA,), "EOS", "earth observation", "https://terra.nasa.gov/"),
    Rule(r"^AQUA$", (NASA,), "EOS", "earth observation", "https://aqua.nasa.gov/"),
    Rule(r"^AURA$", (NASA,), "EOS", "atmospheric chemistry", "https://aura.gsfc.nasa.gov/"),
    Rule(r"^ICESAT-2$", (NASA,), "ICESat-2", "laser altimetry", "https://icesat-2.gsfc.nasa.gov/"),
    Rule(r"^SMAP$", (NASA,), "SMAP", "soil moisture radar", "https://smap.jpl.nasa.gov/"),
    Rule(r"^GPM-CORE$", (NASA,), "GPM", "precipitation radar", "https://gpm.nasa.gov/"),
    Rule(r"^OCO ?2$", (NASA,), "OCO", "carbon spectrometry", "https://ocov2.jpl.nasa.gov/"),
    Rule(r"^PACE$", (NASA,), "PACE", "ocean colour / aerosol", "https://pace.gsfc.nasa.gov/"),
    Rule(r"^SWOT$", (NASA,), "SWOT", "surface water altimetry", "https://swot.jpl.nasa.gov/"),
    Rule(r"NISAR", (NASA,), "NISAR", "L/S-band SAR", "https://nisar.jpl.nasa.gov/"),
    Rule(r"^GRACE-FO [12]$", (NASA,), "GRACE-FO", "gravimetry", "https://gracefo.jpl.nasa.gov/"),
    Rule(r"^CYGFM\d+$", (NASA,), "CYGNSS", "GNSS-R wind", "https://www.nasa.gov/cygnss/"),
    Rule(r"^TIMED$", (NASA,), "TIMED", "upper atmosphere", "https://www.nasa.gov/"),
    Rule(r"^SORCE$", (NASA,), "SORCE", "solar irradiance", "https://www.nasa.gov/"),

    # --- NASA heliophysics / astrophysics / infrastructure ----------------
    Rule(r"^MMS [1-4]$", (NASA,), "MMS", "magnetospheric", "https://www.nasa.gov/mission/mms/"),
    Rule(r"^THEMIS [A-E]$", (NASA,), "THEMIS", "magnetospheric", "https://www.nasa.gov/"),
    Rule(r"^HST$", (NASA,), "Hubble", "astrophysics", "https://science.nasa.gov/mission/hubble/"),
    Rule(r"^TDRS \d+$", (NASA,), "TDRSS", "relay communications", "https://www.nasa.gov/"),
    Rule(r"^ISS \((ZARYA|UNITY|ZVEZDA|DESTINY|NAUKA)\)$", (NASA,), "ISS", "crewed platform",
         "https://www.nasa.gov/international-space-station/"),
)

_COMPILED = tuple((re.compile(r.pattern), r) for r in RULES)


def classify(object_name: str) -> Rule | None:
    name = (object_name or "").strip().upper()
    for rx, rule in _COMPILED:
        if rx.search(name):
            return rule
    return None


def resolve(catalog: list[dict]) -> dict:
    """Attach agency attribution to a frozen catalog snapshot.

    Returns the crosswalk plus the set of rules that matched nothing, so a
    silently-empty fleet cannot pass as success.
    """
    crosswalk, matched = [], set()
    for obj in catalog:
        rule = classify(obj["OBJECT_NAME"])
        if rule is None:
            continue
        matched.add(rule.pattern)
        crosswalk.append({
            "norad_cat_id": int(obj["NORAD_CAT_ID"]),
            "object_id": obj.get("OBJECT_ID"),
            "object_name": obj["OBJECT_NAME"],
            "agency_lead": rule.agencies[0],
            "agencies": list(rule.agencies),
            "program": rule.program,
            "mission_class": rule.mission_class,
            "evidence_url": rule.evidence,
        })
    crosswalk.sort(key=lambda r: r["norad_cat_id"])
    unmatched = [r.pattern for r in RULES if r.pattern not in matched]
    by_agency: dict[str, int] = {}
    for row in crosswalk:
        by_agency[row["agency_lead"]] = by_agency.get(row["agency_lead"], 0) + 1
    return {
        "schema": "satgis.agency-crosswalk/1",
        "rules_total": len(RULES),
        "rules_matched": len(matched),
        "rules_unmatched": unmatched,
        "objects_attributed": len(crosswalk),
        "by_agency_lead": dict(sorted(by_agency.items())),
        "crosswalk": crosswalk,
    }
