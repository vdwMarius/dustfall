# DUSTFALL

Blueprint and C++ survival exploration prototype for Unreal Engine **5.8.4**. Read
[DUSTFALL_GDD.md](DUSTFALL_GDD.md) for the design and
[DUSTFALL_Codex_Prompt.md](DUSTFALL_Codex_Prompt.md) for the phase plan.

## Run

Open `dustfall.uproject` in UE 5.8.4, open
`/Game/World/Maps/L_Dustfall_Foundation`, and press Play. The foundation map
contains a 2 km World Partition landscape, licensed Quixel sand/gravel/rock
surfaces, instanced scanned rocks, exterior wreck/ruin/cruiser landmarks, wind,
and runtime weather and day/night. Phase 3 adds a furnished walkable habitat,
interlocked airlock, suit resources, clone respawn, recovery cache and save/load.
Current content also includes a rounded industrial pod, real hills/ravines/pit,
scavenging, typed inventory, scanner, beacons, lore and an accessible transport
deck. Read [the current handoff](HANDOFF_Phase5.md) and
[validation](Docs/Phase4_Validation.md) for actual results and limitations.

| Control | Action |
| --- | --- |
| WASD | Move |
| Mouse | Look |
| Space | Jump |
| Left Shift | Hold to sprint |
| V | Switch third / first person |
| F | Toggle flashlight |
| E | Airlock / salvage / read record / recover death crate |
| Q | Pulse scanner |
| Tab / J | Inventory / lore journal (survival continues) |
| B | Place beacon for one PowerCell / retrieve nearby beacon with refund |
| F5 / F9 | Save / load complete progress |
| F8 | Disable / enable subtle Strain symptoms |
| Escape | Stop editor play |

Run `Builds/Phase4/Windows/Play_DUSTFALL.cmd` for the current Windows review
build at 1920x1080 High. Keep the complete Windows folder. Alt+F4 exits.
Rebuild with `Scripts/package_phase4.ps1` while the editor is closed.
Crafting, habitat progression, cosmetics and full hallucination/audio systems
remain later work. The user deferred heavy validation; use
[the playtest checklist](Docs/Phase4_Playtest_Checklist.md).

## Phase 3

Rounded custom pod geometry and actual landscape relief are now saved.
Heavy gameplay/hazard regressions, final reload/cooked persistence, visual and
performance acceptance remain deferred to the user. Historical Phase 3 tests
predate these art/terrain changes. The preliminary Phase 3 package starts and
exits cleanly but predates a save-load graph repair; use the corrected Phase 4
build for playtesting. Phase 2 packages are historical.
See [the Phase 3 plan](Docs/Phase3_Plan.md), [habitat contract](Docs/Phase3_Habitat.md)
and [survival contract](Docs/Phase3_Survival.md) for scope and tuning.

Start inside the habitat. Press E near the airlock to begin its cycle: enter
the chamber while the near door is open, wait for sealing, then pass through
the far door. The cycle pauses if a doorway is occupied. Oxygen and power
refill in the sanctuary and drain outside. Sprinting consumes stamina, storms
wear suit integrity, and depleted power shuts down the flashlight. Oxygen or
integrity failure respawns a new clone at home with a recoverable cache outside.

Runtime tuning lives in `/Game/Data/DA_Survival_Phase3` and
`/Game/Data/DA_Environment_Phase2`. Saves use the `Dustfall_Phase3` slot in the
running game's Saved/SaveGames folder. Development verification uses isolated
QA slots. F5 saves immediately; periodic autosave and death/recovery save as well.
Phase 4 keeps a schema-2 full snapshot in `Dustfall_Phase3_Exploration`, including
typed carried/cache inventory, claimed salvage, beacons, journal and private
Strain. Missing companion saves migrate the schema-1 scalar scrap payload.

Use `Scripts/build_phase3.py` in the sole editor for a clean full rebuild;
individual module builders are available for narrower changes. PCG generation
finishes asynchronously: check `Saved/Codex/phase3_build.json` before proceeding.
Run `Scripts/verify_phase3_editor.py` for serial runtime regressions. These
checks do not establish physical-key, final-art or target-hardware acceptance.

## Authoring

After a full Phase 3 rebuild, run `build_phase4_wreck.py` then `build_phase4.py`
in the same sole writer to restore the Phase 4 actors and native HUD. Read
`Docs/Phase4_Exploration.md`; do not use the legacy world-reset builders on
current content. `smoke_phase4_editor.py` is a short isolated callable check.

The `Source/dustfall` C++ runtime module supplies core resource integration,
sanctuary boundaries and sprint exhaustion rules to gameplay Blueprints. Data
assets control tuning; Blueprints handle presentation and orchestration. Python
is used only to author and verify assets in the editor and is not needed to play.
The third-person template assets keep their original paths so mannequin and
Enhanced Input dependencies resolve.

Compile `dustfallEditor Win64 Development` with Unreal's `Build.bat` after changing
C++ headers or source, with the authoring editor closed. The game and editor
targets are tracked under `Source/`. Native automation tests are under
`Dustfall.Core`; run them before the Phase 3 PIE suite after core rule changes.

