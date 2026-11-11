# Phase 2 acceptance playtest

Build: `G:\ue\dustfall\Builds\Phase2\Windows\Play_DUSTFALL.cmd`.
This launches the Development build at 1920×1080, High, 100% render scale,
without dynamic resolution, VSync or a frame cap. Keep the entire Windows folder
intact. Close Unreal Editor for performance testing. Exit with Alt+F4.
Rebuild with `Scripts/package_phase2.ps1` if saved game assets change.

Controls: WASD movement, mouse look, Space jump, hold Left Shift sprint,
F flashlight, V first/third person. Click the game if input is unfocused.

Spend at least 12–15 minutes in normal time. Start is late afternoon in haze;
sunset begins about three minutes later. The first automatic storm begins about
seven minutes after starting and lasts about one minute, with eased transitions.
A complete day takes 30 minutes. These are default timings, not a loading screen.

Record PASS / FAIL / NOT TESTED beside each item:

- [ ] Launch reaches the exterior home spawn with correct materials and no error dialog.
- [ ] Walk, look, jump and sustained Shift sprint work in both camera views.
- [ ] F illuminates nearby ground in both views; camera switching stays usable near rocks.
- [ ] Leave the landing pad, then return using its approach ramp without catching on the edge.
- [ ] Follow the marked routes toward wreck (+150 m, +100 m), ruin (+350 m, −250 m)
      and cruiser (−550 m, +50 m), relative to home. Check each exterior and return home.
- [ ] No floating rocks, exposed scan pivots, collision traps, missing textures or obvious
      streaming holes appear along these routes. Small scatter is deliberately nonblocking.
- [ ] Sunset/night feels oppressive, but flashlight ground detail and the nearby warm
      entrance light remain useful. Record the location if returning home becomes unreadable.
- [ ] Calm/haze/storm blend smoothly. Storm substantially obscures distance, then clears;
      no permanent world alteration remains after it ends.
- [ ] Wind plays continuously, strengthens with storms and has no distracting loop pop,
      clipping or excessive volume. This listening review still needs human acceptance.
- [ ] Note stutters when approaching landmarks, turning quickly or entering a storm.
      Record resolution/settings/hardware and frame-time observations; use the Development
      console (`~`) with `stat fps` and `stat unit` if available.
- [ ] Exit and relaunch: spawn, landscape and scattered layout remain consistent.
- [ ] Optional: observe a full 30-minute day and a second storm, including night travel.

Expected scope: landmarks and habitat are sealed exterior prototypes. There is no
oxygen/power/stamina HUD, inventory, interactable loot, airlock, death or respawn yet.
Those absences are not Phase 2 regressions. Distant home visibility is intentionally
limited by dust; report whether the local return approach remains practical.

## Results to paste into the next chat

```text
Phase 2 build tested: [date / Git commit from HANDOFF_Phase3.md or git rev-parse HEAD]
Machine: [CPU / GPU / RAM], resolution: [...], settings: [...]
Checklist: [item-by-item PASS / FAIL / NOT TESTED]
Visual/night/storm feedback: [...]
Audio feedback: [...]
Performance and stutters: [location, weather, view, frame time/FPS]
Bug: [steps, expected, actual, location, elapsed time, camera, weather]
Evidence: [screenshots and logs]
Accept Phase 2 / fix these issues first: [...]
```

Packaged logs normally live in the build's `dustfall\Saved\Logs` directory;
if absent, check `%LOCALAPPDATA%\dustfall\Saved\Logs`. Attach the latest log for
a startup failure. Raw profiler CSVs are local artifacts, not tracked game content.

For the next agent's editor QA only, start PIE and run
`Scripts/preview_phase2_editor.py` with `WEATHER=0/1/2`, `TIME=0..1` and optional
`SNAP=True` via Python `runpy.run_path(..., init_globals={...})`. It only changes
PIE instances. SNAP checks appearance, not transition behavior. The packaged
playtest should still observe natural transitions at normal time.
