# Development progress

## 2026-11-14 — Resume: atmosphere rounds 3–4, terrain validation, habitat kit import

Lead: Claude. Workers: Codex Sol medium (M5t rounds 2–4, M6 rounds 3–4, M4 kit
round 2). Session resumed after a lost chat; worker results were recovered from
the worktrees.

Completed:
- M6 atmosphere: fog seam removed (both fog systems share one source radiance);
  thinner wind streaks, ground-hugging dust sheets, flashlight cone on dust.
  Storm far silhouettes were lost in round 3 and restored by raising
  `StormLightMultiplier` .52 -> 2.0 (fog look unchanged). A worker proposal that
  darkened the storm fog instead was rejected (daytime storms went near black).
  Captures: `Docs/Phase5/AtmosphereV3_*.png`, `AtmosphereV4_storm_day*.png`.
- M5t terrain: `ValidateTerrainFeatures` dry run (reports every problem in one
  pass), self-solving switchback descents, guard-pinned profiles, simultaneous
  path carving. **Terrain v2 is applied and saved** (canyon "the Scar",
  escarpments, six descents, two new trails). The first applies failed because
  the landscape has a second additive edit layer ("Flat Middle") and the tool
  measured layer 0 alone; authoring now solves on the merged surface and
  writes the inverse into layer 0. Note: a validate-only run now marks the
  landscape proxy packages dirty (read-only access to the upper layer);
  restart the editor without saving afterwards.
- M4 kit: 36-piece Blender habitat kit generated and imported to
  `/Game/Habitat/Kit` (importer scale/socket/collision checks passed). Not yet
  placed in the level; the old shelter is unchanged.

Tested:
- Editor build: zero errors, zero warnings. `Dustfall.Core`: 14/14.
- `smoke_phase5_editor.py` passed after the atmosphere changes.
- Terrain: all 11 paths/descents valid on the merged surface (new trails
  grade <= 0.11, descents 0.18-0.25, cross slope <= 0.011). After apply,
  collision matched authored heights within 0.52 cm at 1,427 points; protected
  sites (home, wreck, ruin, cruiser, routes) verified unmoved; 84 packages
  saved; smoke passed again on the new terrain.
- Terrain captures NOT taken (`capture_phase5_terrain.py` has a Python API
  bug). PCG rocks/debris still sit on the old ground until the M5p dressing
  rebuild runs (in progress): expect floating/buried rocks near the canyon.
- Storm captures at light x2: figures clear at 5/10 m, faint at 15–25 m,
  ridges and the 150 m box readable as faint silhouettes.

Not tested / limits:
- Only the two storm-day views were re-captured after the light change; storm
  at night, haze, dusk and calm were not re-captured with the final values.
  Haze 150 m contrast measured about 0 in round 3 and was not retuned.
- Dust motion (streaks, ground sheets), flashlight cone feel and GPU cost: user
  playtest / profiling only. No packaged build of this state.
- Round 3 and 4 terrain C++ was reviewed by build, tests and dry run, not
  line by line.

Next: PCG dressing rebuild on the new terrain (M5p) and terrain captures,
place the habitat kit, then the performance lock. Nobody has walked the new
terrain yet: descents, trails and fall risks need a user playtest.

## 2026-11-13 — M3b: native survival director, Enhanced Input

Lead: Claude. Workers: Codex Sol medium (M3b-1 C++, M3b-2 input, M3b-3 scripts).

Completed:
- `ADustfallSurvivalDirector` (C++) ports the script-generated Blueprint
  survival rules with identical defaults: drain/refill, sprint exhaustion,
  death, clone respawn, crate, legacy schema-1 save. Each rate has a modifier
  stack (`SetSuitModifier`) and capacities accept bonuses (`SetCapacityBonus`).
