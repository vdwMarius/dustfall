# DUSTFALL — Phase 5 continuation handoff

Updated 2026-11-13. Read this, `PROGRESS.md`, `README.md`, `DUSTFALL_GDD.md`,
`Docs/Phase4_Validation.md` and the Phase 4 playtest checklist before continuing.

## Delivery and repository

Workspace `G:\ue\dustfall`; UE **5.8.4**. Publish **main only** to
`https://github.com/vdwMarius/dustfall.git`. Never push
`codex/phase1-before-history-cleanup`. The previous combined local commits on
`codex/phase3-survival-and-pcg` are preserved; main is split into Phase 3,
Phase 4 and documentation commits. Do not reset to Phase 2 or discard work.
`Content/Megascans_8k/` and `Content/Megascans_RockyGrass_Source.zip` are
unrelated user imports: leave them untracked. Do not stage `Saved/`,
`Intermediate/`, `Builds/` or `DerivedDataCache/`, or any file over 100 MB.
The final pre-push audit is recorded in `PROGRESS.md`; verify local/remote
main equality after delivery when checking publication state.

**Publication pending:** automatic approval review rejected the main-to-main
push, requiring explicit user authorization to upload the DUSTFALL source and
assets to `https://github.com/vdwMarius/dustfall.git`. No upload occurred; remote
main remains at Phase2 base `60004c1`. The three local commits are ready, and
all size/exclusion audits passed. Do not bypass this rejection through another
tool or remote; obtain the specific authorization before retrying main only.

Runnable review build: `Builds/Phase4/Windows/Play_DUSTFALL.cmd`, 1920x1080
High. Keep the complete Windows folder; Alt+F4 exits. Builds are local ignored
artifacts, not included in Git. The earlier Phase 3 package predates the
save-loading repair; use Phase 4. Both phases are implemented, but final
acceptance is still open. Art/UI remain review quality.

## Latest user constraints

Leave heavy testing to the user's playtest to reduce usage. Do not automatically
run full regression, stress, performance, fresh-process persistence or visibility
suites. Use targeted checks for reported defects. Model reasoning effort must
not exceed **medium**. Start from the user's playtest feedback; do not assume
that passing smoke checks accepts the environment, controls or performance.
No Unreal authoring editor/writer should remain running after delivery; inspect
actual processes, map and dirty packages before the next authoring session.

## Runtime contracts and asset paths

| System | Saved asset / native type | Contract |
| --- | --- | --- |
| World | `/Game/World/Maps/L_Dustfall_Foundation` | 2km World Partition landscape; runtime streaming enabled. |
| Player | `/Game/Player/BP_DustfallCharacter` | Preserve Epic mannequin, animation and Enhanced Input dependencies. WASD/mouse, Shift, Space, V view, F flashlight. |
| GameMode | `/Game/Core/BP_DustfallGameMode` | Phase 4 HUD is native `ADustfallExplorationHUD`; historical Phase 3 HUD is `/Game/UI/BP_DustfallSuitHUD`. |
| Habitat | `/Game/Habitat/BP_DustfallHabitatDirector` | `HabitatOrigin`, `InteriorSpawn`, `InnerDoor`, `OuterDoor`, `DF_RequestAirlock`. E operates interlocked doors. |
| Suit | `/Game/Systems/BP_SurvivalDirector` | `GetSuitState`, `SaveProgress`, `LoadProgress`, `RecoverCrate`, `RespawnClone`, `RefreshRecoveryCache`. Owns four resources, clone and crate presentation. |
| Suit tuning | `/Game/Data/DA_Survival_Phase3` | Data-driven drain/refill/sprint/warning/recovery rules; native `UDustfallSurvivalLibrary` supplies shared rules. |
| Recovery | `/Game/Systems/BP_DeathCrate`, `/Game/Systems/M_RecoveryCache` | Nonblocking visible/lit recovery actor; typed payload authority is exploration, not scalar scrap. |
| Environment | `/Game/World/Blueprints/BP_DustfallEnvironmentDirector`, `/Game/Data/DA_Environment_Phase2` | Preserve `SetWeather`, `SetTimeOfDay`, `GetEnvironmentState`, `OnEnvironmentChanged`, normalized `StormIntensity`. |
| PCG | `/Game/World/Phase3/PCG/PCG_DustfallEnvironment`, `/Game/World/Phase3/Blueprints/BP_DustfallPCGCell` | Native seeded landscape/slope/noise sampling, route/home masks, editor-baked instanced output, no gameplay Python. |
| Exploration | `ADustfallExplorationDirector`, `ADustfallSalvageNode` | Always-loaded director/nodes, stable authored IDs, typed inventory/claims, scanner/beacons/journal. |
| Exploration tuning | `/Game/Data/DA_Exploration_Phase4` (`UDustfallExplorationTuning`) | Capacity80; interaction275cm; scanner140m, 2 power, 7s reveal/8s cooldown; max6 beacons; Strain rates/thresholds. |
| Fall hazards | `ADustfallTerrainHazardDirector` | Always loaded. Hard landing damage above1050cm/s; .065 integrity per excess cm/s. Fatal fall cache goes to last grounded rim. Exploration ticks after relocation. |

