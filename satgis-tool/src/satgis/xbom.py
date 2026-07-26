"""CycloneDX 1.6 xBOM covering both the code dependencies and the data sources.

A software BOM alone is not sufficient evidence here: the compilation's
correctness depends as much on *which catalog snapshot* was consumed as on
which version of sgp4 propagated it. Both are therefore components, each with a
hash, a licence, and the authority materially responsible for it.
"""
from __future__ import annotations

import importlib.metadata as md
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

CODE_COMPONENTS = ("sgp4", "geopandas", "shapely", "pyproj", "pyogrio",
                   "pyarrow", "pandas", "numpy", "requests",
                   "cyclonedx-python-lib")


def _pkg(name: str) -> dict:
    try:
        dist = md.distribution(name)
        version = dist.version
        meta = dist.metadata
        lic = meta.get("License-Expression") or meta.get("License") or "see package metadata"
        if lic and len(lic) > 120:
            lic = next((c.split("::")[-1].strip()
                        for c in meta.get_all("Classifier", [])
                        if c.startswith("License ::")), "see package metadata")
    except md.PackageNotFoundError:
        version, lic = "MISSING", "unknown"
    return {
        "type": "library", "name": name, "version": version,
        "purl": f"pkg:pypi/{name}@{version}",
        "licenses": [{"license": {"name": str(lic)}}],
        "scope": "required",
    }


def build_xbom(acquisition_manifest: dict, output_manifest: dict,
               build_metadata: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    components: list[dict] = [_pkg(n) for n in CODE_COMPONENTS]

    for src in acquisition_manifest.get("sources", []):
        components.append({
            "type": "data",
            "name": src["key"],
            "version": src["retrieved_utc"],
            "description": src["description"],
            "supplier": {"name": src["authority"]},
            "licenses": [{"license": {"name": src["license"]}}],
            "hashes": [{"alg": "SHA-256", "content": src["sha256"]}],
            "externalReferences": [{"type": "distribution", "url": src["url"]}],
            "properties": [
                {"name": "satgis:records", "value": str(src["records"])},
                {"name": "satgis:bytes", "value": str(src["bytes"])},
                {"name": "satgis:retrieved_utc", "value": src["retrieved_utc"]},
            ],
        })

    for art in output_manifest.get("artifacts", []):
        components.append({
            "type": "file",
            "name": art["path"],
            "version": build_metadata["propagation_epoch_utc"],
            "hashes": [{"alg": "SHA-256", "content": art["sha256"]}],
            "properties": [
                {"name": "satgis:format", "value": art.get("format", "")},
                {"name": "satgis:bytes", "value": str(art["bytes"])},
                {"name": "satgis:features", "value": str(art.get("features", ""))},
            ],
        })

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "timestamp": now,
            "component": {
                "type": "application",
                "name": "satgis",
                "version": "0.1.0",
                "description": ("Orbital catalog to GIS compilation: SGP4-propagated "
                                "positions, ground tracks and visibility footprints "
                                "for every tracked active satellite, with NASA / NOAA "
                                "/ USGS fleet attribution."),
            },
            "tools": {"components": [{"type": "application", "name": "satgis",
                                      "version": "0.1.0"}]},
            "properties": [
                {"name": "satgis:python", "value": platform.python_version()},
                {"name": "satgis:platform", "value": platform.platform()},
                {"name": "satgis:machine", "value": platform.machine()},
                {"name": "satgis:propagation_epoch_utc",
                 "value": build_metadata["propagation_epoch_utc"]},
                {"name": "satgis:frame_chain", "value": build_metadata["frame_chain"]},
                {"name": "satgis:polar_motion_applied",
                 "value": str(build_metadata["polar_motion_applied"]).lower()},
            ],
        },
        "components": components,
    }


def write_xbom(doc: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return path
