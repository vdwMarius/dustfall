# DUSTFALL — Phase 4 review build handoff

Current continuation: [HANDOFF_Phase5.md](HANDOFF_Phase5.md). The contracts
below describe the Phase4 review build; repository delivery now uses main only.

Updated 2026-11-13. Workspace `G:\ue\dustfall`, branch
`codex/phase3-survival-and-pcg`, UE 5.8.4. Read this before the historical
`HANDOFF_Phase3.md`. Preserve unrelated user imports `Content/Megascans_8k/`
and `Content/Megascans_RockyGrass_Source.zip`; they are excluded from the module.
No reset/revert of the initial uncommitted Phase 3 work was performed.

The combined implementation was originally committed locally as `0fdd58b`.
That unpublished branch is preserved. The user's new delivery instruction is
to split Phase3, Phase4 and documentation on main and push main only to the
configured repository above. Earlier feature-branch push attempts were blocked
and never uploaded. Leave the unrelated imports above untracked.

## User's latest testing instruction

The user explicitly asked to leave heavy testing for them to save usage and
to use no model effort above medium. Full regressions, traversal stress,
final editor/game restart and cooked-layout persistence, 40/60/100m in both
views/weather, subjective art/audio/physical-key acceptance and performance
profiling are deferred, not passed. Do not automatically rerun expensive
suites next chat. `Docs/Phase4_Playtest_Checklist.md` is ready for the user.

## Implemented and saved

- Rounded custom industrial pod: eleven generated/imported meshes, curved
  hull/panels/liner/ribs/endcaps, inset warm windows, damaged plating, repair
  patches, dust/rust/chips, solar/antenna, retained furnished interior and
  airlock/sanctuary/spawn contract. Oversized old landing slab removed.
  Procedural surface finish still falls short of fine hero reference art.
- Real landscape relief across 256 components/4,068,289 vertices; 3,360,817
  samples changed. Authored height delta -12.37..+61m; measured nearby hill
  24.71m, north ridge 48.24m, pit -8.52m, ravine -8.16m, crater -7.32m.
  217 route collision probes retained near-level protected routes. Added
  64 scanned rocky outcrops, seven amber rim stakes, east pit/south ravine
  escape slopes. Actual escape/fall/recovery traversal awaits user testing.
- Rebuilt native terrain-aware PCG: 64 cells, 71,682 rocks, 364 dust sheets,
  195 decorative debris instances. Nanite/Lumen/World Partition retained.
  Exact original landscape baseline: `Scripts/Data/Phase3LandscapeBaseline.bin`.
- Native impact hazard director damages suit on hard landings and relocates
  fatal fall caches to the last grounded rim; out-of-world respawn now
  relocates before exploration saves. Final C++ build passed; this rare edge
  has not received a dedicated runtime test.
- Native Phase 4 exploration: 12 stable salvage/lore nodes (four records),
  capacity-limited typed inventory, complete accumulating recovery payload,
  scanner, persistent glowing physical beacons with PowerCell cost/refund,
  reliable home guidance, inventory/journal HUD, temporary private Strain
  symptoms and F8 accessibility toggle. Exterior/storm/low-suit/death/lore
  strain sources are tunable; sanctuary stops symptoms and reduces strain.
- Accessible crashed transport cargo deck/recorder alcove replaces the old
  transport blockout; original cruiser/ruin remain. Nine ground probes and
  seven static capsule sweeps pass after a 10cm ramp lip correction.
- Save slot remains `Dustfall_Phase3`; authoritative schema-2 full snapshot
  companion `Dustfall_Phase3_Exploration` stores suit, typed inventories,
  world claims, records, beacons and private Strain. Missing companion migrates
  schema-1 scalar scrap. Do not remove either user's save file.

## Actual validation

Final native editor compilation passed. Brief isolated PIE smoke passed all
19 checks, including real legacy save/load, scalar migration, world salvage/
lore, scanner, beacon/refund, lit crate, typed death/recovery/no duplicate,
full snapshot reload and symptom disable. `Docs/Phase4_SmokeResults.json` and
`Docs/Phase4_HUDSmoke.png` preserve evidence. Callable smoke is not physical
keyboard acceptance or a restart/persistence test. QA slots were removed and
the authored slot restored. Editor was saved and closed; no writer lease remains.

Phase 3 preliminary Windows package built and passed a 600-frame isolated
startup/clean-exit smoke, but its cook exposed the old Blueprint
DoesSaveGameExist execution-pin bug. That graph was repaired and actual
legacy load retested successfully before Phase 4. The preliminary Phase 3
artifact predates this fix; use Phase 4 for playtesting.

Final Phase 4 cook passed with zero errors and zero warnings. Final archive
and packaged startup smoke are recorded in `Docs/Phase4_Validation.md`.

## Run and continue

Current launcher: `Builds/Phase4/Windows/Play_DUSTFALL.cmd`; keep its complete
Windows folder. Controls are in README. Full playtest checklist is under Docs.

Use exactly one asset writer. Compile native editor code with the editor closed.
Use `Scripts/editor_session.py` queue host for authoring. Full Phase 3 builder
now sequences habitat/survival/HUD/climate, terrain, core PCG and debris. After
it, run `build_phase4_wreck.py`, then `build_phase4.py` to restore Phase 4.
`repair_phase3_load.py` is the narrow execution-link repair, also fixed in the
repeatable survival builder. Never run old world reset builders over this work.

Package with `Scripts/package_phase4.ps1`; `smoke_packaged.ps1 -Phase Phase4`
uses an isolated UserDir and automatic exit. Native game needs no Python.

Limits: initial Strain symptoms are comms carrier text and transient scanner
echo, without new breathing/hallucination audio. Native Canvas UI and salvage/
wreck dressing are review-build presentation; suit remains the Epic mannequin.
Full cruiser rooms, crafting/upgrades/decoration, cosmetics, broad psychological
events and polished menus remain later phases. Stable 60 FPS is unproven.