- `/Game/Systems/BP_SurvivalDirector` reparented to it by
  `build_phase5_survival_native.py`; Blueprint graphs/variables removed, all 26
  values, object references and the level actor identity preserved. New native
  tuning asset `/Game/Data/DA_Survival` copied from `DA_Survival_Phase3`
  (old asset kept). Backups: `Saved/Codex/Backup_M3b3/`.
- Exploration actions use Enhanced Input (`/Game/Player/Input/IA_Dustfall_*`,
  `IMC_DustfallExploration`, `/Game/Data/DA_Input_Dustfall`); raw key polling
  remains only as a fallback when no config is assigned.
- The historical Phase 3 HUD Blueprint was rebuilt against the native tuning
  class so it compiles; the game HUD is still the native exploration HUD.
  `build_phase3_hud.py` no longer reassigns the GameMode HUD by default.

Tested:
- Editor build: zero errors, zero warnings. `Dustfall.Core`: 7/7.
- `smoke_phase4_editor.py` 19/19 and new `smoke_phase5_editor.py` 45/45
  (oxygen drain -0.12/s, 2x modifier -0.24/s, cleared -0.12/s, refill +8/s,
  capacity bonus, death/clone/crate, save round-trip). Log confirms the
  Enhanced Input path is active in PIE.

Not tested / limits:
- Physical keys (E/Q/Tab/J/B/F5/F9/F8), E at the airlock versus E on salvage,
  and Shift sprint feel: user playtest only. No packaged build yet.
- The native director still binds raw E/F5/F9 for crate/save/load exactly as
  the Blueprint did (kept for parity); to be folded into the input config.
- Exploration HUD bars still assume a maximum of 100; fix with suit upgrades.
- Unreal Python gaps found live and worked around in the scripts:
  `Blueprint.ubergraph_pages` is not exposed; `unreal.Key()` takes no arguments.
- Editor note: force-closing the editor with a dirty package makes the next
  start block on a restore dialog; delete `Saved/Autosaves/PackageRestoreData.json`.

Interim package: `Builds/Phase5/Windows/Play_DUSTFALL.cmd` (cook 0 errors,
0 warnings). Isolated 600-frame startup smoke: exit 0, foundation map loaded,
no runtime errors, Enhanced Input path active. Not a gameplay, traversal or
performance test.

Next: habitat module kit + shelter finish, paths and canyons, performance lock.

## 2026-11-13 — Phase 5 start: atmosphere retune (M1), exploration core rework (M3a)

Lead: Claude. Workers: Codex Terra medium (M1 scripts, M3a validation fix) and
Sol medium (M3a). User Phase 4 playtest: shelter far from finished; environment
acceptable but needs paths and canyons; storms must obscure more; daytime too
bright. All other Phase 4 checklist items remain open (not reported).

Completed:
- Repository: the unpushed local commit containing untracked Megascans imports
  (36 blobs over 100 MB) was redone with docs only and pushed. Imports and
  `mcp.log` are now ignored. Stale `Docs/CLAUDE.md` removed; root `CLAUDE.md`
  is authoritative.
- GDD v1.2 (§8): dim dust-filtered daylight, 40+ m in calm/haze, about 20 m in
  settled storms.
- M1: `DA_Environment_Phase2` and level lights retuned through
  `build_phase3_environment.py`: fog calm/haze/storm .30/.60/2.2, sun 42,
  day sky .95, storm light x.52, rust fog colour .46/.23/.09.
- M3a: exploration code split per system (`Systems/`, `UI/`); gameplay literals
  moved to `UDustfallExplorationTuning` with unchanged defaults; Strain gain is
  base x stacked modifiers (`SetStrainModifier`), raw value still private;
  data-driven symptom pool; save schema 3 (beacon ids) with v2 migration that
  clamps out-of-range values instead of rejecting; node registry replaces
  per-frame actor iteration.

Tested:
- Editor build: zero errors, zero warnings. `Dustfall.Core`: 5/5 passed
  (resource, habitat, modifier stack, save migration, payload overflow).
