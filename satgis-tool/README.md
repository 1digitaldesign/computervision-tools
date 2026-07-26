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

---

# Ground-station access — Spain + Latin America

Every catalogued satellite evaluated against every ground station in the region.

| | |
|---|---|
| Stations | **484** across **18** countries |
| Satellites evaluated | **16,241** (the whole active catalog) |
| Window | 24 h from `2026-07-26T05:00:00Z`, 60 s grid |
| Elevation masks | 0 deg, 5 deg, 10 deg (5 deg is the reported default) |
| Work done | **11.3 G** (satellite, time, station) triples in **~100 s** |
| Contact events | **36,755,130** |
| Total access | **8,173,689 station-hours** |
| Satellites with >=1 contact | 16,037 / 16,241 |
| Access-window pairs | **7,685,471** |
| Verification | **19/19 checks, 7/7 negative controls — PASS** |

```sh
./satgis access --epoch 2026-07-26T05:00:00 --hours 24 --step 60
```

## Station provenance — three tiers

**T1, SPICE frame kernels.** Station geodesy is taken from the operators' own
machine-readable navigation files, not from prose on a web page:
ESA `estrack_v03.tf` and NASA/NAIF `earth_topo_260717.tf`. Position is encoded
in the topocentric frame definition as
`TKFRAME_<f>_ANGLES = ( -longitude, -colatitude, 180 )`, so latitude is
`90 + angle2` and longitude is `-angle1`. Parsing recovers Cebreros at
40.452690 N, 4.367550 W — the published value to six decimals.

**T2, SatNOGS Network API.** The open ground-station registry, 4,383 stations
worldwide, operator-reported coordinates.

**T3, curated institutional.** Deliberately empty. Nothing was added from
memory: a station whose coordinates could not be traced to a citable source at
build time is omitted rather than guessed.

Country is assigned by point-in-polygon against Natural Earth Admin-0, so the
regional filter is geometric rather than a trusted name field. Coastal stations
that fall just outside a 1:50m polygon are rescued by nearest-country within
25 km and flagged `coastal_rescue`. French Guiana is folded into France by
Natural Earth and is relabelled by geometry, so ESA Kourou is correctly placed
in South America.

Station height is 0 for T1 stations — the SPICE FKs carry only the topocentric
*orientation*, with height in the companion SPK. Recorded per station as
`height_known`; the residual elevation error at LEO is well under 0.2 deg.

## Why the access pass is a matrix product

A 24 h window over the whole catalog is 23.4 M positions. Against 484 stations
that is 11.3 G triples, and the naive cost is dominated by re-reading the
561 MB position array once per station — roughly 257 GB of memory traffic.

Expanding the dot products removes the per-station pass over the data:

```
d . u  = P . u - (S . u)          <- second term is a scalar per station
|d|^2  = |P|^2 - 2 (P . S) + |S|^2
```

so each station is two projections of `P` onto fixed 3-vectors. Stacking the
stations turns both into one GEMM, `P (N,3) @ M.T (3, n_st)`, which BLAS runs
at full width. Blocks reduce to pass statistics immediately, so the `(N, n_st)`
intermediate is never materialised whole. Result: **~100 s** for the full job.

The GEMM runs in float32. That choice is **measured, not assumed**: a
stratified control (150 LEO + 150 MEO/GEO/HEO, 145,200 station pairs) recomputed
in float64 found **zero** pass-count disagreements at all three masks, with a
maximum access-time difference of 1.0 min — one 60 s sample flipping at a mask
boundary.

## New layers

| Layer | Container | Rows | Contents |
|---|---|---|---|
| `ground_stations` | GPKG + GeoJSON + Parquet | 484 | Point, with country, network, tier, operator, evidence URL |
| `station_access_summary` | GPKG + GeoJSON + Parquet | 484 | Point, per-station contact totals, per-orbit-class and per-agency counts |
| `satellite_access_summary` | Parquet | 16,241 | per-satellite station count, passes, minutes, peak elevation, best station |
| `access_epoch` | Parquet | 454,555 | instantaneous elevation / azimuth / slant range at the frozen epoch |
| `access_windows` | Parquet | 7,685,471 | per (satellite, station): passes, minutes, max elevation at each mask |

The 7.7 M-row pair table is **Parquet only, and that is stated rather than
silent**: writing it into SQLite would multiply the .gpkg several-fold and slow
every read of the layers people actually render, for a table that is an
analytical join target, not a map layer. It is hashed in the same manifest.

## Regional results (5 deg mask, 24 h)