The historical `/Game/Data/DA_Atmosphere_Phase1` and
`/Game/Data/DA_PlayerFoundation_Phase1` apply at authoring time, not during play.
Current climate uses the runtime environment data described above. Use Phase 3
builders for current world content. `Scripts/build_environment.py` delegates to
the Phase 2 director builder; it does not build the new habitat. Run
`Scripts/build_player.py` only when changing foundation player tuning. Its generated graph
nodes occupy reserved coordinates; keep manual nodes outside that area or extend
the project-owned `/Game/Player/BP_DustfallCharacter` child Blueprint. The
GameMode extension point is `/Game/Core/BP_DustfallGameMode`.

Close other editors that have project assets loaded before running a commandlet
build. Alternatively, run the scripts inside one dedicated editor using
`Scripts/editor_session.py`; its local queue is `Saved/Codex/editor_command.py`.

Historical Phase 1 initial build for a fresh project only (existing Phase 2
projects deliberately reject this reset; use the Phase 2 modules below):

```powershell
& 'G:/Program Files/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$PWD/dustfall.uproject" -run=pythonscript "-script=$PWD/Scripts/build_phase1.py" -unattended -nullrhi -nosplash
```

Prefer running verification through the command queue in the open editor.
If no editor is open, start one dedicated session; do not open a second writer
against loaded project assets:

```powershell
& 'G:/Program Files/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' "$PWD/dustfall.uproject" "-ExecCmds=py $PWD/Scripts/verify_phase1_editor.py" -nosplash
```

The verification report is written to `Saved/Codex/pie_report.json`. Action
injection checks Blueprint action bindings; physical keyboard mappings require
separate validation. `Saved`, `Intermediate`, caches and local reports are ignored
by Git. See `Docs/Phase1_AssetPlan.md` for asset provenance and the acquisition plan.
See `PROGRESS.md` for completed checks and remaining validation limits.

## Historical Phase 2 authoring and runtime

Use one editor with the foundation map and landscape cells loaded. Run
`Scripts/build_phase2.py` for the complete repeatable build, after resolving any
existing dirty packages. It never rebuilds player graphs. Source downloads stay
in ignored `Saved/AssetInbox/Quixel`; the twenty-asset import is incremental.
Imported game assets live under `/Game/World/QuixelPhase2`. Preserve unrelated Fab
imports and original Epic template paths. See `Docs/Phase2_AssetManifest.json`
for source archive hashes, names and imported paths.

Individual modules are `import_phase2_quixel.py`, `build_phase2_landmarks.py`,
`build_phase2_routes.py`, `build_phase2_wasteland.py`, `build_phase2_debris.py`,
`build_phase2_audio.py` and `build_phase2_environment.py`. Save changed external
actor/component packages as well as the map. The legacy `build_environment.py`
now dispatches to Phase 2 atmosphere; Phase 1 full/world rebuilds refuse to reset
an established Phase 2 project.

`/Game/World/Blueprints/BP_DustfallEnvironmentDirector` runs entirely in Blueprint.
`/Game/Data/DA_Environment_Phase2` is read at runtime, unlike the Phase 1 assets.
It tunes fog densities, blend speed, day length, weather durations, sun/skylight,
wind volume and fog color. The default day lasts 30 minutes and starts in late
afternoon. Weather cycles haze → calm → haze → storm → haze; blends are eased
over roughly 30 seconds rather than abrupt swaps.

Blueprint controls: `SetWeather(Value)` (0 calm, 1 haze, 2 storm),
`SetTimeOfDay(Value)` (0 midnight, .25 sunrise, .5 noon, .75 sunset), and
`GetEnvironmentState()` (weather, time, normalized storm intensity).
`OnEnvironmentChanged` fires after each environment update; listeners query
the current state. Manual weather changes reset the weather age. These neutral
signals are extension points; they do not drain stats or implement Strain.

Run `Scripts/verify_phase2_editor.py` for runtime clock, weather/fog, lighting,
wind, automatic transition, query and movement checks. It takes about two minutes
because it waits for real weather blends. Run `Scripts/verify_phase1_editor.py`
for player regression checks. Reports remain under ignored `Saved/Codex`.
See PROGRESS.md for actual test results and outstanding checks.

## Historical Phase 2 playtest build and handoff

Run `G:\ue\dustfall\Builds\Phase2\Windows\Play_DUSTFALL.cmd` for the packaged
Windows Development build at 1920×1080 High. Keep its complete Windows folder.
Use Alt+F4 to exit. Close the editor before performance testing. Reproduce the
build with `Scripts/package_phase2.ps1`; local `Builds` output is ignored by Git.

Follow [the acceptance checklist](Docs/Phase2_Playtest_Checklist.md) and give its
results to the next chat together with [HANDOFF_Phase3.md](HANDOFF_Phase3.md).
The handoff records asset/runtime contracts, editor precautions and Phase 3 scope.
See [validation evidence](Docs/Phase2_Validation.md) for measured results and limits;
representative mid-range stable 60+ FPS and human audio/readability acceptance
remain unverified. Final storm density is 1.0, with an eased transition.

Landmarks are closed exterior prototypes, with non-interactive scanned debris.
Home remains the warm sanctuary landmark. Habitat interior/airlock, survival
stats, death/respawn and inventory remain later-phase work.
