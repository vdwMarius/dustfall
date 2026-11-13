# M5p terrain dressing authoring

Source authoring is ready for the Lead's sole editor session after terrain v2.
No editor commands, assets, native builds, commits or performance suites were
run in this worktree. The six references 01/03/06/08/09/10 were visually inspected.
This implements GDD v1.3 section 8; visual and collision traversal acceptance
remain open until the Lead runs the scripts and reviews captures.

## Rules and output

- Flats: seeded, stretched low-frequency noise follows the 60-degree wind axis;
  the noise threshold leaves large bare regions. Small nonblocking stones occupy
  the surviving patches. Landscape collision normals enforce 0–20 degrees.
- Slopes: blocking medium boulders on 20–45-degree ground. Uphill/downhill
  height probes increase acceptance at convex upper shoulders.
- Talus: only native mask value 85 and actual 10–35-degree slopes. Size declines
  from 6.2m to 1m with distance from the top of the first rising wall profile.
- Faces: native mask 255, actual >=50-degree ground, and canyon/escarpment cross
  position. Overlapping 12–16m-wide, 14–18m-tall composites are embedded 62% of
  their height, aligned to the wall tangent with small yaw/roll variation. The
  2.2m candidate lattice captures narrow steep ribbons; global thinning caps
  faces at 3,500 assemblies without leaving only one side of the map dressed.
- Rims: upright teeth along the exact rounded canyon rims and both escarpment
  high edges. Footprint guards remove teeth near descents and the Shelf notch.
- Spires: 26 south shards at 14–62m, 18 north weathered pillars at 18–55m,
  seven east sentinels at 35–80m, seated over their existing plinths. Four
  overlapping, tapered, rotated scan assemblies per spire: 204 mesh instances.
  South/east stacks lean; north pillars remain upright. Packing is seeded and
  fails explicitly if it cannot fit the required counts safely.
- Tracks: the builder duplicates the existing Phase2 automatic landscape
  material (the actual material builder is `build_phase2_wasteland.py`, while
  `build_phase2_terrain.py` is the retired prototype). Existing sand/gravel/rock
  textures and slope blending remain. A world-position mask darkens the track,
  raises roughness and flattens its normal detail. The terrain build already
  supplies its sunken profile. Small stones and old dusty-metal stake meshes
  follow path edges; original routes retain their wider 8.5m half-width safety
  corridor, so their edge dressing sits beyond that guard. No per-metre decals.

Each candidate and final output uses a conservative rotated/scaled mesh XY
footprint against exact polyline segments, round end caps, protected discs and
world bounds. Native one-metre path segments are spatially indexed for the
audit. Airborne dust is excluded from ground-footprint tests. Decorative debris
gets additional conservative PCG exclusion boxes and is included in the final
corridor audit; some original debris may disappear near the new guards.
Existing hand-authored outcrops, hazard posts and gameplay/landmark actors are
preserved; the audit covers PCG output, not navigation through those actors.

## Tuning and budget

`Scripts/Data/world_dressing_phase5.json` supplies the initial typed fields in
`/Game/Data/DA_WorldDressing_Phase5`, with Blueprint data type
`/Game/Data/BP_WorldDressingData_Phase5`. Rebuilds read that saved asset, preserving
designer edits; new JSON fields receive their initial defaults. Change existing
values in the data asset once it exists. Densities (candidate spacing and keep
probability), sizes, slope/height thresholds, masks' neighbourhood rules,
collision authoring settings and category caps are data, not graph literals.
Spire counts/heights come from the resolved terrain feature design.

Expected, unmeasured output: roughly 40–65k rock instances, including several
hundred to low thousands of face tiles and 204 spire pieces. The exact total
depends on the final landscape and guards. Default category caps sum to
79,004 rock instances (including edges, excluding stakes/dust/debris), below
the hard 82,434 ceiling (+15% over 71,682). Category thinning samples the whole
world deterministically. Both planned and actual totals are checked.

