# Phase 3 — user feedback and implementation plan

## Additional user feedback — 2026-11-13

Phase 3 is not complete. The existing square/chamfered habitat and simple
furnishings are functional testing geometry, not final reference-quality art.
Finish a rounded damaged industrial pod, believable panel/material detail and
a convincing interior while preserving/retesting the airlock, sanctuary and spawn.

Terrain is too flat and insufficiently hostile/otherworldly. Add actual hills,
mounds, jagged rock zones/ridges, depressions/craters, ravines and pitfalls, with
varied elevations, slopes and large-scale silhouettes. More small stones alone
will not address this. Use terrain-aware seeded PCG and deliberate authored
geography; reproject/reseat scatter and retest collisions/routes/landmarks after
landscape changes. Preserve home access and design readable hazards, safe
escape/recovery and intentional damage/death behavior in heavy fog. See
`../HANDOFF_Phase3.md` for current worktree state, remaining gates and worker roles.

Requirements recorded 2026-11-11; implementation updated 2026-11-12.
The environment, habitat, survival, recovery/save and C++ core modules are now
implemented. See `Phase3_Validation.md` for actual checks and remaining limits;
the requirements below remain the acceptance direction, not a claim of final art.

## Current state

Phase 2 provides a 2 km landscape, imported Quixel materials/meshes, 2,185 baked
rock instances in spatial HISM cells, exterior landmark prototypes, weather,
day/night, wind and a runnable Windows Development build. Player movement,
camera switching and flashlight exist. The habitat is sealed; survival stats,
airlock, death/respawn and saving are not implemented.

The user has tested the build. Reported issues: unnatural rock scattering,
insufficient height/shape variation, exposed incomplete scan geometry, daytime
too dark, and insufficient persistent airborne dust/fog. Other manual checklist
results, audio acceptance and target-hardware performance remain unreported.

## Module 3A — environment correction, first priority

Owner: World / Terrain & Atmosphere specialist when implementation begins.
Lead integrates and validates through the single editor writer. This module
belongs at the start of Phase 3, rather than waiting for final polish.

### PCG environment placement

- Use actual Unreal PCG graphs and seeded generation for suitable environment
  elements and their scattering: rocks, gravel, boulders, ridges/cliff assemblies,
  ground debris and environmental dust-region placement. A Python random loop
  writing HISM instances is not the requested PCG workflow. Python may author
  graphs/assets and run editor validation; runtime gameplay stays in Unreal.
- Keep authored landmark/home positions and traversable approaches deliberate;
  feed their footprints, airlock clearance and routes into PCG exclusion data.
  Preserve the shared route contract in `Scripts/phase2_layout.py`.
- Use terrain projection, slope/height masks, clustered density/noise, exposed
  ridges and sparse wind-scoured gaps. Avoid even distribution and repeated
  lines of rocks beside routes. Mix fine scatter, mid-sized rocks and occasional
  larger formations with different vertical profiles and believable geology.
- Vary scale, yaw, restrained pitch/roll, burial and assembly height. Use
  per-asset scale ranges; avoid stretched scans, floating bases and random Z
  offsets that detach rocks from the terrain. Vary terrain/formation relief as
  well as object size. Keep the layout deterministic across reloads and saves.
- Inspect each source mesh from all sides and classify open-backed scans.
  Build reusable boulder/cliff assemblies from overlapping rotated copies of
  the same scan (or compatible scans), orienting finished faces outward and
  burying/hiding open backs and bottoms. Validate the combined silhouette and
  collision around the entire assembly. Two-sided shading alone does not fill
  missing geometry. Record the asset-specific assembly rules after inspection.
- Replace the old scatter output without leaving duplicate rocks. Make repeat
  generation safe and preserve unrelated imports and hand-authored actors.

### Dust, fog and light

- Exterior baseline is an alien planet continuously in dust/sandstorm conditions.
  Even the least intense weather must retain airborne dust and heavy warm haze;
  weather changes its intensity instead of revealing a clean, clear day.
- Brighten daytime diffuse illumination and readable nearby surfaces. Separate
  daylight/exposure tuning from fog extinction so low visibility comes from
  suspended dust rather than crushed blacks. Keep the warm brown/ochre palette,
  a muted sun and a welcoming amber habitat. Preserve a distinct night state.
- Combine height/volumetric fog with wind-driven Niagara dust, near-ground sheets
  and gusts, using local fog regions where useful. PCG can distribute appropriate
  regions; use pooled/bounded effects rather than an emitter per rock or point.
  Prevent exterior dust effects from filling the sealed habitat.
- Recognizable silhouettes at **40+ metres** are the user's visibility target.
  Validate at 40, 60 and 100 m in daytime baseline and settled storm, both views,
  flashlight on/off; record large landmark and human-scale target visibility
  separately. Beyond that range detail should disappear progressively into dust.
  Use distance-marked test captures rather than treating fog density as metres.
  Stronger gusts may briefly reduce clarity, but sustained storms must preserve
  the requested 40+ m silhouette readability.