The habitat anchor is `(0,0,50)`cm. Sanctuary centre `(0,0,285)`, half extent
`(475,325,185)`, clone capsule spawn `(-120,0,198)`. Main floor top Z100cm;
inner/outer door planes X500/X1000. Near door opens0–4s, both seal4–6s,
far door opens6–10s, cycle ends12s. Occupied doorways pause closure. Preserve
the capsule-safe collision proxies and sanctuary contract when changing art.

Custom rounded pod meshes/materials live under `/Game/Habitat/Meshes` and
`/Game/Habitat/Materials`; procedural source is `Scripts/habitat_pod_meshes.py`.
Eleven custom mesh groups form panels/liner/ribs/endcaps/windows/damage/wear.
The exact original landscape baseline is
`Scripts/Data/Phase3LandscapeBaseline.bin` (8.14MB); preserve it for idempotent
heightfield authoring. Native editor-only `UDustfallTerrainLibrary` performs
real height/collision updates, with editor-only Landscape/Foliage/RHI/RenderCore
dependencies. Nanite/Lumen/VSM and terrain-aware PCG remain enabled.

Final generation:64 PCG cells,71,682 rocks,364 dust sheets,195 decorative debris,
64 authored jagged outcrops and7 amber pit/ravine rim stakes. Actual authored
height delta -12.37..+61m; protected routes stay nearly level. Measured pit
floor(-85,-65)m is -8.52m Z, ravine near(180,-185)m is -8.16m Z. Escape slopes
are east of pit/south of ravine; real escape/fatal-cache gameplay is unaccepted.
Read `Docs/Phase3_TerrainResults.json` and `Docs/Phase3_Environment.md`.

The accessible transport is at `(15000,10000,0)`cm, tagged `DF_Phase4_Wreck`.
Board from `(13100,9650)` via a7.5-degree ramp; deck top Z100cm, clear aisle
and recorder alcove. Salvage at `(14350,10320,290)` and `(15500,10320,290)`;
recorder front lip `(15900,9435,300)`. `build_phase4_wreck.py` replaces only
the old tagged transport; leave the separate cruiser and ruin intact.

## Inventory, discovery, saving and Strain

Twelve stable nodes include eight salvage caches and four lore records.
Types: Scrap, Wiring, Glass, Polymer, PowerCell, AlienFragment. E collects a
nearby visible node/record or recovers a crate. Capacity blocks new salvage
without deleting it. Recovering owned cache payload may exceed capacity to
avoid discarding player property. Repeated deaths accumulate the unrecovered
typed payload at the latest death site; recovery transfers once.

Q spends suit power for scanner markers; Tab inventory, J journal. B places a
glowing physical beacon for one PowerCell; B nearby removes it and refunds
the cell. Saved beacon positions reconstruct nonblocking runtime posts/lamps.
Home guidance remains reliable. Inventory/journal do not pause survival.

Survival slot remains `Dustfall_Phase3` (schema1); companion
`Dustfall_Phase3_Exploration` (`UDustfallExplorationSave`, schema2) is the full
authoritative snapshot: suit, location, clone, typed carried/recovery payload,
crate state/location, claimed nodes, journal, beacons, private Strain and symptom
setting. Missing companion migrates scalar carried/cached Scrap. Invalid
versions/data are rejected. Preserve both user save files. F5 saves, F9 loads;
death/recovery and periodic autosave also save. The Blueprint LoadProgress
execution pin was repaired; `repair_phase3_load.py` applies that narrow repair
and `build_phase3_survival.py` now generates the correct graph.

