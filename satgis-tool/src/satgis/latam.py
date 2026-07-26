"""Latin American imaging history — the full catalogued record, back to first entry.

Scope is the whole SATCAT (70,122 objects, active *and* decayed), not the 16,241
with current element sets, because the question is historical: most of the
region's early imagers re-entered years ago and exist only in the historical
catalog.

Three catalog traps this module handles explicitly, each of which silently
corrupts a naive timeline:

  1. **Joint owner codes.** CBERS 1/2/2B/4/4A — the backbone of Brazilian Earth
     observation — carry owner `CHBZ` (China/Brazil), not `BRAZ`. Filtering on
     national codes alone deletes the entire CBERS line.

  2. **Inherited ISS launch dates.** Eleven LATAM CubeSats were deployed from
     the ISS and therefore carry the station's COSPAR designator `1998-067xx`.
     Their SATCAT LAUNCH_DATE reads 1998-11-20 — the launch date of Zarya.
     Sorting on that field puts Guatemala's 2020 CubeSat before Brazil's 1999
     CBERS-1. Flagged as `iss_deployed` and excluded from first-record ranking.

  3. **Objects catalogued under another nation.** Argentina's SAC-B is
     catalogued under owner `US` as the composite "SAC-B & HETE & PEGASUS".

Imaging classification is not derivable from the catalog — SATCAT records no
payload information — so it comes from `data/latam_imaging_crosswalk.json`,
where every entry carries a source URL and a confidence grade. Anything not in
the crosswalk and not matched by a name rule is `unclassified`, never assumed
non-imaging.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

COUNTRY = {
    "ARGN": "Argentina", "BOL": "Bolivia", "BRAZ": "Brazil", "CHLE": "Chile",
    "COL": "Colombia", "CRI": "Costa Rica", "ECU": "Ecuador", "GUAT": "Guatemala",
    "MEX": "Mexico", "PERU": "Peru", "PRY": "Paraguay", "URY": "Uruguay",
    "VENZ": "Venezuela", "CHBZ": "China/Brazil (joint)",
}
# Catalogued under a non-LATAM owner code but a LATAM mission.
EXTERNAL = {24645: ("Argentina", "SAC-B, catalogued under owner US as a composite object")}

ISS_COSPAR_PREFIX = "1998-067"

# Satellogic's constellation is large, uniform in purpose and grows every year;
# a name rule is the maintainable owner of that classification, and it is
# applied only to objects the catalog already attributes to Argentina.
NAME_RULES = (
    (re.compile(r"^NUSAT-\d+", re.I), "Y", "multispectral", None, "M",
     "https://satellogic.com/technology/",
     "Satellogic NewSat/NuSat commercial EO constellation"),
    (re.compile(r"^ICEYE-X\d+", re.I), "Y", "SAR", 0.5, "M",
     "https://www.iceye.com/satellite-missions",
     "ICEYE X-band SAR; these units are registered to Brazil (FAB Lessonia)"),
)

IMG = {"Y": "yes", "P": "partial", "N": "no"}
CONF = {"H": "high", "M": "medium", "L": "low"}


def load_crosswalk(path: Path) -> dict:
    doc = json.loads(path.read_text())
    return {int(r[0]): {"imaging": IMG[r[1]], "sensor_type": r[2] or None,
                        "best_resolution_m": r[3], "confidence": CONF[r[4]],
                        "evidence_url": r[5], "classified_by": "crosswalk"}
            for r in doc["rows"]}


def classify(rec: dict, crosswalk: dict) -> dict:
    nid = int(rec["NORAD_CAT_ID"])
    if nid in crosswalk:
        return dict(crosswalk[nid])
    for rx, img, sensor, res, conf, url, note in NAME_RULES:
        if rx.search(rec["OBJECT_NAME"] or ""):
            return {"imaging": IMG[img], "sensor_type": sensor,
                    "best_resolution_m": res, "confidence": CONF[conf],
                    "evidence_url": url, "classified_by": "name_rule",
                    "rule_note": note}
    return {"imaging": "unclassified", "sensor_type": None,
            "best_resolution_m": None, "confidence": "none",
            "evidence_url": None, "classified_by": "unmatched"}


def build_history(raw_dir: Path, crosswalk_path: Path) -> dict:
    crosswalk = load_crosswalk(crosswalk_path)
    with (raw_dir / "celestrak.satcat.csv").open(newline="", encoding="utf-8") as fh:
        recs = list(csv.DictReader(fh))

    rows = []
    for r in recs:
        nid = int(r["NORAD_CAT_ID"])
        owner = r["OWNER"]
        if owner in COUNTRY:
            country = COUNTRY[owner]
            ext_note = None
        elif nid in EXTERNAL:
            country, ext_note = EXTERNAL[nid]
        else:
            continue
        if r["OBJECT_TYPE"] != "PAY":
            continue
        cls = classify(r, crosswalk)
        iss = (r["OBJECT_ID"] or "").startswith(ISS_COSPAR_PREFIX)
        rows.append({
            "norad_cat_id": nid,
            "object_id": r["OBJECT_ID"],
            "object_name": r["OBJECT_NAME"],
            "country": country,
            "owner_code": owner,
            "launch_date": r["LAUNCH_DATE"] or None,
            "decay_date": r["DECAY_DATE"] or None,
            "on_orbit": not bool(r["DECAY_DATE"]),
            "ops_status_code": r["OPS_STATUS_CODE"] or None,
            "launch_site": r["LAUNCH_SITE"] or None,
            "apogee_km": _num(r["APOGEE"]),
            "perigee_km": _num(r["PERIGEE"]),
            "inclination_deg": _num(r["INCLINATION"]),
            "iss_deployed": iss,
            "launch_date_reliable": not iss,
            "date_caveat": ("launch_date inherited from the ISS COSPAR designator "
                            "1998-067; true deployment was years later" if iss else None),
            "external_catalog_note": ext_note,
            **cls,
        })
    rows.sort(key=lambda x: (x["launch_date"] or "9999", x["norad_cat_id"]))

    imaging = [r for r in rows if r["imaging"] in ("yes", "partial")]
    datable = [r for r in imaging if r["launch_date_reliable"]]
    firsts = {}
    for r in sorted(datable, key=lambda x: x["launch_date"]):
        for c in ([r["country"]] if "joint" not in r["country"] else ["Brazil", r["country"]]):
            firsts.setdefault(c, [])
            if not any(f["imaging"] == "yes" for f in firsts[c]) or r["imaging"] == "yes":
                firsts[c].append({"norad_cat_id": r["norad_cat_id"],
                                  "object_name": r["object_name"],
                                  "launch_date": r["launch_date"],
                                  "imaging": r["imaging"],
                                  "sensor_type": r["sensor_type"]})
    first_by_country = {c: v[0] for c, v in firsts.items()}
    first_strict = [r for r in datable if r["imaging"] == "yes"]

    return {
        "schema": "satgis.latam-imaging-history/1",
        "rows": rows,
        "summary": {
            "payloads_total": len(rows),
            "imaging_yes": sum(1 for r in rows if r["imaging"] == "yes"),
            "imaging_partial": sum(1 for r in rows if r["imaging"] == "partial"),
            "imaging_no": sum(1 for r in rows if r["imaging"] == "no"),
            "unclassified": sum(1 for r in rows if r["imaging"] == "unclassified"),
            "on_orbit": sum(1 for r in rows if r["on_orbit"]),
            "decayed": sum(1 for r in rows if not r["on_orbit"]),
            "iss_deployed_with_inherited_date": sum(1 for r in rows if r["iss_deployed"]),
            "countries": sorted({r["country"] for r in rows}),
            "earliest_payload": rows[0]["launch_date"] if rows else None,
            "earliest_imaging_strict": (
                {"norad_cat_id": first_strict[0]["norad_cat_id"],
                 "object_name": first_strict[0]["object_name"],
                 "launch_date": first_strict[0]["launch_date"],
                 "country": first_strict[0]["country"]} if first_strict else None),
            "first_imaging_by_country": first_by_country,
        },
    }


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