All opaque output is Nanite, including a duplicate of the existing cube stake
mesh. Large assemblies duplicate the Phase3 meshes before adding convex hulls;
source scans and source assemblies are unchanged. Collision checks include
`get_convex_collision_count()` and `get_simple_collision_count()` separately.
Convex hull presence does not establish traversal quality or a gap-free face.

All 64 original spatial PCG owners receive per-cell graphs under
`/Game/World/Phase5/PCG/`. Graphs retain only the original dust/debris branches
plus new baked point/spawner branches. Ground sampling is editor-only; saved
PCG/ISM output requires no Python at runtime. All cells rebuild because every
cell's rules changed. No new actor is always-loaded. Large rocks/spires have
no distance culling, but their owners still stream. Far sentinels may require
HLODs; this task does not create HLODs or establish distant visibility. The
existing Phase3 cell Blueprint is not recompiled by this builder: verify saved
per-instance graph assignments after the next normal editor reopen.

## Lead run order and gates

1. Build/run `build_phase5_terrain.py`; wait for
   `Docs/Phase5_TerrainResults.json` status `complete`. Its resolved features,
   `TerrainMasks/paths.raw`, `cliffs.raw` and `polylines.json` must be present.
2. In the sole editor, stop PIE and resolve pre-existing dirty foundation/task
   packages. Run `Scripts/build_phase5_dressing.py` as `__main__`. It pins all
   authoring cells, samples in Slate tick batches, authors graphs, regenerates
   PCG asynchronously, verifies actual transforms/counts, runs the read-only
   audit and saves newly dirty task/map/external actor/component packages only.
   Unrelated dirty packages are excluded from saving.
3. Wait for `Saved/Codex/phase5_dressing_build.json` status `complete`, not just
   editor queue completion. A `failed` report contains the traceback. Original
   Phase3 graph and assets remain available; do not save unrelated packages
   while recovering a failed build. Failure restores original streaming flags.
4. With all 64 cells loaded, run `Scripts/verify_phase5_dressing_editor.py` as
   `__main__`; inspect `Saved/Codex/phase5_dressing_verify.json`. This reads actual
   components, Nanite, collision hull counts, material assignments, mask
   coverage, category totals and corridor violations. Violations must be zero.
   It does not load cells, write assets, alter streaming or run navigation.
5. Run `verify_phase2_routes_editor.py` and the brief `smoke_phase5_editor.py`.
   Capture with `capture_phase5_terrain.py`; inspect its completion report and
   images, including the three added spire views and flat bare-patch view.
   Send critique before changing visual tuning. Do not run Phase3 PCG/debris
   builders afterward: they restore the old graph/output.
6. Profile loaded-cell counts/frame time with `profile_phase2_editor.py` when
   the Lead/user schedules the performance gate. No performance claim is made
   here; heavy profiling and navigation suites remain user-deferred.

The raw masks are 2048-square uint8, row0=minY, col0=minX, extrema inclusive,
read from native `DustfallTerrainFeatures.cpp` and its report bounds. Path-mask
TGA import reverses rows for bottom-left TGA origin; world UVs address texel
centres. Face/talus classifications are consumed exactly (255/85).

## Verification and live risks

Offline: six geometry/determinism tests passed, covering mask orientation,
segment end caps, large leaning footprints, exact indexed-versus-brute-force
corridor checks, deterministic candidates and malformed masks. Python AST
parsing and tuning JSON parsing passed. Run them without launching Unreal:

`Engine/Binaries/ThirdParty/Python3/Win64/python.exe Scripts/test_phase5_dressing_rules.py`

Checked against installed UE headers: PCG CreatePoints supports world coordinate
space and serializable points; graph topology pins/edges and material output
introspection are exposed; static mesh convex collision APIs exist. Not verified
live: Python enum/property spellings, graph duplication and retained upstream
node traversal, imported grayscale sampler orientation, descriptor grouping,
asynchronous completion behaviour, saved instance graph persistence, convex
fit on stretched meshes and final silhouette quality. The build fails on
missing assets, incompatible terrain data, wrong output counts/transforms,
empty categories, missing collision/Nanite or corridor violations. These gates
do not replace captures, short descent/notch traversal or the streaming profile.
