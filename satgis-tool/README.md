# satgis — orbital catalog → GIS compilation

Compiles **every tracked active satellite** into open GIS formats: subsatellite
position, one-revolution ground track, and instantaneous visibility footprint
for each object, with **NASA / NOAA / USGS** fleet attribution carried as a
first-class attribute.

Built and verified on Apple M4 Max. A full build of the 16,241-object active
catalog takes **~7 s**.

## Current compilation

| | |
|---|---|
| Propagation epoch | `2026-07-26T05:00:00Z` (frozen) |
| Objects propagated | **16,241** |
| Orbit classes | LEO 15,430 · GEO 537 · MEO 219 · HEO 55 |
| Agency-attributed | NASA 42 · NOAA 13 · USGS 2 · USSF 2 |
| Element-set freshness | median **0.76 d**, mean 0.86 d |
| Outputs | 18 artifacts, 222 MB |
| Verification | **11/11 checks, 4/4 negative controls — PASS** |

## Usage

```sh
./satgis doctor                              # environment + driver preflight
./satgis acquire                             # fetch + hash the catalog snapshot
./satgis build --epoch 2026-07-26T05:00:00   # snapshot -> GIS + xBOM
./satgis verify                              # 3 independent methods + controls
./satgis package                             # bundle outputs + evidence
```

Every verb is idempotent and exits non-zero on substantive failure. `build`
reads only the frozen snapshot — never the network — so a build is reproducible
from `data/raw/acquisition-manifest.json` alone.

## Outputs

`data/out/`

| Artifact | Format | Contents |
|---|---|---|
| `satgis_orbital_catalog.gpkg` | OGC GeoPackage | all three layers, canonical container |
| `satellites.{parquet,geojson}` | GeoParquet / GeoJSON | Point — subsatellite position at epoch, 34 attributes |
| `footprints.{parquet,geojson}` | GeoParquet / GeoJSON | Polygon — instantaneous visibility cap |
| `ground_tracks.{parquet,geojson}` | GeoParquet / GeoJSON | LineString — one full revolution |
| `agency_{nasa,noaa,usgs}_*.geojson` | GeoJSON | the three agency fleets, cut out on their own |
| `xbom.cdx.json` | CycloneDX 1.6 | code **and** data bill of materials |
| `SHA256SUMS{,.json}` | manifest | per-artifact digests |
| `build-metadata.json` | JSON | epoch, frame chain, counts, rejects |

## Reference frames — stated, because this is the main correctness risk

SGP4 emits position in **TEME**, not J2000 and not ECEF. The chain is:

```
SGP4 -> TEME -> Rz(GMST82) -> ECEF (PEF) -> PROJ EPSG:4978->4979 -> WGS84 lon/lat/alt
```

**Polar motion (x_p, y_p) is deliberately not applied.** It is a sub-metre to
few-metre effect, far below the ~1 km epoch error of the element sets
themselves, and applying it would add an Earth-orientation-parameter authority
to the dependency graph for no measurable gain. This is recorded as
`polar_motion_applied: false` in `build-metadata.json` — omitted, not hidden.

Footprints are the spherical visibility cap

```
rho    = Re / (Re + h)
lambda = arccos(rho * cos(eps)) - eps     (eps = elevation mask, default 0 deg = horizon)
```

swept as a geodesic circle of great-circle radius `Re*lambda`. A spherical cap
on an ellipsoidal Earth: sub-km error at LEO, appropriate for coverage
cartography. At GEO this yields lambda = 81.30 deg and a 9,050 km cap radius —
the textbook values.

Antimeridian crossing and pole enclosure are both handled explicitly
(`geometry.py`); a naive implementation smears rings across the whole map.

## Agency attribution

Attribution is **derived, not asserted**. Each rule is a name pattern resolved
against the frozen snapshot, so every NORAD ID in the crosswalk is provably
present in the data actually propagated, and a rule matching nothing is a
reported coverage failure rather than a silent no-op. Current run: **28/28
rules matched**.

Roles follow the **operating** agency, not the building agency:

- **USGS** — Landsat 8, Landsat 9. NASA-built, USGS-operated.
- **NOAA** — GOES-16/17/18/19, NOAA-20/21 (JPSS), Suomi NPP, Jason-3,
  Sentinel-6A/6B, DMSP F16/F17/F18.
