# Phase 4 user playtest

The user requested that heavy validation be left for their playtest on
2026-11-13. These are acceptance checks, not claims that they passed.
Read `Phase4_Validation.md` for the actual build and smoke results.

Start `Builds/Phase4/Windows/Play_DUSTFALL.cmd` (1920x1080 High).

- [ ] Walk the rounded habitat, check the curved hull, damaged panels, interior,
  warm windows and practical lights. Press E near the airlock, enter its
  chamber while the near door is open, wait for pressure cycling, then exit.
  Check both travel directions, doorway obstruction and safe clone spawn.
- [ ] Inspect hills, mounds, jagged outcrops, crater, dry ravine and marked pit.
  Preserve enough oxygen for the return. Check readable hazard rims, east
  pit escape and south ravine escape. Check for floating or buried rocks.
- [ ] Review dusty daylight and settled storms at 40, 60 and 100 metres, in
  first and third person (V), with F flashlight on/off. Review night separately.
- [ ] Q scans nearby salvage and records. E collects a nearby visible node.
  Tab shows typed inventory. Collect several item types and test capacity.
  Salvaged nodes should stay collected after F5, exit, restart and F9.
- [ ] B spends a PowerCell to place a beacon; B near it recovers it and refunds
  the cell. Check world light and HUD guidance, night visibility and reload.
- [ ] Board the crashed transport using its ramp. Walk the cargo aisle and
  recorder alcove. Collect interior supplies and read the manifest record.
  J opens/closes archived lore. Check text legibility and all discovered logs.
- [ ] Die with several item types carried. Confirm a new clone, empty carried
  inventory, the complete crate payload and one-time E recovery. Repeat death
  before recovery and check accumulation. Test fatal falls and reachable
  rim cache placement. Save/restart with an unrecovered crate, then recover.
- [ ] Make a longer expedition and read records. Initial symptoms should be
  brief and subtle, never change critical suit telemetry, and stop at home.
  F8 disables/re-enables symptoms. Check the setting survives restart.
- [ ] Review physical WASD/mouse/Shift/Space/E/F/V/Tab/Q/B/J/F5/F9/F8 controls
  and warning audio. Survival continues while inventory/journal is open.
- [ ] Profile actual packaged traversal and storms at 1080p High. Record median,
  p95/p99, worst hitches, GPU/CPU times and hardware. Check cold startup/PSO
  and streaming hitches separately. Stable 60 FPS is not established.

Optional editor automation: `Scripts/verify_phase3_editor.py`,
`Scripts/verify_phase3_hazards_editor.py`,
`Scripts/verify_layout_persistence.py`, and profiling/capture helpers.
Use one editor writer and isolated QA slots. The layout helper must run before
and after an actual editor restart. Do not treat historical Phase 3 reports
as results for the changed terrain and pod.

Playtest record: date/build commit, hardware, resolution/settings, pass/fail
for each item, reproduction steps and screenshot/log paths for failures.
Leave untested boxes unchecked; report subjective art/audio separately.
