# Phase 3 environment authoring

Use the dedicated editor queue with the foundation map loaded and PIE stopped.
The lead owns editor asset writes. These scripts author Unreal assets; gameplay
does not require Python.

1. Run `Scripts/build_phase3_environment.py` to tune the existing runtime
   environment Data Asset and saved editor lighting. The director's weather,
   time, state-query and notification contract is preserved.
2. Run `Scripts/build_phase3_pcg.py` and wait for
   `Saved/Codex/phase3_pcg_build.json` to report `complete`. Queue completion
   alone does not mean PCG generation finished.
3. Run `Scripts/build_phase3_pcg_debris.py` after the core completes. Its report
   is `Saved/Codex/phase3_pcg_debris_build.json`. This extends the same graph with
   decorative industrial debris around landmark regions.
4. Run `Scripts/capture_phase3_visibility.py` with PIE stopped for temporary
   human-scale and boulder targets at 40, 60 and 100 metres in three daytime
   weather states. Inspect `Saved/Codex/Phase3Visibility/`. The script restores
   fog/light settings and deletes its test actors; it does not save test content.
5. Re-run the player, environment and route regressions; validate first/third
   person gameplay, airlock/interior dust exclusion, packaged reload and frame
   times. Captures and numeric fog values alone are not user acceptance.

`capture_phase3_art.py` records the habitat exterior, living area, workbench and
four sides of an actual generated large-rock instance with warmed Lumen history.
`inspect_phase3_environment.py` audits actual output counts, Nanite, convex hulls,
scale/height ranges, route/home centre clearance and a canonical layout hash.
For exposure tuning, `capture_phase3_lighting_bracket.py` captures three temporary
native world exposure/light combinations, then restores the original settings.

## Native PCG content

Graph: `/Game/World/Phase3/PCG/PCG_DustfallEnvironment`.
Cell Blueprint: `/Game/World/Phase3/Blueprints/BP_DustfallPCGCell`.
Generated meshes/materials live under `/Game/World/Phase3`.

Native Get Landscape Data feeds Surface Samplers. Normal-to-density and density
filtering reject unstable slopes; spatial fractal noise makes geological
clusters and wind-scoured gaps. Create Points describes only authored exclusion
volumes, not randomly baked rock placement. Difference nodes protect full route,
habitat, airlock and landmark footprints. Transform Points varies scale,
rotation and burial; Static Mesh Spawners produce instanced Nanite geometry.
Difference uses binary discrete subtraction so partially overlapping bounds
cannot leak positive-density instances through exclusions. Route boxes extend
the 5.5m traversal guard past both endpoints as well as sideways, covering the
Euclidean segment end caps. Decorative debris instead excludes actual landmark
piece footprints, allowing crash-site dressing inside the broader rock-free
landmark regions.

The denser small-scatter pass uses .009/.006/.004 points per square metre for
the first three scans with 100/120/140m instance end-culling. Native output is
71,838 rock instances in the final full-world audit. Medium and large
formation densities retain their earlier values. Loaded instance counts are
different from rendered or visible instances.

Sixty-four 250 m authoring owners cover the 2 km map. They remain loaded during
generation, then become spatially streamed. Components use Generate On Demand,
so baked static output does not require runtime generation. Generation checks
every owner and records per-cell counts before removing the old Phase 2 rocks.
Verify baked output survives a fresh editor load and cooked build.

The first three small rock scans use normalized, seated pivots. The five larger
scans use three overlapping copies of the same scan at 120-degree rotations,
forming an exterior around inward-facing unfinished backs. These are merged
into reusable Nanite assembly meshes with their original materials and new
convex collision. Do not mistake construction rules for all-sided visual QA:
inspect the assemblies, seams, burial and collision from all walking angles.
Original Quixel meshes remain unchanged. The initial small-scan output may have
the legacy double `SM_` basename; the generator reuses it safely.

## Dust and lighting

Atmosphere starts at noon with fixed EV1000 exposure, Sun96/Sky2 and a .72 storm
light multiplier. NightSky.0005 compensates the exposure lift for sky light.
Fog .18 / .28 / .45 and volumetric extinction.8 retain dust across all three
weather states. The project's original atmospheric scattering/absorption
coefficients are preserved. Warm fog light-color overrides, directional
inscattering(.3,.2,.11), native scene-color tint(1,.65,.35) and saturation.75
remove the blue-grey sky while retaining readable daytime foregrounds. These
are the saved authoring values; user visual acceptance and night/flashlight
balance still need review. Numeric fog densities are not visibility distances.

Two PCG branches distribute bounded ground sheets and suspended veils using
`M_WindblownDust`: lit translucency, continuously panned procedural noise, soft
UV borders, depth fade and distance culling. These use animated Unreal material
sheets, not Niagara. Placement clearance and an explicit material mask remove
these sheets within the habitat's surrounding sanctuary. There is no per-rock
particle emitter. Verify global fog remains unobtrusive inside the sealed hab.