| Country | Stations | Contacts | Access (station-minutes) |
|---|---:|---:|---:|
| Spain | 184 | 15,880,815 | 208,644,336 |
| Argentina | 79 | 6,519,025 | 83,004,952 |
| Brazil | 63 | 4,215,622 | 59,516,928 |
| Mexico | 44 | 2,896,588 | 38,111,204 |
| Colombia | 31 | 1,764,916 | 26,039,608 |
| Chile | 16 | 1,343,723 | 16,824,840 |
| Peru | 13 | 776,009 | 11,019,243 |
| Ecuador | 12 | 678,912 | 9,873,130 |
| Costa Rica | 10 | 581,014 | 8,268,176 |
| Dominican Republic | 7 | 438,257 | 6,210,045 |
| Uruguay | 5 | 418,192 | 5,310,438 |
| Paraguay | 4 | 283,973 | 3,794,663 |
| Guatemala | 4 | 240,796 | 3,331,101 |
| Venezuela | 4 | 232,565 | 3,461,251 |
| Bolivia | 3 | 186,576 | 2,657,221 |
| French Guiana (FRA) | 3 | 170,731 | 2,625,949 |
| Cuba | 1 | 67,514 | 891,878 |
| Honduras | 1 | 59,902 | 836,384 |

Institutional (T1) stations, ranked by 24 h contacts:

| Station | Country | Contacts | NASA | NOAA | USGS |
|---|---|---:|---:|---:|---:|
| DSN DSS-53/54/55/56/63/65 | Spain | ~87,197 each | 38 | 10 | 2 |
| ESTRACK Cebreros | Spain | 87,177 | 38 | 10 | 2 |
| ESTRACK Villafranca | Spain | 87,170 | 38 | 10 | 2 |
| ESTRACK Malargüe | Argentina | 85,941 | 38 | 13 | 2 |
| ESTRACK Santiago | Chile | 80,837 | 38 | 13 | 2 |
| ESTRACK Maspalomas | Spain | 75,634 | 38 | 11 | 2 |
| ESTRACK Kourou | French Guiana | 56,927 | 38 | 12 | 2 |

## Access verification

The headline check is a **cross-layer invariant**. The footprint layer and the
access layer are computed by entirely disjoint code paths — one a spherical
visibility cap swept as a geodesic circle, the other an ECEF topocentric dot
product — yet "the station is inside the satellite's 0 deg footprint" and "the
satellite is at non-negative elevation from the station" are the same physical
statement. **99.960%** of sampled pairs agree. Two independent derivations of
one fact is corroboration; re-checking one derivation against itself is not.

Supporting checks: the 204 never-visible satellites are **zero LEO** — they are
192 GEO, 9 MEO and 3 HEO objects parked over longitudes the region cannot see,
exactly `537-345`, `219-210` and `55-52` from the orbital layer. Contact counts
rise with station latitude (Spearman rho **0.877**, strictly increasing across
10-degree bands) because polar and sun-synchronous orbits converge poleward.
Station country assignment re-derives 100.000% on an independent spatial join.

### Two more assertions the verifier got wrong

Consistent with the orbital build, both first-run access failures were defects
in the *instrument*, and the fix was to correct the assertion, not the bar:

- *Latitude trend measured on the wrong sample.* The check ran over the 12
  institutional stations and failed at rho = 0.4386. The trend was not absent —
  8 of those 12 are the Madrid complex, within **0.028 deg** of each other, with
  pass counts differing by 30 out of 87,200 (0.034%). Rank-correlating noise
  across a degenerate cluster measures nothing. Re-measured over all 484
  stations, spanning 5 deg to 50 deg: **rho = 0.877**, bands strictly increasing.
- *Pass count is not monotone in the elevation mask.* The control asserted
  `passes(10 deg) <= passes(5 deg)` and failed. **The data was right and the
  assertion was wrong.** For slow, eccentric or near-stationary orbits the
  elevation profile inside one 5 deg window is not unimodal, so one 5 deg
  contact can split into several 10 deg contacts. PHASE 3B (AO-10), a
  Molniya-type HEO satellite, goes from 2 passes / 617 min at 5 deg to
  3 passes / 404 min at 10 deg. All 2,798 exceptions (0.0364%) are MEO/GEO/HEO;
  **zero are LEO**. Access *minutes* is the genuinely monotone quantity, and it
  holds with **0 violations across all 7,685,471 pairs**.

## A note on acquisition

CelesTrak began returning 403 after repeated full-catalog pulls during
development — correct behaviour on their part. `acquire` is now idempotent: a
source already on disk whose bytes still hash to its recorded digest is
*reused*, not re-fetched, and `--refresh` forces the fetch.

More importantly, a failed refresh no longer destroys provenance. The first
403 left `celestrak.gp.active.json` intact on disk but moved its manifest entry
into `failures`, so the snapshot silently lost the authority, licence and
retrieval timestamp of its single most important source while the data it
described was still sitting there. A refresh failure now carries the prior
entry forward and annotates it. The lost entry was recovered from commit
`ebb7c6b` with the frozen bytes SHA-256-verified unchanged before restoring.
