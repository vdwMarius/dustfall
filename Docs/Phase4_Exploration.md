# Phase 4 exploration runtime

Native runtime source: `DustfallExploration`, `DustfallExplorationHUD` and
`DustfallTerrainHazardDirector`. Author `Scripts/build_phase4_wreck.py` then
`Scripts/build_phase4.py` after compiling/restarting the editor. Python is an
authoring/verification tool, never a packaged gameplay dependency.

The existing Blueprint suit director remains responsible for suit stats,
airlock, clone spawning and cache presentation. Native exploration holds typed
Scrap, Wiring, Glass, Polymer, PowerCell and AlienFragment inventory, authored
stable salvage/record IDs, a journal, scanner, placed beacons and hidden Strain.
New salvage respects an 80-item capacity. Recovering owned death payload may
exceed capacity so it cannot discard player property. Repeated deaths accumulate
unrecovered typed payload at the current cache. Cached inventory transfers once.

Save schema 2 stores one full exploration/suit snapshot in
`<survival SaveSlotName>_Exploration`; absent companion saves migrate schema-1
carried/cached scalar scrap. Existing Phase3 saves remain readable. Invalid or
unsupported snapshots leave current session state intact. F9 restores the
complete snapshot after the original suit Blueprint load. F5 and exploration
autosave update both the native snapshot and legacy suit state. Autosave is
synchronous every 30 seconds; larger later inventories should use asynchronous
I/O. First-load position collision/streaming safety remains a validation item.

Controls: E interacts/retrieves cache, Q scanner (2 power, 140 m range, 7-second
reveal, 8-second cooldown), Tab inventory grid, J archived records, B places a
beacon using one PowerCell or retrieves a nearby beacon with cell refund,
F8 toggles subtle symptoms and persists the accessibility choice. Beacons rebuild
nonblocking emissive amber posts with local shadow-free lights from saved marker
positions, and remove those props on retrieval. Existing
WASD/mouse, Shift/Space, F flashlight, V camera, F5/F9 controls remain.
Reading/inventory do not pause survival. Home guidance is always reliable.

Strain stays private. Exterior time, storm intensity, low suit resources, deaths and selected
records increase it; habitat sanctuary lowers it. Only a brief carrier-overlap
message and temporary unresolved scanner echo currently express symptoms.
Symptoms expire, stop in sanctuary and can be disabled. Critical suit warnings
and actual suit readings remain reliable. Full hallucinations/audio layering,
crafting/upgrades, equippable cosmetics and full cruiser interiors are later
scope.

Terrain hazard director applies collision-driven fall damage above 1050 cm/s,
with .065 integrity per excess cm/s. Fatal falls move the crate to the last
safe grounded rim and refresh/save cache presentation, protecting recovery.
Large falls below the collision world trigger clone recovery. Terrain hazard
and exploration directors must be always loaded; exploration ticks after hazard
relocation to save the corrected cache location.

Validation: native modules compiled successfully, Phase4 assets authored, and the
brief callable PIE smoke passed all 19 checks. `Phase4_SmokeResults.json` records
legacy suit SaveProgress/LoadProgress restoration after the execution-link repair,
schema1 scalar migration (2 carried/3 cached Scrap), actual world salvage/record
interaction, capacity rejection, scanner power cost, beacon placement/refund,
visible/lit recovery cache, typed death/recovery without duplication, full native
snapshot restore and symptom disabling. This is a brief functional smoke, not
physical keyboard validation. `Phase4_HUDSmoke.png` is one actual 1495x862 PIE
viewport screenshot with normal texture residency, showing native suit HUD,
home guidance and typed inventory. No representative performance claim follows.

The existing LoadProgress Blueprint had an unconnected execution input on
DoesSaveGameExist. `Scripts/repair_phase3_load.py` corrected the current graph,
and the original builder now wires execution before reading the return value.
The saved graph compiled with zero graph errors; actual save/load restored
Oxygen from an edited 21 back to the saved 67 during the smoke.

Full regression, fresh-process/cooked persistence, physical-key/audio/visual
acceptance and performance testing remain deferred to the user per latest
direction. `Scripts/smoke_phase4_editor.py` uses isolated
`Dustfall_Phase4_BriefQA` slots and cleans them after PIE. Final packaged smoke
and final hazard edge-case compilation are integration responsibilities.