- `smoke_phase4_editor.py`: 19/19 after both changes.
- In-game (PIE, 1495x862) screenshots with human-scale targets at 10/20/30/40 m:
  `Docs/Phase5/Atmosphere_*.png`. Storm: 20 m visible, 30 m marginal, 40 m gone.
- Baseline editor profile before the changes, seven stationary cases:
  frame median 16.6-16.7 ms (60 fps cap), p99 18.8-19.5 ms, worst 27.3 ms,
  GPU median 3.2-3.6 ms, game thread about 9 ms. All 64 PCG cells (71,682
  rocks) stay loaded everywhere except the far corner.

Not tested / limits:
- No packaged build, no traversal or 1080p packaged profile, no night captures.
- The schema-3 migration has unit tests only; no real schema-2 user save from
  the packaged build was loaded. Editor save games were backed up to
  `Saved/SaveGames_backup_pre_schema3`.
- Behaviour changes: storm and low-suit Strain modifiers now multiply when both
  apply; a symptom event shows one weighted effect, not both.
- Look and feel of the new atmosphere needs the user's eyes.

Next: M3b native suit component + Enhanced Input, then habitat module kit and
shelter finish, paths and canyons, performance lock.

## 2026-11-13 — main-only delivery and Phase 5 handoff

Prepared `HANDOFF_Phase5.md` with current native/Blueprint contracts, asset
paths, save schemas, authoring/build/verify scripts, measured evidence and
unfinished work. Expanded the Phase4 checklist with unchecked acceptance
items and a result-recording template. Heavy tests remain user-deferred.

The combined unpublished branch is preserved. Delivery history on main is
split into Phase3, Phase4 and documentation. The Phase3 GameMode uses its
suit HUD; Phase4 switches to the native exploration HUD. The final code/asset
tree is preserved byte-for-byte relative to the packaged review build; the
interim HUD asset is used only in the Phase3 commit. No new gameplay tests or
content changes were introduced while preparing history.

Audit all tracked/outgoing blobs against100MB and each staged tree for
Saved/Intermediate/Builds/DerivedDataCache and unrelated imports before push.
Push only main to `https://github.com/vdwMarius/dustfall.git`, never the backup
or preserved combined feature branch. Actual audit results are recorded below.

Repository pre-push audit **passed**:1,121 tracked files; largest24,799,535bytes
(24.80MB). No tracked file or blob anywhere in the three outgoing commits is
over100,000,000bytes. Every staged commit tree excludes Saved/, Intermediate/,
Builds/, DerivedDataCache/, Content/Megascans_8k/ and the source ZIP. The active
index is clean after the split; both unrelated imports remain untracked.
Phase3 commit `bf0f954`, Phase4 commit `a046107`; final docs form the third
commit. Remote main was fetched and still matches base `60004c1`, allowing
an ordinary fast-forward with the explicit main-to-main refspec. The combined
local history and backup branch remain unchanged and are not push targets.

Publication **succeeded** after the user explicitly authorized uploading the
DUSTFALL source/assets to `https://github.com/vdwMarius/dustfall` on main.
The explicit main-to-main push advanced remote main from `60004c1` to
`f365d7b`, publishing Phase3 `bf0f954`, Phase4 `a046107` and docs `f365d7b`.
This small follow-up docs commit records the successful publication. Earlier
automatic approval blocks are resolved; no backup/feature branch or tags were
pushed. Both unrelated imports remain untracked. Heavy testing stays deferred.

## 2026-11-13 — rounded pod, real relief and Phase 4 review build

Continued the complete uncommitted Phase 3 tree with three fresh specialists
and one serialized Unreal asset writer. Preserved unrelated Megascans imports.
User subsequently asked to defer heavy testing to their playtest and cap model
effort at medium; no new full regressions/performance/stress runs were made.

