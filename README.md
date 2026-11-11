# DUSTFALL

Blueprint survival exploration prototype for Unreal Engine **5.8.4**. Read
[DUSTFALL_GDD.md](DUSTFALL_GDD.md) for the design and
[DUSTFALL_Codex_Prompt.md](DUSTFALL_Codex_Prompt.md) for the phase plan.

## Run

Open `dustfall.uproject` in UE 5.8.4, open
`/Game/World/Maps/L_Dustfall_Foundation`, and press Play. The foundation map
contains a 2 km World Partition landscape, licensed Quixel sand/gravel/rock
surfaces, instanced scanned rocks, exterior wreck/ruin/cruiser landmarks, wind,
and runtime weather and day/night. The habitat remains a sealed exterior blockout.

| Control | Action |
| --- | --- |
| WASD | Move |
| Mouse | Look |
| Space | Jump |
| Left Shift | Hold to sprint |
| V | Switch third / first person |
| F | Toggle flashlight |
| Escape | Stop editor play |

Inventory, scanner, interaction, oxygen and Strain arrive in later phases.

## Authoring

Gameplay is stored in Blueprint assets; Python is used only to author and verify
assets in the editor. No native game module or Python runtime is required to play.
The third-person template assets keep their original paths so mannequin and
Enhanced Input dependencies resolve.

The tuning assets are `/Game/Data/DA_Atmosphere_Phase1` and
`/Game/Data/DA_PlayerFoundation_Phase1`. These Phase 1 authoring assets apply their
values when the corresponding build script runs; they do not hot-reload in play.
After changing its values, run `Scripts/build_environment.py` through Unreal's
Python editor console to reapply the environment. This rebuilds only the tagged
foundation pad and habitat blockout. It preserves the map and existing tuning
values. Run `Scripts/build_player.py` to reapply player tuning. Its generated graph
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

## Phase 2 authoring and runtime

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

## Phase 2 playtest build and handoff

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
