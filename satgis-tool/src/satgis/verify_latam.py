"""Verification for the LATAM imaging-history layer.

The two negative controls here are unusual and deliberate: instead of mutating
the *output*, they re-run the build with a documented safeguard removed, and
assert that the result visibly degrades. That is the only honest way to show a
data-handling rule earns its place — if deleting the rule changes nothing, the
rule was decoration.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .verify import _result


def m1_history_integrity(out_dir: Path, crosswalk_path: Path) -> list[dict]:
    checks = []
    meta = json.loads((out_dir / "latam-history-metadata.json").read_text())
    df = pd.read_parquet(out_dir / "latam_imaging_history.parquet")
    s = meta["summary"]

    ok = len(df) == s["payloads_total"]
    checks.append(_result("history_row_count", "M1", ok,
                          f"{len(df)} payload rows, metadata says {s['payloads_total']}",
                          rows=int(len(df))))

    unc = int((df["imaging"] == "unclassified").sum())
    checks.append(_result("no_unclassified_payloads", "M1", unc == 0,
                          f"{unc} payloads left unclassified — every object is "
                          f"explicitly yes/partial/no with a source, rather than "
                          f"defaulting to non-imaging"))

    xw = json.loads(crosswalk_path.read_text())["rows"]
    ids = set(df["norad_cat_id"].tolist())
    orphan = [r[0] for r in xw if r[0] not in ids]
    checks.append(_result("crosswalk_ids_resolve", "M1", not orphan,
                          f"all {len(xw)} researched NORAD IDs resolve to a real "
                          f"LATAM payload in the frozen SATCAT"
                          if not orphan else f"orphans: {orphan}",
                          crosswalk_entries=len(xw)))

    imaged = df[df["imaging"].isin(["yes", "partial"])]
    missing_src = int(imaged["evidence_url"].isna().sum())
    checks.append(_result("imaging_claims_are_sourced", "M1", missing_src == 0,
                          f"{len(imaged)} imaging claims, {missing_src} without an "
                          f"evidence URL"))
    return checks


def m2_history_chronology(out_dir: Path) -> list[dict]:
    checks = []
    df = pd.read_parquet(out_dir / "latam_imaging_history.parquet")
    meta = json.loads((out_dir / "latam-history-metadata.json").read_text())

    strict = df[(df["imaging"] == "yes") & (df["launch_date_reliable"])]
    earliest = strict.sort_values("launch_date").iloc[0]
    ok = int(earliest["norad_cat_id"]) == 24291
    checks.append(_result("earliest_imager_is_musat1", "M2", ok,
                          f"earliest date-reliable imaging payload is "
                          f"{earliest['object_name']} ({int(earliest['norad_cat_id'])}, "
                          f"{earliest['launch_date']}, {earliest['country']}) — "
                          f"catalogued only as the generic string 'MICROSAT', which is "
                          f"why name-based lookups miss it"))

    cbers = df[df["owner_code"] == "CHBZ"]
    checks.append(_result("cbers_line_present", "M2", len(cbers) == 5,
                          f"{len(cbers)} CBERS objects retained under the joint "
                          f"China/Brazil owner code CHBZ "
                          f"({', '.join(sorted(cbers['object_name']))})"))

    iss = df[df["iss_deployed"]]
    all_flagged = bool((~iss["launch_date_reliable"]).all())
    checks.append(_result("iss_dates_flagged", "M2",
                          len(iss) == 11 and all_flagged,
                          f"{len(iss)} ISS-deployed payloads carry COSPAR 1998-067 and "
                          f"are all flagged launch_date_reliable=False, so none can "
                          f"contaminate a first-record ranking"))

    fb = meta["summary"]["first_imaging_by_country"]
    monotone = all(
        df[df["norad_cat_id"] == f["norad_cat_id"]]["launch_date"].iloc[0] == f["launch_date"]
        for f in fb.values())
    checks.append(_result("first_by_country_consistent", "M2", monotone,
                          f"first-imaging record for each of {len(fb)} countries "
                          f"re-reads identically from the row table"))
    return checks


def history_negative_controls(out_dir: Path, raw_dir: Path,
                              crosswalk_path: Path) -> list[dict]:
    """Re-run the build with a safeguard removed; the result must visibly degrade."""
    from . import latam
    controls = []

    # Baseline full build — also reused by NC9 so both controls share one snapshot.
    h_full = latam.build_history(raw_dir, crosswalk_path)
    baseline = h_full["summary"]["payloads_total"]

    # NC8: drop the joint China/Brazil owner code -> the CBERS line vanishes.
    saved = dict(latam.COUNTRY)
    try:
        latam.COUNTRY.pop("CHBZ", None)
        h = latam.build_history(raw_dir, crosswalk_path)
        lost = baseline - h["summary"]["payloads_total"]
        names = {r["object_name"] for r in h["rows"]}
        cbers_gone = not any(n.startswith("CBERS") for n in names)
    finally:
        latam.COUNTRY.clear(); latam.COUNTRY.update(saved)
    controls.append(_result("NC8_joint_owner_code_matters", "M2-control",
                            lost == 5 and cbers_gone,
                            f"removing owner code CHBZ deletes {lost} payloads and the "
                            f"entire CBERS line disappears — a national-code-only filter "
                            f"would silently drop the backbone of Brazilian Earth "
                            f"observation"))

    # NC9: rank first-records on the raw LAUNCH_DATE field.
    # The first version of this control asserted the *global* first imager would
    # be corrupted, and failed: 1998-11-20 sorts AFTER 1996-08-29, so MICROSAT
    # still comes first. The assertion was wrong, not the data. The inherited
    # date does real damage in two measured places instead — per-country firsts,
    # and ordering against the 1999 CBERS-1 milestone.
    rows = [r for r in h_full["rows"] if r["imaging"] in ("yes", "partial")]
    naive = {}
    for r in sorted(rows, key=lambda r: (r["launch_date"] or "9999", r["norad_cat_id"])):
        naive.setdefault(r["country"], r)
    true = h_full["summary"]["first_imaging_by_country"]
    flipped = [c for c in true
               if c in naive and naive[c]["norad_cat_id"] != true[c]["norad_cat_id"]]
    ghosts = [r["object_name"] for r in rows
              if r["iss_deployed"] and (r["launch_date"] or "") < "1999-10-14"]
    ok = {"Mexico", "Peru"} <= set(flipped) and len(ghosts) >= 4
    controls.append(_result("NC9_iss_inherited_date_matters", "M2-control", ok,
                            f"ranking on the raw LAUNCH_DATE field flips the "
                            f"first-imager for {sorted(flipped)} and floats "
                            f"{len(ghosts)} ISS-deployed CubeSats "
                            f"({', '.join(sorted(ghosts))}) to 1998-11-20, ahead of "
                            f"CBERS-1 (1999-10-14) — inserting spacecraft deployed "
                            f"between 2014 and 2026 into the 1990s"))
    return controls


def verify_latam_all(out_dir: Path, raw_dir: Path, crosswalk_path: Path) -> dict:
    return {
        "checks": (m1_history_integrity(out_dir, crosswalk_path)
                   + m2_history_chronology(out_dir)),
        "negative_controls": history_negative_controls(out_dir, raw_dir, crosswalk_path),
    }