Saved eleven custom curved pod meshes, worn panels/damage/repairs/windows,
retained functional furnished interior/airlock/spawn and removed the old slab.
Authored real landscape heightfield relief (-12.37..+61m delta), 64 jagged
outcrops, marked pit/ravine and native impact/safe-rim crate rules. Collision
probes confirm hills/depressions and nearly level protected routes. Rebuilt
64 PCG cells: 71,682 rocks, 364 dust sheets, 195 debris. Minimal art captures
show the actual rounded pod and rising terrain; reference-quality finish and
40+m player-view acceptance remain open.

Phase 4 implements native typed inventory/cache/save migration, 12 stable
salvage/lore nodes, scanner, glowing persistent beacons with PowerCell refund,
home guidance, journal, four records, temporary private Strain and F8 symptom
toggle. Added an accessible crashed transport cargo/recorder section; nine
ground probes/seven static capsule sweeps pass after correcting the ramp lip.
The Phase 3 cook exposed a pruned save-existence node; repaired its execution
path and repeatable builder. Actual legacy load and scalar migration pass.

Final editor C++ compilation passed. Brief isolated Phase 4 PIE smoke passed
19/19 checks; actual HUD/inventory screenshot saved. Both Phase 3 and Phase 4
Windows archives built and passed short isolated packaged startup/clean-exit
smokes. The preliminary Phase 3 artifact predates the save-load repair; use
the final Phase 4 build, whose cook has zero errors and zero warnings.
Launcher: `Builds/Phase4/Windows/Play_DUSTFALL.cmd` (1920x1080 High).

Heavy gameplay/hazard regression, final fresh-restart/cooked-layout persistence,
physical keys/audio/visual acceptance, packaged traversal/PSO/performance and
mid-range stable60 remain deferred to user. Review-build Canvas UI, modular
ship/pod finish, Epic mannequin and text/scanner-only initial symptoms remain
explicit limits. Crafting/progression/decoration/cosmetics/full cruiser and
psychological/audio layer are later work. See `HANDOFF_Phase4.md`,
`Docs/Phase4_Validation.md` and `Docs/Phase4_Playtest_Checklist.md`.

The older entries below are historical evidence, not current acceptance.

Historical implementation commit: `0fdd58b`, preserved locally. Earlier
feature-branch push attempts were rejected by automatic approval review and
never uploaded. The latest instruction supersedes those attempts: split the
commits and push main only. Unrelated Megascans folder/source ZIP remain
untracked and excluded.

## 2026-11-13 — current handoff and unfinished Phase 3 work

Updated `HANDOFF_Phase3.md` to replace the obsolete Phase 2 starting-point text.
Current branch: `codex/phase3-survival-and-pcg`; HEAD remains `60004c1`.
Phase 3 work is uncommitted, including new assets/scripts and the C++ runtime
module. No Phase 3 commit/push or Windows package was completed. No specialist
worker is currently running; fresh workers can continue from the saved files.

Implemented with three specialists plus lead: native Blueprint-callable suit/
sanctuary/exhaustion rules, survival/HUD, walkable prototype habitat/interlocked
airlock, clone respawn, minimal recovery cache/save, native PCG scatter/debris,
composite rocks and brighter persistent warm dust. Native editor compilation
and both C++ automation tests passed. All five runtime suites passed, including
18 navigation waypoints in three weather/time cases. Final PCG audit passed:
71,838 rocks, 370 dust sheets, 195 debris, 64 spatial cells. Seven editor profiling
cases completed at 691x464 High; a 91.791 ms CPU hitch remains. See Phase 3
validation/results/performance docs for evidence and limits.

User feedback: the square/basic habitat is a testing prototype, not final art.
Finish a rounded damaged industrial pod and convincing interior toward the
references. Terrain is too flat: add actual hills, mounds, jagged rocky zones,
ridges/depressions/ravines and pitfalls with varied elevation and deliberate,
readable hazards. More small scatter alone is insufficient. These requirements
are in the handoff/plan for the next environment and habitat workers.

