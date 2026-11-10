# DUSTFALL

Blueprint survival exploration prototype for Unreal Engine **5.8.4**. Read
[DUSTFALL_GDD.md](DUSTFALL_GDD.md) for the design and
[DUSTFALL_Codex_Prompt.md](DUSTFALL_Codex_Prompt.md) for the phase plan.

## Run

Open `dustfall.uproject` in UE 5.8.4, open
`/Game/World/Maps/L_Dustfall_Foundation`, and press Play. The foundation map
contains a World Partition landscape, warm dust haze, a collision pad and a
temporary habitat exterior. The habitat is a sealed exterior blockout in Phase 1.

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

Example initial build in PowerShell (adjust the engine installation path):

```powershell
& 'G:/Program Files/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$PWD/dustfall.uproject" -run=pythonscript "-script=$PWD/Scripts/build_phase1.py" -unattended -nullrhi -nosplash
```

Run the play verification in a dedicated editor instance, preserving any unsaved
scene in another instance:

```powershell
& 'G:/Program Files/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' "$PWD/dustfall.uproject" "-ExecCmds=py $PWD/Scripts/verify_phase1_editor.py" -nosplash
```

The verification report is written to `Saved/Codex/pie_report.json`. Action
injection checks Blueprint action bindings; physical keyboard mappings require
separate validation. `Saved`, `Intermediate`, caches and local reports are ignored
by Git. See `Docs/Phase1_AssetPlan.md` for asset provenance and the acquisition plan.
See `PROGRESS.md` for completed checks and remaining validation limits.

## Next phase

Phase 2 develops the world and atmosphere: Fab / Quixel Megascans terrain,
rocks and debris, weather and dust storms, day/night lighting, wreck / cruiser /
ruin landmarks, ambience, and streaming/performance profiling.