Nanite is enabled on the suitable opaque assemblies; ISM, distance culling,
World Partition and the existing Lumen/VSM rendering baseline are retained.
Translucent dust is deliberately excluded from shadow casting and distance-field
lighting. Profile translucency overdraw, Lumen, fog, shadows and streaming on
the target hardware before claiming an FPS improvement.

## Evidence and limits

Local JSON reports, captures and Unreal logs under `Saved/Codex` are the source
of actual run results. The final full-world audit passed with 64 cells,
71,838 rocks, 370 dust sheets and 195 decorative debris instances, with minimum
rock-centre route clearance about7.8m. These are loaded geometry counts, not
rendered-instance or FPS measurements.

The distant cliff initially looked untextured in SceneCapture images because
its high texture mips were not resident for that secondary camera. Full-mip
capture QA restored visible scan texture/normal detail without changing source
or merged assets; UV samples and material paths remain valid. The art helper
temporarily prestreams the formation and fully loads used texture mips, then
restores those settings. Those images are visual QA, not streaming/performance
evidence; validate normal player-camera approach separately.

This document does not assert that user visual, performance or packaged
acceptance has passed. User
references are in `Docs/References/Phase3/` and the acceptance targets are in
`Docs/Phase3_Plan.md`.

## Hostile relief authoring — 2026-11-13 continuation

`Scripts/build_phase3_terrain.py` now authors the actual Landscape heightfield
through `UDustfallTerrainLibrary` before rebuilding native PCG. The editor-only
native helper reads the base edit layer, saves its exact original 16-bit heights
with section extents to `Scripts/Data/Phase3LandscapeBaseline.bin`, and applies
deterministic hills, ridge masses, windward mounds, a crater, a dry ravine and a
terraced sinkhole. Reauthoring uses that baseline, so relief does not accumulate.
Terrain is saved/cooked as normal Landscape render and collision data; runtime
does not depend on Python or the terrain authoring function.

Home, landmark footprints and the shared route polylines retain original heights
with smooth transition bands. The pit is near (-85,-65) metres with an east escape
ramp; the ravine is near (180,-185) metres with a broad south escape bank and
protected route saddle. Scanned composite outcrops follow traced footprint heights
and conceal their bases. Seven amber survey stakes mark hazardous rims. Native
`ADustfallTerrainHazardDirector` handles impact suit damage and safe-rim recovery
cache placement after fatal falls.

Run order: compiled editor -> terrain builder -> wait for
`Saved/Codex/phase3_terrain_build.json` status `complete` -> rebuild native PCG ->
rebuild PCG debris. The terrain report records real feature collision heights,
outcrop counts and lightweight protected-route collision sampling. A separate
optional `verify_phase3_hazards_editor.py` exercises physical pit landing damage,
walking escape and fatal safe-rim cache recovery using isolated QA save slots.

At the user's later direction, heavy regression/traversal/performance testing is
left for user testing. The new terrain scripts have passed Python syntax checks;
native compilation and terrain authoring results are recorded below. Package
results remain the integration lead's responsibility. Earlier 71,838-rock
audit/performance results predate relief.

### Actual authoring results

Native editor compilation succeeded. Terrain authoring completed across all 256
Landscape components / 4,068,289 vertices, changing 3,360,817 vertices with a
designed height delta of -12.37 to +61.00 metres. Real collision traces measured
home at 0m, the near hill at 24.71m, the northern ridge at 48.24m, pit floor at
-8.52m, east ramp at +2.13m, ravine probe at -8.16m and crater floor at -7.32m.
The 217 route collision samples measured a maximum grade of 0.00534; these are
authoring sanity probes and do not establish walking regression success.

Saved 64 traced scanned outcrops, seven warning stakes and the always-loaded
native impact/cache-safety director. Rebuilt all 64 PCG cells on the new terrain:
71,682 rocks, 364 dust sheets and 195 decorative debris instances. Saved dirty
Landscape external packages and generated actors. Exact baseline SHA-256:
`548cbe72e5631233e7c0522d455c97e027b7c5c42b04f3329101a9b044914525`.
See `Phase3_TerrainResults.json` for measured authoring output.

Two lightweight normal-residency SceneCapture images under
`Saved/Codex/Phase3Terrain/` were inspected: the sinkhole depression and amber
rim stakes are visible; the nearby hill has real rising terrain and seated large
outcrops. Readable warm dusty daylight is retained in these views. These are two
editor views, not the 40/60/100m weather/view matrix, subjective reference-quality
acceptance, player-camera texture streaming or runtime performance evidence.
Full navigation, fall/recovery regression and performance remain deferred to the
user; the optional hazard verifier has not been run.