Still unfinished: terrain/habitat corrections, final dense-layout reload/cooked
persistence, Phase 3 packaging/smoke/performance tests, physical input/audio/
visual acceptance, and commit/push of verified work. The earlier 7,881-instance
restart check does not validate final dense-layout persistence. Finish these
gates before Phase 4. Next-chat prompt: `NEXT_CHAT_Phase4_PROMPT.md`.

## 2026-11-11 — user playtest feedback and Phase 3 priorities

User confirmed testing the Phase 2 build and reported unnatural rock placement,
incomplete/open-backed rock scans, insufficient height/size variation, overly
dark daytime and insufficient persistent dust/fog. Acceptance remains open;
unreported checklist items are not marked passed.

Recorded the first Phase 3 module as PCG environment placement/scattering,
all-sided composite boulders/cliffs, varied natural formations and brighter
daytime inside continuous dust/sandstorm haze, with silhouettes readable at
40+ metres. Use appropriate Unreal tools including Nanite, Lumen, instancing
and World Partition, validated against frame-time/streaming measurements.
Saved all four reference images and documented habitat, interior, wreck and
suit direction in `Docs/Phase3_Plan.md`. Updated the handoff accordingly.

This update changes planning/documentation only; game assets and the existing
packaged build are unchanged. Next: implement and validate Module 3A, then the
habitat/airlock, survival/HUD, and death/recovery/save modules.

## 2026-11-11 — Phase 2 world and runtime atmosphere module

Created exactly five agents, sequencing the four specialists within the runtime
limit. Inspected clean main at 5191249 and the open foundation editor before
authoring. Used one editor writer and preserved later unrelated Fab additions.

Completed:

- Imported twenty user-owned Quixel downloads: eight 2K surfaces and twelve
  Nanite meshes. Recorded archive hashes, source IDs and paths in the asset manifest.
- Replaced mound placeholders with 2,185 scanned rock instances in 64 spatial HISM
  cells, seed 2042. Added world-coordinate sand/gravel and slope-driven rock material.
- Added exterior wreck, ruin and roughly 200 m cruiser prototypes, 80 scanned
  industrial props, 36 route stakes and a gentle return-home ramp. The cruiser
  occupies a measured flatter site near (-550 m, +50 m).
- Runtime Blueprint director reads DA_Environment_Phase2 for calm/haze/storm,
  eased transitions, autonomous cycling, a 30-minute day, night lighting and wind.
  SetWeather, SetTimeOfDay, GetEnvironmentState and OnEnvironmentChanged expose
  neutral future-system hooks. No runtime Python or survival/Strain mechanics.
- Project-owned synthesized wind loops through an AudioComponent. This version
  uses SoundWave, not MetaSound; subjective listening review remains.
- Repeatable module builders and guarded legacy scripts preserve player graphs,
  template paths and Phase 2 lighting. Probe assets and generated files are ignored.

Tested:

- Revised environment PIE suite passed, including actual fog targets after blends,
  automatic storm transition, clock, query, wind playback/volume, sun/skylight and
  player movement. Full Phase 1 regression passed in a visible editor.
- Physical V/F/Space and mouse look passed. Brief Shift input did not establish
  sustained physical sprint; callable events verify its speed change.
- Final collision-based navigation passed all 18 waypoints and returned home in
  day/calm, night/haze and day/storm: about 2.03 km each, over 6 km total. Tests
  used 4x game time and are not performance measurements.
- All downloaded textures inspected at 2048x2048; Nanite and convex collision
  checked separately. Development build/cook/stage/archive succeeded. Initial
  cook reported zero errors and zero warnings.

CommonUI requires Unreal's generated temporary launch target for packaging;
it remains under ignored Intermediate/Binaries, with no native gameplay Source
module. MCP is restricted to Editor targets because its descriptor is NoRedist.