- This updates the GDD's earlier default of storms reducing visibility to only
  metres. Do not retain that earlier target over the user's latest direction.
- Retain the environment director's runtime query/events and data-driven tuning.
  Review weather light attenuation as well as sun, sky, exposure and fog settings;
  do not simply increase the existing storm fog density of 1.0.

### Unreal rendering and performance

- Use Nanite for suitable opaque static rocks, large assemblies, wrecks and
  habitat geometry; verify imported assets and rendered results. Keep appropriate
  collision separate from rendering complexity.
- Use Lumen GI/reflections for suitable exterior/interior lighting. It already
  forms part of the project's rendering baseline; verify the active settings
  and tune scalability with actual scenes. It is not a free performance gain.
- Use World Partition-aware PCG generation/output, ISM/HISM where appropriate,
  distance culling, HLOD where useful, and suitable shadows/LOD choices. Prefer
  baked/editor-generated static scatter for the fixed world unless measured
  runtime generation provides a clear benefit. Keep generation cost out of play.
- Profile Niagara overdraw, volumetric fog, shadows, Lumen and streaming at
  1080p High in packaged traversal and storms. Compare median/p95/p99 and hitches
  to the Phase 2 baseline; stable 60+ FPS on mid-range hardware remains a target,
  not an established result. Balance visual improvement against measured cost.

Acceptance: review all-sided rock assemblies, varied natural formations, no
floating rocks/open backs/collision traps, deterministic PCG rebuild/reload,
clear home/airlock access, brighter dusty daytime and distance-marked silhouette
captures. Re-run player, environment and route regressions, then package for
user review. Update existing environment tests to the new intended climate;
passing old numeric fog targets does not establish visual acceptance.

## Remaining Phase 3 modules

1. **3B — habitat and airlock:** replace the sealed blockout with a walkable
   sanctuary, capsule-safe doors/floors and an operable airlock. Establish a
   reliable interior/exterior state and safe clone spawn. Include bed, broken
   fabricator and practical lighting; crafting/upgrades remain later phases.
2. **3C — survival and HUD:** data-driven Oxygen, Power, Integrity and Stamina;
   outside drain, habitat refill, sprint costs and readable warnings/minimal
   diegetic HUD. Consume weather via the existing environment interface. Keep
   hidden Strain extension points private; no numeric Strain HUD.
3. **3D — death, recovery and save:** oxygen/integrity zero triggers death and
   one new clone respawn inside the habitat. Leave a recoverable death crate
   with a minimal future inventory contract. Save/load the Phase 3 state and
   validate restart, repeated deaths and recovery without duplication or loss.

Player / Survival owns stats and death; Habitat / Progression owns shell,
interior and airlock; UI / Polish + Asset Integration owns presentation,
reference matching and asset integration. Lead sequences the four specialist
assignments within available slots and serializes editor writes. Test each
module and keep the game runnable. Full inventory/scavenging/scanner/lore,
crafting, progression and full psychological effects remain later phases.

## Visual references

Saved in `Docs/References/Phase3/` so future work does not depend on Downloads.
The user's habitat image number appears to be a typo: image 3 shows the suit,
while image 4 shows the habitat exterior. Use the visible subjects as follows:

| Reference | File | Direction |
| --- | --- | --- |
| Image 1 — habitat interior | [interior](References/Phase3/hyper-realistic-interior-4.jpg) | Compact worn metal living space; bed, shelves, exposed services, warm task lamps and cool practical accents. Plants/greenhouse are visual direction; functional greenhouse progression remains later. |
| Image 2 — explorable crashed ship | [wreck](References/Phase3/hyper-realistic-concept-3.jpg) | Massive tilted, partly buried hull, torn plating and readable exposed decks in dusty haze. Preserve this as an explorable destination, not a permanently sealed prop. |
| Image 3 — player | [suit](References/Phase3/hyper-realistic-third-person-view-2.jpg) | Weathered pale pressure suit, life-support pack, hoses, amber reflective visor and handheld light; strong silhouette in dense windblown dust. |
| Image 4 — habitat exterior | [habitat](References/Phase3/hyper-realistic-concept-art-1.jpg) | Rounded damaged pod, airlock, solar panels, antennas, warm windows/lamps and grounded rocky terrain. |

Reference matching must not be reported as finished character/ship assets.
Phase 3 owns the functional habitat. Record the explorable wreck requirement
for Phase 4 discovery planning; implement a first accessible section there and
reserve additional cruiser rooms/stories for later phases. Suit art integration
must preserve the tested character, animation, input and first/third-person
camera contracts; final art depends on suitable assets and validation.
