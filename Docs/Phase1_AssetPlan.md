# Phase 1 asset and validation plan

Inventory inspected 2026-11-10. This is an on-disk snapshot, not a complete Asset Registry, dependency, or license audit.

| Asset group | Provenance and current use |
| --- | --- |
| `/Game/ThirdPerson` | Epic's installed UE 5.8 `Templates/TP_ThirdPersonBP/Content`; imported template character, controller, game mode and example content provide the movement baseline. |
| `/Game/Characters`, `/Game/Input` | Epic's installed `Templates/TemplateResources/High/Characters/Content` and `Input/Content`; mannequin/animation and Enhanced Input dependencies. The template also declares `LevelPrototyping` as a High shared pack; verify dependency closure in the editor and during cook. |
| `/Game/Player/BP_DustfallCharacter`, `/Game/Core/BP_DustfallGameMode` | Project-owned child Blueprints extending the imported character and game mode. |
| `/Game/World`, `/Game/Habitat`, `/Game/Data` | Project foundation map, authored tuning and temporary blockout materials; the map uses the engine Open World template and engine primitives. Habitat is a sealed exterior shell. |
| `/Game/__ExternalActors__`, `/Game/__ExternalObjects__` | Externalized level data associated with project maps; retain with the map. |
| Fab / Quixel | None identified in the project inventory. Phase 2 candidates include terrain surfaces, rocks and debris; select and acquire explicitly. |

The installed First Person Blueprint template is a possible reference; its presence does not establish a project import or a license determination. The installed Epic template files are the provenance of the temporary baseline. Confirm applicable engine and content terms before distribution.

## Provenance on future import

For every imported pack record asset name and project path, creator/publisher, source listing URL or local template path, version, acquisition date/account, license and applicable restrictions, attribution requirements, modifications, and redistribution/package rights. Retain a receipt or license snapshot outside distributable content. Verify the applicable Epic/Fab/Quixel terms for the specific acquisition before use. Use the editor Reference Viewer and a test cook to verify complete dependencies and plugin requirements. Avoid importing unrelated variants or raw marketplace source into distribution.

## Phase 1 verification

PIE smoke report `Saved/Codex/pie_report.json` records a pass on 2026-11-10 for `/Game/World/Maps/L_Dustfall_Foundation` in the dedicated editor. It compiled the template and project player/game mode Blueprints, possessed `BP_DustfallCharacter`, traced ground below the settled pawn, observed one active camera, and walked the pawn into the habitat shell through injected action input. The report observed fog and renderer CVars and found World Partition present. World Settings UI separately showed Enable Streaming checked; the report could not read that protected property.

- [x] Enhanced Input action injection moved and jumped the pawn; the measured jump rose about 128 cm. This exercises action bindings, not physical keys or mapping contexts.
- [x] Callable player events toggled flashlight visibility and camera arm length, and raised then restored sprint speed. These checks do not verify the F, V or Shift keyboard bindings.
- [x] Physically checked viewport focus, F, V, Space, brief movement and mouse look. A short Shift chord did not yield a sustained speed observation; callable runtime events verify sprint behavior. E, Tab and Q are later-system controls.
- [x] Visually inspected both views, flashlight illumination and the warm habitat entrance in dust haze. The Phase 1 entrance is sealed; extended traversal and camera collision coverage remain for later profiling.
- [x] Fresh editor startup loaded the saved foundation map without an explicit map argument, and the full PIE smoke test passed again. A packaged test cook remains unverified.
- [ ] Benchmark representative frame time/FPS on target mid-range hardware, recording resolution and scalability. The 60+ FPS target has not been established by this PIE smoke test.

Future HUD should use clean, minimal amber-on-dark, thin-line sci-fi styling. Hidden Strain must not expose a numeric value; critical suit warnings must remain reliable and accessible. HUD, inventory and survival behavior are outside Phase 1 unless implemented.