Finalization: accepted visually denser storm fog (1.0), re-ran the full runtime
environment suite successfully, and packaged the exact saved content into
Builds/Phase2/Windows. Completed seven-location final editor CSV profiling and
streaming counts: 15–45 loaded rock cells, frame median about 16.67 ms, p95
17.465–19.618 ms at 691×464 High. Isolated spikes remain; this is not a 1080p
or representative target-hardware guarantee. Added a 1080p High playtest launcher,
reproducible packaging script, CSV analyzer, user checklist and Phase 3 handoff.
Packaged startup, default map/GameMode, physical V/F and clean profiler exit passed.
1080p High capture (5,400 frames after warmup): median 16.652 ms, p95 18.839 ms,
p99 20.622 ms, maximum 107.442 ms; GPU median 4.093 ms. Cold PSO creation hitches
and later waits remain a documented performance limitation, not a stable-60 claim.

Next: user acceptance using Docs/Phase2_Playtest_Checklist.md, then Phase 3 per
HANDOFF_Phase3.md. Stable 60+ FPS on representative mid-range hardware is not
established. See Docs/Phase2_Validation.md for evidence and remaining limits. Unrelated
Content/Megascans_8k imports and the source ZIP in Content remain outside this module.

## 2026-11-10 — Phase 1: Core Foundation

Completed a Blueprint foundation using UE 5.8.4's third-person template and
project-owned character / GameMode children. Added first-person switching,
camera-mounted flashlight and sprint. Created the project-owned Open World map
with World Partition, dense warm volumetric dust, fixed exposure, brown terrain,
and a sealed temporary habitat shell with a warm entrance light. Both startup
and game default maps point to the foundation.

Player and atmosphere values live in Blueprint Data Assets and are applied by
editor authoring scripts. Python has no gameplay runtime role. Epic template
dependencies retain their original paths. Fab / Quixel acquisition is planned
for Phase 2; no acquired packs are claimed in this phase.

Validated in the editor:

- Template and project player / GameMode Blueprints compile without errors.
- The project character is possessed at the intended exterior spawn; the
  settled capsule centre is about 92 cm above the collision surface.
- Enhanced Input action injection moves the pawn about 413 cm and produces a
  jump of about 128 cm. Walking toward the habitat stops against the shell.
- Flashlight toggles, camera arm switches 400 cm to 0 cm and back, and sprint
  speed changes 500 to 750 cm/s and restores correctly.
- Physical viewport input confirms F, V, Space, brief movement and mouse look.
  Automated callable events validate sprint; the short physical Shift chord
  did not provide a sustained speed measurement.
- World Settings shows Enable Streaming checked. Runtime CVars confirm Nanite,
  Lumen GI / reflections and virtual shadows enabled.
- A repeated full authoring build succeeds. Visual review confirms warm dust,
  a visible entrance lamp and flashlight illumination in first person.
- Editor spot check: approximately 60 FPS / 16.7 ms. This is not a representative
  mid-range hardware benchmark; stable 60+ FPS remains a profiling target.

Reports are local under `Saved/Codex` (`pie_report.json`, `keyboard_report.json`,
editor logs); they are intentionally ignored by Git. A packaged build / cook has
not been validated.

Next: **Phase 2 — World & Atmosphere**. Acquire and integrate Fab / Quixel
Megascans surfaces, rocks and debris; develop dust storms, day/night, wind
ambience, wreck / cruiser / ruin landmarks, and profile streaming and frame time.
Survival, habitat interior / airlock, death and respawn remain Phase 3. Hidden
Strain and temporary hallucinations follow the later phases in the GDD.

Fresh editor startup loaded the saved foundation map without an explicit map
argument, and the complete PIE smoke test passed again with no reported errors.
No Phase 1 implementation blockers remain.

GitHub rejected the first push because the original unpublished history contained
a 122 MB generated asset-registry cache. The original history is preserved locally
on `codex/phase1-before-history-cleanup`. Generated `Intermediate`, `Saved` and
`DerivedDataCache` entries were removed from `main` history; the tested game tree
was unchanged. Only `main` is pushed.