Strain is private and never numeric on HUD. Exterior time, storms, low suit,
deaths and lore increase it; sanctuary reduces it and interrupts symptoms.
Initial symptoms are temporary carrier-overlap text/unresolved scanner echo.
F8 disables/enables them and persists the accessibility choice. Critical suit
telemetry/warnings stay accurate; no permanent hallucination world changes.

## Authoring, build and verification

One asset writer only. Compile native editor code with the editor closed:

```powershell
& 'G:/Program Files/UE_5.8/Engine/Build/BatchFiles/Build.bat' dustfallEditor Win64 Development '-Project=G:/ue/dustfall/dustfall.uproject' -WaitMutex -NoHotReloadFromIDE
```

Dedicated queue: `Scripts/editor_session.py`, command
`Saved/Codex/editor_command.py`, result `Saved/Codex/editor_result.txt`.
Load whole-world authoring cells with `load_phase3_authoring_cells.py`; this
does not disable runtime streaming. Save external actor/component packages
as well as the map. Do not use legacy Phase1/2 world-reset builders.

Repeatable authoring order: `build_phase3.py` sequences habitat/suit/HUD/climate,
terrain, core PCG, debris with asynchronous completion gates; then run
`build_phase4_wreck.py` and `build_phase4.py` to restore Phase4 actors/HUD.
Wait for actual JSON completion, not just the queue's execution result.

| Helper | Use / result |
| --- | --- |
| `smoke_phase4_editor.py` | Brief callable PIE checks; isolated QA slots, restores authored slot. Evidence `Docs/Phase4_SmokeResults.json`. |
| `verify_phase3_editor.py` | Full serial survival/habitat/player/environment/navigation regressions; user-deferred. |
| `verify_phase3_hazards_editor.py` | Actual fall/escape/fatal-cache traversal; prepared but unrun. |
| `verify_layout_persistence.py` | Full loaded layout hash before/after a real editor restart; prepared but final layout unverified. |
| `inspect_phase3_environment.py` | Read-only PCG counts, masks, renderer/Nanite audit. |
| `capture_phase3_art.py`, `capture_phase3_terrain.py`, `capture_phase3_visibility.py` | Art/terrain/distance evidence; temporary capture-only mip overrides must be restored. |
| `profile_phase3_editor.py`, `summarize_phase3_csv.py` | Profiling helpers; no new heavy profiling requested. |
| `package_phase4.ps1` | Native Game build/cook/stage/archive to ignored `Builds/Phase4`. |
| `smoke_packaged.ps1 -Phase Phase4` |600-frame stationary startup/clean-exit check, isolated UserDir; not gameplay/performance acceptance. |

Native automation filter `Dustfall.Core`; historical resource/boundary tests
passed before latest terrain/art changes. Final native Editor/Game builds
passed; Phase4 cook had **0 errors/0 warnings**. The brief19-check PIE smoke
passed, including actual legacy load, schema migration, world salvage/lore,
scanner, beacon/refund, lit crate, typed death/recovery/no duplicate and native
snapshot reload. Actual HUD screenshot: `Docs/Phase4_HUDSmoke.png`. Packaged
startup loaded the foundation and exited0 without runtime errors; evidence
`Docs/Phase4_PackagedSmoke.json` / `Docs/Phase4_Validation.md`.

## Unfinished and next scope

Full Phase3/4 acceptance is **not complete**: fresh-process save and final
dense/cooked layout persistence, full regressions/hazard escape, physical keys,
audio, normal texture streaming, both-view40/60/100m weather/night readability,
packaged traversal/PSO/hitch profiling and representative mid-range60FPS remain
for the user. Historical691x464 editor results do not establish1080p acceptance.
Use `Docs/Phase4_Playtest_Checklist.md` and resolve reported defects first.

Pod/wreck modular/procedural finish is below the fine references; salvage uses
worn basic mesh dressing, Canvas panels are functional UI, suit is still Epic's
mannequin. Symptoms lack new breathing/hallucination audio. The rare immediate
out-of-world cache relocation compiled but has no dedicated runtime test.

Phase5 design direction, when requested: fabricator/crafting, habitat repairs,
power/oxygen/airlock progression, suit/scanner upgrades and additional habitat
modules. These are not implemented yet. Keep typed inventory/save migration
compatible and define costs/unlocks/state in data assets before progression.
Full decoration/cosmetics/hallucinations and additional cruiser rooms/stories
remain later scope; do not silently implement them without the next instruction.