- **NASA** — EOS (Terra, Aqua, Aura), ICESat-2, SMAP, GPM, OCO-2, PACE, SWOT,
  NISAR, GRACE-FO, CYGNSS, TIMED, SORCE, MMS, THEMIS, Hubble, TDRSS, ISS.
- **USSF** — EWS-G2/EWS-G3. Formerly GOES-15/GOES-14; **transferred out of
  NOAA**, so they are explicitly *not* attributed to NOAA.

### Fleet-state findings from this build

Discovered from the data, then cross-checked against `.gov` sources:

1. **CelesTrak retired `GROUP=noaa` upstream.** Probing it now returns
   `Invalid query ... (GROUP=noaa not found)`. The NOAA polar assets moved into
   `GROUP=weather` after the NOAA-15/18/19 POES fleet was decommissioned.
2. **Landsat 7 is absent from the active catalog**, consistent with its USGS
   decommissioning after 25 years of operation.
3. **NISAR (65053) and Sentinel-6B (66514) are present and propagating.**
4. **DSCOVR does not appear** — it operates at Sun-Earth L1, outside the Earth
   orbital regime SGP4 models, so it is out of scope by construction.
5. **Element epochs run slightly negative** (min -1.84 d relative to the frozen
   epoch): CelesTrak publishes forward-predicted element sets for some recently
   launched objects. A data property, not an error; carried as
   `element_age_days`.

## Verification — three independent methods, each with a negative control

The three methods are deliberately *not* variations on one idea.

| Method | What it proves | Result |
|---|---|---|
| **M1 integrity** | SHA-256 recomputation, layer counts, CRS identity, geometry validity, required columns | 3/3 |
| **M2 physics** | datum re-derived by a converged Bowring solution that never touches PROJ; external ground truth (ISS band, GEO radius/speed); Kepler's third law | 4/4 |
| **M3 topology** | every satellite inside its own cap; world bounds; cap radius monotone in altitude; no empty tracks | 4/4 |

Negative controls — **an assertion that cannot fail is not evidence**:

| Control | Mutation | Outcome |
|---|---|---|
| NC1 | single-byte flip in `footprints.parquet` | detected, original restored |
| NC2 | move every satellite to its antipode | 0/2000 still contained |
| NC3 | seeded permutation of altitudes | Spearman rho collapses 1.000 -> 0.000348 |
| NC4 | 25 km Z-axis injection into the datum | max dlat 0.216 deg >> 1e-8 deg threshold |

**The verifier caught two defects in itself on first run. Both were fixed by
improving the instrument rather than relaxing the bar:**

- *Single-pass Bowring does not converge at GEO.* It failed at
  max dlat = 4.518e-07 deg, driven entirely by the geostationary belt, because
  its parametric-latitude seed assumes a near-surface point. Adding fixed-point
  refinement restored full double precision — **max dlat is now 2.132e-14 deg**
  — which keeps the M2 tolerance tight enough to be worth asserting.
- *A fixed +120 deg longitude displacement is not a valid falsifier.* Near the
  poles that is a tiny ground distance, so 18/185 polar caps legitimately still
  contained the displaced point. Replaced with the antipode, which is provably
  exterior: every cap in the catalog has central angle < 90 deg (max
  **87.340 deg**), so the antipodal point is outside unconditionally.

Independently, GMST82 is validated against **Vallado Example 3-5**
(1992-08-20 12:14:00 UT1 -> 152.578787810 deg) and agrees to **1e-9 degrees**.

## Sources and licensing

| Source | Authority | Licence |
|---|---|---|
| CelesTrak SATCAT + GP/OMM element sets | CelesTrak (T.S. Kelso), redistributing USSF 18th/19th SDS data | US Government work, 17 U.S.C. 105 |
| NOAA fleet roster | NOAA NESDIS | US Government work |
| Landsat mission status | USGS | US Government work |

Every source carries its authority, licence, retrieval timestamp, byte count,
record count, and SHA-256 in `xbom.cdx.json` and
`data/raw/acquisition-manifest.json`.

## Reproducing

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt   # exact pins
./satgis doctor && ./satgis acquire && ./satgis build && ./satgis verify
```

`requirements.txt` is a uv-compiled lock with exact pins — no `@latest` wiring.
